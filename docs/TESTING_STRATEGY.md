# Testing Strategy Blueprint

## Overview

This document defines comprehensive testing strategies based on best practices from leading clinical annotation tools (Nirvana, PCGR, CancerVar, InterVar, OncoKB). We adopt a **multi-layered validation** approach with **clinical-grade test cases** and **continuous integration**.

## Testing Architecture

### Core Principles (Based on Industry Leaders)

1. **Clinical Validation First** (Nirvana pattern): Real-world variants with known clinical interpretations
2. **Continuous Integration** (Nirvana pattern): Daily validation against baseline expectations
3. **Concordance Testing** (PCGR pattern): Compare against established tools and databases
4. **Regression Prevention** (Enterprise pattern): Prevent clinical interpretation regressions

## Testing Pyramid Structure

### 1. Unit Tests (Foundation Layer)

Following **PCGR's** modular testing approach with **Strategy Pattern & Dependency Injection** improvements:

#### Evidence Scoring Strategy Tests (NEW - 2025-06-17)
```python
# tests/test_scoring_strategies.py
import pytest
from annotation_engine.scoring_strategies import (
    FDAApprovedScorer, GuidelineEvidenceScorer, EvidenceScoringManager
)
from annotation_engine.models import Evidence, ActionabilityType, EvidenceWeights

class TestFDAApprovedScorer:
    """Unit tests for FDA evidence scorer - isolated testability"""
    
    def test_can_score_fda_evidence(self, default_weights):
        scorer = FDAApprovedScorer(default_weights)
        fda_evidence = Evidence(description="FDA-approved biomarker...")
        assert scorer.can_score(fda_evidence) == True
    
    def test_calculate_score_by_context(self, default_weights):
        scorer = FDAApprovedScorer(default_weights)
        therapeutic_score = scorer.calculate_score(evidence, ActionabilityType.THERAPEUTIC)
        diagnostic_score = scorer.calculate_score(evidence, ActionabilityType.DIAGNOSTIC)
        assert therapeutic_score > diagnostic_score
```

#### Dependency Injection Tests (NEW - 2025-06-17)
```python
# tests/test_dependency_injection.py  
from annotation_engine.dependency_injection import (
    create_test_tiering_engine, DependencyContainer
)
from unittest.mock import Mock

def test_tiering_engine_with_mocked_dependencies():
    """Test TieringEngine with injected mock dependencies"""
    mock_evidence_aggregator = Mock()
    mock_scoring_manager = Mock()
    
    engine = create_test_tiering_engine(
        evidence_aggregator=mock_evidence_aggregator,
        scoring_manager=mock_scoring_manager
    )
    
    # Test with clean mocks - no complex manual setup
    assert engine.evidence_aggregator == mock_evidence_aggregator
    assert engine.scoring_manager == mock_scoring_manager
```

