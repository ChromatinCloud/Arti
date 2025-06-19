# Technical Filtering <-> Arti Backend API Integration

## Current Status: ✅ Fully Integrated

The technical filtering module is now fully integrated with the Arti backend API. Here's how the integration works:

## API Flow

### 1. **Tech Filtering Frontend -> Backend**
```
POST /api/v1/tech-filtering/apply
```
- Accepts filter parameters and input VCF path
- Applies bcftools filters based on mode (tumor-only/tumor-normal)
- Returns filtered VCF path and variant counts

### 2. **Tech Filtering -> Arti Main Pipeline**
```
POST /api/v1/variants/annotate-file
```
- Accepts filtered VCF file path from tech filtering
- Includes sample metadata (patient UID, case ID, OncoTree code, tumor purity)
- Starts background annotation job
- Returns job ID for tracking

## Key Integration Points

### File Path Updates ✅
- All reference files moved from `src/assay_configs` to `./resources`
- Separate directories for genome reference vs assay-specific files
- BCFtoolsFilterBuilder updated to use new paths

### API Endpoint Alignment ✅
- Created `/annotate-file` endpoint to accept file paths (not just content)
- Handles both `.vcf` and `.vcf.gz` files
- Preserves metadata throughout the pipeline

### Mode Conversion ✅
- Frontend uses hyphenated mode names: `tumor-only`, `tumor-normal`
- Backend expects underscored: `tumor_only`, `tumor_normal`
- Automatic conversion in API calls

### Authentication ✅
- Tech filtering endpoints protected by authentication
- Uses same auth system as main Arti API
- Requires `write_interpretations` permission for annotation

## Sample Metadata Flow

1. **Capture in Tech Filtering UI**:
   - Patient UID
   - Case ID
   - OncoTree code (required for full functionality)
   - Tumor purity estimate
   - Specimen type

2. **Pass to Arti Backend**:
   ```javascript
   {
     vcf_path: "/path/to/filtered.vcf.gz",
     case_uid: "CASE_001",
     patient_uid: "PT_001",
     cancer_type: "SKCM",  // OncoTree code
     analysis_type: "tumor_only",
     tumor_purity: 0.75,
     specimen_type: "FFPE"
   }
   ```

3. **Stored in Job Metadata**:
   - All metadata preserved in annotation job
   - Available throughout processing pipeline
   - Used for context-specific interpretation

## Error Handling

- File not found errors return 400 status
- Missing OncoTree code defaults to demo cancer types
- Failed bcftools commands captured with stderr
- Background cleanup of temporary files

## Testing the Integration

1. **Start Arti Backend**:
   ```bash
   cd /Users/lauferva/Desktop/Arti
   poetry run uvicorn src.annotation_engine.api.main:app --reload
   ```

2. **Start Tech Filtering Frontend**:
   ```bash
   cd src/tech_filtering
   npm install
   npm run dev
   ```

3. **Test Flow**:
   - Upload VCF to tech filtering
   - Apply filters
   - Click "Send to Arti"
   - Monitor job progress via job ID

## Next Steps

1. **Real VEP Integration**: Replace demo annotation with actual VEP runner
2. **Job Status UI**: Add job tracking interface in main Arti frontend
3. **Result Visualization**: Display annotation results in clinical interpretation UI
4. **Batch Processing**: Support multiple VCFs in single submission

## Configuration

### Environment Variables
```bash
# Tech Filtering Frontend
REACT_APP_API_URL=http://localhost:8000

# Arti Backend
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
```

### Required Tools
- bcftools (for filtering operations)
- tabix (for VCF indexing)
- Java 17 (for Nextflow/VEP)

The integration is complete and functional. The tech filtering module can now seamlessly hand off filtered VCFs to the main Arti annotation pipeline with full metadata preservation.