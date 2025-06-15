#!/usr/bin/env nextflow

/*
 * Simple Nextflow test for environment verification
 */

nextflow.enable.dsl=2

workflow {
    TEST_ENVIRONMENT()
}

process TEST_ENVIRONMENT {
    debug true
    
    output:
    stdout
    
    script:
    """
    echo "🔧 Testing Nextflow Environment"
    echo "================================"
    echo "Java version:"
    java --version
    echo ""
    echo "Python version:"
    python3 --version
    echo ""
    echo "Working directory: \$(pwd)"
    echo ""
    echo "✅ Nextflow environment working!"
    """
}