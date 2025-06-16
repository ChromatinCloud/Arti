#!/usr/bin/env bash
set -euo pipefail

#
# VEP Setup Script for Annotation Engine
# Uses Docker for maximum compatibility and reproducibility
#

# --- Configuration ------------------------------------------------------------
VEP_VERSION="114"
VEP_ASSEMBLY="GRCh38"
SPECIES="homo_sapiens"

# Docker tag logic: allow override, default to first 114-series image, fallback to latest
DEFAULT_DOCKER_TAG="release_114.1"
DOCKER_TAG="${VEP_DOCKER_TAG:-$DEFAULT_DOCKER_TAG}"

# --- Colors for output --------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Directory Setup ----------------------------------------------------------
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)")"
REFS_DIR="$REPO_ROOT/.refs"
VEP_DIR="$REFS_DIR/vep_setup"
VEP_CACHE_DIR="$REFS_DIR/functional_predictions/vep_cache"
VEP_PLUGINS_DIR="$REFS_DIR/functional_predictions/vep_plugins"

mkdir -p "$VEP_CACHE_DIR" "$VEP_PLUGINS_DIR"

# --- Logging ------------------------------------------------------------------
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Helpers ------------------------------------------------------------------
image_ref() { echo "ensemblorg/ensembl-vep:${DOCKER_TAG}"; }

# --- Docker Checks ------------------------------------------------------------
check_docker() {
  if ! command -v docker &>/dev/null; then
    log_error "Docker is not installed!"
    log_info  "Install Docker: https://docs.docker.com/get-docker/"
    return 1
  fi
  if ! docker info &>/dev/null; then
    log_error "Docker daemon is not running!"
    log_info  "Please start Docker and try again."
    return 1
  fi
  log_success "Docker is installed and running"
  return 0
}

# --- Pull Image ---------------------------------------------------------------
pull_vep_image() {
  local img
  img="$(image_ref)"
  
  if docker image inspect "$img" &>/dev/null; then
    log_success "VEP Docker image already exists: $img"
    return 0
  fi
  
  log_info "Pulling VEP Docker image: ${img}"
  if docker pull "${img}"; then
    log_success "VEP Docker image pulled successfully"
    return 0
  else
    log_error "Failed to pull VEP Docker image"
    return 1
  fi
}

# --- Check Cache --------------------------------------------------------------
check_vep_cache() {
  local cache_subdir extracted_cache
  cache_subdir="${SPECIES}/${VEP_VERSION}_${VEP_ASSEMBLY}"
  extracted_cache="$VEP_CACHE_DIR/$cache_subdir"
  
  # Check if cache is already extracted and ready
  if [[ -d "$extracted_cache" ]] && [[ -d "$extracted_cache/1" ]]; then
    log_success "VEP cache already ready at: $extracted_cache"
    return 0
  fi
  
  # Check if cache exists in tmp directory (user's setup)
  local tmp_cache="$VEP_DIR/tmp/$cache_subdir"
  if [[ -d "$tmp_cache" ]]; then
    log_info "Moving VEP cache from tmp to proper location..."
    mv "$tmp_cache" "$extracted_cache"
    log_success "VEP cache moved to: $extracted_cache"
    return 0
  fi
  
  if [[ "${force_download:-false}" == "true" ]]; then
    log_warning "VEP cache not found. This would require downloading ~15-20 GB"
    log_error "Automatic cache download not implemented yet. Please manually set up cache."
    return 1
  else
    log_warning "VEP cache not found. Use --force to attempt download (not implemented)"
    log_info "Continuing without cache - VEP may not work properly"
    return 0
  fi
}

# --- Plugins ------------------------------------------------------------------
download_plugins() {
  log_info "Checking VEP plugins..."
  
  # Check if plugins are already downloaded
  if [[ -d "$VEP_PLUGINS_DIR/.git" ]] && [[ -f "$VEP_PLUGINS_DIR/dbNSFP.pm" ]]; then
    log_success "VEP plugins already downloaded"
    return 0
  fi
  
  log_info "Downloading VEP plugins repository..."
  if [[ -d "$VEP_PLUGINS_DIR/.git" ]]; then
    cd "$VEP_PLUGINS_DIR"
    git fetch --quiet
    git checkout "release/${VEP_VERSION}" --quiet 2>/dev/null || {
      log_warning "Release branch not available, using main"
      git checkout main --quiet
    }
  else
    # Try release branch first, fallback to main
    if ! git clone --depth 1 --branch "release/${VEP_VERSION}" \
        https://github.com/Ensembl/VEP_plugins.git "$VEP_PLUGINS_DIR" 2>/dev/null; then
      log_warning "Release branch not available, cloning main branch"
      git clone --depth 1 \
        https://github.com/Ensembl/VEP_plugins.git "$VEP_PLUGINS_DIR"
    fi
  fi
  cd "$REPO_ROOT"
  log_success "VEP plugins downloaded"
  return 0
}

