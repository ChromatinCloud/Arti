# Annotation Workflow KB Mapping - Developer Reference

**Purpose:** Comprehensive mapping of knowledge bases to workflow steps, clinical guidelines, and canned text generation  
**Date:** June 16, 2025  
**For:** Development implementation of annotation engine

## Workflow Overview

```
Input VCF → VEP Annotation → Evidence Aggregation → Tier Assignment → Canned Text → Output JSON
    ↓              ↓                 ↓                ↓               ↓
  Parse         Functional        Clinical         AMP/VICC      8 Text Types
 Variants       Predictions       Evidence         Scoring       Generation
```

## Phase 1: VEP Annotation (Functional Predictions)

### Access Method: VEP Plugins
**Goal:** Annotate variants with functional impact scores and predictions

#### dbNSFP Plugin
**Location:** `functional_predictions/plugin_data/pathogenicity/`  
**Size:** ~15GB (when downloaded)  
**Access:** `--plugin dbNSFP,/path/to/dbNSFP5.1.gz,COLUMNS`

**Fields Needed:**
- `SIFT_score` - Deleteriousness score (0-1, lower = more deleterious)
- `SIFT_pred` - Prediction (D=Deleterious, T=Tolerated)
- `Polyphen2_HDIV_score` - PolyPhen2 score (0-1, higher = more damaging)
- `Polyphen2_HDIV_pred` - Prediction (D,P,B = Damaging,Possibly,Benign)
- `CADD_phred` - CADD scaled score (>20 = top 1% most deleterious)
- `REVEL_score` - Ensemble score (0-1, higher = more pathogenic)
- `GERP++_RS` - Conservation score (higher = more conserved)
- `phyloP30way_mammalian` - Phylogenetic conservation
- `phastCons30way_mammalian` - Conservation probability

**Usage in Guidelines:**
- **VICC 2022:** OP1 (+1 point if multiple predictors agree on pathogenic)
- **AMP 2017:** Supporting evidence for functional impact
- **OncoKB:** Background functional context

**Feeds Into Canned Text:**
- **General Variant Info:** Functional prediction summary
- **Variant Dx Interpretation:** Pathogenicity assessment

**Implementation Notes:**
```python
# VEP command
--plugin dbNSFP,/path/to/dbNSFP5.1.gz,SIFT_score,SIFT_pred,Polyphen2_HDIV_score,Polyphen2_HDIV_pred,CADD_phred,REVEL_score,GERP++_RS,phyloP30way_mammalian,phastCons30way_mammalian

# Evidence aggregator parsing
def parse_dbnsfp_scores(vep_json):
    scores = {}
    if 'SIFT_score' in transcript:
        scores['sift'] = {'score': float(transcript['SIFT_score']), 'pred': transcript['SIFT_pred']}
    # ... parse other scores
    return scores
```

#### AlphaMissense Plugin  
**Location:** `functional_predictions/plugin_data/protein_impact/AlphaMissense_aa_substitutions.tsv.gz`  
**Size:** 1.1GB  
**Access:** `--plugin AlphaMissense,file=/path/to/file.tsv.gz`

**Fields Needed:**
- `am_pathogenicity` - Pathogenicity score (0-1, >0.564 = likely pathogenic)
- `am_class` - Classification (likely_pathogenic, likely_benign, ambiguous)

**Usage in Guidelines:**
- **VICC 2022:** OP1 (+1 point if likely_pathogenic)
- **AMP 2017:** Strong functional evidence if likely_pathogenic
- **OncoKB:** High-confidence missense assessment

**Implementation Notes:**
```python
# Classification thresholds
if am_pathogenicity > 0.564:
    classification = "likely_pathogenic"
    vicc_points += 1  # OP1 evidence
elif am_pathogenicity < 0.34:
    classification = "likely_benign"
    vicc_points -= 1  # SBP1 evidence
```

#### SpliceAI Plugin
**Location:** `functional_predictions/plugin_data/splicing/spliceai_scores.raw.snv.hg38.vcf.gz`  
**Access:** `--plugin SpliceAI,snv=/path/to/spliceai_snv.vcf.gz`