#### Traditional Rule Engine Tests
```python
# tests/unit/test_rule_engine.py
import pytest
from src.annotation_engine.rules.engine import RuleEngine
from src.annotation_engine.models import Variant, KnowledgeBaseAnnotations

class TestACMGRuleEngine:
    """Unit tests for ACMG rule engine following InterVar patterns"""
    
    @pytest.fixture
    def rule_engine(self):
        return RuleEngine("AMP_ACMG")
    
    @pytest.fixture
    def pathogenic_variant_data(self):
        """TP53 p.R273H - well-characterized pathogenic variant"""
        return {
            "variant": Variant(
                chromosome="17",
                position=7673803,
                reference="G",
                alternate="A",
                gene_symbol="TP53",
                hgvsc="c.818G>A",
                hgvsp="p.Arg273His"
            ),
            "kb_annotations": KnowledgeBaseAnnotations(
                clinvar={
                    "clinical_significance": "Pathogenic",
                    "review_status": "reviewed_by_expert_panel",
                    "variation_id": 12345
                },
                oncokb={
                    "oncogenicity": "Oncogenic",
                    "mutation_effect": "Loss-of-function",
                    "highest_sensitive_level": "LEVEL_1"
                },
                cosmic={
                    "mutation_count": 156,
                    "is_hotspot": True
                }
            )
        }
    
    def test_ps1_rule_invocation(self, rule_engine, pathogenic_variant_data):
        """Test PS1 rule: Same amino acid change as pathogenic variant"""
        variant = pathogenic_variant_data["variant"]
        kb_annotations = pathogenic_variant_data["kb_annotations"]
        
        result = rule_engine.evaluate_variant(variant, kb_annotations)
        
        # Check that PS1 rule was invoked
        ps1_rules = [r for r in result.rules_invoked if r.rule_id == "PS1"]
        assert len(ps1_rules) == 1
        
        ps1_rule = ps1_rules[0]
        assert ps1_rule.evidence_strength == "STRONG"
        assert ps1_rule.applied_weight == 0.8
        assert "ClinVar" in ps1_rule.evidence_sources
    
    def test_pm1_hotspot_rule(self, rule_engine):
        """Test PM1 rule: Mutational hotspot detection"""
        variant = Variant(
            chromosome="17",
            position=7673803,
            reference="G",
            alternate="T",  # Different nucleotide change at same hotspot
            gene_symbol="TP53",
            hgvsc="c.818G>T",
            hgvsp="p.Arg273Leu"
        )
        
        kb_annotations = KnowledgeBaseAnnotations(
            cosmic={"mutation_count": 45, "is_hotspot": True},
            oncokb={"hotspot": True}
        )
        
        result = rule_engine.evaluate_variant(variant, kb_annotations)
        
        pm1_rules = [r for r in result.rules_invoked if r.rule_id == "PM1"]
        assert len(pm1_rules) == 1
        assert pm1_rules[0].applied_weight == 0.5
    
    def test_tier_assignment_logic(self, rule_engine, pathogenic_variant_data):
        """Test overall tier assignment based on rule weights"""
        variant = pathogenic_variant_data["variant"]
        kb_annotations = pathogenic_variant_data["kb_annotations"]
        
        result = rule_engine.evaluate_variant(variant, kb_annotations)
        
        # Should be classified as Tier I based on strong evidence
        assert result.tier_assigned == "Tier_I"
        assert result.confidence_score >= 0.8
        
        # Check that multiple pathogenic rules were invoked
        pathogenic_rules = [r for r in result.rules_invoked 
                          if r.rule_id.startswith(('PVS', 'PS', 'PM', 'PP'))]
        assert len(pathogenic_rules) >= 2

class TestKnowledgeBaseIntegration:
    """Test knowledge base annotation extraction"""
    
    def test_oncokb_annotation_parsing(self):
        """Test OncoKB annotation processing"""
        from src.annotation_engine.knowledge_bases.oncokb import OncoKBAnnotator
        
        mock_oncokb_response = {
            "oncogenicity": "Oncogenic",
            "mutationEffect": "Loss-of-function",
            "highestSensitiveLevel": "LEVEL_1",
            "treatments": [
                {
                    "level": "LEVEL_1",
                    "drugs": ["Platinum compounds"],
                    "cancer_types": ["Lung Adenocarcinoma"]
                }
            ]
        }
        
        annotator = OncoKBAnnotator()
        result = annotator.parse_response(mock_oncokb_response)
        
        assert result.oncogenicity == "Oncogenic"
        assert result.mutation_effect == "Loss-of-function"
        assert len(result.treatments) == 1
        assert result.treatments[0]["level"] == "LEVEL_1"
```

### 2. Integration Tests (Component Layer)

Following **CancerVar's** workflow validation:

```python
# tests/integration/test_annotation_pipeline.py
class TestAnnotationPipeline:
    """Integration tests for complete annotation pipeline"""
    
    @pytest.fixture
    def sample_vcf(self):
        """Sample VCF with known variants"""
        return """##fileformat=VCFv4.2
##reference=GRCh38
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE1
17	7673803	.	G	A	100	PASS	DP=50;AF=0.45	GT:AD:DP	0/1:27,23:50
7	140753336	.	T	A	95	PASS	DP=45;AF=0.52	GT:AD:DP	0/1:22,23:45"""
    
    def test_complete_annotation_workflow(self, sample_vcf):
        """Test complete workflow from VCF to clinical interpretation"""
        from src.annotation_engine.pipeline import AnnotationPipeline
        
        pipeline = AnnotationPipeline()
        
        # Process VCF
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(sample_vcf)
            vcf_path = f.name
        
        try:
            # Run complete pipeline
            results = pipeline.process_vcf(
                vcf_path=vcf_path,
                case_uid="TEST_CASE_001",
                cancer_type="lung_adenocarcinoma"
            )
            
            # Verify results structure
            assert len(results.variants) == 2
            
            # Check TP53 variant (first variant)
            tp53_variant = results.variants[0]
            assert tp53_variant.gene_symbol == "TP53"
            assert "AMP_ACMG" in tp53_variant.tiering_results
            assert tp53_variant.tiering_results["AMP_ACMG"].tier_assigned in ["Tier_I", "Tier_II"]
            
            # Check that KB annotations were retrieved
            assert tp53_variant.kb_annotations.oncokb is not None
            assert tp53_variant.kb_annotations.clinvar is not None
            
            # Check that canned text was generated
            assert tp53_variant.canned_interpretations.variant_dx_interpretation is not None
            
        finally:
            os.unlink(vcf_path)
    
    def test_multiallelic_variant_processing(self):
        """Test handling of multi-allelic variants"""
        multiallelic_vcf = """##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE1
17	7673803	.	G	A,T	100	PASS	DP=60;AF=0.3,0.2	GT:AD:DP	1/2:18,18,24:60"""
        
        from src.annotation_engine.vcf.processor import VCFProcessor
        
        processor = VCFProcessor()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vcf', delete=False) as f:
            f.write(multiallelic_vcf)
            vcf_path = f.name
        
        try:
            processed_variants = processor.process_vcf(vcf_path)
            
            # Should split into 2 separate variants
            assert len(processed_variants) == 2
            
            # Check that both variants are at the same position but different alleles
            assert all(v['position'] == 7673803 for v in processed_variants)
            assert processed_variants[0]['alternate_allele'] == 'A'
            assert processed_variants[1]['alternate_allele'] == 'T'
            
            # Check that multiallelic flag is set
            assert all(v['processing_flags']['multiallelic'] for v in processed_variants)
            
        finally:
            os.unlink(vcf_path)
```

