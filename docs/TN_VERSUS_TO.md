**SUBJECT:** Technical Specification for Differentiating Tumor-Normal (T-N) and Tumor-Only (T-O) Somatic Variant Analysis Workflows

## 1.0 PURPOSE
This document provides a concise technical specification for a bioinformatics pipeline to process, annotate, and interpret somatic variants from VCF files, correctly differentiating between Tumor-Normal (T-N) and Tumor-Only (T-O) workflows. The logic herein should be used to modulate downstream analysis, knowledge base (KB) queries, rule application, and reporting.

## 2.0 INGESTION & INITIAL PROCESSING
The workflow logic bifurcates at the moment of metadata assignment.

### 2.1 Critical Metadata Flag
  - **Key:** `analysis_type`
  - **Values:** `TUMOR_NORMAL`, `TUMOR_ONLY`
  - **Action:** This flag MUST be present for each sample/case and dictates the entire downstream pipeline logic.

### 2.2 VCF Input & Initial Filtering
  - **`analysis_type: TUMOR_NORMAL`**
      - **Input:** Requires two VCF files: one tumor, one matched normal.
      - **Core Logic:** Direct subtraction. Variants present in the normal sample at a significant VAF (e.g., \>5%) are filtered out as germline. This is the highest-confidence filter for somatic status.
      - **Variant Caller:** Variant callers (e.g., GATK Mutect2, VarScan2) should be run in paired mode.

  - **`analysis_type: TUMOR_ONLY`**
      - **Input:** Requires one VCF file: the tumor sample.
      - **Core Logic:** In-silico germline filtering. Somatic status is *inferred*, not directly observed.
      - **Primary Filters:**
        1.  **Panel of Normals (PoN):** REQUIRED. Filter any variant present in the PoN VCF. This removes recurrent sequencing artifacts and common technical noise.
        2.  **Population AF Databases:** REQUIRED. Filter variants with an allele frequency (AF) above a defined threshold in population databases (e.g., gnomAD AF \> 1%). **Caution:** This can erroneously filter out true somatic variants that are also common in the population (e.g., `JAK2` V617F) or rare germline variants below the threshold.
      - **Variant Caller:** Variant callers should be run in tumor-only mode, which relies heavily on the germline resource and PoN for filtering.

## 3.0 KNOWLEDGE BASE (KB) INTERPRETATION LOGIC
The `analysis_type` flag fundamentally changes the interpretation and confidence level of data retrieved from KBs.

| KB Category | KB Examples | `TUMOR_NORMAL` Logic | `TUMOR_ONLY` Logic (Critical Differences) |
| :--- | :--- | :--- | :--- |
| **Population Allele Frequency** | gnomAD, dbSNP | - Used for context, QC, and annotating known common polymorphisms.\<br\>- Not the primary germline filter. | - **CRITICAL/PRIMARY GERMLINE FILTER.**\<br\>- Variants with AF \> 1% are generally assumed to be germline and filtered.\<br\>- Variants absent from gnomAD receive higher confidence of being somatic. |
| **Clinical Significance (General)** | ClinVar | - Interpretation is direct. A "Pathogenic" variant confirmed as somatic is interpreted in the context of the tumor. | - **AMBIGUOUS INTERPRETATION.** A "Pathogenic" ClinVar finding could be:\<br\>  1. A somatic driver.\<br\>  2. A germline predisposition variant.\<br\>  3. A benign germline polymorphism misclassified in ClinVar.\<br\>- Confidence in somatic actionability is **reduced**. |
| **Somatic/Cancer-Specific** | OncoKB, CIViC, COSMIC CGC, Cancer Hotspots | - Direct application. The variant is known to be somatic, so therapeutic/diagnostic/prognostic evidence is applied with high confidence. | - **LOWER CONFIDENCE APPLICATION.** The KB evidence is only relevant *if the variant is truly somatic*. A match in OncoKB is a "potential" therapeutic target, pending confirmation of somatic origin. |
| **Germline Pathogenicity & Dosage**| ClinGen Haplo/Triplosensitivity, ACMG-SF Gene Lists | - **Confirmatory role.** If a pathogenic LoF variant is found in a tumor suppressor (e.g., `TP53`), these KBs confirm the gene is sensitive to dosage, strengthening the "second hit" hypothesis. | - **RED FLAG / WARNING ROLE.** If a variant is found in a gene with high haploinsufficiency or on an ACMG-SF list, it has a higher prior probability of being a **medically significant germline finding.** This triggers a need for a specific disclaimer. |
| **Functional Prediction** | VEP plugins (SIFT, PolyPhen), SpliceAI, AlphaMissense | - Tool output is used to assess the functional impact of a confirmed somatic variant. | - Tool output is identical, but the *implication* is different. A "damaging" prediction for a variant of unknown origin (T-O) requires cautious interpretation; it may describe the impact of a germline variant. |

