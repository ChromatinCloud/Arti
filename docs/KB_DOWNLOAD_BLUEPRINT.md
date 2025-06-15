# Knowledge Base Download Blueprint

This document records verified URLs and approaches for downloading knowledge bases for the annotation engine.

## Comprehensive Knowledge Base URLs - "Recipe Approach" (Last Updated: 2025-06-15)

### Recent Updates (This Session)
- Added PCGR supplemental knowledge bases discovered from examination of PCGR data bundle
- Enhanced `scripts/setup_comprehensive_kb.sh` with additional hotspot sources and clinical resources
- Added biomarkers, gene mappings, disease ontologies, and cell line data sources
- Created `src/annotation_engine/api_clients.py` and `src/annotation_engine/plugin_manager.py` for API and VEP plugin management

### Essential Clinical Databases (~550MB total)

#### ClinVar (Clinical Significance)
- **VCF**: `https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz` (200MB)
- **VCF Index**: `https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz.tbi` (1MB)
- **TSV Summary**: `https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz` (150MB)
- **Update Frequency**: Weekly
- **Status**: ✅ Working

#### CIViC (Clinical Evidence)
- **Variant Summaries**: `https://civicdb.org/downloads/nightly/nightly-VariantSummaries.tsv` (5MB)
- **Clinical Evidence Hotspots**: `https://civicdb.org/downloads/nightly/nightly-ClinicalEvidenceSummaries.tsv` (10MB)
- **Update Frequency**: Nightly
- **Status**: ✅ Working

#### OncoKB (Cancer Genes)
- **Public Genes**: `https://www.oncokb.org/api/v1/utils/allCuratedGenes.txt` (1MB)
- **Requires**: No API key for basic gene list
- **Status**: ✅ Working

#### CancerMine (Literature Mining)
- **TSV**: `http://bionlp.bcgsc.ca/cancermine/cancermine_collated.tsv` (20MB)
- **Content**: Literature-mined oncogenes and tumor suppressors
- **Status**: ✅ Working

#### Cancer Hotspots (Multiple Sources)
- **Primary VCF**: `https://www.cancerhotspots.org/files/hotspots_v3_hg38.vcf.gz` (5MB)
- **Primary Index**: `https://www.cancerhotspots.org/files/hotspots_v3_hg38.vcf.gz.tbi` (1MB)
- **MSK SNVs**: `https://www.cbioportal.org/webAPI/cancerhotspots/single-nucleotide-variants` (10MB)
- **MSK Indels**: `https://www.cbioportal.org/webAPI/cancerhotspots/indels` (5MB)
- **MSK 3D Hotspots**: `https://www.3dhotspots.org/3d_hotspots.txt` (5MB)
- **Status**: ✅ Working

#### Clinical Biomarkers
- **PCGR Biomarkers**: `https://raw.githubusercontent.com/sigven/pcgr/main/pcgrdb/data/biomarkers.tsv` (2MB)
- **Content**: Clinical biomarker thresholds and definitions
- **Status**: ✅ Working

#### Gene Mappings and Ontologies
- **HGNC Mappings**: `https://ftp.ebi.ac.uk/pub/databases/genenames/hgnc/tsv/hgnc_complete_set.txt` (5MB)
- **OncoTree**: `http://oncotree.mskcc.org/api/tumorTypes/tree?version=oncotree_latest_stable` (1MB)
- **Content**: Gene symbol standardization and disease classifications
- **Status**: ✅ Working

### Population Frequency Databases (20-150GB)

#### gnomAD v4.1 (Population Frequencies)
- **Exomes**: `gs://gcp-public-data--gnomad/release/4.1/vcf-grch38/exomes/gnomad.exomes.v4.1.sites.grch38.vcf.bgz` (20GB)
- **Exomes Index**: `gs://gcp-public-data--gnomad/release/4.1/vcf-grch38/exomes/gnomad.exomes.v4.1.sites.grch38.vcf.bgz.tbi` (200MB)
- **Genomes**: `gs://gcp-public-data--gnomad/release/4.1/vcf-grch38/genomes/gnomad.genomes.v4.1.sites.grch38.vcf.bgz` (150GB)
- **Genomes Index**: `gs://gcp-public-data--gnomad/release/4.1/vcf-grch38/genomes/gnomad.genomes.v4.1.sites.grch38.vcf.bgz.tbi` (1GB)
- **Requires**: Google Cloud SDK (gsutil)
- **Status**: ✅ Working