### 3. Clinical Validation Tests

Based on **Nirvana's** clinical validation approach:

```python
# tests/clinical/test_known_variants.py
class TestKnownVariants:
    """Test against clinically validated variants"""
    
    @pytest.fixture
    def clinical_test_cases(self):
        """Curated set of variants with known clinical interpretations"""
        return [
            {
                "name": "TP53_R273H_pathogenic",
                "variant": {
                    "chromosome": "17",
                    "position": 7673803,
                    "reference": "G",
                    "alternate": "A",
                    "gene_symbol": "TP53"
                },
                "expected_tier": "Tier_I",
                "expected_significance": "Pathogenic",
                "cancer_type": "lung_adenocarcinoma",
                "evidence_sources": ["ClinVar", "OncoKB", "COSMIC"],
                "minimum_confidence": 0.8
            },
            {
                "name": "BRAF_V600E_actionable",
                "variant": {
                    "chromosome": "7",
                    "position": 140753336,
                    "reference": "A",
                    "alternate": "T",
                    "gene_symbol": "BRAF"
                },
                "expected_tier": "Tier_I",
                "expected_significance": "Pathogenic",
                "cancer_type": "melanoma",
                "therapeutic_implications": ["Vemurafenib", "Dabrafenib"],
                "minimum_confidence": 0.9
            },
            {
                "name": "EGFR_L858R_sensitizing",
                "variant": {
                    "chromosome": "7",
                    "position": 55181378,
                    "reference": "T",
                    "alternate": "G",
                    "gene_symbol": "EGFR"
                },
                "expected_tier": "Tier_I",
                "expected_significance": "Pathogenic",
                "cancer_type": "lung_adenocarcinoma",
                "therapeutic_implications": ["Erlotinib", "Gefitinib", "Osimertinib"],
                "minimum_confidence": 0.95
            },
            {
                "name": "KRAS_G12C_emerging_actionable",
                "variant": {
                    "chromosome": "12",
                    "position": 25245350,
                    "reference": "C",
                    "alternate": "A",
                    "gene_symbol": "KRAS"
                },
                "expected_tier": "Tier_II",  # Emerging actionability
                "expected_significance": "Pathogenic",
                "cancer_type": "lung_adenocarcinoma",
                "therapeutic_implications": ["Sotorasib", "Adagrasib"],
                "minimum_confidence": 0.8
            }
        ]
    
    def test_clinical_validation_suite(self, clinical_test_cases):
        """Run clinical validation against known variants"""
        from src.annotation_engine.pipeline import AnnotationPipeline
        
        pipeline = AnnotationPipeline()
        failed_cases = []
        
        for test_case in clinical_test_cases:
            try:
                # Create variant object
                variant = Variant(**test_case["variant"])
                
                # Annotate variant
                result = pipeline.annotate_single_variant(
                    variant=variant,
                    cancer_type=test_case["cancer_type"]
                )
                
                # Validate tier assignment
                tier_result = result.tiering_results["AMP_ACMG"]
                if tier_result.tier_assigned != test_case["expected_tier"]:
                    failed_cases.append({
                        "case": test_case["name"],
                        "expected_tier": test_case["expected_tier"],
                        "actual_tier": tier_result.tier_assigned,
                        "confidence": tier_result.confidence_score
                    })
                
                # Validate confidence threshold
                if tier_result.confidence_score < test_case["minimum_confidence"]:
                    failed_cases.append({
                        "case": test_case["name"],
                        "issue": "low_confidence",
                        "expected_min": test_case["minimum_confidence"],
                        "actual": tier_result.confidence_score
                    })
                
                # Validate therapeutic implications (if specified)
                if "therapeutic_implications" in test_case:
                    oncokb_treatments = result.kb_annotations.oncokb.treatments
                    found_drugs = [t["drugs"] for t in oncokb_treatments if t.get("drugs")]
                    
                    for expected_drug in test_case["therapeutic_implications"]:
                        drug_found = any(expected_drug in drugs for drugs in found_drugs)
                        if not drug_found:
                            failed_cases.append({
                                "case": test_case["name"],
                                "issue": "missing_therapeutic",
                                "expected_drug": expected_drug,
                                "found_treatments": found_drugs
                            })
            
            except Exception as e:
                failed_cases.append({
                    "case": test_case["name"],
                    "issue": "exception",
                    "error": str(e)
                })
        
        # Report failures
        if failed_cases:
            failure_report = "\n".join([
                f"FAILED: {case}" for case in failed_cases
            ])
            pytest.fail(f"Clinical validation failures:\n{failure_report}")
```