**Fields Needed:**
- `DS_AG` - Delta score acceptor gain (0-1)
- `DS_AL` - Delta score acceptor loss (0-1) 
- `DS_DG` - Delta score donor gain (0-1)
- `DS_DL` - Delta score donor loss (0-1)
- `DP_AG`, `DP_AL`, `DP_DG`, `DP_DL` - Distance to predicted sites

**Usage in Guidelines:**
- **VICC 2022:** OP1 (+1) if max(DS) > 0.5 (high confidence splice alteration)
- **AMP 2017:** Strong evidence for splice-site variants

**Implementation Notes:**
```python
def evaluate_spliceai(scores):
    max_ds = max(scores['DS_AG'], scores['DS_AL'], scores['DS_DG'], scores['DS_DL'])
    if max_ds > 0.8:
        return "high_confidence_splice_altering"
    elif max_ds > 0.5:
        return "likely_splice_altering"  # VICC OP1
    elif max_ds > 0.2:
        return "possible_splice_altering"
    return "unlikely_splice_altering"
```

#### REVEL Plugin
**Location:** `functional_predictions/plugin_data/pathogenicity/revel-v1.3_all_chromosomes.zip` (extract)  
**Access:** `--plugin REVEL,/path/to/revel_scores.tsv.gz`

**Fields Needed:**
- `REVEL_score` - Ensemble pathogenicity score (0-1, >0.5 = likely pathogenic)

**Usage in Guidelines:**
- **VICC 2022:** OP1 (+1) if score > 0.7
- **AMP 2017:** Supporting functional evidence

#### Conservation Plugin
**Location:** `functional_predictions/plugin_data/conservation/hg38.phastCons100way.bw`  
**Access:** `--plugin Conservation,/path/to/conservation.bw`

**Fields Needed:**
- `GERP_RS` - GERP rejection substitution score
- `phyloP_score` - Phylogenetic p-value
- `phastCons_score` - Conservation probability

**Usage in Guidelines:**
- **VICC 2022:** OP1 (+1) if highly conserved (GERP > 4, phyloP > 2)

#### Other VEP Plugins (Implementation Priority)
- **PrimateAI:** Missense predictions for OP1 scoring
- **BayesDel:** Meta-deleteriousness for OP1  
- **LoFtool:** Gene intolerance for OVS1/OS1 weighting
- **FATHMM:** Additional pathogenicity predictor
- **MaveDB:** Experimental functional scores

## Phase 2: Evidence Aggregation (Clinical Data)

### Access Method: Direct KB Queries
**Goal:** Gather clinical evidence for tier assignment and therapeutic actionability

#### ClinVar
**Location:** `clinical_evidence/clinvar/`  
**Access:** Direct VCF/TSV parsing with tabix

**Fields Needed:**
- `CLNSIG` - Clinical significance (Pathogenic, Likely_pathogenic, etc.)
- `CLNREVSTAT` - Review status (practice_guideline, reviewed_by_expert_panel, etc.)
- `CLNDN` - Disease name
- `GENEINFO` - Gene information
- `MC` - Molecular consequence
- `CLNHGVS` - HGVS expressions

**Usage in Guidelines:**
- **VICC 2022:** OS2 (+4) if Pathogenic/Likely_pathogenic with expert review
- **AMP 2017:** Strong clinical evidence for tier assignment
- **OncoKB:** Cross-validation of clinical significance

**Implementation Notes:**
```python
def query_clinvar(chr, pos, ref, alt):
    # Use tabix for position-based lookup
    results = tabix_query(clinvar_vcf, f"{chr}:{pos}-{pos}")
    for record in results:
        if record.ref == ref and alt in record.alts:
            clnsig = record.info.get('CLNSIG', '')
            if 'Pathogenic' in clnsig or 'Likely_pathogenic' in clnsig:
                return {
                    'significance': clnsig,
                    'review_status': record.info.get('CLNREVSTAT', ''),
                    'vicc_points': 4  # OS2 evidence
                }
    return None
```

**Feeds Into Canned Text:**
- **General Variant Info:** Clinical significance summary
- **Variant Dx Interpretation:** Pathogenicity rationale

#### CIViC
**Location:** `clinical_evidence/civic/civic_variants.tsv`  
**Access:** Direct TSV parsing with pandas/CSV reader

