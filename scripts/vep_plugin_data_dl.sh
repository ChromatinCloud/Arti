#!/bin/bash

# This script downloads the specified GRCh38 files from the Ensembl FTP site.

# Get repo root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_DATA_DIR="$REPO_ROOT/.refs/functional_predictions/plugin_data"

# Create directories in the correct location
mkdir -p "$PLUGIN_DATA_DIR/regulatory"
mkdir -p "$PLUGIN_DATA_DIR/phenotype" 
mkdir -p "$PLUGIN_DATA_DIR/splicing"

# URLs to download
urls=(
  "https://ftp.ensembl.org/pub/release-114/variation/Enformer/enformer_grch38.vcf.gz"
  "https://ftp.ensembl.org/pub/release-114/variation/Enformer/enformer_grch38.vcf.gz.tbi"
  "https://ftp.ensembl.org/pub/release-114/variation/PhenotypeOrthologous/PhenotypesOrthologous_homo_sapiens_112_GRCh38.gff3.gz"
  "https://ftp.ensembl.org/pub/release-114/variation/PhenotypeOrthologous/PhenotypesOrthologous_homo_sapiens_112_GRCh38.gff3.gz.tbi"
  "https://ftp.ensembl.org/pub/release-114/variation/SpliceVault/SpliceVault_data_GRCh38.tsv.gz"
  "https://ftp.ensembl.org/pub/release-114/variation/SpliceVault/SpliceVault_data_GRCh38.tsv.gz.tbi"
)

# Function to download files
download_files() {
  for url in "${urls[@]}"; do
    # Extract filename and determine correct directory
    filename=$(basename "$url")
    
    if [[ "$url" == *"Enformer"* ]]; then
      target_dir="$PLUGIN_DATA_DIR/regulatory"
    elif [[ "$url" == *"PhenotypeOrthologous"* ]]; then
      target_dir="$PLUGIN_DATA_DIR/phenotype"
    elif [[ "$url" == *"SpliceVault"* ]]; then
      target_dir="$PLUGIN_DATA_DIR/splicing"
    else
      echo "Error: Unknown plugin data source for $filename"
      continue
    fi
    
    echo "Downloading $filename to $target_dir"
    wget -P "$target_dir" "$url"
  done
}

# Execute the download function
download_files

echo "Download complete."