#### dbSNP (Variant IDs)
- **VCF**: `https://ftp.ncbi.nlm.nih.gov/snp/latest_release/VCF/GCF_000001405.40.gz` (25GB)
- **Content**: Common variant identifiers
- **Status**: ✅ Working

### Specialized Databases (~2.5GB total)

#### TCGA (Cancer Mutations)
- **MC3 MAF**: `https://api.gdc.cancer.gov/data/1c8cfe5f-e52d-41ba-94da-f15ea1337efc` (200MB)
- **Content**: Pan-cancer somatic mutations
- **Status**: ✅ Working

#### Drug-Target Associations
- **Open Targets**: `https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/latest/output/etl/json/targets/targets.json.gz` (500MB)
- **DGIdb**: `http://dgidb.org/data/monthly_tsvs/2024-Jan/interactions.tsv` (50MB)
- **Status**: ✅ Working

#### Protein Annotations
- **UniProt Swiss-Prot**: `https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/uniprot_sprot.dat.gz` (300MB)
- **Pfam**: `https://ftp.ebi.ac.uk/pub/databases/Pfam/current_release/Pfam-A.hmm.gz` (100MB)
- **Status**: ✅ Working

#### Extended Gene Mappings
- **NCBI Gene Info**: `https://ftp.ncbi.nlm.nih.gov/gene/DATA/gene_info.gz` (200MB)
- **MONDO Disease**: `https://github.com/monarch-initiative/mondo/releases/latest/download/mondo.obo` (50MB)
- **Status**: ✅ Working

#### Additional Cancer Resources
- **COSMIC Cancer Gene Census**: `https://cancer.sanger.ac.uk/cosmic/file_download/GRCh38/cosmic/v97/cancer_gene_census.csv` (2MB)
- **Status**: ⚠️ Requires COSMIC account

#### Cell Line and Functional Genomics
- **DepMap Mutations**: `https://depmap.org/portal/api/download/file?file_name=OmicsSomaticMutationsMatrixHotspot.csv&bucket=depmap-external-downloads` (100MB)
- **DepMap Gene Effects**: `https://depmap.org/portal/api/download/file?file_name=CRISPRGeneEffect.csv&bucket=depmap-external-downloads` (200MB)
- **Content**: Cell line mutation and dependency data
- **Status**: ✅ Working

## VEP Plugin Data (Handled via VEP Setup)

These are managed by the VEP plugin system rather than direct downloads:

### dbNSFP (Functional Predictions)
- **Method**: VEP Plugin
- **Data File**: Downloaded via VEP cache setup
- **Content**: SIFT, PolyPhen, CADD, REVEL scores
- **Status**: ✅ Via VEP Plugin

### AlphaMissense (Missense Predictions)
- **Method**: VEP Plugin
- **Data File**: `AlphaMissense_hg38.tsv.gz`
- **Content**: DeepMind protein structure predictions
- **Status**: ✅ Via VEP Plugin

### SpliceAI (Splice Predictions)
- **Method**: VEP Plugin
- **Data File**: `spliceai_scores.raw.snv.hg38.vcf.gz`
- **Content**: Deep learning splice site predictions
- **Status**: ✅ Via VEP Plugin

## Usage Scripts

### Primary Scripts
- **`./scripts/setup_comprehensive_kb.sh`** - Main KB downloader with "recipe approach"
- **`./scripts/setup_vep.sh`** - VEP installation via Docker

### Usage Examples

```bash
# Quick start with essential databases (~550MB)
./scripts/setup_comprehensive_kb.sh --essential

# Complete setup with interactive prompts for large files
./scripts/setup_comprehensive_kb.sh --all

# Download specialized databases only
./scripts/setup_comprehensive_kb.sh --specialized

# List all available knowledge bases
./scripts/setup_comprehensive_kb.sh --list

# Verify what's already downloaded
./scripts/setup_comprehensive_kb.sh --verify

# Force re-download of existing files
./scripts/setup_comprehensive_kb.sh --essential --force
```

### Setup VEP
```bash
# Install VEP via Docker with plugins
./scripts/setup_vep.sh
```

## API Integration

Our system also includes API clients for real-time data access:

