#!/bin/bash
# Environment setup script for Annotation Engine

# Java setup for Nextflow
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"

# Add user bin to PATH for Nextflow
export PATH="$HOME/bin:$PATH"

# Verify installations
echo "🔧 Environment Setup"
echo "===================="
echo "Java version:"
java --version
echo ""
echo "Nextflow version:"
~/bin/nextflow -version
echo ""
echo "Python version:"
python --version
echo ""
echo "Poetry environment:"
poetry env info --path