**Generalization Rule for Agent:** If a KB's primary value is derived from distinguishing between germline and somatic states, its utility and interpretation are fundamentally altered in a `TUMOR_ONLY` workflow. Confidence scores for annotations from such KBs should be down-weighted.

## 4.0 ADVANCED ANALYSIS & QC
### 4.1 Tumor Purity & Ploidy
  - **Importance:** Crucial for both workflows but essential for interpreting T-O results. Affects VAF-based filtering, copy number variation (CNV) analysis, and Loss of Heterozygosity (LOH) calls.
  - **`TUMOR_NORMAL`:** Purity/ploidy can be estimated more accurately using somatic variant VAFs and B-allele frequencies at heterozygous germline SNP sites.
  - **`TUMOR_ONLY`:** Purity estimation is more challenging and less accurate. It relies on assumptions about tumor ploidy and identifying somatic variants from a mixed signal.
  - **Reference Implementation:** Tools like `HMF Oncoanalyser` provide robust methods for purity, ploidy, and CNV estimation, which are highly recommended.

### 4.2 Contamination Handling

  - **Problem:** Cross-sample contamination can introduce false-positive variants.
  - **Solution:** Use tools (e.g., `VerifyBamID`, `Conpair`) to estimate contamination levels. The `HMF Oncoanalyser` pipeline also includes contamination checks.
  - **Logic:** VAFs of contaminating variants are typically low and can be modeled. In T-O, this is harder to distinguish from subclonal somatic mutations.

## 5.0 GUIDELINE APPLICATION & TIERING
### 5.1 AMP/ASCO/CAP Somatic Tiering
  - **`TUMOR_NORMAL`:** Tiers are assigned with high confidence based on evidence for the confirmed somatic variant.
  - **`TUMOR_ONLY`:**
      - **Tier I/II (Strong/Potential Clinical Significance):** Assignment requires extreme caution. A variant may meet all criteria (e.g., `BRAF` V600E in melanoma) but confidence is lowered by the non-zero chance it's a germline or artifactual finding. Reports must reflect this.
      - **Tier III (Unknown Clinical Significance):** This tier may be broader in T-O, capturing variants of uncertain origin that cannot be confidently placed in Tier I/II or IV.
      - **Tier IV (Benign/Likely Benign):** Assignment is primarily driven by high AF in gnomAD. It is difficult to definitively prove a rare variant is benign without a matched normal.

### 5.2 VICC/CGC Framework
  - **`TUMOR_NORMAL`:** All oncogenicity (`OVS1`, `OS1`, etc.) and benign (`BA1`, `BS1`, `BS2`) evidence codes can be applied as intended.
  - **`TUMOR_ONLY`:**
      - Benign evidence codes based on germline observations (`BA1`, `BS1`, `BS2`) cannot be confidently applied.
      - Oncogenicity codes (`OS`, `OM`, `OP`) are applied to variants that *survive* the germline filtering, but the final oncogenicity score carries the implicit uncertainty of the variant's somatic status.

