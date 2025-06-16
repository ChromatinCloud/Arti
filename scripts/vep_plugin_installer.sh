#!/bin/bash

# ==============================================================================
#
#  Fully Automated VEP & Plugin Installation Script (Version 5.0)
#
#  This non-interactive script automates the entire VEP setup.
#  Paths are hardcoded in the configuration section below.
#
#  v5.0 Changes:
#  - Uninstalls default Homebrew mysql and installs mysql@8.0 to fix the
#    fundamental library incompatibility with the DBD::mysql driver.
#  - Updates all paths to point to the mysql@8.0 installation.
#
# ==============================================================================

# --- CONFIGURATION ---
# Set your project-specific paths here.
INSTALL_DIR="/Users/lauferva/Desktop/Arti/ensembl-vep"
VEP_DATA_DIR="/Users/lauferva/Desktop/Arti/.refs/vep"
# --- END CONFIGURATION ---


# --- Script Setup (Do not modify below this line) ---
set -e
CACHE_DIR="$VEP_DATA_DIR/cache"
PLUGINS_DIR="$VEP_DATA_DIR/plugins"
PERL_VERSION="5.26.2"
VEP_PLUGINS_LIST=(
  "AlphaMissense" "AVADA" "BayesDel" "ClinPred" "Conservation" "dbscSNV" "EVE"
  "Enformer" "FATHMM" "FATHMM_MKL" "GeneBe" "LoFtool" "MaveDB" "NMD" "Phenotypes"
  "PolyPhen_SIFT" "PrimateAI" "REVEL" "SpliceAI" "SpliceRegion"
  "StructuralVariantOverlap" "UTRAnnotator" "VARITY" "gnomADc" "gnomAD"
)
DBNSFP_PLUGIN="dbNSFP"

# --- Helper Functions ---
log_info() { echo -e "\n\033[1;34m[INFO]\033[0m $1"; }
log_success() { echo -e "\033[1;32m[SUCCESS]\033[0m $1"; }
log_warn() { echo -e "\033[1;33m[WARNING]\033[0m $1"; }
add_to_profile() {
  local line="$1"
  local profile_file="$2"
  if ! grep -qF -- "$line" "$profile_file"; then
    log_info "Adding '$line' to $profile_file"
    echo "$line" >> "$profile_file"
  fi
}

# --- Installation Functions ---
install_dependencies() {
    log_info "Checking/installing dependencies: Xcode Tools, Homebrew, xz..."
    if ! xcode-select -p &>/dev/null; then xcode-select --install; fi
    if ! command -v brew &>/dev/null; then /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; fi
    if [ -x "/opt/homebrew/bin/brew" ]; then eval "$(/opt/homebrew/bin/brew shellenv)"; fi
    brew install xz || true

    # --- MODIFIED COMMANDS FOR v5.0 ---
    log_info "Uninstalling any existing default mysql to prevent version conflicts..."
    # The '|| true' prevents an error if it's not installed, allowing the script to continue.
    brew uninstall mysql || true
    brew untap mysql || true
    log_info "Installing mysql@8.0 for compatibility with the DBD::mysql driver..."
    brew install mysql@8.0
}

install_perl_environment() {
    log_info "Setting up Perl environment with Perlbrew..."
    if ! command -v perlbrew &>/dev/null; then
        curl -L http://install.perlbrew.pl | bash
        add_to_profile "source $HOME/perl5/perlbrew/etc/bashrc" "$SHELL_PROFILE"
        source "$HOME/perl5/perlbrew/etc/bashrc"
    fi
    if ! perlbrew list | grep -q "$PERL_VERSION"; then
        log_info "Installing Perl $PERL_VERSION (with --notest to avoid common build failures)..."
        perlbrew install perl-$PERL_VERSION --as $PERL_VERSION -j 5 --notest -D usethreads -D 64bitall -D useshrplib
    fi
    perlbrew switch "$PERL_VERSION"
    log_info "Installing cpanm (forcing overwrite if it exists)..."
    perlbrew install-cpanm -f

    # --- MODIFIED COMMANDS FOR v5.0 ---
    log_info "Installing required Perl modules using mysql@8.0..."
    local mysql_prefix="$(brew --prefix mysql@8.0)"
    local mysql_config_path="${mysql_prefix}/bin/mysql_config"
    
    if [ ! -f "$mysql_config_path" ]; then
      log_warn "FATAL: Cannot find mysql_config at $mysql_config_path. Aborting."
      exit 1
    fi

    # Set environment for build-time (finding mysql_config) and run-time (finding .dylib files)
    export PATH="${mysql_prefix}/bin:$PATH"
    export DYLD_LIBRARY_PATH="${mysql_prefix}/lib:$DYLD_LIBRARY_PATH"
    
    cpanm DBI
    cpanm --configure-args="--mysql_config=$mysql_config_path" DBD::mysql@4.050

    log_info "Installing remaining modules..."
    cpanm --force LWP
    cpanm Test::Differences Test::Exception Test::Perl::Critic Archive::Zip PadWalker Error Devel::Cycle Role::Tiny::With List::MoreUtils

    # Add the paths to the shell profile for future use
    add_to_profile "export PATH=\"${mysql_prefix}/bin:\$PATH\"" "$SHELL_PROFILE"
    add_to_profile "export DYLD_LIBRARY_PATH=\"${mysql_prefix}/lib:\$DYLD_LIBRARY_PATH\"" "$SHELL_PROFILE"
}