# --- Plugin Data Files -------------------------------------------------------
check_plugin_data() {
  log_info "Checking plugin data files..."
  
  local missing_files=0
  local required_files=(
    "dbNSFP5.1.gz"
    "AlphaMissense_hg38.tsv.gz"
    "revel_all_chromosomes.tsv.gz"
    "PrimateAI_scores_v0.2.tsv.gz"
  )
  
  for file in "${required_files[@]}"; do
    # Check in plugin data directory
    if [[ ! -f "$REFS_DIR/functional_predictions/plugin_data/pathogenicity/$file" ]] && 
       [[ ! -f "$REFS_DIR/functional_predictions/plugin_data/protein_impact/$file" ]]; then
      log_warning "Missing plugin data file: $file"
      ((missing_files++))
    fi
  done
  
  if [[ $missing_files -gt 0 ]]; then
    log_warning "$missing_files plugin data files are missing"
    log_info "Download plugin data files manually or VEP plugins won't work"
    log_info "See documentation for plugin data URLs"
  else
    log_success "All required plugin data files present"
  fi
}

# --- Wrapper Script -----------------------------------------------------------
create_vep_wrapper() {
  local wrapper_path="$REPO_ROOT/scripts/vep"
  log_info "Creating VEP wrapper script..."
  cat > "$wrapper_path" <<EOF
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="\$(cd "\$SCRIPT_DIR/.." && pwd)"
REFS_DIR="\$REPO_ROOT/.refs"
VEP_CACHE_DIR="\$REFS_DIR/functional_predictions/vep_cache"
VEP_PLUGINS_DIR="\$REFS_DIR/functional_predictions/vep_plugins"
DOCKER_TAG="${DOCKER_TAG}"

INPUT_DIR="\$(pwd)"
OUTPUT_DIR="\$(pwd)"

for arg in "\$@"; do
  [[ -f "\$arg" ]] && { INPUT_DIR="\$(cd "\$(dirname "\$arg")" && pwd)"; break; }
done

docker run --rm \\
  -v "\$VEP_CACHE_DIR:/opt/vep/.vep:ro" \\
  -v "\$VEP_PLUGINS_DIR:/opt/vep/plugins:ro" \\
  -v "\$INPUT_DIR:/data" \\
  -v "\$OUTPUT_DIR:/output" \\
  -w /data \\
  "ensemblorg/ensembl-vep:\${DOCKER_TAG}" \\
  vep \\
  --cache \\
  --offline \\
  --dir_cache /opt/vep/.vep \\
  --dir_plugins /opt/vep/plugins \\
  --fasta /opt/vep/.vep/homo_sapiens/114_GRCh38/Homo_sapiens.GRCh38.dna.toplevel.fa.gz \\
  "\$@"
EOF
  chmod +x "$wrapper_path"
  log_success "VEP wrapper script created at: $wrapper_path"
  return 0
}

# --- Main ---------------------------------------------------------------------
setup_vep() {
  log_info "Starting VEP setup using Docker..."
  check_docker        || return 1
  pull_vep_image      || return 1
  check_vep_cache     || return 1
  download_plugins    || return 1
  check_plugin_data   || return 1
  create_vep_wrapper  || return 1

  log_success "VEP setup completed successfully!"
  echo
  log_info "VEP Configuration:"
  log_info "  Docker image: $(image_ref)"
  log_info "  Cache dir   : $VEP_CACHE_DIR"
  log_info "  Plugins dir : $VEP_PLUGINS_DIR"
  log_info "  Wrapper     : $REPO_ROOT/scripts/vep"
  echo
}

# --- CLI ----------------------------------------------------------------------
show_usage() {
  echo "Usage: $0 [--force] [--help]"
  echo "Options:"
  echo "  --force    Force download of cache (not implemented)"
  echo "  --help     Show this help message"
}

main() {
  force_download=false  # Make global for use in check_vep_cache
  while [[ $# -gt 0 ]]; do
    case $1 in
      --force) force_download=true; shift ;;
      --help)  show_usage; exit 0 ;;
      *)       log_error "Unknown option: $1"; show_usage; exit 1 ;;
    esac
  done
  setup_vep
}

main "$@"