#!/bin/bash
# Setup script for accessing gnomAD data via Google Cloud Platform

set -e

echo "🧬 Setting up gnomAD GCP Access"
echo "================================"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud SDK not found. Please install it first:"
    echo "   curl https://sdk.cloud.google.com | bash"
    echo "   exec -l $SHELL"
    exit 1
fi

echo "✅ Google Cloud SDK found"

# Check authentication
echo "🔐 Checking GCP authentication..."
if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    echo "✅ Already authenticated with GCP"
else
    echo "🔑 Please authenticate with Google Cloud:"
    gcloud auth login
fi

# Set up project (if needed)
echo "📁 Current GCP project:"
gcloud config get-value project

echo ""
echo "🧬 gnomAD Data Access Information"
echo "================================="
echo "gnomAD v4 data is available in Google Cloud Storage:"
echo "  gs://gcp-public-data--gnomad/release/4.0/"
echo ""
echo "🔧 Example commands:"
echo "  List gnomAD files:    gsutil ls gs://gcp-public-data--gnomad/release/4.0/"
echo "  Download VCF:         gsutil cp gs://gcp-public-data--gnomad/release/4.0/vcf/exomes/gnomad.exomes.v4.0.sites.vcf.bgz ."
echo "  Download frequencies: gsutil cp gs://gcp-public-data--gnomad/release/4.0/ht/exomes/gnomad.exomes.v4.0.sites.ht ."
echo ""
echo "💡 For large files, consider using:"
echo "  gsutil -m cp -r   (parallel downloads)"
echo "  gsutil rsync       (synchronization)"
echo ""

# Test access
echo "🧪 Testing gnomAD access..."
if gsutil ls gs://gcp-public-data--gnomad/release/4.0/ > /dev/null 2>&1; then
    echo "✅ gnomAD GCP access working!"
    echo ""
    echo "📊 Available gnomAD v4.0 datasets:"
    gsutil ls gs://gcp-public-data--gnomad/release/4.0/ | head -10
else
    echo "❌ Cannot access gnomAD data. Please check:"
    echo "  1. GCP authentication: gcloud auth list"
    echo "  2. Project permissions"
    echo "  3. Network connectivity"
fi

echo ""
echo "🐳 To use in Docker containers:"
echo "  1. Mount GCP credentials: -v ~/.config/gcloud:/root/.config/gcloud"
echo "  2. Or use service account key: -v /path/to/key.json:/app/secrets/gcp-key.json"
echo "  3. Set environment: GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/gcp-key.json"