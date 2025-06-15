```bash
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
VEP_DIR="$REFS_DIR/vep"
VEP_CACHE_DIR="$VEP_DIR/cache"
VEP_PLUGINS_DIR="$VEP_DIR/plugins"

mkdir -p "$VEP_CACHE_DIR" "$VEP_PLUGINS_DIR"

# --- Logging ------------------------------------------------------------------
log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Helpers ------------------------------------------------------------------
image_ref() { echo "ensemblorg/ensembl-vep:${DOCKER_TAG}"; }

tag_exists() {
  curl -fsSL "https://registry.hub.docker.com/v2/repositories/ensemblorg/ensembl-vep/tags/${DOCKER_TAG}" \
    >/dev/null 2>&1
}

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
  if ! tag_exists; then
    log_warning "Tag '${DOCKER_TAG}' not found on Docker Hub – falling back to 'latest'"
    DOCKER_TAG="latest"
    img="$(image_ref)"
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

# --- Download Cache -----------------------------------------------------------
download_vep_cache() {
  local img
  img="$(image_ref)"
  log_info "Checking for existing VEP cache..."
  if [[ -d "$VEP_CACHE_DIR/${SPECIES}/${VEP_VERSION}_${VEP_ASSEMBLY}" ]]; then
    log_info "VEP cache already exists. Use --force to re-download."
    return 0
  fi
  log_info "Downloading VEP cache for $SPECIES $VEP_ASSEMBLY (this may take a while)…"
  log_warning "This will download ~15-20 GB"
  if docker run --rm \
      -v "$VEP_CACHE_DIR:/opt/vep/.vep" \
      "${img}" \
      perl /opt/vep/src/ensembl-vep/INSTALL.pl \
      --AUTO c \
      --SPECIES "$SPECIES" \
      --ASSEMBLY "$VEP_ASSEMBLY" \
      --CACHEDIR /opt/vep/.vep \
      --NO_UPDATE; then
    log_success "VEP cache downloaded successfully"
    return 0
  else
    log_error "Failed to download VEP cache"
    return 1
  fi
}

# --- Plugins ------------------------------------------------------------------
download_plugins() {
  log_info "Downloading VEP plugins repository..."
  if [[ -d "$VEP_PLUGINS_DIR/.git" ]]; then
    cd "$VEP_PLUGINS_DIR"
    git fetch --quiet
    git checkout "release/${VEP_VERSION}" --quiet
  else
    git clone --depth 1 --branch "release/${VEP_VERSION}" \
      https://github.com/Ensembl/VEP_plugins.git "$VEP_PLUGINS_DIR"
  fi
  cd "$REPO_ROOT"
  log_success "VEP plugins downloaded"
  return 0
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
VEP_CACHE_DIR="\$REFS_DIR/vep/cache"
VEP_PLUGINS_DIR="\$REFS_DIR/vep/plugins"
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
  download_vep_cache  || return 1
  download_plugins    || return 1
  create_vep_wrapper  || return 1

  log_success "VEP setup completed successfully!"
  echo
  log_info "VEP Configuration:"
  log_info "  Docker image: \$(image_ref)"
  log_info "  Cache dir   : $VEP_CACHE_DIR"
  log_info "  Plugins dir : $VEP_PLUGINS_DIR"
  log_info "  Wrapper     : $REPO_ROOT/scripts/vep"
  echo
}

# --- CLI ----------------------------------------------------------------------
show_usage() {
  echo "Usage: $0 [--force] [--help]"
}

main() {
  local force_download=false
  while [[ \$# -gt 0 ]]; do
    case \$1 in
      --force) force_download=true; shift ;;
      --help)  show_usage; exit 0 ;;
      *)       log_error "Unknown option: \$1"; show_usage; exit 1 ;;
    esac
  done
  setup_vep
}

main "\$@"
```

**Changes made**

* Introduced `DEFAULT_DOCKER_TAG="release_114.1"` with `VEP_DOCKER_TAG` override and automatic fallback to `latest` if the tag is missing.
* Added `tag_exists()` helper that uses the Docker Hub API to verify tag presence before pulling.
* Updated every reference to the Docker image to use the dynamic `DOCKER_TAG` via the `image_ref()` helper and in the generated wrapper script.
* Displayed the resolved image reference in the final configuration summary.
