#!/bin/bash -ue
cd /Users/lauferva/Desktop/Arti/workflows
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"

echo "Testing VCF validation with Nextflow..."
poetry run python -m src.annotation_engine \
    --input proper_test.vcf \
    --case-uid NF_TEST_001 \
    --cancer-type lung_adenocarcinoma \
    --dry-run
echo "✅ Nextflow + Annotation Engine integration working!"