install_vep_core() {
    log_info "Cloning the ensembl-vep repository into $INSTALL_DIR..."
    mkdir -p "$(dirname "$INSTALL_DIR")"
    cd "$(dirname "$INSTALL_DIR")"
    if [ -d "$(basename "$INSTALL_DIR")" ]; then
        log_warn "Found existing ensembl-vep directory. Removing for fresh install."
        rm -rf "$(basename "$INSTALL_DIR")"
    fi
    git clone https://github.com/ensembl/ensembl-vep "$(basename "$INSTALL_DIR")"
    cd "$INSTALL_DIR"
    log_info "Running the VEP installer to download VEP core, BioPerl, and cache..."
    log_warn "This is the long step (can be 1-2 hours) that downloads the cache files."
    perl INSTALL.pl --NO_TEST --AUTO p -g all --CACHEDIR "$CACHE_DIR" --PLUGINSDIR "$PLUGINS_DIR"
}

install_vep_plugins() {
    log_info "Proceeding to plugin installation..."
    cd "$INSTALL_DIR"
    local CSV_PLUGINS=$(IFS=,; echo "${VEP_PLUGINS_LIST[*]}")
    log_info "Installing the first batch of plugins..."
    perl INSTALL.pl --NO_TEST --AUTO p --PLUGINS "$CSV_PLUGINS" --CACHEDIR "$CACHE_DIR" --PLUGINSDIR "$PLUGINS_DIR"
    log_info "Installing the large dbNSFP plugin..."
    perl INSTALL.pl --NO_TEST --AUTO p --PLUGINS "$DBNSFP_PLUGIN" --CACHEDIR "$CACHE_DIR" --PLUGINSDIR "$PLUGINS_DIR"
}

# --- Main Script Logic ---
log_info "VEP Automated Installation Script v5.0 (Final)"
log_info "VEP code will be installed in: $INSTALL_DIR"
log_info "VEP data (cache/plugins) will be in: $VEP_DATA_DIR"
mkdir -p "$INSTALL_DIR"
mkdir -p "$CACHE_DIR"
mkdir -p "$PLUGINS_DIR"

SHELL_PROFILE="$HOME/.bash_profile"
if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
  SHELL_PROFILE="$HOME/.zshrc"
fi
log_info "Using shell profile: $SHELL_PROFILE"

VEP_EXECUTABLE="$INSTALL_DIR/vep"
INSTALL_VEP_CORE=true
if [ -f "$VEP_EXECUTABLE" ] && [ -d "$CACHE_DIR/homo_sapiens" ]; then
    log_warn "Existing VEP installation and cache found. Skipping core install."
    INSTALL_VEP_CORE=false
else
    log_info "No existing VEP installation found. Proceeding with full setup."
    INSTALL_VEP_CORE=true
fi

if [ "$INSTALL_VEP_CORE" = true ]; then
    install_dependencies
    install_perl_environment
    install_vep_core
else
    log_info "Sourcing Perl environment for plugin installation..."
    if ! command -v perlbrew &>/dev/null; then
      source "$HOME/perl5/perlbrew/etc/bashrc"
    fi
    perlbrew switch "$PERL_VERSION"
fi

install_vep_plugins

# --- Finalization ---
log_success "VEP Automated Script Finished!"
log_warn "CRITICAL: To run VEP, you must use the custom paths specified in this script."
log_info "Example command to run VEP:"
echo
echo "cd \"$INSTALL_DIR\""
echo "./vep -i your_input.vcf -o your_output.vcf --cache --force_overwrite \\"
echo "    --dir_cache \"$CACHE_DIR\" \\"
echo "    --dir_plugins \"$PLUGINS_DIR\" \\"
echo "    --plugin REVEL"
echo
log_warn "To ensure all environment changes take effect, please close and RESTART your terminal window before running the command above."

exit 0