## 6.0 REPORTING & DISCLAIMERS
The final report must transparently communicate the limitations of the analysis.

### 6.1 Mandatory Disclaimers for `TUMOR_ONLY` Reports
1.  **Somatic Status:** "This analysis was performed on a tumor sample without a matched normal specimen. Somatic variants were inferred by filtering against population databases and a panel of normals. The germline or somatic origin of the reported variants has not been confirmed."
2.  **Therapeutic Implications:** "Therapeutic recommendations based on these findings are predictive and assume the variants are somatic drivers. The absence of a matched normal sample reduces confidence in this assumption."
3.  **Incidental/Secondary Findings:** "This assay may detect variants in cancer predisposition genes (e.g., BRCA1/2, TP53). Any such finding is of uncertain origin (somatic vs. germline) and should be considered a **potential incidental finding.** Confirmatory germline testing from a non-tumor specimen (e.g., blood) is required for definitive diagnosis and genetic counseling."
4.  **Biomarker Limitations:** "Tumor Mutational Burden (TMB) may be overestimated due to the potential inclusion of unfiltered germline variants. Copy Number Variation (CNV) and structural variant (SV) analysis is limited and less accurate without a matched normal."

### 6.2 
# Incidental Findings:
T-N: (Not applicable unless germline analysis was also performed).
T-O: Must trigger a standard, non-optional block detailing the potential germline finding and recommending confirmatory testing and genetic counseling.


### Confidence modellign: 7.0

You are absolutely right. A flat confidence penalty is a blunt, first-generation approach. It fails to capture the rich spectrum of evidence available in a Tumor-Only (T-O) analysis. A modern, robust system should replace this with a dynamic confidence model that quantifies the probability of a variant being somatic based on a multi-featured assessment.

Here is a revised technical specification for an agent, outlining a **Dynamic Somatic Confidence Scoring** model.

---

## 8.0 Abstract

This document supersedes the previous specification's static penalty approach. We will implement a **Dynamic Somatic Confidence (DSC)** score for each variant identified in a Tumor-Only (`analysis_type: TUMOR_ONLY`) workflow. This score, ranging from 0.0 to 1.0, estimates `P(Somatic | evidence)` and directly modulates tiering, rule application, and reporting language. It moves from a simple penalty to a granular, evidence-based probability.

## 8.0 Dynamic Somatic Confidence (DSC) Model

The DSC score for each variant is a function of several independent but complementary evidence modules.

### 8.1 Module 1: Allele Frequency & Purity Context

This module assesses if the variant's VAF is consistent with a somatic event, given the tumor purity.

-   **Inputs:** Variant VAF, Estimated Tumor Purity (e.g., from a tool like `HMF Oncoanalyser`, `ASCAT`, or `facets`).
-   **Logic:**
    -   **High Confidence (Score: 0.8-1.0):** VAF is highly consistent with a heterozygous or homozygous somatic mutation in the main tumor clone. (e.g., VAF ≈ Purity / 2, or VAF ≈ Purity for LOH events).
    -   **Medium Confidence (Score: 0.4-0.7):** VAF is significantly lower than expected for the main clone but plausible for a subclonal somatic event. Requires careful cross-referencing with other modules.
    -   **Low Confidence (Score: <0.4):** VAF is inconsistent with tumor purity (e.g., VAF >> Purity) or falls in a highly ambiguous range (e.g., 1-5%) that could also represent artifacts, contamination, or Clonal Hematopoiesis of Indeterminate Potential (CHIP), especially in blood-contaminated samples.

### 8.2 Module 2: Somatic & Germline Prior Probability

This module leverages external knowledge bases to assess the *a priori* likelihood of the variant being a known somatic driver vs. a known germline variant.

