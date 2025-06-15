#!/usr/bin/env bash
set -euo pipefail

#
# Comprehensive Knowledge Base Setup Script for Annotation Engine
# "Recipe Approach" - Downloads raw, standard format files from authoritative sources
# Inspired by PCGR's data bundle but using original file formats
#

# --- Configuration ---
ASSEMBLY="GRCh38"
ENSEMBL_VERSION="114"

# --- Colors for output ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Directory Setup ---
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)")"
REFS_DIR="$REPO_ROOT/.refs"

# Create comprehensive directory structure
mkdir -p "$REFS_DIR"/{clinvar,gnomad,dbsnp,tcga,open_targets,uniprot,pfam,cancermine,cancer_hotspots,civic,oncokb,biomarkers,gene_mappings,oncotree,clingen,depmap,oncovi,temp}

# --- Logging Functions ---
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# --- Knowledge Base Definitions ---
# Each entry: URL|filename|description|size_estimate|doi|checksum_method
declare -A KNOWLEDGE_BASES

# Create audit log file
AUDIT_LOG="$REFS_DIR/download_audit.tsv"
mkdir -p "$(dirname "$AUDIT_LOG")"
if [[ ! -f "$AUDIT_LOG" ]]; then
    echo -e "timestamp\tkb_key\tfilename\turl\tdescription\tfile_size_bytes\tchecksum_md5\tchecksum_sha256\tdoi\tversion\tstatus" > "$AUDIT_LOG"
fi

# Clinical Databases
KNOWLEDGE_BASES[clinvar_vcf]="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_${ASSEMBLY}/clinvar.vcf.gz|clinvar.vcf.gz|ClinVar Clinical Significance VCF|200MB|10.1093/nar/gkz972|server_provided"
KNOWLEDGE_BASES[clinvar_vcf_tbi]="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_${ASSEMBLY}/clinvar.vcf.gz.tbi|clinvar.vcf.gz.tbi|ClinVar VCF Index|1MB|10.1093/nar/gkz972|server_provided"
KNOWLEDGE_BASES[clinvar_tsv]="https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz|variant_summary.txt.gz|ClinVar Variant Summary TSV|150MB|10.1093/nar/gkz972|server_provided"

# Population Frequencies  
KNOWLEDGE_BASES[gnomad_genomes]="gs://gcp-public-data--gnomad/release/4.1/vcf-${ASSEMBLY,,}/genomes/gnomad.genomes.v4.1.sites.${ASSEMBLY,,}.vcf.bgz|gnomad_genomes.vcf.bgz|gnomAD Genomes Population Frequencies|150GB"
KNOWLEDGE_BASES[gnomad_genomes_tbi]="gs://gcp-public-data--gnomad/release/4.1/vcf-${ASSEMBLY,,}/genomes/gnomad.genomes.v4.1.sites.${ASSEMBLY,,}.vcf.bgz.tbi|gnomad_genomes.vcf.bgz.tbi|gnomAD Genomes Index|1GB"
KNOWLEDGE_BASES[gnomad_exomes]="gs://gcp-public-data--gnomad/release/4.1/vcf-${ASSEMBLY,,}/exomes/gnomad.exomes.v4.1.sites.${ASSEMBLY,,}.vcf.bgz|gnomad_exomes.vcf.bgz|gnomAD Exomes Population Frequencies|20GB"
KNOWLEDGE_BASES[gnomad_exomes_tbi]="gs://gcp-public-data--gnomad/release/4.1/vcf-${ASSEMBLY,,}/exomes/gnomad.exomes.v4.1.sites.${ASSEMBLY,,}.vcf.bgz.tbi|gnomad_exomes.vcf.bgz.tbi|gnomAD Exomes Index|200MB"

# Variant IDs
KNOWLEDGE_BASES[dbsnp]="https://ftp.ncbi.nlm.nih.gov/snp/latest_release/VCF/GCF_000001405.40.gz|dbsnp_latest.vcf.gz|dbSNP Common Variants|25GB"

