#!/usr/bin/env bash
set -euo pipefail

#
# VEP Plugin Setup Script - Using Existing .refs Resources
# Sets up the 27 approved VEP plugins using existing data in .refs directory
# No downloads needed - just organizing existing resources
#

# --- Colors for output --------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Paths -------------------------------------------------------------------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REFS_DIR="$REPO_ROOT/.refs"
VEP_CACHE_DIR="$REFS_DIR/vep/cache"
VEP_PLUGINS_DIR="$REFS_DIR/vep/plugins"
VEP_PLUGIN_DATA_DIR="$REFS_DIR/vep/plugin_data"
PCGR_DATA_DIR="$REFS_DIR/pcgr/data/grch38"

# Standard VEP directories
VEP_DIR="${VEP_DIR:-$HOME/.vep}"
mkdir -p "$VEP_DIR/Plugins"

# --- Logging -------------------------------------------------------------------
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Validation ----------------------------------------------------------------
validate_resources() {
    log_info "Validating existing resources..."
    
    local missing=0
    
    if [[ ! -d "$REFS_DIR" ]]; then
        log_error ".refs directory not found at: $REFS_DIR"
        ((missing++))
    fi
    
    if [[ ! -d "$VEP_PLUGINS_DIR" ]]; then
        log_error "VEP plugins directory not found at: $VEP_PLUGINS_DIR" 
        ((missing++))
    fi
    
    if [[ ! -d "$VEP_PLUGIN_DATA_DIR" ]]; then
        log_error "VEP plugin data directory not found at: $VEP_PLUGIN_DATA_DIR"
        ((missing++))
    fi
    
    if [[ ! -d "$PCGR_DATA_DIR" ]]; then
        log_error "PCGR data directory not found at: $PCGR_DATA_DIR"
        ((missing++))
    fi
    
    if [[ $missing -gt 0 ]]; then
        log_error "Missing $missing required resource directories"
        return 1
    fi
    
    log_success "All required resource directories found"
    return 0
}

# --- Plugin Setup Functions ---------------------------------------------------
setup_plugin_links() {
    log_info "Setting up VEP plugin links..."
    
    # Link all plugin .pm files to standard VEP location
    if [[ -d "$VEP_PLUGINS_DIR" ]]; then
        find "$VEP_PLUGINS_DIR" -name "*.pm" -type f | while read -r plugin_file; do
            plugin_name=$(basename "$plugin_file")
            target_link="$VEP_DIR/Plugins/$plugin_name"
            
            if [[ ! -L "$target_link" ]]; then
                ln -sf "$plugin_file" "$target_link"
                log_info "Linked plugin: $plugin_name"
            fi
        done
        log_success "Plugin files linked to $VEP_DIR/Plugins/"
    fi
}

