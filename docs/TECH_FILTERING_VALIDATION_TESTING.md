# Technical Filtering Validation and Testing Guide

## Overview

The technical filtering module includes comprehensive validation for VCF files and metadata to ensure data integrity before processing. This document describes the validation rules, testing approach, and error handling.

## VCF Validation Rules

### 1. **Tumor-Only Mode**
- **Required**: Exactly 1 sample in VCF
- **Rejected**: Multi-sample VCFs
- **Error Message**: "Tumor-only mode requires single-sample VCF, found N samples: [sample names]"

### 2. **Tumor-Normal Mode**
Accepts two formats:

#### Option A: Multi-sample VCF
- **Required**: At least 2 samples
- **Sample Identification**:
  - Automatic: Looks for "tumor", "normal", "cancer", "blood" in sample names
  - Manual: User can specify sample names via UI
  - Fallback: First sample = tumor, second = normal
- **Warning**: If >2 samples, extras are ignored

#### Option B: Separate VCF Files
- **Required**: Exactly 2 VCF files
- **Validation**: 
  - Each file must have exactly 1 sample
  - VCF versions must match
  - Reports variant overlap statistics

### 3. **General VCF Requirements**
- **Format**: Must have `##fileformat=VCFv4.x` header
- **Header**: Must have `#CHROM` line with 9 required columns
- **Extensions**: Accepts `.vcf` and `.vcf.gz`
- **Size Limit**: 5GB per file

## Metadata Validation

### Required Fields
- `case_id` (string): Unique case identifier
- `cancer_type` (string): OncoTree code (e.g., "SKCM", "LUAD")

### Optional Fields
- `patient_uid` (string): Patient identifier
- `tumor_purity` (float): 0.0-1.0 range
- `specimen_type` (string): FFPE, Fresh Frozen, Blood, etc.
- `tumor_sample` (string): For multi-sample VCF
- `normal_sample` (string): For multi-sample VCF

### Validation Warnings
- Invalid OncoTree code format (should be uppercase letters)
- FFPE specimen without tumor purity estimate
- Non-standard specimen types

## API Error Responses

### Validation Errors
```json
{
  "success": false,
  "error": "VCF validation failed: Tumor-only mode requires single-sample VCF, found 2 samples: TUMOR, NORMAL"
}
```

### Metadata Errors
```json
{
  "success": false,
  "error": "Metadata validation failed: Missing required field: case_id"
}
```

## Frontend Validation

### VCF Upload Component
- Real-time file validation on upload
- Reads first 1MB to check format
- Counts samples and validates against mode
- Shows warnings for potential issues

### Error Display
- Red border and error icon for invalid files
- Yellow warning box for non-critical issues
- Green checkmark for valid uploads

## Testing Strategy

### Unit Tests (`test_vcf_validation.py`)

#### VCF Validator Tests
- ✅ Valid single-sample for tumor-only
- ✅ Multi-sample rejected for tumor-only
- ✅ Multi-sample accepted for tumor-normal
- ✅ Separate files for tumor-normal
- ✅ Sample name identification
- ✅ Missing file handling
- ✅ Invalid format detection
- ✅ Gzipped file support

#### Metadata Validator Tests
- ✅ Minimal valid metadata
- ✅ Complete metadata with all fields
- ✅ Missing required fields
- ✅ Invalid tumor purity values
- ✅ OncoTree code warnings
- ✅ FFPE purity warnings
- ✅ Non-standard specimen types

### Integration Tests (`test_tech_filtering_integration.py`)

#### API Integration Tests
- ✅ Valid tumor-only submission
- ✅ Multi-sample VCF error for TO
- ✅ Valid tumor-normal multi-sample
- ✅ Separate file tumor-normal
- ✅ Missing metadata validation
- ✅ Invalid tumor purity
- ✅ Sample name specification
- ✅ Invalid analysis modes

#### End-to-End Tests
- ✅ Filter application workflow
- ✅ Handoff to Arti annotation
- ✅ Job tracking integration

#### Edge Cases
- ✅ Empty VCF handling
- ✅ Malformed headers
- ✅ Version mismatches
- ✅ Large file handling

## Running Tests

### Unit Tests
```bash
cd /Users/lauferva/Desktop/Arti
poetry run pytest tests/test_vcf_validation.py -v
```

### Integration Tests
```bash
poetry run pytest tests/test_tech_filtering_integration.py -v
```

### Full Test Suite
```bash
poetry run pytest tests/test_vcf_validation.py tests/test_tech_filtering_integration.py -v --cov=src.annotation_engine.api.validators --cov=src.annotation_engine.api.routers.tech_filtering
```

## Common Validation Scenarios

### Scenario 1: OncoSeq Multi-sample VCF
```
Input: Single VCF with TUMOR and NORMAL columns
Mode: tumor-normal
Result: ✅ Accepted, samples automatically identified
```

### Scenario 2: Legacy Single-sample Files
```
Input: tumor.vcf, normal.vcf (separate files)
Mode: tumor-normal
Result: ✅ Accepted, overlap statistics calculated
```

### Scenario 3: Research Multi-sample VCF
```
Input: VCF with Patient1_DNA, Patient1_RNA, Control_DNA
Mode: tumor-normal
Action: User specifies Patient1_DNA as tumor, Control_DNA as normal
Result: ✅ Accepted with manual sample mapping
```

### Scenario 4: Incorrect Mode Selection
```
Input: Multi-sample VCF
Mode: tumor-only
Result: ❌ Rejected with clear error message
```

## Best Practices

1. **Always validate metadata** before VCF processing
2. **Check sample counts** match analysis mode
3. **Provide clear error messages** with actionable fixes
4. **Log validation warnings** even if processing continues
5. **Support both modern and legacy** VCF formats
6. **Allow user override** for sample identification
7. **Fail fast** with informative errors

## Future Enhancements

1. **Sample Splitting**: Automatically split multi-sample VCFs for separate processing
2. **Format Conversion**: Support VCF 4.1 → 4.2 upgrades
3. **Batch Validation**: Validate multiple VCFs before processing
4. **Smart Mode Detection**: Suggest mode based on VCF structure
5. **Performance**: Stream large VCFs instead of loading fully