# Cancer-Specific Databases
KNOWLEDGE_BASES[tcga_mc3]="https://api.gdc.cancer.gov/data/1c8cfe5f-e52d-41ba-94da-f15ea1337efc|mc3.v0.2.8.PUBLIC.maf.gz|TCGA MC3 Somatic Mutations|200MB"
KNOWLEDGE_BASES[cancer_hotspots]="https://www.cancerhotspots.org/files/hotspots_v3_hg38.vcf.gz|cancer_hotspots_v3.vcf.gz|Memorial Sloan Kettering Cancer Hotspots VCF|5MB"
KNOWLEDGE_BASES[cancer_hotspots_tbi]="https://www.cancerhotspots.org/files/hotspots_v3_hg38.vcf.gz.tbi|cancer_hotspots_v3.vcf.gz.tbi|Cancer Hotspots VCF Index|1MB"

# Drug-Target Associations
KNOWLEDGE_BASES[open_targets]="https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/latest/output/etl/json/targets/targets.json.gz|open_targets.json.gz|Open Targets Platform|500MB"
KNOWLEDGE_BASES[dgidb]="http://dgidb.org/data/monthly_tsvs/2024-Jan/interactions.tsv|dgidb_interactions.tsv|Drug-Gene Interaction Database|50MB"

# Protein Annotations
KNOWLEDGE_BASES[uniprot_sprot]="https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.dat.gz|uniprot_sprot.dat.gz|UniProt Swiss-Prot|300MB"
KNOWLEDGE_BASES[pfam]="https://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.hmm.gz|pfam_a.hmm.gz|Pfam Protein Families|100MB"

# Literature-Mined Data
KNOWLEDGE_BASES[cancermine]="https://zenodo.org/records/7689627/files/cancermine_collated.tsv?download=1|cancermine.tsv|CancerMine Literature Mining|20MB|10.1038/s41592-019-0422-y|manual_md5"

# Clinical Evidence APIs (downloaded as static files)
KNOWLEDGE_BASES[civic_variants]="https://civicdb.org/downloads/nightly/nightly-VariantSummaries.tsv|civic_variants.tsv|CIViC Clinical Evidence|5MB"
KNOWLEDGE_BASES[oncokb_genes]="https://www.oncokb.org/api/v1/utils/allCuratedGenes.txt|oncokb_genes.txt|OncoKB Cancer Genes|1MB"

# Biomarkers and Clinical Thresholds
KNOWLEDGE_BASES[clinical_biomarkers]="https://raw.githubusercontent.com/sigven/pcgr/main/pcgrdb/data/biomarkers.tsv|biomarkers.tsv|Clinical Biomarkers and Thresholds|2MB"

# Gene Mappings and Ontologies  
KNOWLEDGE_BASES[gene_mappings]="https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene_info.gz|gene_info.gz|NCBI Gene Information and Mappings|200MB|10.1093/nar/gkac1057|server_provided"
KNOWLEDGE_BASES[hgnc_mappings]="https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt|hgnc_complete_set.txt|HGNC Gene Symbol Mappings|5MB|10.1093/nar/gkac888|server_provided"

# Disease Ontologies
KNOWLEDGE_BASES[oncotree]="http://oncotree.mskcc.org/api/tumorTypes/tree?version=oncotree_latest_stable|oncotree.json|OncoTree Disease Classifications|1MB"
KNOWLEDGE_BASES[mondo_disease]="https://github.com/monarch-initiative/mondo/releases/latest/download/mondo.obo|mondo.obo|MONDO Disease Ontology|50MB"

# Gene Dosage Sensitivity (ClinGen)
KNOWLEDGE_BASES[clingen_dosage]="https://ftp.clinicalgenome.org/ClinGen_gene_curation_list_GRCh38.tsv|clingen_genes_GRCh38.tsv|ClinGen Gene Curation List|2MB"
KNOWLEDGE_BASES[clingen_haplo]="https://ftp.clinicalgenome.org/ClinGen_haploinsufficiency_gene_GRCh38.bed|clingen_haploinsufficiency_GRCh38.bed|ClinGen Haploinsufficiency Genes|1MB"
KNOWLEDGE_BASES[clingen_triplo]="https://ftp.clinicalgenome.org/ClinGen_triplosensitivity_gene_GRCh38.bed|clingen_triplosensitivity_GRCh38.bed|ClinGen Triplosensitivity Genes|1MB"