**Fields Needed:**
- `variant` - Variant description
- `disease` - Cancer type
- `drugs` - Associated therapies
- `evidence_type` - Predictive, Prognostic, Diagnostic, Predisposing
- `evidence_level` - A, B, C, D, E
- `evidence_direction` - Supports, Does_not_support
- `clinical_significance` - Sensitivity/Resistance, etc.
- `gene` - Gene symbol
- `chromosome`, `start`, `stop` - Genomic coordinates

**Usage in Guidelines:**
- **AMP 2017:** Level A/B evidence → Tier I, Level C/D → Tier II
- **OncoKB:** Cross-reference therapeutic evidence
- **VICC 2022:** OS2 (+4) for well-established clinical evidence

**Implementation Notes:**
```python
def query_civic(gene, hgvs_variant=None, coordinates=None):
    civic_df = pd.read_csv(civic_tsv, sep='\t')
    
    # Gene-based lookup
    gene_matches = civic_df[civic_df['gene'] == gene]
    
    # Coordinate-based lookup if available
    if coordinates:
        coord_matches = gene_matches[
            (gene_matches['chromosome'] == coordinates['chr']) &
            (gene_matches['start'] <= coordinates['pos']) &
            (gene_matches['stop'] >= coordinates['pos'])
        ]
        
    # Extract therapeutic evidence
    therapeutic_evidence = []
    for _, row in coord_matches.iterrows():
        if row['evidence_type'] == 'Predictive':
            therapeutic_evidence.append({
                'drug': row['drugs'],
                'evidence_level': row['evidence_level'],
                'significance': row['clinical_significance'],
                'disease': row['disease']
            })
    
    return therapeutic_evidence
```

**Feeds Into Canned Text:**
- **Variant Dx Interpretation:** Therapeutic actionability
- **General Gene Info:** Gene-drug associations

#### OncoKB
**Location:** `clinical_evidence/oncokb/oncokb_genes.txt`  
**Access:** Direct file parsing + API calls for detailed evidence

**Fields Needed:**
- `Hugo Symbol` - Gene name
- `OncoKB Annotated` - Yes/No
- `Is Oncogene` - True/False
- `Is Tumor Suppressor Gene` - True/False
- `# of occurrence within TCGA tumors` - Frequency data

**API Fields (when available):**
- `oncogenic` - Oncogenic classification
- `mutationEffect` - Gain-of-function, Loss-of-function, etc.
- `treatments` - FDA approved therapies
- `level` - Evidence level (1, 2A, 2B, 3A, 3B, 4, R1, R2)

**Usage in Guidelines:**
- **OncoKB Levels:** Direct tier mapping (Level 1→Tier IA, 2A→Tier IB, etc.)
- **VICC 2022:** OS1 (+4) for known oncogenes, OVS1 (+8) for tumor suppressors
- **AMP 2017:** Therapeutic actionability evidence

**Implementation Notes:**
```python
def query_oncokb(gene, variant_hgvs):
    # Check if gene is OncoKB annotated
    oncokb_genes = pd.read_csv(oncokb_genes_file, sep='\t')
    gene_info = oncokb_genes[oncokb_genes['Hugo Symbol'] == gene]
    
    if gene_info.empty:
        return None
        
    is_oncogene = gene_info['Is Oncogene'].iloc[0]
    is_tsg = gene_info['Is Tumor Suppressor Gene'].iloc[0]
    
    # API call for variant-specific evidence (if API key available)
    # Otherwise use gene-level classification
    
    evidence = {
        'gene_role': 'oncogene' if is_oncogene else 'tsg' if is_tsg else 'unknown',
        'vicc_points': 4 if is_oncogene else 8 if is_tsg else 0,
        'therapeutic_implications': []  # Populate from API
    }
    
    return evidence
```

#### Cancer Hotspots (MSK)
**Location:** `cancer_signatures/hotspots/`  
**Access:** Direct VCF parsing with position lookup

**Fields Needed:**
- `chromosome`, `position`, `ref`, `alt` - Variant coordinates
- `sample_count` - Number of samples with this variant
- `tumor_types` - Cancer types where observed
- `hotspot_type` - single, in-frame_indel, etc.