### CIViC API Client (`src/annotation_engine/api_clients.py`)
- **Endpoint**: `https://civicdb.org/api/variants`
- **Usage**: Supplement downloaded files with real-time queries
- **No Auth Required**: Public API

### OncoKB API Client
- **Endpoint**: `https://www.oncokb.org/api/v1`
- **Usage**: Real-time variant annotation
- **Auth Required**: Set `ONCOKB_API_KEY` environment variable

## File Organization

All knowledge bases are organized under `.refs/` with logical subdirectories:

```
.refs/
├── clinvar/          # ClinVar VCF and TSV files
├── civic/            # CIViC variant and evidence files
├── oncokb/           # OncoKB gene lists
├── cancer_hotspots/  # All hotspot sources (MSK, CIVIC, 3D)
├── gnomad/           # gnomAD population frequencies
├── dbsnp/            # dbSNP variant IDs
├── tcga/             # TCGA cancer mutation data
├── open_targets/     # Drug-target and pathway data
├── biomarkers/       # Clinical biomarker definitions
├── gene_mappings/    # Gene symbol and ID mappings
├── oncotree/         # Disease classification ontologies
├── depmap/           # Cell line mutation and dependency data
├── uniprot/          # Protein sequence and function data
├── pfam/             # Protein family annotations
└── cancermine/       # Literature-mined cancer genes
```

## Deprecated/Removed Knowledge Bases

### COSMIC (Commercial)
- **Status**: ❌ No longer free for academic use
- **Alternative**: Use Cancer Hotspots, DepMap, or MSK sources

### Old Cancer Hotspots URLs
- **Previous**: Various outdated hotspot URLs
- **Status**: ❌ Replaced with comprehensive multi-source approach

---

## Recipe Approach Philosophy

This "recipe approach" was inspired by PCGR's data bundle curation work but implements these key principles:

1. **Raw Format Files**: Download original formats (VCF, TSV, JSON) rather than pre-processed data
2. **Authoritative Sources**: Get data directly from original databases
3. **Reproducible**: All downloads are scripted and versioned
4. **Modular**: Users can choose essential, population, or specialized subsets
5. **Transparent**: All URLs and versions are documented and tracked

This approach provides the benefits of PCGR's curation (knowing which databases are valuable) while maintaining flexibility for custom processing pipelines.

## Institution-Specific Resources

The `internal/` directory contains institution-specific quality control, technical, and interpretive resources:

### Quality Control Flags (`internal/QC_Flags.tsv.gz`)
- **Content**: Standardized QC flag codes, descriptions, and recommended actions
- **Example Flags**: QNS (Quantity Not Sufficient), LOW_DEPTH, FAIL_AMP, POOR_QUAL
- **Usage**: Applied during variant calling and annotation QC steps

### Technical Comments (`internal/Technical_Comments.tsv.gz`)
- **Content**: Pre-written technical comments for common assay issues
- **Categories**: Indeterminate results, sample quality issues, assay limitations
- **Usage**: Incorporated into clinical reports for standardized messaging
- **Source**: Institution-specific laboratory protocols (e.g., "MM - Excelsior")

These internal resources provide standardized quality control frameworks and technical interpretations that complement the external knowledge bases.

## OncoVI Knowledge Base Compilation Process

The OncoVI (Oncogenic Variant Interpreter) knowledge bases represent highly curated resources from MGCarta that have been specifically processed for clinical variant interpretation. Understanding their compilation process is crucial for troubleshooting and quality assessment.

### Publication Reference
- **Paper**: "OncoVI: A Simple and Automatic Tool for Classifying the Oncogenicity of Somatic Variants"
- **DOI**: https://doi.org/10.1101/2024.10.10.24315072
- **Implementation**: Python 3.8.8

### Data Sources and Processing Methods

#### Tumor Suppressor Gene List (`oncovi_tsg.txt`)
- **Primary Sources**: 
  - COSMIC Cancer Gene Census (filtered for "TSG" role)
  - OncoKB Cancer Gene List (tumor suppressors only)
- **Processing**: Union of both sources, duplicates removed
- **Usage**: Critical for VICC OVS1 criterion (null variant in tumor suppressor)

#### Oncogene List (`oncovi_oncogenes.txt`)
- **Primary Sources**:
  - COSMIC Cancer Gene Census (filtered for "oncogene" role)
  - OncoKB Cancer Gene List (oncogenes only)