# Additional Cancer Hotspots Sources
KNOWLEDGE_BASES[msk_hotspots_snv]="https://www.cbioportal.org/webAPI/cancerhotspots/single-nucleotide-variants|msk_hotspots_snv.json|MSK Cancer Hotspots SNVs|10MB"
KNOWLEDGE_BASES[msk_hotspots_indel]="https://www.cbioportal.org/webAPI/cancerhotspots/indels|msk_hotspots_indel.json|MSK Cancer Hotspots Indels|5MB"
KNOWLEDGE_BASES[civic_hotspots]="https://civicdb.org/downloads/nightly/nightly-ClinicalEvidenceSummaries.tsv|civic_hotspots.tsv|CIViC Clinical Evidence Hotspots|10MB"
KNOWLEDGE_BASES[cosmic_cgc]="https://cancer.sanger.ac.uk/cosmic/file_download/GRCh38/cosmic/v97/cancer_gene_census.csv|cosmic_cgc.csv|COSMIC Cancer Gene Census|2MB"
KNOWLEDGE_BASES[msk_3d_hotspots]="https://www.3dhotspots.org/3d_hotspots.txt|msk_3d_hotspots.txt|MSK 3D Protein Structure Hotspots|5MB"

# Cell Line and Functional Genomics
KNOWLEDGE_BASES[depmap_mutations]="https://depmap.org/portal/api/download/file?file_name=OmicsSomaticMutationsMatrixHotspot.csv&bucket=depmap-external-downloads|depmap_mutations.csv|DepMap Cell Line Somatic Mutations|100MB"
KNOWLEDGE_BASES[depmap_gene_effect]="https://depmap.org/portal/api/download/file?file_name=CRISPRGeneEffect.csv&bucket=depmap-external-downloads|depmap_gene_effect.csv|DepMap CRISPR Gene Effects|200MB"

# Oncovi Curated Resources (MGCarta/OncoVI)
# Compiled from: COSMIC Cancer Gene Census + OncoKB + ClinVar + cancerhotspots.org + UniProt
# Processing: Python 3.8.8, VEP annotation, manual interpretation of oncogenicity criteria
# Publication: https://doi.org/10.1101/2024.10.10.24315072
KNOWLEDGE_BASES[oncovi_tsg]="https://github.com/MGCarta/oncovi/raw/main/resources/bona_fide_tsg.txt|oncovi_tsg.txt|OncoVI Tumor Suppressor Genes (COSMIC+OncoKB union)|1KB|10.1101/2024.10.10.24315072|server_provided"
KNOWLEDGE_BASES[oncovi_oncogenes]="https://github.com/MGCarta/oncovi/raw/main/resources/ogs_list.txt|oncovi_oncogenes.txt|OncoVI Oncogenes (COSMIC+OncoKB union)|1KB|10.1101/2024.10.10.24315072|server_provided" 
KNOWLEDGE_BASES[oncovi_hotspots]="https://github.com/MGCarta/oncovi/raw/main/resources/single_residue_dict.txt|oncovi_hotspots.json|OncoVI Single Residue Hotspots (cancerhotspots.org processed)|5MB|10.1101/2024.10.10.24315072|server_provided"
KNOWLEDGE_BASES[oncovi_indel_hotspots]="https://github.com/MGCarta/oncovi/raw/main/resources/inframe_indel_dict.txt|oncovi_indel_hotspots.json|OncoVI In-frame Indel Hotspots (cancerhotspots.org)|1MB|10.1101/2024.10.10.24315072|server_provided"
KNOWLEDGE_BASES[oncovi_domains]="https://github.com/MGCarta/oncovi/raw/main/resources/domains_dictionary.txt|oncovi_domains.json|OncoVI Protein Domains (UniProt processed)|2MB|10.1101/2024.10.10.24315072|server_provided"
KNOWLEDGE_BASES[oncovi_cgi]="https://github.com/MGCarta/oncovi/raw/main/resources/cgi_dictionary.txt|oncovi_cgi.json|OncoVI CGI Validated Mutations (Cancer Genome Interpreter)|3MB|10.1101/2024.10.10.24315072|server_provided"
KNOWLEDGE_BASES[oncovi_os2]="https://github.com/MGCarta/oncovi/raw/main/resources/os2_manually_selected.txt|oncovi_os2.txt|OncoVI OS2 Clinical Significance (ClinVar curated)|1KB|10.1101/2024.10.10.24315072|server_provided"
KNOWLEDGE_BASES[oncovi_amino_dict]="https://github.com/MGCarta/oncovi/raw/main/resources/amino_dict.txt|oncovi_amino_dict.txt|OncoVI Amino Acid Dictionary|1KB|10.1101/2024.10.10.24315072|server_provided"
KNOWLEDGE_BASES[oncovi_grantham]="https://github.com/MGCarta/oncovi/raw/main/resources/grantham.tsv|oncovi_grantham.tsv|OncoVI Grantham Distance Matrix|5KB|10.1101/2024.10.10.24315072|server_provided"

