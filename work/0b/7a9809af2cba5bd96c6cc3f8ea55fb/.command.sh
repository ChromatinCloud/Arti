#!/bin/bash -ue
echo "🔧 Testing Nextflow Environment"
echo "================================"
echo "Java version:"
java --version
echo ""
echo "Python version:"
python3 --version
echo ""
echo "Working directory: $(pwd)"
echo ""
echo "✅ Nextflow environment working!"
