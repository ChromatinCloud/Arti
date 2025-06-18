# Person A Implementation Guide: Input Validation & Patient Context

## Overview

You are responsible for implementing the input validation layer that ensures all data entering the annotation pipeline is valid, normalized, and ready for processing. Your code will be the first line of defense against bad data and will create the `ValidatedInput` object that flows through the entire system.

## Your Deliverables

### 1. Core Module: `input_validator.py`
- Rename `input_validator_stub.py` to `input_validator.py`
- Implement all methods marked with `NotImplementedError`
- Follow the `InputValidatorProtocol` interface exactly

### 2. Core Module: `patient_context.py`
- Create this new module for patient/clinical data management
- Import and use the `PatientContext` dataclass from interfaces
- Implement OncoTree code lookup and validation

### 3. CLI Updates
- Update `cli.py` to add new command-line arguments:
  - `--patient-uid` (required)
  - `--oncotree-code` (required, but accept `--cancer-type` as alias)
  - `--output-format {json,phenopacket,va}`
  - `--vrs-normalize` (flag)
  - `--export-va` (flag)

### 4. Output Formatter Enhancement
- Create `output_formatter.py` for concordance metrics display
- Add methods to show when multiple databases agree on interpretations

## Key Implementation Details

### VCF Validation (`validate_vcf` method)

```python
def validate_vcf(self, vcf_path: Path, sample_type: SampleType) -> ValidatedVCF:
    """
    Comprehensive VCF validation
    """
    errors = []
    
    # 1. Check file exists and is readable
    if not vcf_path.exists():
        raise FileNotFoundError(f"VCF file not found: {vcf_path}")
    
    # 2. Parse VCF headers
    with open(vcf_path) as f:
        headers = []
        sample_names = []
        for line in f:
            if line.startswith("##"):
                headers.append(line.strip())
            elif line.startswith("#CHROM"):
                # Extract sample names from column headers
                columns = line.strip().split("\t")
                sample_names = columns[9:]  # Samples start at column 10
                break
    
    # 3. Detect genome version from headers
    genome_version = "GRCh38"  # Default
    for header in headers:
        if "reference" in header or "assembly" in header:
            if "GRCh37" in header or "hg19" in header:
                genome_version = "GRCh37"
            elif "GRCh38" in header or "hg38" in header:
                genome_version = "GRCh38"
    
    # 4. Check chromosome format (chr1 vs 1)
    normalized_chromosomes = None
    variant_count = 0
    has_genotypes = False
    has_allele_frequencies = False
    
    with open(vcf_path) as f:
        for line in f:
            if line.startswith("#"):
                continue
            variant_count += 1
            if variant_count == 1:  # Check first variant
                chrom = line.split("\t")[0]
                normalized_chromosomes = chrom.startswith("chr")
                
                # Check for GT and AF fields
                if len(line.split("\t")) > 9:
                    has_genotypes = True
                if ":AF:" in line or "AF=" in line:
                    has_allele_frequencies = True
            
            if variant_count >= 100:  # Sample first 100 variants
                break
    
    # 5. Additional validations for tumor-normal pairs
    if sample_type == SampleType.NORMAL and len(sample_names) > 1:
        warnings.append(ValidationError(
            field="vcf_samples",
            message=f"Normal VCF has multiple samples: {sample_names}",
            severity="warning"
        ))
    
    return ValidatedVCF(
        path=vcf_path,
        sample_type=sample_type,
        sample_names=sample_names,
        variant_count=variant_count,
        has_genotypes=has_genotypes,
        has_allele_frequencies=has_allele_frequencies,
        genome_version=genome_version,
        normalized_chromosomes=normalized_chromosomes
    )
```

### Patient Context Validation

```python
def validate_patient_context(self,
                           patient_uid: str,
                           case_id: str, 
                           oncotree_code: str) -> PatientContext:
    """
    Validate patient and clinical information
    """
    # 1. Validate patient UID format (customize based on your requirements)
    if not patient_uid or not patient_uid.strip():
        raise ValueError("Patient UID is required")
    
    if not self._is_valid_patient_uid(patient_uid):
        raise ValueError(f"Invalid patient UID format: {patient_uid}")
    
    # 2. Validate case ID
    if not case_id or not case_id.strip():
        raise ValueError("Case ID is required")
    
    # 3. Validate OncoTree code
    oncotree_code = oncotree_code.upper()
    if oncotree_code not in self.oncotree_codes:
        # Try to find close matches
        close_matches = self._find_close_oncotree_matches(oncotree_code)
        if close_matches:
            raise ValueError(
                f"Unknown OncoTree code: {oncotree_code}. "
                f"Did you mean one of: {', '.join(close_matches)}?"
            )
        else:
            raise ValueError(f"Unknown OncoTree code: {oncotree_code}")
    
    # 4. Get additional cancer information
    cancer_info = self._get_cancer_info(oncotree_code)
    
    return PatientContext(
        patient_uid=patient_uid,
        case_id=case_id,
        cancer_type=oncotree_code,
        cancer_display_name=self.oncotree_codes[oncotree_code],
        primary_site=cancer_info.get("primary_site"),
        stage=None,  # Could be parsed from additional inputs
        prior_treatments=None,
        clinical_notes=None
    )

def _is_valid_patient_uid(self, uid: str) -> bool:
    """Validate patient UID format"""
    # Example: alphanumeric with optional hyphens
    import re
    return bool(re.match(r'^[A-Za-z0-9\-_]+$', uid))
```

