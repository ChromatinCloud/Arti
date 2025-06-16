# Annotation Engine Completion Roadmap

## Phase 1: Core Engine Completion (Current Sprint)

### Week 1-2: Core Module Implementation

#### 1. VEP Runner Module (`vep_runner.py`)
**Status**: In Progress  
**Dependencies**: VEP installation, plugin data setup  
**Tasks**:
- [ ] Implement `run_vep()` function to shell out to VEP with --json flag
- [ ] Parse VEP JSON output into Python objects compatible with `models.Evidence`
- [ ] Handle VEP error cases and validation
- [ ] Add support for custom VEP parameters per cancer type
- [ ] Unit tests for VEP execution and JSON parsing

**Key Implementation Details**:
```python
def run_vep(vcf_path: str, cancer_type: str) -> List[Dict]:
    # Shell out to: vep --json --input_file vcf_path --output_file json_path
    # Parse JSON into Evidence-compatible format
    # Return list of variant dicts
```

#### 2. Evidence Aggregator Module (`evidence_aggregator.py`)  
**Status**: In Progress  
**Dependencies**: KB reorganization (✅ Complete), VEP output format  
**Tasks**:
- [ ] Implement lazy loading of KB data from `.refs/` structure
- [ ] Create matching logic for OncoKB gene lists → variants
- [ ] Create matching logic for CIViC evidence → variants  
- [ ] Create matching logic for COSMIC hotspots → variants
- [ ] Aggregate evidence objects per variant
- [ ] Cache loaded KB data globally for performance

**Key Implementation Details**:
```python
def aggregate_evidence(vep_variants: List[Dict]) -> List[Evidence]:
    # Load OncoKB from .refs/clinical_evidence/oncokb/
    # Load CIViC from .refs/clinical_evidence/civic/
    # Load COSMIC from .refs/cancer_signatures/hotspots/
    # Match each variant against all KBs
    # Return Evidence objects with aggregated data
```

#### 3. Tiering Module (`tiering.py`)
**Status**: In Progress  
**Dependencies**: Evidence objects, clinical guidelines mapping  
**Tasks**:
- [ ] Implement 12 CancerVar CBP criteria as scoring functions
- [ ] Map evidence types to CBP weights (Strong=3, Moderate=2, Supporting=1)
- [ ] Implement AMP 2017 tier assignment logic (Tier I-IV)
- [ ] Implement VICC 2022 oncogenicity classification  
- [ ] Create `assign_tier(evidence_list) -> TierResult` function
- [ ] Add confidence scoring based on evidence quality

**Key Implementation Details**:
```python
def assign_tier(evidence_list: List[Evidence]) -> TierResult:
    # Apply 12 CBP criteria from CancerVar
    # Sum weighted scores (Strong=3, Moderate=2, Supporting=1)
    # Map to AMP Tiers I-IV based on thresholds
    # Return TierResult with tier, confidence, evidence breakdown
```

### Week 3: Integration and Testing

#### 4. End-to-End Pipeline Integration
**Tasks**:
- [ ] Connect VEP Runner → Evidence Aggregator → Tiering pipeline
- [ ] Implement CLI interface in `cli.py` 
- [ ] Add proper error handling and logging throughout pipeline
- [ ] Validate JSON output format matches specification
- [ ] Performance optimization for large VCF processing

#### 5. Comprehensive Testing
**Tasks**:
- [ ] Expand `tests/test_smoke.py` with known Tier I and Tier III variants
- [ ] Add integration tests for full VCF → JSON workflow
- [ ] Create test cases for edge cases (multi-allelic, complex variants)
- [ ] Validate against reference datasets (COSMIC hotspots, CIViC evidence)
- [ ] Performance tests with realistic VCF sizes

### Week 4: Validation and Documentation

#### 6. Clinical Validation
**Tasks**:
- [ ] Test with example tumor-normal and tumor-only VCFs
- [ ] Validate tier assignments against expert clinical review
- [ ] Ensure BRAF V600E → Tier I (known actionable)
- [ ] Ensure benign polymorphisms → appropriate classification
- [ ] Document any discrepancies and resolution approach

#### 7. Production Readiness
**Tasks**:
- [ ] Comprehensive error handling and user-friendly error messages
- [ ] Input validation (VCF format, required fields)
- [ ] Performance benchmarking and optimization
- [ ] Memory usage optimization for large knowledge bases
- [ ] Final documentation and user guide updates

## Phase 1 Success Metrics

### Technical Deliverables
- [x] VCF input processing (tumor-normal and tumor-only)
- [ ] VEP annotation integration  
- [ ] Evidence aggregation from OncoKB, CIViC, COSMIC
- [ ] AMP/VICC tier assignment
- [ ] JSON output generation
- [ ] Comprehensive test suite (>80% coverage)

### Clinical Validation
- [ ] Known actionable variants correctly assigned Tier I
- [ ] Known VUS correctly assigned Tier III  
- [ ] Benign variants appropriately classified
- [ ] Evidence reasoning traceable in output
- [ ] Performance suitable for clinical workflow (<5 min per sample)

### Quality Assurance
- [ ] All tests passing: `poetry run pytest -q`
- [ ] Code quality: `poetry run ruff --select I --target-version py310`
- [ ] No critical security vulnerabilities
- [ ] Documentation complete and accurate
- [ ] Docker containerization working

## Phase 2 Planning (Future)

### Database Integration
- Persistent case storage (PostgreSQL + SQLModel)
- Audit trail for manual tier overrides
- Patient/case/variant tracking

### Web Interface  
- Interactive curation portal
- Tier override capabilities with justification
- PDF report generation
- Authentication and authorization

### Advanced Analytics
- Quantitative tier confidence scoring
- Machine learning calibration on historical data
- Population-specific frequency analysis
- Comprehensive biomarker integration (TMB, MSI, HRD)

## Implementation Notes

### Development Approach
1. **Modular Development**: Each module (VEP, Evidence, Tiering) developed independently
2. **Test-Driven**: Unit tests written alongside implementation
3. **Incremental Integration**: Components integrated progressively
4. **Clinical Focus**: Validation against real clinical scenarios throughout

### Risk Mitigation
- **VEP Dependency**: Containerized VEP setup to ensure consistency
- **KB Size**: Lazy loading and caching to manage memory usage  
- **Clinical Accuracy**: Extensive validation against reference datasets
- **Performance**: Benchmarking and optimization throughout development

### Success Criteria for Completion
The annotation engine will be considered complete for Phase 1 when:
1. End-to-end VCF processing produces clinically meaningful JSON output
2. Known reference variants are correctly tiered  
3. All tests pass consistently
4. Performance meets clinical workflow requirements
5. Code quality and documentation standards are met

This roadmap provides a clear path from current state to a production-ready Phase 1 annotation engine.