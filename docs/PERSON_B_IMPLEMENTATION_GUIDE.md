# Person B Implementation Guide: Workflow Router

## Overview

You are responsible for implementing the workflow routing layer that takes validated input and determines how it should be processed. Your code will configure the entire pipeline based on the analysis type (tumor-only vs tumor-normal) and cancer type, setting knowledge base priorities, evidence weights, and processing parameters.

## Your Deliverables

### 1. Core Module: `workflow_router.py`
- Rename `workflow_router_stub.py` to `workflow_router.py`
- Implement all methods marked with `NotImplementedError`
- Follow the `WorkflowRouterProtocol` interface exactly

### 2. Configuration Files
- Create `config/workflow_settings.yaml` with workflow definitions
- Create `config/kb_priorities.yaml` with KB configurations per cancer type
- Create `config/ga4gh_endpoints.yaml` for external service endpoints

### 3. Update Existing Modules
- Modify `evidence_aggregator.py` to accept `WorkflowContext`
- Modify `tiering.py` to use workflow-specific rules
- Ensure changes are backward compatible

## Key Implementation Details

### Workflow Configuration Structure

Create `config/workflow_settings.yaml`:

```yaml
# Workflow definitions
workflows:
  tumor_only_default:
    description: "Default tumor-only workflow"
    kb_priorities:
      - source: oncokb
        weight: 1.2
        enabled: true
        min_evidence_level: "3B"
      - source: civic  
        weight: 1.0
        enabled: true
      - source: cosmic
        weight: 0.9
        enabled: true
      - source: clinvar
        weight: 0.8
        enabled: true
      - source: gnomad
        weight: 0.5  # Lower weight for germline DB
        enabled: true
    thresholds:
      min_tumor_vaf: 0.05
      min_coverage: 20
      min_alt_reads: 4
      population_af_threshold: 0.01
    processing:
      require_somatic_evidence: false  # Can't require for tumor-only
      penalize_germline_evidence: true
      boost_hotspot_variants: true
      
  tumor_normal_default:
    description: "Default tumor-normal workflow"
    kb_priorities:
      - source: oncokb
        weight: 1.5  # Higher weight when we're confident it's somatic
        enabled: true
      - source: civic
        weight: 1.2
        enabled: true
      - source: cosmic
        weight: 1.0
        enabled: true
      - source: clinvar
        weight: 0.5  # Lower weight in T/N since we filter germline
        enabled: true
    thresholds:
      min_tumor_vaf: 0.02  # Can go lower with normal
      min_normal_vaf: 0.02  # For filtering
      min_coverage: 20
      min_alt_reads: 4
    processing:
      require_somatic_evidence: true
      penalize_germline_evidence: false  # Already filtered
      boost_hotspot_variants: true

# Cancer-specific overrides
cancer_specific:
  SKCM:  # Melanoma
    tumor_only:
      kb_priorities:
        - source: oncokb
          weight: 1.5  # Boost OncoKB for melanoma
        - source: cosmic
          weight: 1.2  # COSMIC very good for melanoma
      thresholds:
        min_tumor_vaf: 0.02  # Lower VAF for subclonal BRAF
        
  LUAD:  # Lung adenocarcinoma  
    tumor_only:
      kb_priorities:
        - source: oncokb
          weight: 1.3
        - source: civic
          weight: 1.1  # CIViC strong for lung
      processing:
        check_signatures: true  # Smoking signature
```

### Main Router Implementation

```python
class WorkflowRouter(WorkflowRouterProtocol):
    
    def __init__(self, config_path: Optional[str] = None):
        config_path = config_path or "config/workflow_settings.yaml"
        self.config = self._load_config(config_path)
        self.kb_priorities_config = self._load_kb_priorities()
        
    def route(self, validated_input: ValidatedInput) -> WorkflowContext:
        """
        Main routing logic
        """
        # 1. Determine analysis type
        analysis_type = self.determine_analysis_type(validated_input)
        
        # 2. Get base workflow
        base_workflow_key = f"{analysis_type.value}_default"
        base_config = self.config["workflows"][base_workflow_key]
        
        # 3. Apply cancer-specific overrides
        cancer_type = validated_input.patient.cancer_type
        if cancer_type in self.config.get("cancer_specific", {}):
            cancer_config = self.config["cancer_specific"][cancer_type]
            workflow_specific = cancer_config.get(analysis_type.value, {})
            base_config = self._merge_configs(base_config, workflow_specific)
        
        # 4. Build workflow configuration
        workflow_config = self._build_workflow_configuration(base_config)
        
        # 5. Create workflow route
        route = WorkflowRoute(
            analysis_type=analysis_type,
            workflow_name=f"{analysis_type.value}_{cancer_type}",
            configuration=workflow_config,
            processing_steps=self._get_processing_steps(analysis_type),
            filter_config=self._build_filter_config(analysis_type, workflow_config),
            aggregator_config=self._build_aggregator_config(workflow_config),
            tiering_config=self._build_tiering_config(workflow_config),
            output_formats=validated_input.requested_outputs,
            include_filtered_variants=False,
            include_germline_findings=(analysis_type == AnalysisType.TUMOR_ONLY)
        )
        
        # 6. Create context
        return WorkflowContext(
            validated_input=validated_input,
            route=route,
            execution_id=str(uuid.uuid4()),
            start_time=datetime.utcnow().isoformat(),
            enable_caching=True,
            cache_namespace=f"{cancer_type}_{analysis_type.value}"
        )
```