### OncoTree Data Loading

Create a JSON file with OncoTree mappings:

```json
{
  "LUAD": {
    "name": "Lung Adenocarcinoma", 
    "primary_site": "Lung",
    "tissue": "Lung",
    "main_type": "Non-Small Cell Lung Cancer"
  },
  "SKCM": {
    "name": "Skin Cutaneous Melanoma",
    "primary_site": "Skin", 
    "tissue": "Skin",
    "main_type": "Melanoma"
  }
}
```

### Chromosome Normalization

```python
def normalize_chromosome_names(self, vcf_path: Path, target_format: str = "chr") -> Path:
    """
    Normalize chromosome names to consistent format
    
    Args:
        vcf_path: Input VCF
        target_format: "chr" for chr1 format, "no_chr" for 1 format
        
    Returns:
        Path to normalized VCF (may be same as input if no changes needed)
    """
    # Implementation details...
```

### Multi-Sample Detection

```python
def detect_multi_sample_vcf(self, vcf_path: Path) -> Dict[str, Any]:
    """
    Detect if VCF contains multiple samples and extract pairing info
    """
    # Parse sample names
    # Look for NORMAL/TUMOR in sample names
    # Return pairing information
```

## Integration Points

### With Workflow Router (Person B)

Your main interface is the `ValidatedInput` object:

```python
@dataclass
class ValidatedInput:
    tumor_vcf: ValidatedVCF
    normal_vcf: Optional[ValidatedVCF]
    patient: PatientContext
    analysis_type: str
    # ... other fields
```

The workflow router will call:
```python
validator = InputValidator()
result = validator.validate(...)
if result.is_valid:
    workflow_context = router.route(result.validated_input)
```

### With CLI

Update `cli.py` to use your validator:

```python
def main():
    args = parse_args()
    
    # Initialize validator
    validator = InputValidator()
    
    # Validate inputs
    validation_result = validator.validate(
        tumor_vcf_path=args.tumor_vcf or args.input,
        patient_uid=args.patient_uid,
        case_id=args.case_uid,
        oncotree_code=args.oncotree_code or args.cancer_type,
        # ... other args
    )
    
    if not validation_result.is_valid:
        for error in validation_result.errors:
            print(f"ERROR: {error.message}", file=sys.stderr)
        return 1
```

## Testing Your Implementation

Create comprehensive tests in `tests/test_input_validator.py`:

```python
def test_valid_tumor_only_input():
    validator = InputValidator()
    result = validator.validate(
        tumor_vcf_path=Path("test_data/tumor.vcf"),
        patient_uid="PT001",
        case_id="CASE001",
        oncotree_code="LUAD"
    )
    assert result.is_valid
    assert result.validated_input.analysis_type == "tumor_only"

def test_invalid_oncotree_code():
    validator = InputValidator()
    result = validator.validate(
        tumor_vcf_path=Path("test_data/tumor.vcf"),
        patient_uid="PT001", 
        case_id="CASE001",
        oncotree_code="INVALID"
    )
    assert not result.is_valid
    assert any("OncoTree" in e.message for e in result.errors)

def test_chromosome_normalization():
    # Test that chr1 and 1 formats are detected correctly
    pass
```

## Files You Should NOT Modify

- Any files in `src/annotation_engine/ga4gh/`
- `evidence_aggregator.py` (Person B will modify this)
- `tiering.py` (Person B will modify this)
- `vep_runner.py`
- Any test files except your own

## Coordination Points

1. **OncoTree Codes**: Coordinate with team on which OncoTree version to use
2. **Patient UID Format**: Agree on format requirements with clinical team
3. **Output Formats**: Ensure CLI flags match what output formatter can handle

## Quick Start Checklist

- [ ] Copy `input_validator_stub.py` to `input_validator.py`
- [ ] Create `patient_context.py` module
- [ ] Add OncoTree data file (JSON or YAML)
- [ ] Update `cli.py` with new arguments
- [ ] Implement VCF validation logic
- [ ] Implement patient context validation
- [ ] Create comprehensive tests
- [ ] Create `output_formatter.py` for concordance display
- [ ] Document any assumptions or decisions

## Questions to Clarify

1. What patient UID format should we accept?
2. Should we support custom OncoTree mappings?
3. How should we handle VCFs with inconsistent chromosome naming?
4. What validation warnings should be fatal vs informational?