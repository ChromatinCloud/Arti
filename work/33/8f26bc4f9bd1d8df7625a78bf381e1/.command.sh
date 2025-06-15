#!/bin/bash -ue
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"

echo "Testing VCF validation with Nextflow..."
echo "Working directory: $(pwd)"
echo "VCF file: proper_test.vcf"
echo "Project directory: /Users/lauferva/Desktop/Arti/workflows"

cd /Users/lauferva/Desktop/Arti/workflows
echo "Changed to project directory: $(pwd)"

# Test that our CLI works from project root
export PYTHONPATH="/Users/lauferva/Desktop/Arti/workflows/src:$PYTHONPATH"
poetry run python -c "import sys; print('Python path:', sys.path)"
poetry run python -m annotation_engine \
    --input proper_test.vcf \
    --case-uid NF_TEST_001 \
    --cancer-type lung_adenocarcinoma \
    --dry-run
echo "✅ Nextflow + Annotation Engine integration working!"