| Evidence Source | Logic & Score Adjustment |
| :--- | :--- |
| **Cancer Hotspots / OncoKB / CIViC** | **Strong Positive Weight:** A variant at a well-established somatic hotspot (e.g., `BRAF` V600E, `IDH1` R132H) has an extremely high prior probability of being somatic. The DSC score should be strongly pushed towards 1.0. |
| **COSMIC Cancer Gene Census / OncoVI TSG & Oncogene lists**| **Moderate Positive Weight:** A novel but predicted-damaging variant (e.g., frameshift, nonsense) in a known tumor suppressor gene or a missense in a known oncogene activation domain increases somatic confidence. |
| **gnomAD / Population DBs**| **Strong Negative Weight:** Any presence in gnomAD, even if below the hard 1% filter threshold, increases the probability of it being a rare germline variant. The score should be proportionally reduced based on its allele frequency and homozygote count. Absence from gnomAD is a positive indicator. |
| **ClinVar / ClinGen (Germline focus)**| **Strong Negative Weight:** A variant listed as "Pathogenic" for a *germline* condition in ClinVar, or in a gene with high ClinGen haploinsufficiency, has a high prior probability of being germline. The DSC score should be significantly lowered, and it should be flagged for secondary findings review. |

### 8.3 Module 3: Genomic Context (For Advanced Implementation)

This module looks at co-occurring genomic events that support a somatic hypothesis.

-   **Loss of Heterozygosity (LOH):** If a variant in a tumor suppressor gene occurs in a region of clear, somatic LOH (determined via B-allele frequency from SNP arrays or sequencing), the confidence that the variant is the "first hit" increases dramatically.
-   **Mutational Signatures:** If the variant's mutation type (e.g., C>T at a CpG site) perfectly matches a dominant, high-confidence mutational signature found in the tumor (e.g., SBS1-Aging), it provides supporting evidence.

## 9.0 Actionable Implementation of the DSC Score

The calculated DSC score is not just an annotation; it actively drives the interpretation logic.

### 9.1 Tiering Logic

-   **Tier I (Strong Clinical Significance):** Requires **DSC Score > 0.9**. The evidence for somatic origin must be nearly unequivocal for the highest tier of actionability.
-   **Tier II (Potential Clinical Significance):** Can be assigned for variants with **0.6 < DSC Score <= 0.9**. The variant meets actionability criteria, but its somatic origin has medium-to-high confidence. The report must reflect this.
-   **Tier III (Unknown Significance):** This is the default for variants with an ambiguous DSC score (e.g., **0.2 < DSC Score <= 0.6**) OR for high-confidence somatic variants (`DSC > 0.9`) that lack a known clinical significance. The score helps distinguish between "unknown significance because origin is unclear" and "unknown significance because function is unclear."

### 9.2 Reporting Language Modulation

The DSC score dictates the certainty of the language used in the report.

| DSC Score Range | Sample `Variant Dx Interpretation` Language |
| :--- | :--- |
| **> 0.99** | "This **somatic** `BRAF` V600E variant confers sensitivity to..." |
| **0.6 - 0.9** | "This `KIT` D816V variant, **which is likely somatic,** has been associated with..." |
| **0.2 - 0.6** | "A `TP53` R248Q variant of **uncertain origin** was detected. If somatic, this variant is..." |
| **< 0.99** | "A variant was detected but has low confidence of being somatic and is likely a rare germline finding. Not reported as a primary finding." |

### 9.3 Automated Disclaimers & Reflex Actions

-   **Secondary Findings Flag:** Any variant in an ACMG-SF gene with a **DSC Score < 0.8** (i.e., it cannot be confidently ruled-in as purely somatic) MUST trigger the mandatory disclaimer about potential incidental findings and the need for confirmatory germline testing.
-   **Manual Review Trigger:** All variants meeting Tier I/II criteria but with a **DSC Score < 0.9** should be automatically flagged for mandatory manual review by a qualified pathologist or genomic scientist.