### Knowledge Base Priority Configuration

```python
def _build_workflow_configuration(self, config_dict: Dict) -> WorkflowConfiguration:
    """
    Build WorkflowConfiguration from config dictionary
    """
    # Parse KB priorities
    kb_priorities = []
    for kb_config in config_dict.get("kb_priorities", []):
        kb_priorities.append(KnowledgeBasePriority(
            source=EvidenceSource(kb_config["source"]),
            weight=kb_config.get("weight", 1.0),
            enabled=kb_config.get("enabled", True),
            min_evidence_level=kb_config.get("min_evidence_level")
        ))
    
    # Parse thresholds
    thresholds = config_dict.get("thresholds", {})
    
    # Parse processing flags
    processing = config_dict.get("processing", {})
    
    return WorkflowConfiguration(
        kb_priorities=kb_priorities,
        min_tumor_vaf=thresholds.get("min_tumor_vaf", 0.05),
        min_normal_vaf=thresholds.get("min_normal_vaf", 0.02),
        evidence_weight_multipliers=self._get_evidence_multipliers(config_dict),
        min_coverage=thresholds.get("min_coverage", 20),
        min_alt_reads=thresholds.get("min_alt_reads", 4),
        population_af_threshold=thresholds.get("population_af_threshold", 0.01),
        require_somatic_evidence=processing.get("require_somatic_evidence", False),
        penalize_germline_evidence=processing.get("penalize_germline_evidence", True),
        boost_hotspot_variants=processing.get("boost_hotspot_variants", True),
        check_signatures=processing.get("check_signatures", False),
        infer_clonality=processing.get("infer_clonality", False)
    )
```

### Processing Steps Definition

```python
def _get_processing_steps(self, analysis_type: AnalysisType) -> List[str]:
    """
    Define ordered processing steps for each workflow
    """
    if analysis_type == AnalysisType.TUMOR_NORMAL:
        return [
            "validate_pairing",          # Ensure samples are paired correctly
            "tumor_normal_filtering",    # Subtract normal variants
            "vep_annotation",           # Run VEP
            "evidence_aggregation",     # Collect evidence from KBs
            "somatic_classification",   # DSC scoring
            "tier_assignment",          # Assign tiers
            "ga4gh_processing",         # VRS IDs, VICC queries
            "output_generation"         # Format outputs
        ]
    else:  # TUMOR_ONLY
        return [
            "population_filtering",     # Filter common variants
            "vep_annotation",          # Run VEP
            "evidence_aggregation",    # Collect evidence from KBs
            "germline_filtering",      # Additional germline filtering
            "somatic_classification",  # DSC scoring (lower confidence)
            "tier_assignment",         # Assign tiers
            "ga4gh_processing",        # VRS IDs, VICC queries
            "output_generation"        # Format outputs
        ]
```

### Evidence Aggregator Integration

Update `evidence_aggregator.py`:

```python
class EvidenceAggregator:
    """
    Your existing aggregator class - add workflow awareness
    """
    
    def aggregate_evidence(self, 
                          variant: VariantAnnotation,
                          workflow_context: Optional[WorkflowContext] = None) -> List[Evidence]:
        """
        Updated method that respects workflow configuration
        """
        if workflow_context is None:
            # Backward compatibility - use default behavior
            return self._aggregate_evidence_legacy(variant)
        
        # Get KB priorities from workflow
        kb_priorities = workflow_context.route.configuration.kb_priorities
        
        all_evidence = []
        
        # Process KBs in priority order
        for kb_config in kb_priorities:
            if not kb_config.enabled:
                continue
                
            # Get evidence from this source
            if kb_config.source == EvidenceSource.ONCOKB:
                evidence = self._get_oncokb_evidence(variant)
            elif kb_config.source == EvidenceSource.CIVIC:
                evidence = self._get_civic_evidence(variant)
            elif kb_config.source == EvidenceSource.CLINVAR:
                evidence = self._get_clinvar_evidence(variant)
            # ... other sources
            
            # Apply weight multiplier
            for e in evidence:
                e.score = int(e.score * kb_config.weight)
                
                # Apply minimum evidence level filter
                if kb_config.min_evidence_level:
                    if not self._meets_min_level(e, kb_config.min_evidence_level):
                        continue
                        
                all_evidence.append(e)
        
        return all_evidence
```

### Tiering Integration

Update `tiering.py`:

```python
class TieringEngine:
    """
    Your existing tiering class - add workflow awareness
    """
    
    def assign_tier(self,
                   variant: VariantAnnotation,
                   evidence_list: List[Evidence],
                   workflow_context: Optional[WorkflowContext] = None) -> TierResult:
        """
        Updated method that respects workflow configuration
        """
        if workflow_context is None:
            # Backward compatibility
            return self._assign_tier_legacy(variant, evidence_list)
        
        config = workflow_context.route.configuration
        
        # Apply workflow-specific filtering
        if config.require_somatic_evidence:
            evidence_list = [e for e in evidence_list 
                           if self._is_somatic_evidence(e)]
        
        # Apply hotspot boosting
        if config.boost_hotspot_variants and self._is_hotspot(variant):
            for e in evidence_list:
                e.score = int(e.score * 1.5)
        
        # Apply germline penalty
        if config.penalize_germline_evidence:
            for e in evidence_list:
                if self._is_germline_evidence(e):
                    e.score = int(e.score * 0.5)
        
        # Continue with normal tiering
        return self._calculate_tier(variant, evidence_list)
```

## Configuration Management

### Create Configuration Loader

```python
class ConfigurationManager:
    """
    Manages workflow configurations with validation and caching
    """
    
    def __init__(self, config_dir: Path = Path("config")):
        self.config_dir = config_dir
        self._cache = {}
        
    def load_workflow_config(self, name: str) -> Dict:
        """Load and validate workflow configuration"""
        if name in self._cache:
            return self._cache[name]
            
        config_path = self.config_dir / f"{name}.yaml"
        if not config_path.exists():
            raise ValueError(f"Configuration not found: {name}")
            
        with open(config_path) as f:
            config = yaml.safe_load(f)
            
        # Validate configuration
        self._validate_config(config)
        
        self._cache[name] = config
        return config
        
    def _validate_config(self, config: Dict):
        """Validate configuration structure"""
        required_fields = ["workflows", "kb_priorities", "thresholds"]
        # Add validation logic
```

## Integration Points

### From Input Validator (Person A)

You receive a `ValidatedInput` object:

```python
@dataclass 
class ValidatedInput:
    tumor_vcf: ValidatedVCF
    normal_vcf: Optional[ValidatedVCF]
    patient: PatientContext
    analysis_type: str
    # ... other fields
```

### To Downstream Components

You provide a `WorkflowContext` object that contains:

1. **For Filtering**: `context.route.filter_config`
2. **For Evidence Aggregation**: `context.route.aggregator_config`
3. **For Tiering**: `context.route.tiering_config`
4. **For Output**: `context.route.output_formats`

## Testing Your Implementation

Create comprehensive tests in `tests/test_workflow_router.py`:

```python
def test_tumor_only_routing():
    router = WorkflowRouter()
    
    # Create validated input
    validated_input = ValidatedInput(
        tumor_vcf=ValidatedVCF(...),
        normal_vcf=None,
        patient=PatientContext(cancer_type="LUAD", ...),
        analysis_type="tumor_only"
    )
    
    context = router.route(validated_input)
    
    assert context.route.analysis_type == AnalysisType.TUMOR_ONLY
    assert "population_filtering" in context.route.processing_steps
    assert context.route.configuration.penalize_germline_evidence

def test_cancer_specific_override():
    router = WorkflowRouter()
    
    # Test melanoma-specific configuration
    validated_input = ValidatedInput(
        patient=PatientContext(cancer_type="SKCM", ...),
        # ...
    )
    
    context = router.route(validated_input)
    
    # Check melanoma-specific KB weights
    oncokb_priority = next(
        kb for kb in context.route.configuration.kb_priorities 
        if kb.source == EvidenceSource.ONCOKB
    )
    assert oncokb_priority.weight == 1.5  # Melanoma boost

def test_kb_priority_ordering():
    # Ensure KBs are processed in configured order
    pass
```

## Files You Should NOT Modify

- Any files in `src/annotation_engine/ga4gh/`
- `input_validator.py` (Person A's domain)
- `patient_context.py` (Person A's domain)
- `vep_runner.py`
- Core models in `models.py`

## Coordination Points

1. **Config File Format**: Agree on YAML structure with team
2. **Processing Steps**: Ensure step names match actual implementation
3. **Evidence Weights**: Coordinate ranges with clinical team
4. **Cache Namespace**: Ensure doesn't conflict with Person C's caching

## Quick Start Checklist

- [ ] Copy `workflow_router_stub.py` to `workflow_router.py`
- [ ] Create `config/workflow_settings.yaml`
- [ ] Create `config/kb_priorities.yaml`
- [ ] Implement router methods
- [ ] Update `evidence_aggregator.py` to accept WorkflowContext
- [ ] Update `tiering.py` to use workflow rules
- [ ] Create comprehensive tests
- [ ] Document configuration schema
- [ ] Ensure backward compatibility

## Questions to Clarify

1. Should we support custom workflow definitions via API?
2. How should we handle missing cancer-specific configs?
3. Should KB weights be additive or multiplicative?
4. What should happen if a required KB is unavailable?