- **Processing**: Union of both sources, standardized gene symbols
- **Usage**: Critical for VICC OS1 criterion (activating variant in oncogene)

#### Single Residue Hotspots (`oncovi_hotspots.json`)
- **Primary Source**: cancerhotspots.org database
- **Processing**: 
  - Downloaded and parsed hotspot mutation data
  - Organized by gene and residue position
  - Includes mutation frequency counts for each amino acid change
  - Formatted as nested JSON dictionary
- **Usage**: Implements VICC OS3 criterion (well-established hotspot)

#### In-frame Indel Hotspots (`oncovi_indel_hotspots.json`)
- **Primary Source**: cancerhotspots.org database
- **Processing**: Filtered for in-frame insertions and deletions only
- **Usage**: Supports VICC OM3 criterion (protein length-altering variant)

#### Protein Domains Dictionary (`oncovi_domains.json`)
- **Primary Source**: UniProt database
- **Processing**:
  - Downloaded human protein domain annotations
  - Converted UniProtKB accessions to HUGO gene symbols
  - Organized by gene for rapid lookup
- **Usage**: Implements VICC OM1 criterion (critical functional domain)

#### Cancer Genome Interpreter Mutations (`oncovi_cgi.json`)
- **Primary Source**: Cancer Genome Interpreter (CGI) database
- **Processing**: Downloaded catalog of validated oncogenic mutations
- **Usage**: Provides established oncogenic variant evidence

#### OS2 Clinical Significance Mappings (`oncovi_os2.txt`)
- **Primary Source**: ClinVar API
- **Processing**: 
  - Manual curation of clinical significance terms
  - Selected terms that trigger VICC OS2 criterion
  - Quality-controlled list of significance descriptors
- **Usage**: Implements VICC OS2 criterion (well-established in professional guidelines)

#### Utility Files
- **Amino Acid Dictionary**: 3-letter to 1-letter conversion table
- **Grantham Matrix**: Amino acid substitution scoring matrix

### Technical Implementation Notes

#### Quality Control Measures
1. **Manual Interpretation**: Each oncogenicity criterion was manually translated into IF-ELSE programming logic
2. **Point-based Scoring**: Automated assignment of evidence weights according to VICC guidelines
3. **Database Version Control**: All source databases are version-controlled with access dates
4. **Cross-validation**: Gene symbols standardized across all databases using HUGO nomenclature

#### Reproducibility Features
1. **Open Source**: All processing code available in MGCarta/oncovi GitHub repository
2. **Versioned Downloads**: Using GitHub raw URLs ensures specific commit reproducibility
3. **Documented Sources**: All original data sources documented with access methods
4. **Processing Scripts**: Python scripts available for regenerating knowledge bases

### Troubleshooting Guide

#### Common Issues and Solutions

1. **Gene Symbol Mismatches**:
   - **Issue**: Gene not found in oncovi lists
   - **Solution**: Check HGNC mappings, may use alternative gene symbol
   - **Fix**: Update gene symbol mapping or regenerate oncovi lists

2. **Hotspot Position Mismatches**:
   - **Issue**: Known hotspot not found in oncovi hotspot dictionary
   - **Solution**: Check protein coordinates vs. genomic coordinates
   - **Fix**: Verify VEP annotation accuracy, check for isoform differences

3. **Domain Annotation Gaps**:
   - **Issue**: Protein domain not found for variant
   - **Solution**: Check UniProt accession mapping to gene symbol
   - **Fix**: Update domain dictionary from latest UniProt release

4. **Clinical Significance Mapping**:
   - **Issue**: ClinVar significance not triggering OS2
   - **Solution**: Check if significance term is in oncovi_os2.txt
   - **Fix**: Add missing terms to curated OS2 list

### Update Procedures

To regenerate OncoVI knowledge bases with updated source data:

1. **Clone Repository**: `git clone https://github.com/MGCarta/oncovi.git`
2. **Update Sources**: Modify source URLs in processing scripts
3. **Run Processing**: Execute Python processing scripts
4. **Validate Output**: Compare gene counts and format consistency
5. **Update URLs**: Point our KB script to new processed files

This documentation ensures we can maintain and troubleshoot the OncoVI knowledge bases as source data evolves.