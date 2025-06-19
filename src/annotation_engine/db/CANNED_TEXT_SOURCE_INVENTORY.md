# Canned Text Source File Inventory

## Summary of Available Source Files

Based on the 8 TextTemplateType categories in the expanded schema, here's what we have:

### ✅ **FOUND - Well Articulated Sources**

#### 1. **General Gene and Variant Info** 
- **Source**: `tbl_reportable_comments_proc.tsv`
- **Column**: `General_Gene_and_Variant_Info`
- **Count**: 1,849 entries
- **Example**: Gene function descriptions, variant impact explanations

#### 2. **Variant Dx Interpretation**
- **Source**: `tbl_reportable_comments_proc.tsv`
- **Column**: `Interpretation`
- **Count**: 1,619 entries
- **Example**: Clinical significance interpretations for specific variants

#### 3. **Pertinent Negatives**
- **Source**: `Pertinent_Negatives.tsv`
- **Structure**: Tissue-specific lists of genes to report as negative
- **Count**: Multiple entries by tissue type (ANY, LUNG, etc.)

#### 4. **Technical Comments** (New 9th type)
- **Source 1**: `Technical_Comments.tsv` (specimen/technical disclaimers)
- **Source 2**: `technical_comments_canned_text.tsv` (we created yesterday)
- **Count**: ~10 specimen disclaimers + 11 technical challenge comments

#### 5. **Clinical Implications** (subset of interpretations)
- **Source**: `tbl_reportable_comments_proc.tsv`
- **Column**: `clinical_implications`
- **Count**: 1,485 entries

#### 6. **Clinical Trials** (subset of interpretations)
- **Source**: `tbl_reportable_comments_proc.tsv`
- **Column**: `clinical_trials`
- **Count**: 1,061 entries

### ❌ **MISSING - Need to Create or Find**

#### 1. **General Gene Info** (standalone gene descriptions)
- Not found as separate file
- May need to extract from `General_Gene_and_Variant_Info` column
- Or create from gene databases (COSMIC, OncoKB gene descriptions)

#### 2. **Gene Dx Interpretation** (gene-level diagnostic text)
- Not found as separate entity
- Different from variant-specific interpretations
- Would describe gene's role in cancer diagnosis

#### 3. **Incidental/Secondary Findings**
- No dedicated source file found
- Would need ACMG SF v3.0 gene list templates
- Important for germline reporting

#### 4. **Chromosomal Alteration Interpretation**
- No dedicated source file found
- Would cover aneuploidy, large deletions, translocations
- Different format from SNV/indel interpretations

#### 5. **Biomarkers**
- Not found as structured templates
- Would include TMB, MSI, HRD templates
- May exist in a different format

### 📊 **Data Structure Analysis**

The main file (`tbl_reportable_comments_proc.tsv`) combines multiple text types in single rows:
- Each row represents a variant or alteration
- Multiple text fields per row (info, interpretation, clinical implications)
- Would need to be split/reorganized for the database schema

### 🔄 **Migration Strategy**

1. **Direct Mappings** (can migrate now):
   - Pertinent Negatives → `text_templates` (type: PERTINENT_NEGATIVES)
   - Technical Comments → `technical_comment_templates` (separate table)
   - Variant Interpretations → `text_templates` (type: VARIANT_DX_INTERPRETATION)

2. **Need Extraction/Processing**:
   - Split `General_Gene_and_Variant_Info` into:
     - Gene-only descriptions → GENERAL_GENE_INFO
     - Variant-specific info → GENERAL_VARIANT_INFO

3. **Need Creation**:
   - Gene Dx Interpretation templates
   - Incidental/Secondary Findings templates
   - Chromosomal Alteration templates
   - Biomarker templates

### 📝 **Recommendation**

We have good coverage for:
- Variant-level interpretations (main use case)
- Pertinent negatives
- Technical comments

We're missing templates for:
- Gene-level descriptions
- Chromosomal alterations
- Secondary findings
- Biomarkers

These missing types may not be critical for initial deployment, as the variant interpretation templates are the most frequently used.