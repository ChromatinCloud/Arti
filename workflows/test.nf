#!/usr/bin/env nextflow

/*
 * Test Nextflow workflow for Annotation Engine
 */

nextflow.enable.dsl=2

workflow {
    // Test that we can call our CLI from Nextflow
    vcf_input = Channel.fromPath("${projectDir}/example_input/proper_test.vcf")
    
    VALIDATE_VCF(vcf_input)
}

process VALIDATE_VCF {
    debug true
    
    input:
    path vcf
    
    output:
    stdout
    
    script:
    """
    export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
    export PATH="\$JAVA_HOME/bin:\$PATH"
    
    echo "Testing VCF validation with Nextflow..."
    echo "Working directory: \$(pwd)"
    echo "VCF file: ${vcf}"
    echo "Project directory: ${projectDir}"
    
    cd ${projectDir}
    echo "Changed to project directory: \$(pwd)"
    
    # Test that our CLI works from project root
    export PYTHONPATH="${projectDir}/src:\$PYTHONPATH"
    poetry run python -c "import sys; print('Python path:', sys.path)"
    poetry run python -m annotation_engine \\
        --input ${vcf} \\
        --case-uid NF_TEST_001 \\
        --cancer-type lung_adenocarcinoma \\
        --dry-run
    echo "✅ Nextflow + Annotation Engine integration working!"
    """
}