**Usage in Guidelines:**
- **VICC 2022:** OS3 (+4) if >50 samples, OM3 (+2) if 10-50 samples
- **AMP 2017:** Hotspot evidence for tier assignment
- **OncoKB:** Validate known hotspots

**Implementation Notes:**
```python
def query_cancer_hotspots(chr, pos, ref, alt):
    # Position-based lookup in hotspots VCF
    hotspot_record = tabix_query(hotspots_vcf, f"{chr}:{pos}-{pos}")
    
    for record in hotspot_record:
        if record.ref == ref and alt in record.alts:
            sample_count = int(record.info.get('COUNT', 0))
            
            if sample_count >= 50:
                return {'type': 'established_hotspot', 'vicc_points': 4, 'count': sample_count}
            elif sample_count >= 10:
                return {'type': 'moderate_hotspot', 'vicc_points': 2, 'count': sample_count}
            else:
                return {'type': 'rare_hotspot', 'vicc_points': 1, 'count': sample_count}
    
    return None
```

#### gnomAD Population Frequencies
**Location:** `population_frequencies/gnomad/`  
**Access:** Direct VCF parsing with tabix

**Fields Needed:**
- `AF` - Overall allele frequency
- `AF_popmax` - Maximum population frequency
- `nhomalt` - Number of homozygotes
- `AC` - Allele count
- `AN` - Allele number

**Usage in Guidelines:**
- **VICC 2022:** SBVS1 (-8) if AF > 1%, SBP1 (-1) if AF > 0.1%
- **AMP 2017:** Population frequency filtering for somatic variants
- **Tumor-only analysis:** Critical for germline filtering

**Implementation Notes:**
```python
def query_gnomad(chr, pos, ref, alt):
    gnomad_record = tabix_query(gnomad_vcf, f"{chr}:{pos}-{pos}")
    
    for record in gnomad_record:
        if record.ref == ref and alt in record.alts:
            af = float(record.info.get('AF', 0))
            af_popmax = float(record.info.get('AF_popmax', 0))
            
            # VICC scoring based on frequency
            if af_popmax > 0.01:  # 1%
                vicc_points = -8  # SBVS1
            elif af_popmax > 0.001:  # 0.1%
                vicc_points = -1   # SBP1
            else:
                vicc_points = 1    # OP4 (absent from population)
                
            return {
                'af': af,
                'af_popmax': af_popmax,
                'vicc_points': vicc_points,
                'likely_germline': af > 0.001  # For tumor-only analysis
            }
    
    return {'af': 0, 'vicc_points': 1}  # Absent = OP4
```

## Phase 3: Tier Assignment (Clinical Guidelines)

### AMP/ASCO/CAP 2017 Implementation
**Algorithm:** Evidence-weighted tier assignment

```python
def assign_amp_tier(evidence):
    tier = "III"  # Default VUS
    
    # Tier I: Strong clinical significance
    if evidence['therapeutic']['fda_approved'] or evidence['civic']['level_a']:
        tier = "IA"
    elif evidence['guideline_recommended'] or evidence['civic']['level_b']:
        tier = "IB"
    
    # Tier II: Potential clinical significance  
    elif evidence['clinical_trials'] or evidence['civic']['level_c']:
        tier = "IIC"
    elif evidence['preclinical_evidence']:
        tier = "IID"
    elif evidence['emerging_evidence']:
        tier = "IIE"
    
    # Tier IV: Benign/Likely benign
    elif evidence['population_frequency'] > 0.01:  # 1% population frequency
        tier = "IV"
    elif evidence['functional_predictions']['benign_consensus']:
        tier = "IV"
        
    return tier
```

### VICC/CGC 2022 Implementation  
**Algorithm:** Point-based scoring system

