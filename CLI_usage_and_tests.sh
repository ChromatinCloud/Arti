Testing Commands for Annotation Engine

  1. Basic Health Checks

  # Check if installed correctly
  poetry run annotation-engine --version

  # Check VEP plugin status (just added!)
  poetry run annotation-engine --check-plugins

  # Run built-in test mode
  poetry run annotation-engine --test

  2. Test with Example VCF

  # Basic tumor-only annotation
  poetry run annotation-engine \
    --input example_input/proper_test.vcf \
    --case-uid TEST001 \
    --cancer-type melanoma

  # Check the output
  ls -la out/results/TEST001/
  cat out/results/TEST001/annotation_results.json | jq '.' | head -50

  3. Test Different Cancer Types

  # Lung cancer (should recognize KRAS as driver)
  poetry run annotation-engine \
    --input example_input/proper_test.vcf \
    --case-uid LUNG001 \
    --cancer-type lung_adenocarcinoma

  # Colorectal (different driver priorities)
  poetry run annotation-engine \
    --input example_input/proper_test.vcf \
    --case-uid CRC001 \
    --cancer-type colorectal_cancer

  4. Test Quality Filters

  # Strict quality filtering
  poetry run annotation-engine \
    --input example_input/proper_test.vcf \
    --case-uid STRICT001 \
    --cancer-type melanoma \
    --min-depth 30 \
    --min-vaf 0.10

  # Skip QC to see all variants
  poetry run annotation-engine \
    --input example_input/proper_test.vcf \
    --case-uid NOQC001 \
    --cancer-type melanoma \
    --skip-qc

  5. Test Output Formats

  # JSON only
  poetry run annotation-engine \
    --input example_input/proper_test.vcf \
    --case-uid JSON001 \
    --cancer-type melanoma \
    --output-format json

  # TSV only
  poetry run annotation-engine \
    --input example_input/proper_test.vcf \
    --case-uid TSV001 \
    --cancer-type melanoma \
    --output-format tsv

  # All formats
  poetry run annotation-engine \
    --input example_input/proper_test.vcf \
    --case-uid ALL001 \
    --cancer-type melanoma \
    --output-format all

  6. Test VEP Functionality

  # Test VEP directly with dbNSFP
  poetry run python scripts/test_vep_with_dbnsfp.py

  # Debug VEP with specific plugins
  poetry run python scripts/debug_vep_dbnsfp.py

  7. Validate Your Own VCF

  # If you have your own VCF file
  poetry run annotation-engine \
    --input /path/to/your.vcf \
    --case-uid YOUR001 \
    --cancer-type melanoma \
    --output ./my_results

  8. Check Results

  # View tier assignments
  cat out/results/TEST001/annotation_results.json | jq '.variants[].clinical_annotation | {gene: .gene_symbol, tier: .tier, confidence: .confidence_score}'

  # Check evidence aggregation
  cat out/results/TEST001/annotation_results.json | jq '.variants[].evidence_items[] | {source, clinical_significance}'

  # View summary
  cat out/results/TEST001/summary_report.txt

  9. Test Error Handling

  # Missing required arguments
  poetry run annotation-engine --input example_input/proper_test.vcf

  # Invalid cancer type
  poetry run annotation-engine \
    --input example_input/proper_test.vcf \
    --case-uid ERROR001 \
    --cancer-type invalid_cancer

  # Non-existent file
  poetry run annotation-engine \
    --input does_not_exist.vcf \
    --case-uid ERROR002 \
    --cancer-type melanoma

  10. Performance Testing

  # Time the execution
  time poetry run annotation-engine \
    --input example_input/proper_test.vcf \
    --case-uid PERF001 \
    --cancer-type melanoma

  # Run with verbose logging
  poetry run annotation-engine \
    --input example_input/proper_test.vcf \
    --case-uid VERBOSE001 \
    --cancer-type melanoma \
    --verbose 2

  Expected Results:

  - Tier assignments: BRAF V600E should be Tier III in melanoma
  - Evidence: Should see OncoKB, CIViC, COSMIC evidence
  - Performance: Should complete in ~75 seconds
  - Output files: JSON with full details, summary text file

  Quick Diagnostic:

  # One command to test if everything works
  poetry run annotation-engine --test && echo "✅ Engine is working!"