### 4. Concordance Testing

Following **Nirvana's** concordance validation approach:

```python
# tests/concordance/test_tool_comparison.py
class TestToolConcordance:
    """Test concordance with established clinical annotation tools"""
    
    @pytest.fixture
    def benchmark_variants(self):
        """Variants with known annotations from multiple tools"""
        return load_benchmark_dataset("data/benchmark_variants.json")
    
    def test_oncokb_concordance(self, benchmark_variants):
        """Test concordance with OncoKB annotations"""
        from src.annotation_engine.knowledge_bases.oncokb import OncoKBAnnotator
        
        annotator = OncoKBAnnotator()
        concordance_stats = {"total": 0, "concordant": 0, "discordant": []}
        
        for variant_case in benchmark_variants:
            if "oncokb_expected" not in variant_case:
                continue
            
            variant = Variant(**variant_case["variant"])
            result = annotator.annotate(variant)
            expected = variant_case["oncokb_expected"]
            
            concordance_stats["total"] += 1
            
            # Check oncogenicity concordance
            if result.oncogenicity == expected["oncogenicity"]:
                concordance_stats["concordant"] += 1
            else:
                concordance_stats["discordant"].append({
                    "variant": f"{variant.gene_symbol} {variant.hgvsp}",
                    "expected": expected["oncogenicity"],
                    "actual": result.oncogenicity
                })
        
        # Require >95% concordance
        concordance_rate = concordance_stats["concordant"] / concordance_stats["total"]
        assert concordance_rate > 0.95, f"OncoKB concordance too low: {concordance_rate:.2%}"
    
    def test_clinvar_concordance(self, benchmark_variants):
        """Test concordance with ClinVar annotations"""
        from src.annotation_engine.knowledge_bases.clinvar import ClinVarAnnotator
        
        annotator = ClinVarAnnotator()
        concordance_stats = {"total": 0, "concordant": 0}
        
        for variant_case in benchmark_variants:
            if "clinvar_expected" not in variant_case:
                continue
            
            variant = Variant(**variant_case["variant"])
            result = annotator.annotate(variant)
            expected = variant_case["clinvar_expected"]
            
            concordance_stats["total"] += 1
            
            # Map clinical significance to standard terms
            actual_sig = self._normalize_clinical_significance(result.clinical_significance)
            expected_sig = self._normalize_clinical_significance(expected["clinical_significance"])
            
            if actual_sig == expected_sig:
                concordance_stats["concordant"] += 1
        
        concordance_rate = concordance_stats["concordant"] / concordance_stats["total"]
        assert concordance_rate > 0.99, f"ClinVar concordance too low: {concordance_rate:.2%}"
```

### 5. Performance and Load Testing

