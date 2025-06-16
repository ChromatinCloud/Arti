# Knowledge Base to Canned Text and Guideline Mapping

## 8 Canned Text Types
1. **General Gene Info** – boilerplate overview of the gene
2. **Gene Dx Interpretation** – gene-level meaning for the patient's specific diagnosis  
3. **General Variant Info** – technical description of the variant itself
4. **Variant Dx Interpretation** – variant-specific clinical meaning for the diagnosis
5. **Incidental / Secondary Findings** – ACMG-SF-style reportables unrelated to the primary dx
6. **Chromosomal Alteration Interpretation** – CNVs / fusions / large SVs
7. **Pertinent Negatives** – explicit "no clinically significant variants found in …" statements
8. **Biomarkers** – TMB, MSI, expression; we just bucket values vs. thresholds

## 3 Clinical Guidelines
1. **AMP/ASCO/CAP 2017**: Standards and Guidelines for Somatic Variant Interpretation in Cancer
2. **VICC/CGC 2022**: Variant Interpretation for Cancer Consortium / Cancer Gene Census
3. **OncoKB**: Memorial Sloan Kettering precision oncology knowledge base

## KB to Canned Text Correspondence

### For "General Gene Info" (Text Type 1)
**Primary KBs:**
- NCBI Gene Info (gene descriptions, aliases)
- HGNC Mappings (official symbols)
- UniProt Swiss-Prot (protein function)
- Pfam Domains (domain architecture)
- COSMIC Cancer Gene Census (cancer gene roles)
- CancerMine (literature-mined roles)
- OncoVI Tumor Suppressors/Oncogenes (definitive classifications)

### For "Gene Dx Interpretation" (Text Type 2)
**Primary KBs:**
- COSMIC Cancer Gene Census (TSG/oncogene status)
- OncoKB Genes (cancer-specific gene roles)
- ClinGen Gene Curation (gene-disease relationships)
- DepMap Gene Effects (gene essentiality)
- Open Targets Platform (disease associations)
- OncoTree Classifications (cancer type context)

### For "General Variant Info" (Text Type 3)
**Primary KBs:**
- dbSNP (rsIDs, variant identifiers)
- gnomAD (population frequencies)
- ClinVar (review status, submissions)
- Cancer Hotspots (recurrence data)
- MSK Hotspots (frequency data)
- OncoVI Single Residue Hotspots (detailed frequencies)

### For "Variant Dx Interpretation" (Text Type 4)
**Primary KBs:**
- ClinVar (pathogenicity)
- CIViC Variants (clinical evidence)
- OncoKB (therapeutic levels)
- DGIdb (drug interactions)
- Cancer Hotspots (driver status)
- dbNSFP/AlphaMissense/SpliceAI (functional predictions)
- OncoVI CGI Mutations (validated interpretations)

### For "Incidental / Secondary Findings" (Text Type 5)
**Primary KBs:**
- ClinVar (germline pathogenic variants)
- ClinGen Gene Curation (gene-disease validity)
- ACMG SF gene lists (need to add)

### For "Chromosomal Alteration Interpretation" (Text Type 6)
**Primary KBs:**
- ClinGen Haploinsufficiency/Triplosensitivity
- COSMIC Structural Variants (need in .refs)
- Fusion databases in PCGR bundle

### For "Pertinent Negatives" (Text Type 7)
**Primary KBs:**
- All gene lists (for comprehensive coverage)
- Cancer gene panels in PCGR

### For "Biomarkers" (Text Type 8)
**Primary KBs:**
- Clinical Biomarkers (TMB/MSI thresholds)
- TCGA expression data (in PCGR)
- DepMap expression profiles

## KB to Guideline Mapping

### AMP/ASCO/CAP 2017 Primary KBs:
- ClinVar (Tier I-IV evidence)
- CIViC (evidence levels A-D)
- OncoKB (Level 1-4)
- Cancer Hotspots (driver validation)
- DGIdb (drug interactions)

### VICC/CGC 2022 Primary KBs:
- COSMIC CGC (OVS1/OS1 classification)
- gnomAD (SBVS1/OP4 rules)
- dbNSFP (OP1/SBP1 computational)
- ClinVar (OS2/SBS2 professional)
- Hotspots (OS3/OM3 recurrence)

### OncoKB Framework Primary KBs:
- OncoKB Genes (core framework)
- OncoTree (cancer type matching)
- DGIdb (therapeutic context)
- Clinical Biomarkers (FDA thresholds)