```python
def assign_vicc_oncogenicity(evidence):
    points = 0
    
    # Very Strong Evidence
    if evidence['lof_in_tsg']:
        points += 8  # OVS1
    if evidence['population_frequency'] > 0.01:
        points -= 8  # SBVS1
    
    # Strong Evidence  
    if evidence['known_oncogene_activating']:
        points += 4  # OS1
    if evidence['clinvar_pathogenic']:
        points += 4  # OS2
    if evidence['established_hotspot']:
        points += 4  # OS3
    if evidence['silent_with_no_impact']:
        points -= 4  # SBS1
    
    # Moderate Evidence
    if evidence['critical_domain']:
        points += 2  # OM1
    if evidence['functional_studies_support']:
        points += 2  # OM2
    if evidence['moderate_hotspot']:
        points += 2  # OM3
    if evidence['known_cancer_gene']:
        points += 2  # OM4
    
    # Supporting Evidence
    if evidence['computational_pathogenic']:
        points += 1  # OP1
    if evidence['somatic_in_multiple_tumors']:
        points += 1  # OP2
    if evidence['in_hotspot_region']:
        points += 1  # OP3
    if evidence['absent_population']:
        points += 1  # OP4
    if evidence['computational_benign']:
        points -= 1  # SBP1
    
    # Classification
    if points >= 7:
        return "Oncogenic"
    elif points >= 4:
        return "Likely Oncogenic"
    elif points >= 0:
        return "Uncertain Significance"
    elif points >= -3:
        return "Likely Benign"
    else:
        return "Benign"
```

## Phase 4: Canned Text Generation

### Text Type 1: General Gene Info
**Data Sources:**
- OncoKB gene classifications
- COSMIC Cancer Gene Census
- Gene mappings (HGNC)
- UniProt protein information

**Template:**
```python
def generate_general_gene_info(gene, evidence):
    text = f"{gene} is "
    
    if evidence['oncokb']['is_oncogene']:
        text += "a known oncogene"
    elif evidence['oncokb']['is_tsg']:
        text += "a tumor suppressor gene"
    else:
        text += "a gene"
    
    text += f" involved in {evidence['pathways']}. "
    
    if evidence['therapeutic_targets']:
        text += f"It is targeted by {', '.join(evidence['therapeutic_targets'])}."
    
    return text
```

### Text Type 2: Gene Dx Interpretation  
**Data Sources:**
- ClinGen dosage sensitivity
- Disease associations (MONDO)
- TCGA mutation frequencies

### Text Type 3: General Variant Info
**Data Sources:**
- Functional predictions (VEP plugins)
- Population frequencies (gnomAD)
- Conservation scores

### Text Type 4: Variant Dx Interpretation
**Data Sources:**
- ClinVar clinical significance
- CIViC therapeutic evidence
- Cancer hotspots data
- Tier assignment results

### Text Type 5: Incidental/Secondary Findings
**Data Sources:**
- ACMG actionable gene lists (ClinGen)
- Pathogenic variants in actionable genes

### Text Type 6: Chromosomal Alteration Interpretation
**Data Sources:**
- Gene context within altered regions
- Dosage sensitivity data

### Text Type 7: Pertinent Negatives
**Data Sources:**
- Coverage analysis
- Expected pathogenic variants not found

### Text Type 8: Biomarkers
**Data Sources:**
- Clinical biomarker thresholds
- TMB/MSI calculations

## Implementation Checklist

### VEP Plugin Setup
- [ ] Download and index dbNSFP 5.1
- [ ] Configure AlphaMissense plugin  
- [ ] Set up SpliceAI with proper data files
- [ ] Extract and prepare REVEL scores
- [ ] Configure Conservation plugin with BigWig files

### Direct KB Setup
- [ ] Index ClinVar VCF with tabix
- [ ] Prepare CIViC TSV for pandas queries
- [ ] Set up OncoKB gene lists and API access
- [ ] Index cancer hotspots VCF
- [ ] Index gnomAD for population queries

### Evidence Aggregator Implementation
- [ ] VEP JSON parser for functional scores
- [ ] ClinVar position-based query system
- [ ] CIViC gene/variant lookup system
- [ ] Cancer hotspots position lookup
- [ ] Population frequency calculation

### Tier Assignment Implementation
- [ ] AMP/ASCO/CAP evidence weighting algorithm
- [ ] VICC/CGC point-based scoring system
- [ ] OncoKB level mapping

### Canned Text Implementation
- [ ] Template system for 8 text types
- [ ] Evidence-to-text mapping functions
- [ ] Clinical language standardization

This document serves as the comprehensive blueprint for implementing our annotation workflow with precise KB usage patterns.