```python
# tests/performance/test_scalability.py
class TestPerformance:
    """Performance and scalability testing"""
    
    def test_large_vcf_processing(self):
        """Test processing of large VCF files"""
        import time
        from src.annotation_engine.pipeline import AnnotationPipeline
        
        # Generate test VCF with 1000 variants
        large_vcf = self._generate_test_vcf(num_variants=1000)
        
        pipeline = AnnotationPipeline()
        start_time = time.time()
        
        results = pipeline.process_vcf(large_vcf)
        
        processing_time = time.time() - start_time
        
        # Should process <10 seconds per 1000 variants
        assert processing_time < 10.0, f"Processing too slow: {processing_time:.2f}s"
        assert len(results.variants) == 1000
    
    def test_concurrent_requests(self):
        """Test handling of concurrent annotation requests"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def annotate_variant(variant_data):
            pipeline = AnnotationPipeline()
            return pipeline.annotate_single_variant(**variant_data)
        
        # Create 50 concurrent requests
        variant_requests = [
            {"variant": self._create_test_variant(i), "cancer_type": "lung"}
            for i in range(50)
        ]
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            start_time = time.time()
            results = list(executor.map(annotate_variant, variant_requests))
            processing_time = time.time() - start_time
        
        # All requests should complete successfully
        assert len(results) == 50
        assert all(r is not None for r in results)
        
        # Should handle concurrent load efficiently
        assert processing_time < 30.0, f"Concurrent processing too slow: {processing_time:.2f}s"
```

## Continuous Integration Strategy

### Daily Validation Pipeline

Following **Nirvana's** daily monitoring approach:

```yaml
# .github/workflows/clinical_validation.yml
name: Clinical Validation Pipeline

on:
  schedule:
    - cron: '0 6 * * *'  # Daily at 6 AM UTC
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  clinical_validation:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install poetry
        poetry install
    
    - name: Download test data
      run: |
        ./scripts/download_test_data.sh
    
    - name: Run unit tests
      run: |
        poetry run pytest tests/unit/ -v --cov=src/annotation_engine
    
    - name: Run integration tests
      run: |
        poetry run pytest tests/integration/ -v
    
    - name: Run clinical validation
      run: |
        poetry run pytest tests/clinical/ -v --tb=short
    
    - name: Run concordance tests
      run: |
        poetry run pytest tests/concordance/ -v
      env:
        ONCOKB_API_TOKEN: ${{ secrets.ONCOKB_API_TOKEN }}
    
    - name: Performance benchmarks
      run: |
        poetry run pytest tests/performance/ -v
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3
```

### Test Data Management

```python
# tests/conftest.py
import pytest
import json
from pathlib import Path

@pytest.fixture(scope="session")
def test_data_dir():
    """Test data directory"""
    return Path(__file__).parent / "data"

@pytest.fixture(scope="session")
def benchmark_variants(test_data_dir):
    """Load benchmark variants for validation"""
    with open(test_data_dir / "benchmark_variants.json") as f:
        return json.load(f)

@pytest.fixture(scope="session") 
def mock_kb_responses(test_data_dir):
    """Mock knowledge base responses for testing"""
    responses = {}
    for kb_file in (test_data_dir / "mock_responses").glob("*.json"):
        with open(kb_file) as f:
            responses[kb_file.stem] = json.load(f)
    return responses

@pytest.fixture
def vcf_processor():
    """VCF processor with test configuration"""
    from src.annotation_engine.vcf.processor import VCFProcessor
    return VCFProcessor(config_path="tests/data/test_config.yaml")
```

## Quality Metrics and Reporting

### Test Metrics Dashboard

```python
# tests/reporting/metrics_collector.py
class TestMetricsCollector:
    """Collect and report test metrics"""
    
    def __init__(self):
        self.metrics = {
            "clinical_concordance": {},
            "performance_benchmarks": {},
            "coverage_stats": {},
            "error_rates": {}
        }
    
    def record_clinical_concordance(self, tool_name: str, concordance_rate: float):
        """Record concordance with external tools"""
        self.metrics["clinical_concordance"][tool_name] = {
            "rate": concordance_rate,
            "timestamp": datetime.utcnow(),
            "threshold": 0.95,
            "status": "PASS" if concordance_rate >= 0.95 else "FAIL"
        }
    
    def record_performance_benchmark(self, test_name: str, duration: float, threshold: float):
        """Record performance benchmark results"""
        self.metrics["performance_benchmarks"][test_name] = {
            "duration": duration,
            "threshold": threshold,
            "status": "PASS" if duration <= threshold else "FAIL"
        }
    
    def generate_report(self) -> dict:
        """Generate comprehensive test report"""
        return {
            "summary": self._calculate_summary(),
            "detailed_metrics": self.metrics,
            "recommendations": self._generate_recommendations()
        }
```

This testing strategy provides comprehensive validation following clinical-grade standards with continuous monitoring and transparent reporting.