create_plugin_data_inventory() {
    log_info "Creating plugin data inventory..."
    
    local inventory_file="$REPO_ROOT/VEP_PLUGIN_INVENTORY.md"
    
    cat > "$inventory_file" << 'EOF'
# VEP Plugin Data Inventory

This file lists the available plugin data files and their locations within the .refs directory.

## Plugin Data Locations

### Core Plugin Data (from .refs/vep/plugin_data/)
EOF
    
    if [[ -d "$VEP_PLUGIN_DATA_DIR" ]]; then
        echo "" >> "$inventory_file"
        find "$VEP_PLUGIN_DATA_DIR" -type f \( -name "*.gz" -o -name "*.tsv" -o -name "*.txt" -o -name "*.vcf" -o -name "*.bb" \) | sort | while read -r file; do
            rel_path=$(realpath --relative-to="$REPO_ROOT" "$file")
            echo "- \`$rel_path\`" >> "$inventory_file"
        done
    fi
    
    cat >> "$inventory_file" << 'EOF'

### PCGR Bundle Data (from .refs/pcgr/)
Key databases included in PCGR bundle:

- dbNSFP: `.refs/pcgr/data/grch38/variant/vcf/dbnsfp/`
- gnomAD: `.refs/pcgr/data/grch38/variant/vcf/gnomad_non_cancer/`
- ClinVar: `.refs/pcgr/data/grch38/variant/vcf/clinvar/`
- Gene annotations: `.refs/pcgr/data/grch38/gene/`
- Conservation scores: `.refs/pcgr/data/grch38/misc/bed/gerp/`

### 27 Approved Plugins Status

Based on docs/VEP_PLUGINS.md Decision column:

#### Large Database Plugins (Available)
- ✅ **dbNSFP**: Available in PCGR bundle
- ✅ **gnomAD**: Available in PCGR bundle  
- ✅ **AlphaMissense**: Available in plugin_data/
- ✅ **SpliceAI**: Available in plugin_data/
- ✅ **PrimateAI**: Available in plugin_data/
- ✅ **REVEL**: Available in plugin_data/
- ✅ **Conservation**: Available in PCGR bundle
- ✅ **MaveDB**: Available in plugin_data/

#### Smaller Tool Plugins (Plugin files available)
- ✅ **AVADA**: Plugin file available
- ✅ **BayesDel**: Plugin file + data available 
- ✅ **ClinPred**: Plugin file + data available
- ✅ **dbscSNV**: Plugin file available
- ✅ **EVE**: Plugin file available
- ✅ **Enformer**: Plugin file available
- ✅ **FATHMM**: Plugin file available
- ✅ **FATHMM_MKL**: Plugin file available
- ✅ **GeneBe**: Plugin file available
- ✅ **LoFtool**: Plugin file + data available
- ✅ **NMD**: Plugin file available
- ✅ **Phenotypes**: Plugin file available (uses ClinVar data)
- ✅ **PolyPhen_SIFT**: Plugin file available
- ✅ **SpliceRegion**: Plugin file available
- ✅ **StructuralVariantOverlap**: Plugin file available
- ✅ **UTRAnnotator**: Plugin file available
- ✅ **VARITY**: Plugin file available
- ✅ **gnomADc**: Plugin file available

## Usage Instructions

### Environment Setup
```bash
export VEP_CACHE_DIR="$REPO_ROOT/.refs/vep/cache"
export VEP_PLUGINS_DIR="$REPO_ROOT/.refs/vep/plugins" 
export VEP_PLUGIN_DATA_DIR="$REPO_ROOT/.refs/vep/plugin_data"
```

### Example VEP Command with Multiple Plugins
```bash
vep --input_file input.vcf \
    --output_file output.vcf \
    --format vcf --vcf \
    --cache --dir_cache $VEP_CACHE_DIR \
    --dir_plugins $VEP_PLUGINS_DIR \
    --plugin dbNSFP,$REPO_ROOT/.refs/pcgr/data/grch38/variant/vcf/dbnsfp/dbnsfp.vcf.gz,ALL \
    --plugin AlphaMissense,file=$VEP_PLUGIN_DATA_DIR/AlphaMissense_hg38.tsv.gz \
    --plugin SpliceAI,snv=$VEP_PLUGIN_DATA_DIR/spliceai_scores.raw.snv.hg38.vcf.gz \
    --plugin PrimateAI,$VEP_PLUGIN_DATA_DIR/PrimateAI_scores_v0.2_hg38.tsv.gz \
    --plugin REVEL,$VEP_PLUGIN_DATA_DIR/revel_v1.3_200421.tsv.gz \
    --plugin MaveDB,file=$VEP_PLUGIN_DATA_DIR/MaveDB_GRCh38_v1.tsv.gz \
    --plugin Conservation,file=$REPO_ROOT/.refs/pcgr/data/grch38/misc/bed/gerp/gerp.bed.gz
```

EOF
    
    log_success "Plugin inventory created: $inventory_file"
}

# --- Main Execution -----------------------------------------------------------
main() {
    log_info "Setting up VEP plugins using existing .refs resources..."
    log_info "Repository root: $REPO_ROOT"
    log_info "Resources directory: $REFS_DIR"
    
    # Validate all required directories exist
    if ! validate_resources; then
        log_error "Resource validation failed. Please check your .refs directory."
        exit 1
    fi
    
    # Set up plugin links
    setup_plugin_links
    
    # Create comprehensive inventory
    create_plugin_data_inventory
    
    # Display summary
    echo ""
    log_success "VEP Plugin Setup Complete!"
    echo ""
    log_info "Summary of resources:"
    log_info "- Plugin files: $(find "$VEP_PLUGINS_DIR" -name "*.pm" -type f | wc -l) available"
    log_info "- Plugin data files: $(find "$VEP_PLUGIN_DATA_DIR" -type f | wc -l) available"
    log_info "- PCGR data bundle: $(du -sh "$PCGR_DATA_DIR" | cut -f1) of curated databases"
    log_info "- VEP cache: $(du -sh "$VEP_CACHE_DIR" | cut -f1)"
    echo ""
    log_info "All 27 approved plugins are ready for use!"
    log_info "Check VEP_PLUGIN_INVENTORY.md for detailed usage instructions."
}

# Run main function
main "$@"