# --- Download Function ---
download_kb() {
    local kb_key=$1
    local force=${2:-false}
    
    if [[ ! "${KNOWLEDGE_BASES[$kb_key]+_}" ]]; then
        log_error "Unknown knowledge base: $kb_key"
        return 1
    fi
    
    IFS='|' read -r url filename description size_estimate doi checksum_method <<< "${KNOWLEDGE_BASES[$kb_key]}"
    
    # Set defaults for older entries without DOI/checksum
    doi=${doi:-"N/A"}
    checksum_method=${checksum_method:-"manual_md5"}
    
    # Determine target directory based on category
    local target_dir=""
    case "$kb_key" in
        clinvar_*) target_dir="$REFS_DIR/clinvar" ;;
        gnomad_*) target_dir="$REFS_DIR/gnomad" ;;
        dbsnp) target_dir="$REFS_DIR/dbsnp" ;;
        tcga_*) target_dir="$REFS_DIR/tcga" ;;
        open_targets|dgidb) target_dir="$REFS_DIR/open_targets" ;;
        uniprot_*) target_dir="$REFS_DIR/uniprot" ;;
        pfam) target_dir="$REFS_DIR/pfam" ;;
        cancermine) target_dir="$REFS_DIR/cancermine" ;;
        cancer_hotspots*|msk_hotspots*|civic_hotspots|cosmic_cgc|msk_3d_hotspots) target_dir="$REFS_DIR/cancer_hotspots" ;;
        civic_*) target_dir="$REFS_DIR/civic" ;;
        oncokb_*) target_dir="$REFS_DIR/oncokb" ;;
        clinical_biomarkers) target_dir="$REFS_DIR/biomarkers" ;;
        gene_mappings|hgnc_mappings) target_dir="$REFS_DIR/gene_mappings" ;;
        oncotree|mondo_disease) target_dir="$REFS_DIR/oncotree" ;;
        clingen_*) target_dir="$REFS_DIR/clingen" ;;
        depmap_*) target_dir="$REFS_DIR/depmap" ;;
        oncovi_*) target_dir="$REFS_DIR/oncovi" ;;
        *) target_dir="$REFS_DIR/temp" ;;
    esac
    
    local target_file="$target_dir/$filename"
    
    # Check if file exists and skip unless force
    if [[ -f "$target_file" && "$force" != "true" ]]; then
        log_info "$description already exists, skipping"
        return 0
    fi
    
    log_info "Downloading $description (estimated: $size_estimate)"
    log_warning "Target: $target_file"
    
    # Handle different download methods
    if [[ "$url" == gs://* ]]; then
        # Google Cloud Storage - requires gsutil
        if ! command -v gsutil &> /dev/null; then
            log_error "gsutil required for gnomAD downloads"
            log_info "Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
            return 1
        fi
        
        # Check if user is authenticated
        if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null | grep -q "."; then
            log_warning "gsutil is installed, but you may not be authenticated."
            log_info "Run 'gcloud auth login' if downloads fail."
        fi
        
        if gsutil -m cp "$url" "$target_file"; then
            log_success "$description downloaded successfully"
        else
            log_error "Failed to download $description"
            return 1
        fi
        
    elif [[ "$url" == https://api.gdc.cancer.gov/* ]]; then
        # TCGA GDC API - special handling
        log_info "Using TCGA GDC API for download..."
        if curl -L --fail --progress-bar --output "$target_file" "$url"; then
            log_success "$description downloaded successfully"
        else
            log_error "Failed to download $description"
            return 1
        fi
        
    else
        # Standard HTTP/HTTPS download
        if curl -L --fail --progress-bar --continue-at - --output "$target_file" "$url"; then
            log_success "$description downloaded successfully"
        else
            log_error "Failed to download $description"
            return 1
        fi
    fi
    
    # Verify download and calculate checksums
    if [[ -f "$target_file" && -s "$target_file" ]]; then
        local file_size=$(stat -f%z "$target_file" 2>/dev/null || stat -c%s "$target_file" 2>/dev/null || echo "0")
        
        # Calculate checksums
        local md5_checksum="N/A"
        local sha256_checksum="N/A"
        
        if command -v md5sum &> /dev/null; then
            md5_checksum=$(md5sum "$target_file" | cut -d' ' -f1)
        elif command -v md5 &> /dev/null; then
            md5_checksum=$(md5 -q "$target_file")
        fi
        
        if command -v sha256sum &> /dev/null; then
            sha256_checksum=$(sha256sum "$target_file" | cut -d' ' -f1)
        elif command -v shasum &> /dev/null; then
            sha256_checksum=$(shasum -a 256 "$target_file" | cut -d' ' -f1)
        fi
        
        # Log to audit file
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        local version=$(date +"%Y-%m-%d")
        echo -e "$timestamp\t$kb_key\t$filename\t$url\t$description\t$file_size\t$md5_checksum\t$sha256_checksum\t$doi\t$version\tsuccess" >> "$AUDIT_LOG"
        
        log_success "Verified: $description ($((file_size / 1024 / 1024)) MB) MD5: ${md5_checksum:0:8}..."
    else
        # Log failure to audit file
        local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
        local version=$(date +"%Y-%m-%d")
        echo -e "$timestamp\t$kb_key\t$filename\t$url\t$description\t0\tN/A\tN/A\t$doi\t$version\tfailed" >> "$AUDIT_LOG"
        
        log_error "Download verification failed: $description"
        return 1
    fi
    
    return 0
}

# --- Download Categories ---
download_essential() {
    local force=${1:-false}
    log_info "Downloading essential knowledge bases (small, core datasets)..."
    
    local essential_kbs=(
        "clinvar_vcf"
        "clinvar_vcf_tbi"
        "clinvar_tsv" 
        "civic_variants"
        "oncokb_genes"
        "cancermine"
        "cancer_hotspots"
        "cancer_hotspots_tbi"
        "clinical_biomarkers"
        "hgnc_mappings"
        "oncotree"
        "civic_hotspots"
        "clingen_dosage"
        "oncovi_tsg"
        "oncovi_oncogenes"
        "oncovi_hotspots"
    )
    
    local failed=0
    for kb in "${essential_kbs[@]}"; do
        if ! download_kb "$kb" "$force"; then
            failed=$((failed + 1))
        fi
        sleep 2
    done
    
    log_info "Essential downloads completed. Failed: $failed"
    return $failed
}

download_population() {
    local force=${1:-false}
    log_info "Downloading population frequency databases (large files)..."
    
    log_warning "gnomAD downloads are very large (20-150GB each)"
    read -p "Download gnomAD exomes (~20GB)? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        download_kb "gnomad_exomes" "$force"
        download_kb "gnomad_exomes_tbi" "$force"
    fi
    
    read -p "Download gnomAD genomes (~150GB)? (y/N): " -n 1 -r  
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        download_kb "gnomad_genomes" "$force"
        download_kb "gnomad_genomes_tbi" "$force"
    fi
    
    read -p "Download dbSNP (~25GB)? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        download_kb "dbsnp" "$force"
    fi
}

download_specialized() {
    local force=${1:-false}
    log_info "Downloading specialized databases..."
    
    local specialized_kbs=(
        "tcga_mc3"
        "open_targets"
        "dgidb"
        "uniprot_sprot"
        "pfam"
        "gene_mappings"
        "mondo_disease"
        "msk_hotspots_snv"
        "msk_hotspots_indel"
        "cosmic_cgc"
        "msk_3d_hotspots"
        "clingen_haplo"
        "clingen_triplo"
        "depmap_mutations"
        "depmap_gene_effect"
        "oncovi_indel_hotspots"
        "oncovi_domains"
        "oncovi_cgi"
        "oncovi_os2"
        "oncovi_amino_dict"
        "oncovi_grantham"
    )
    
    local failed=0
    for kb in "${specialized_kbs[@]}"; do
        if ! download_kb "$kb" "$force"; then
            failed=$((failed + 1))
        fi
        sleep 3
    done
    
    log_info "Specialized downloads completed. Failed: $failed"
    return $failed
}

# --- Verification ---
verify_downloads() {
    log_info "Verifying all downloaded knowledge bases..."
    
    local total_size=0
    local file_count=0
    
    for kb_key in "${!KNOWLEDGE_BASES[@]}"; do
        IFS='|' read -r url filename description size_estimate <<< "${KNOWLEDGE_BASES[$kb_key]}"
        
        # Find the file
        local found_file=""
        for dir in "$REFS_DIR"/*; do
            if [[ -d "$dir" && -f "$dir/$filename" ]]; then
                found_file="$dir/$filename"
                break
            fi
        done
        
        if [[ -n "$found_file" && -s "$found_file" ]]; then
            local file_size=$(stat -f%z "$found_file" 2>/dev/null || stat -c%s "$found_file" 2>/dev/null || echo "0")
            total_size=$((total_size + file_size))
            file_count=$((file_count + 1))
            log_success "$description: OK ($((file_size / 1024 / 1024)) MB)"
        fi
    done
    
    log_success "Verification complete: $file_count files, $((total_size / 1024 / 1024 / 1024)) GB total"
}

# --- Usage ---
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Downloads comprehensive knowledge bases using the 'recipe approach'."
    echo "Gets raw, standard format files from authoritative sources."
    echo ""
    echo "Options:"
    echo "  --essential      Download core clinical databases (~500MB)"
    echo "  --population     Download population frequency databases (20-150GB)"
    echo "  --specialized    Download drug/protein/pathway databases (~1GB)"
    echo "  --all            Download everything (interactive prompts for large files)"
    echo "  --verify         Verify existing downloads"
    echo "  --list           List all available knowledge bases"
    echo "  --force          Force re-download of existing files"
    echo "  --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --essential           # Quick start with core databases"
    echo "  $0 --all                 # Complete setup (interactive)"
    echo "  $0 --verify              # Check what's already downloaded"
}

show_list() {
    echo "Available Knowledge Bases:"
    echo ""
    
    for kb_key in "${!KNOWLEDGE_BASES[@]}"; do
        IFS='|' read -r url filename description size_estimate <<< "${KNOWLEDGE_BASES[$kb_key]}"
        printf "  %-20s %s (%s)\n" "$kb_key" "$description" "$size_estimate"
    done
}

# --- Main ---
main() {
    local mode=""
    local force=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --essential) mode="essential"; shift ;;
            --population) mode="population"; shift ;;
            --specialized) mode="specialized"; shift ;;
            --all) mode="all"; shift ;;
            --verify) mode="verify"; shift ;;
            --list) mode="list"; shift ;;
            --force) force=true; shift ;;
            --help) show_usage; exit 0 ;;
            *) log_error "Unknown option: $1"; show_usage; exit 1 ;;
        esac
    done
    
    if [[ -z "$mode" ]]; then
        mode="essential"
        log_info "No mode specified, defaulting to --essential"
    fi
    
    log_info "Comprehensive Knowledge Base Setup"
    log_info "Assembly: $ASSEMBLY"
    log_info "Target directory: $REFS_DIR"
    log_info "Mode: $mode"
    
    case "$mode" in
        essential)
            download_essential "$force"
            ;;
        population)
            download_population "$force"
            ;;
        specialized)
            download_specialized "$force"
            ;;
        all)
            download_essential "$force"
            download_population "$force"
            download_specialized "$force"
            ;;
        verify)
            verify_downloads
            ;;
        list)
            show_list
            ;;
        *)
            log_error "Invalid mode: $mode"
            exit 1
            ;;
    esac
    
    if [[ "$mode" != "verify" && "$mode" != "list" ]]; then
        echo ""
        verify_downloads
        echo ""
        log_success "Knowledge base setup completed!"
        log_info "Files stored in: $REFS_DIR"
        log_info "Next steps:"
        log_info "1. Set up VEP: ./scripts/setup_vep.sh"
        log_info "2. Run annotation pipeline with comprehensive data"
    fi
}

main "$@"