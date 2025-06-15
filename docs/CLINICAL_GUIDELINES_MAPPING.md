# Clinical Guidelines Mapping for 42 Knowledge Bases

This document provides comprehensive mapping of all 42 knowledge bases to specific clinical classification guidelines: AMP/ASCO/CAP (2017), VICC/CGC (2022), and OncoKB therapeutic tiers.

## Framework Abbreviations
- **AMP/ASCO/CAP 2017**: Standards and Guidelines for Somatic Variant Interpretation in Cancer
- **VICC/CGC**: Variant Interpretation for Cancer Consortium / Cancer Gene Census  
- **OncoKB**: Memorial Sloan Kettering precision oncology knowledge base

---

## Complete Knowledge Base to Clinical Rule Mapping

### **Population Frequencies & Variant Context**

#### 1. gnomAD Exomes (20GB)
**Purpose**: Population allele frequencies for rare variant assessment
**Somatic Use**: Core filtering step to remove common germline polymorphisms from somatic call sets, especially in tumor-only analysis
**Tools Using Resource**: Ensembl VEP, Annovar, OpenCRAVAT, PCGR, GATK FilterMutectCalls

- **AMP/ASCO/CAP 2017 Rules**:
  - **Tier IV assignment**: VAF >1% suggests common germline variant, unlikely to be somatic driver
  - **Tier filtering**: Remove high-frequency variants before therapeutic tier assessment
- **VICC/CGC Rules**:
  - **SBVS1** (Strong Benign Very Strong): VAF >5% → Strong Evidence Against Oncogenicity (-8 points)
  - **OP4** (Oncogenic Supporting): Absent from population databases → Supporting Oncogenic (+1 point)
- **OncoKB**: Population frequency context for variant filtering before therapeutic assessment
- **Tiering Impact**: Common variants (>1% VAF) → Tier IV (benign/germline); Rare variants (<0.1% VAF) → Eligible for Tiers I-III assessment
- **Implementation**: Query VAF by ancestry group, apply population-specific thresholds for tumor-only filtering

#### 2. gnomAD Genomes (150GB) + Indices (1GB + 200MB)
**Purpose**: Comprehensive population frequencies including structural variants
- **Same rule mapping as gnomAD Exomes**
- **Additional**: Structural variant population frequencies for CNV interpretation
- **Implementation**: Primary source for VAF lookups due to broader coverage

#### 3. dbSNP (25GB)
**Purpose**: Variant identifiers and common variant flagging
**Somatic Use**: Variant standardization and common variant identification for somatic filtering
**Tools Using Resource**: Ensembl VEP, Annovar, OpenCRAVAT, PCGR, GATK FilterMutectCalls

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier IV assignment**: dbSNP common variants (with population frequency) likely germline = Tier IV
  - **Variant standardization**: Consistent rsID nomenclature supports reliable tier assignment
  - **Evidence quality**: rsID presence provides variant validation for tier assignment
  - **Evidence levels**: Multi-submitter rsIDs > single submitter > novel variants
  - **Context**: Essential for both tumor-only and tumor-normal; variant identification infrastructure
- **VICC/CGC 2022 Impact**:
  - **SBVS1** (-8 points): dbSNP common variants provide strong benign evidence when paired with frequency data
  - **Variant validation**: rsID presence supports variant quality for oncogenicity scoring
- **OncoKB Impact**:
  - **Variant standardization**: dbSNP rsIDs enable consistent OncoKB therapeutic annotation lookup
  - **Quality filtering**: rsID validation supports reliable therapeutic matching
- **Canned Text Types**:
  - **General Variant Info**: rsID nomenclature included in variant identification
  - **Technical Comments**: Variant standardization status included in technical notes
- **Implementation**: rsID lookup, common variant flagging, variant standardization, quality validation

### **Clinical Evidence & Pathogenicity**

#### 4. ClinVar VCF (200MB) + Index (1MB) + TSV (150MB)
**Purpose**: Clinical significance classifications and prior observations
**Somatic Use**: Very useful - also contains classifications for somatic variants and their clinical significance in cancer
**Tools Using Resource**: Ensembl VEP, Annovar, OpenCRAVAT, PCGR

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I assignment**: Pathogenic variants with FDA-approved therapy evidence in ClinVar
  - **Tier II assignment**: Pathogenic variants with investigational therapy evidence
  - **Tier III assignment**: Pathogenic variants without clear therapeutic actionability
  - **Tier IV assignment**: Benign/likely benign classifications or conflicting interpretations
  - **Evidence levels**: Expert panel assertions (★★★★) > multiple submitters (★★★) > single submitter (★★)
  - **Context**: Applicable to both tumor-only and tumor-normal; somatic classifications prioritized
- **VICC/CGC 2022 Impact**:
  - **OS2** (+4 points): Well-established pathogenic in professional cancer guidelines
  - **SBS2** (-4 points): Well-established benign with functional studies showing no oncogenic effect
  - **Context**: Cancer-specific ClinVar submissions weighted higher than germline
- **OncoKB Impact**:
  - **Cross-validation**: ClinVar pathogenic + OncoKB evidence → Enhanced confidence
  - **Conflict resolution**: OncoKB therapeutic evidence takes precedence over ClinVar for tier assignment
- **Canned Text Types**:
  - **General Variant Info**: ClinVar significance and review status included in variant descriptions
  - **Variant Dx Interpretation**: Pathogenic ClinVar classifications increase likelihood of detailed interpretation message
  - **Technical Comments**: Conflicting ClinVar interpretations trigger technical annotation messages
- **Implementation**: Parse review status, prioritize expert panel assertions, filter for somatic/cancer significance, weight by submission quality

#### 5. CIViC Variants (5MB) + Hotspots (10MB)
**Purpose**: Clinical evidence summaries for cancer variants
**Somatic Use**: Primary use - provides evidence-based interpretations of variants for diagnosis, prognosis, and therapy prediction
**Tools Using Resource**: Ensembl VEP (plugin), OpenCRAVAT, PCGR

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I assignment**: CIViC Level A evidence for FDA-approved therapies in this cancer type
  - **Tier II assignment**: CIViC Level B evidence for investigational therapies or Level A for different cancer type
  - **Tier IIe assignment**: CIViC emerging evidence with high-quality clinical trials
  - **Tier III assignment**: CIViC Level C/D evidence without clear therapeutic actionability
  - **Tier IV assignment**: CIViC evidence suggesting lack of clinical significance
  - **Evidence levels**: Level A (★★★★) > Level B (★★★) > Level C (★★) > Level D (★)
  - **Context**: Exclusively somatic/cancer-focused evidence
- **VICC/CGC 2022 Impact**:
  - **OS2** (+4 points): CIViC Level A/B evidence with strong clinical validation
  - **OM4** (+2 points): CIViC evidence for mutation in gene with established oncogenic role
  - **OM2** (+2 points): CIViC functional studies demonstrating oncogenic mechanism
- **OncoKB Impact**:
  - **Cross-validation**: CIViC + OncoKB concordance → Enhanced evidence strength
  - **Complementary evidence**: CIViC clinical trials + OncoKB therapeutic annotations
- **Canned Text Types**:
  - **Variant Dx Interpretation**: High-level CIViC evidence (A/B) triggers detailed therapeutic interpretation messages
  - **Biomarkers**: CIViC biomarker evidence increases likelihood of biomarker-specific text
  - **General Variant Info**: CIViC evidence summaries included in variant annotations
- **Implementation**: Evidence tier mapping, therapeutic context integration, CIViC evidence level to AMP tier translation, clinical trial data extraction

#### 6. OncoKB Genes (1MB)
**Purpose**: Curated cancer gene lists and actionability framework
**Somatic Use**: PRIMARY resource for therapeutic actionability - links specific somatic mutations to their oncogenic effects and associated therapies (clinical actionability)
**Tools Using Resource**: OncoKB MafAnnotator, OpenCRAVAT, PCGR

- **AMP/ASCO/CAP 2017 Impact**: 
  - **Tier I assignment**: OncoKB Level 1 evidence (FDA-approved therapy for this cancer type)
  - **Tier II assignment**: OncoKB Level 2A/2B evidence (FDA-approved for different cancer or investigational)
  - **Tier III assignment**: OncoKB Level 3A/3B evidence (Clinical evidence but not standard care)
  - **Tier IV assignment**: OncoKB Level 4 evidence (Biological evidence only) or no OncoKB evidence
- **VICC/CGC 2022 Impact**: 
  - **OVS1** (+8 points): Null variant in OncoKB tumor suppressor gene
  - **OS1** (+4 points): Activating variant in OncoKB oncogene
  - **Gene context validation**: Cross-validates cancer gene classifications
- **OncoKB Impact**: 
  - **Core framework**: Direct evidence level mapping (Level 1-4)
  - **Therapeutic matching**: Cancer-type-specific therapy recommendations
  - **Drug-variant associations**: Specific mutation-therapy pairs
- **Canned Text Types**: 
  - **Gene Dx Interpretation**: OncoKB gene summaries and cancer roles
  - **Variant Dx Interpretation**: Specific variant therapeutic implications
  - **Biomarkers**: FDA-approved biomarker classifications
- **Implementation**: Gene classification lookup, therapeutic context assignment, cancer-type-specific therapy matching

#### 7. CancerMine (20MB)
**Purpose**: Literature-mined oncogenes and tumor suppressors
**Somatic Use**: Used to annotate genes with their cancer-related roles based on automated literature mining
**Tools Using Resource**: OpenCRAVAT, Custom annotation scripts

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I clincher**: CancerMine oncogene/TSG + OncoKB Level 1 therapy = definitive Tier I
  - **Tier II clincher**: CancerMine cancer gene + investigational therapy evidence = solid Tier II
  - **Tier III assignment**: CancerMine cancer gene role + hotspot evidence but no therapy = Tier III
  - **Tier IV assignment**: CancerMine contradicts other sources OR no cancer gene role = Tier IV consideration
  - **Evidence levels**: High-confidence literature mining (>10 papers) > moderate (3-10 papers) > low (<3 papers)
  - **Context**: Applicable to both tumor-only and tumor-normal; gene-level classification
- **VICC/CGC 2022 Impact**:
  - **OS1** (+4 points): CancerMine high-confidence oncogene classification
  - **OVS1** (+8 points): CancerMine high-confidence tumor suppressor classification
  - **Supporting evidence**: When COSMIC CGC unavailable, CancerMine provides backup gene classification
- **OncoKB Impact**:
  - **Cross-validation**: CancerMine + OncoKB gene concordance → Enhanced confidence in gene role
  - **Conflict resolution**: OncoKB takes precedence over CancerMine for therapeutic decisions
- **Canned Text Types**:
  - **Gene Dx Interpretation**: CancerMine high-confidence classifications increase likelihood of gene role description
  - **General Gene Info**: Literature-mined gene roles included in background information
- **Implementation**: Literature confidence scoring, automated text mining validation, conflict resolution with authoritative sources

### **Cancer Hotspots & Recurrent Mutations**

#### 8. Cancer Hotspots VCF (5MB) + Index (1MB)
**Purpose**: Memorial Sloan Kettering recurrent mutations
**Somatic Use**: Core resource - identifies recurrently mutated codons (hotspots) that are likely cancer drivers
**Tools Using Resource**: Ensembl VEP, Annovar, OpenCRAVAT, PCGR, vcf2maf

- **AMP/ASCO/CAP 2017 Rules**:
  - **Tier II-III assignment**: Hotspot evidence supports driver status and therapeutic tier assignment
  - **Driver validation**: Recurrent mutations indicate likely oncogenic mechanism
- **VICC/CGC Rules**:
  - **OS3** (Oncogenic Strong): Well-established hotspot with significant recurrence (+4 points)
  - **OM3** (Oncogenic Moderate): Hotspot with moderate evidence (+2 points)
- **OncoKB**: Evidence for variant-level therapeutic significance
- **Tiering Impact**: Hotspot variants in actionable genes → Tier I-II (if therapy available); Hotspot in driver gene without therapy → Tier III; Non-hotspot variants → Lower tier consideration
- **Implementation**: Position-based lookup with recurrence threshold, frequency-based scoring

#### 9. MSK SNV Hotspots (10MB) + Indel Hotspots (5MB)
**Purpose**: cBioPortal comprehensive hotspot data
**Somatic Use**: An updated, curated list of SNV and indel hotspots from MSK, indicating likely driver events
**Tools Using Resource**: Ensembl VEP, Annovar, OpenCRAVAT, PCGR, vcf2maf

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I clincher**: MSK hotspot + OncoKB Level 1 therapy in same gene = definitive Tier I
  - **Tier II clincher**: MSK hotspot + investigational therapy OR hotspot in druggable gene = solid Tier II
  - **Tier III assignment**: MSK hotspot in cancer gene but no targeted therapy available = Tier III
  - **Tier IV assignment**: Hotspot with conflicting evidence OR low recurrence = Tier IV consideration
  - **Evidence levels**: High-frequency hotspots (>10 observations) > moderate (3-10) > low (2-3)
  - **Context**: Applicable to both tumor-only and tumor-normal; position-specific evidence
- **VICC/CGC 2022 Impact**:
  - **OS3** (+4 points): High-frequency MSK hotspot with significant recurrence (>10 cases)
  - **OM3** (+2 points): Moderate-frequency MSK hotspot (3-10 cases)
  - **Indel-specific**: In-frame indel hotspots qualify for OM3 scoring
- **OncoKB Impact**:
  - **Hotspot validation**: MSK + OncoKB hotspot concordance → Enhanced therapeutic relevance
  - **Extended coverage**: MSK provides broader hotspot coverage than OncoKB alone
- **Canned Text Types**:
  - **Variant Dx Interpretation**: High-frequency hotspots increase likelihood of detailed driver mechanism description
  - **General Variant Info**: Hotspot recurrence data included in variant frequency annotations
- **Implementation**: Extended hotspot coverage beyond point mutations, frequency-based scoring, indel hotspot identification

#### 10. MSK 3D Hotspots (5MB)
**Purpose**: Protein structure-based hotspot predictions
**Somatic Use**: Identifies mutation hotspots clustered in 3D protein structures, providing functional evidence for driver status
**Tools Using Resource**: OpenCRAVAT, PCGR, Custom annotation scripts

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I clincher**: 3D hotspot + therapeutic target in same domain = strong Tier I evidence
  - **Tier II clincher**: 3D structural hotspot + druggable protein domain = solid Tier II
  - **Tier III assignment**: 3D hotspot suggests functional impact but no therapy = Tier III
  - **Tier IV assignment**: Variant outside structural hotspots = lower tier consideration
  - **Evidence levels**: High-confidence 3D clustering (>5 mutations/domain) > moderate (3-5) > low (2-3)
  - **Context**: Applicable to both tumor-only and tumor-normal; domain-level functional evidence
- **VICC/CGC 2022 Impact**:
  - **OM1** (+2 points): Variant located in 3D structural hotspot within critical functional domain
  - **Enhanced confidence**: 3D clustering provides stronger evidence than linear hotspots alone
- **OncoKB Impact**:
  - **Structural context**: 3D hotspots provide mechanistic support for OncoKB therapeutic annotations
  - **Domain targeting**: Structural hotspots identify druggable domains for therapeutic development
- **Canned Text Types**:
  - **Variant Dx Interpretation**: 3D structural evidence increases likelihood of mechanistic interpretation
  - **General Variant Info**: Protein domain context included in structural annotations
- **Implementation**: 3D structure-based domain criticality assessment, spatial clustering analysis, functional domain mapping

#### 11. COSMIC Cancer Gene Census (2MB)
**Purpose**: Curated cancer gene classifications  
**Somatic Use**: Primary use - the Cancer Gene Census lists genes with causal roles in cancer
**Tools Using Resource**: Ensembl VEP, OpenCRAVAT, PCGR

- **AMP/ASCO/CAP 2017 Rules**:
  - **Driver gene context**: CGC classification supports higher tier assignment for variants in established cancer genes
  - **Therapeutic targeting**: Known cancer genes more likely to have targeted therapy options
- **VICC/CGC Rules**:
  - **OVS1/OS1** primary source for tumor suppressor/oncogene classification
  - **Core framework** for VICC rule implementation
- **OncoKB**: Gene classification cross-validation
- **Tiering Impact**: Variants in CGC genes → Higher tier eligibility; Loss-of-function in CGC tumor suppressors → Tier I-II potential; Activating variants in CGC oncogenes → Tier I-II potential
- **Implementation**: Authoritative gene role assignment (TSG vs. oncogene vs. fusion), cancer gene context for therapeutic relevance

### **Gene Function & Protein Domains**

#### 12. UniProt Swiss-Prot (300MB)
**Purpose**: Curated protein sequences and functional annotations
**Somatic Use**: Foundational - provides reference protein sequences and functional information to assess a variant's impact
**Tools Using Resource**: Ensembl VEP, Annovar, OpenCRAVAT

- **AMP/ASCO/CAP 2017 Rules**:
  - **Functional context**: Critical domain variants more likely to have therapeutic implications
  - **Driver assessment**: Functional impact supports somatic driver classification for tier assignment
- **VICC/CGC Rules**:
  - **OM1** (Oncogenic Moderate): Critical functional domain (+2 points)
  - **SBP1** (Supporting Benign): Non-critical domain (-1 point)
- **OncoKB**: Protein function context for therapeutic relevance
- **Tiering Impact**: Variants in critical functional domains → Higher tier consideration; Variants in non-functional regions → Tier IV tendency; Domain disruption in druggable proteins → Tier I-II potential
- **Implementation**: Domain boundary mapping, functional consequence prediction, protein structure context

#### 13. Pfam Domains (100MB)
**Purpose**: Protein family and domain classifications
**Somatic Use**: Foundational - used to annotate a variant's location within a protein's functional domains
**Tools Using Resource**: Ensembl VEP, Annovar, OpenCRAVAT

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I clincher**: Critical Pfam domain disruption + FDA-approved domain-targeted therapy = definitive Tier I
  - **Tier II clincher**: Functional domain variant + investigational domain-targeting therapy = solid Tier II
  - **Tier III assignment**: Important domain disruption but no domain-specific therapy = Tier III
  - **Tier IV assignment**: Variant in non-functional domain regions = Tier IV consideration
  - **Evidence levels**: Highly conserved domains > moderately conserved > poorly conserved domains
  - **Context**: Applicable to both tumor-only and tumor-normal; domain-level functional assessment
- **VICC/CGC 2022 Impact**:
  - **OM1** (+2 points): Variant in critical functional Pfam domain (DNA-binding, kinase, etc.)
  - **SBP1** (-1 point): Variant in non-critical or poorly conserved domain regions
- **OncoKB Impact**:
  - **Domain-level targeting**: Pfam domain annotations support domain-specific therapeutic strategies
  - **Functional validation**: Domain disruption provides mechanistic support for OncoKB annotations
- **Canned Text Types**:
  - **Variant Dx Interpretation**: Critical domain disruption increases likelihood of functional impact description
  - **General Variant Info**: Pfam domain context included in protein functional annotations
- **Implementation**: Domain family criticality assessment, conservation scoring, functional domain boundary mapping

#### 14. NCBI Gene Info (200MB)
**Purpose**: Comprehensive gene annotations and mappings
**Somatic Use**: Foundational dependency for all gene-based annotators - provides comprehensive gene context
**Tools Using Resource**: Foundational for VEP, Annovar, and all gene-based annotation tools

- **AMP/ASCO/CAP 2017 Impact**:
  - **Essential infrastructure**: Gene symbol standardization required for all tier assignments
  - **Cross-database coordination**: Links genes across OncoKB, CIViC, COSMIC for consistent tier assignment
  - **Gene context validation**: Ensures accurate gene-therapy matching for Tier I-II assignments
  - **Context**: Foundational for both tumor-only and tumor-normal; gene-level infrastructure
- **VICC/CGC 2022 Impact**:
  - **Gene context foundation**: Essential for all VICC rule applications requiring gene identification
  - **Cross-reference validation**: Ensures consistent gene symbols across oncogenicity assessment databases
- **OncoKB Impact**:
  - **Gene matching infrastructure**: Critical for accurate gene-therapy associations in OncoKB
  - **Symbol standardization**: Ensures consistent gene targeting across therapeutic annotations
- **Canned Text Types**:
  - **General Gene Info**: NCBI gene descriptions and aliases included in gene background text
  - **Gene Dx Interpretation**: Official gene names and descriptions enhance gene interpretation messages
- **Implementation**: Gene symbol mapping, cross-database coordination, alias resolution, gene description integration

#### 15. HGNC Mappings (5MB)
**Purpose**: Official gene symbol standardization
**Somatic Use**: Foundational dependency for all gene-based annotators - provides official gene symbol authority
**Tools Using Resource**: Foundational for VEP, Annovar, OpenCRAVAT, PCGR, and all annotation tools

- **AMP/ASCO/CAP 2017 Impact**:
  - **Critical infrastructure**: HGNC standardization prevents gene mismatching that could affect tier assignments
  - **Therapeutic accuracy**: Ensures accurate gene-drug matching for Tier I-II assignments
  - **Cross-database consistency**: Uniform gene symbols across OncoKB, CIViC, and COSMIC prevent annotation errors
  - **Context**: Essential for both tumor-only and tumor-normal; gene symbol foundation
- **VICC/CGC 2022 Impact**:
  - **Rule application accuracy**: HGNC standardization ensures correct gene context for all VICC scoring
  - **Database integration**: Prevents gene symbol conflicts that could affect oncogenicity scoring
- **OncoKB Impact**:
  - **Therapeutic precision**: HGNC ensures accurate gene-therapy associations in OncoKB mapping
  - **Symbol authority**: Official gene symbols prevent therapeutic mismatching
- **Canned Text Types**:
  - **All text types**: HGNC provides official gene symbols and names for all gene-related text generation
  - **Gene Dx Interpretation**: Official gene nomenclature ensures professional gene name usage
- **Implementation**: Primary gene symbol authority, alias resolution, cross-database gene symbol harmonization

### **Clinical Biomarkers & Thresholds**

#### 16. Clinical Biomarkers (2MB)
**Purpose**: Curated biomarker definitions and clinical thresholds
**Somatic Use**: Essential for standardization - provides clinical thresholds for TMB, MSI, HRD cutoffs used in therapeutic decisions
**Tools Using Resource**: PCGR, OpenCRAVAT, Custom biomarker analysis pipelines

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I clincher**: High TMB (>20 mut/Mb) + FDA-approved immunotherapy = definitive Tier I biomarker
  - **Tier I clincher**: MSI-High + FDA-approved pembrolizumab = definitive Tier I biomarker
  - **Tier II assignment**: Intermediate biomarker levels + investigational therapy evidence = Tier II
  - **Tier IV assignment**: Biomarker levels below therapeutic thresholds = Tier IV
  - **Evidence levels**: FDA-approved thresholds > professional guideline thresholds > research thresholds
  - **Context**: Strongly skewed toward tumor-only analysis (TMB, MSI, HRD calculations)
- **VICC/CGC 2022 Impact**:
  - **Not directly applicable**: VICC focuses on variant-level oncogenicity, not genome-wide biomarkers
  - **Indirect support**: High TMB may indicate hypermutated tumor supporting individual variant significance
- **OncoKB Impact**:
  - **Level 1 biomarkers**: Direct integration with FDA-approved biomarker thresholds
  - **Level 2-4 biomarkers**: Research and investigational biomarker threshold applications
- **Canned Text Types**:
  - **Biomarkers**: High-level biomarkers (TMB-High, MSI-High) trigger specific biomarker interpretation messages
  - **Variant Dx Interpretation**: Biomarker context enhances individual variant therapeutic interpretation
- **Implementation**: TMB, MSI, HRD threshold application for therapeutic decisions, biomarker-therapy matching, clinical cutoff validation

#### 17. OncoTree Classifications (1MB)
**Purpose**: Cancer type taxonomies for context-specific interpretation
**Somatic Use**: Provides a standardized ontology for cancer types, which is essential for context-specific variant interpretation
**Tools Using Resource**: OncoKB MafAnnotator, cBioPortal data validation scripts

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I clincher**: Variant + OncoKB Level 1 therapy + exact OncoTree cancer type match = definitive Tier I
  - **Tier II assignment**: Variant + therapy approved for related OncoTree cancer type = Tier II
  - **Tier III assignment**: Variant + therapy for distant OncoTree cancer type = Tier III consideration
  - **Context dependency**: Tier assignment heavily dependent on cancer type specificity
  - **Evidence levels**: Exact cancer type match > related cancer type > organ system match > distant cancer type
  - **Context**: Essential for both tumor-only and tumor-normal; cancer-type-specific therapeutic matching
- **VICC/CGC 2022 Impact**:
  - **Tumor type context**: OncoTree classification provides cancer-specific context for oncogenicity assessment
  - **Gene relevance**: Cancer type determines relevance of specific oncogenes/TSGs for scoring
- **OncoKB Impact**:
  - **Primary framework**: OncoTree classification directly determines OncoKB therapeutic indication matching
  - **Level assignment**: OncoKB evidence levels depend on cancer type specificity via OncoTree
- **Canned Text Types**:
  - **Gene Dx Interpretation**: Cancer-specific gene relevance based on OncoTree classification
  - **Variant Dx Interpretation**: Cancer-type-specific therapeutic implications enhance interpretation messages
- **Implementation**: Cancer type standardization, therapeutic context matching, hierarchical cancer classification

### **Gene Dosage Sensitivity**

#### 18. ClinGen Gene Curation (2MB)
**Purpose**: Expert-curated gene-disease relationships
**Somatic Use**: PCGR (for contextual gene information)
**Tools Using Resource**: PCGR, VEP for gene context

- **AMP/ASCO/CAP 2017 Impact**:
  - **Gene context validation**: ClinGen gene curation supports cancer gene relevance for tier assignment
  - **LoF relevance**: Null variants in ClinGen-curated cancer genes more likely to achieve higher tiers
  - **Tier III assignment**: Variants in ClinGen genes without therapy = Tier III consideration
  - **Evidence levels**: Expert panel curation > multiple submitter consensus > single submissions
  - **Context**: Primarily germline-focused but provides gene-disease context for somatic interpretation
- **VICC/CGC 2022 Impact**:
  - **OVS1** (+8 points): ClinGen curation supports tumor suppressor classification for null variants
  - **Gene mechanism validation**: Expert curation provides high-confidence gene function evidence
- **OncoKB Impact**:
  - **Gene validation**: ClinGen expert curation cross-validates OncoKB gene-cancer associations
  - **Mechanism confirmation**: LoF mechanisms from ClinGen support therapeutic targeting strategies
- **Canned Text Types**:
  - **Gene Dx Interpretation**: ClinGen expert curation enhances gene-disease relationship descriptions
  - **General Gene Info**: Curated gene mechanisms included in background information
- **Implementation**: Authoritative source for gene-disease mechanisms, expert panel evidence integration

#### 19. ClinGen Haploinsufficiency (1MB)
**Purpose**: Genes sensitive to single-copy loss
**Somatic Use**: PCGR (to add context to somatic loss-of-function mutations)
**Tools Using Resource**: PCGR for dosage sensitivity context

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier II-III enhancement**: Haploinsufficient genes with LoF variants may have enhanced therapeutic relevance
  - **Copy loss significance**: Validates importance of heterozygous deletions in cancer genes
  - **Evidence levels**: Haploinsufficiency score 3 (sufficient evidence) > score 2 (emerging) > score 1 (little)
  - **Context**: More relevant for tumor-normal analysis where germline LoF can be identified
- **VICC/CGC 2022 Impact**:
  - **OVS1** (+8 points): Haploinsufficiency strongly supports tumor suppressor mechanism for null variants
  - **Gene dosage validation**: High HI scores validate single-hit inactivation potential
- **OncoKB Impact**:
  - **Dosage sensitivity context**: Haploinsufficiency informs therapeutic strategies for tumor suppressors
  - **Copy number relevance**: Validates therapeutic targeting of genes sensitive to copy loss
- **Canned Text Types**:
  - **Gene Dx Interpretation**: Haploinsufficiency scores enhance tumor suppressor mechanism descriptions
  - **Technical Comments**: Dosage sensitivity scoring included in technical annotation notes
- **Implementation**: Haploinsufficiency scoring, LoF variant prioritization, dosage sensitivity thresholding

#### 20. ClinGen Triplosensitivity (1MB)
**Purpose**: Genes sensitive to extra copies
**Somatic Use**: PCGR (to add context to somatic copy number gains)
**Tools Using Resource**: PCGR for amplification sensitivity context

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I-II enhancement**: Triplosensitive oncogenes with amplification + targeted therapy = higher tier potential
  - **Amplification significance**: Validates therapeutic relevance of gene amplifications
  - **Evidence levels**: Triplosensitivity score 3 (sufficient) > score 2 (emerging) > score 1 (little)
  - **Context**: Relevant for both tumor-only and tumor-normal when assessing amplifications
- **VICC/CGC 2022 Impact**:
  - **OS1** (+4 points): Triplosensitivity supports oncogene mechanism for amplified genes
  - **Gene dosage validation**: High TS scores validate gain-of-function through amplification
- **OncoKB Impact**:
  - **Amplification targeting**: Triplosensitivity informs therapeutic strategies for amplified oncogenes
  - **Copy gain relevance**: Validates therapeutic targeting of amplification-sensitive genes
- **Canned Text Types**:
  - **Gene Dx Interpretation**: Triplosensitivity scores enhance oncogene amplification descriptions
  - **Chromosomal Alteration Interpretation**: TS scores inform copy gain significance interpretation
- **Implementation**: CNV significance assessment, amplification scoring, dosage sensitivity for gains

### **Drug-Target Associations**

#### 21. Open Targets Platform (500MB)
**Purpose**: Disease-target and drug-target associations
**Somatic Use**: Used to evaluate a gene's association with cancer, helping to prioritize potential somatic driver genes
**Tools Using Resource**: PCGR, Custom research pipelines

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier II clincher**: Open Targets high-score cancer association + investigational therapy = solid Tier II
  - **Tier III assignment**: Open Targets cancer association but pre-clinical evidence only = Tier III
  - **Evidence prioritization**: Disease association scores guide therapeutic relevance assessment
  - **Evidence levels**: Clinical evidence > genetic association > functional evidence > literature mining
  - **Context**: Applicable to both tumor-only and tumor-normal; gene-disease association focus
- **VICC/CGC 2022 Impact**:
  - **OS1** (+4 points): Open Targets cancer association supports oncogene/TSG classification validation
  - **Gene context**: Disease association scores provide supporting evidence for cancer gene relevance
- **OncoKB Impact**:
  - **Gene prioritization**: Open Targets association scores complement OncoKB gene classifications
  - **Target validation**: Disease-target associations validate therapeutic gene targeting strategies
- **Canned Text Types**:
  - **Gene Dx Interpretation**: Open Targets disease associations enhance gene-cancer relationship descriptions
  - **General Gene Info**: Disease association scores included in gene background information
- **Implementation**: Disease association scoring, therapeutic target validation, gene-cancer relationship quantification

#### 22. DGIdb Interactions (50MB)
**Purpose**: Drug-gene interaction database
**Somatic Use**: Primary use - used to find potential therapies by identifying drug-gene interactions for mutated genes
**Tools Using Resource**: OpenCRAVAT, PCGR

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I clincher**: Variant in gene + DGIdb FDA-approved drug + OncoKB Level 1 = definitive Tier I
  - **Tier II clincher**: Variant in gene + DGIdb investigational drug + clinical trial evidence = solid Tier II
  - **Tier IIe assignment**: Variant in gene + DGIdb emerging targeted therapy = Tier IIe consideration
  - **Tier III assignment**: Variant in druggable gene but pre-clinical stage drugs only = Tier III
  - **Tier IV assignment**: No drug-gene interactions available = lower tier consideration
  - **Evidence levels**: FDA-approved drugs (★★★★) > clinical trial drugs (★★★) > preclinical (★★)
  - **Context**: Applicable to both tumor-only and tumor-normal; gene-drug interaction focus
- **VICC/CGC 2022 Impact**:
  - **Supporting context**: DGIdb drug-target relationships provide additional confidence for oncogene/TSG classification
  - **Therapeutic relevance**: Druggable genes receive enhanced consideration in oncogenicity scoring
- **OncoKB Impact**:
  - **Level 2-4 evidence**: DGIdb provides broader drug interaction context beyond OncoKB curated set
  - **Drug mechanism validation**: Cross-validates OncoKB therapeutic annotations with broader drug interaction data
- **Canned Text Types**:
  - **Variant Dx Interpretation**: Drug-gene interactions increase likelihood of targeted therapy discussion
  - **Biomarkers**: Druggable genes enhance biomarker-relevant therapeutic interpretation
- **Implementation**: Targeted therapy identification, drug mechanism validation, therapeutic target prioritization, FDA approval status integration

### **Disease & Pathway Context**

#### 23. MONDO Disease Ontology (50MB)
**Purpose**: Structured disease classifications
**Somatic Use**: Essential for standardization - provides hierarchical cancer classification linking specific cancer types to broader terms
**Tools Using Resource**: Foundational for Monarch Initiative, Kids First DRC, ClinGen/VICC frameworks

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier assignment context**: MONDO cancer classification provides standardized context for tier assignment
  - **Cancer type matching**: Hierarchical disease structure enables therapeutic indication matching
  - **Evidence standardization**: Common disease terminology supports consistent tier assignment across cases
  - **Evidence levels**: Specific cancer type > cancer group > organ system > general cancer
  - **Context**: Essential framework for both tumor-only and tumor-normal cancer type classification
- **VICC/CGC 2022 Impact**:
  - **Cancer classification context**: MONDO ontology provides standardized framework for cancer-specific oncogenicity assessment
  - **Disease hierarchy**: Enables cancer type-specific gene relevance assessment
- **OncoKB Impact**:
  - **Disease matching framework**: MONDO provides structured cancer classification for OncoKB therapeutic indication matching
  - **Level assignment context**: Disease hierarchy supports precise therapeutic context assignment
- **Canned Text Types**:
  - **Gene Dx Interpretation**: Cancer classification terms standardize gene-disease relationship descriptions
  - **Variant Dx Interpretation**: Disease ontology enhances cancer-specific variant interpretation messages
  - **General Gene Info**: Standardized cancer terminology in gene background descriptions
- **Implementation**: Disease term standardization, clinical context mapping, hierarchical cancer classification

#### 24. TCGA MC3 Mutations (200MB)
**Purpose**: Pan-cancer somatic mutation landscape
**Somatic Use**: Used as a reference/comparison cohort for mutation frequencies or to build other annotation resources (e.g., hotspots)
**Tools Using Resource**: maftools (R package for analysis), used as input to build resources for other tools

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I-II enhancement**: TCGA recurrent mutations provide population-level driver validation for therapeutic targeting
  - **Tier III assignment**: TCGA prevalent mutations without therapeutic actionability = Tier III consideration
  - **Frequency thresholds**: >1% TCGA prevalence → driver validation; >5% prevalence → strong driver evidence
  - **Evidence levels**: Pan-cancer prevalence > cancer-type prevalence > single cancer type observation
  - **Context**: Applicable to both tumor-only and tumor-normal; somatic mutation frequency reference
- **VICC/CGC 2022 Impact**:
  - **OS3** (+4 points): TCGA high-frequency mutations provide strong hotspot validation evidence
  - **Population context**: Cancer-specific mutation frequencies support oncogenicity assessment
- **OncoKB Impact**:
  - **Mutation validation**: TCGA prevalence data validates OncoKB mutation significance across cancer types
  - **Population context**: Frequency data supports therapeutic relevance assessment
- **Canned Text Types**:
  - **Variant Dx Interpretation**: TCGA prevalence data enhances variant significance descriptions
  - **General Variant Info**: Population frequency context included in variant annotations
- **Implementation**: Cancer mutation frequency analysis, hotspot validation, prevalence-based scoring, pan-cancer recurrence assessment

### **Cell Line & Functional Genomics**

#### 25. DepMap Mutations (100MB)
**Purpose**: Cell line somatic mutation profiles
**Somatic Use**: Provides the mutational context for the cell lines in the DepMap project, linking genetics to gene dependency
**Tools Using Resource**: OpenCRAVAT, Custom research pipelines

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier II-III enhancement**: DepMap functional validation supports therapeutic targeting rationale
  - **Drug sensitivity context**: Cell line drug response data enhances therapeutic tier assignment
  - **Functional validation**: Mutation-dependency relationships support driver status for tier evaluation
  - **Evidence levels**: Multiple cell line validation > single line > no functional data
  - **Context**: Functional evidence applicable to both tumor-only and tumor-normal interpretation
- **VICC/CGC 2022 Impact**:
  - **OM2** (+2 points): DepMap functional studies demonstrating oncogenic mechanism for mutated genes
  - **Functional validation**: Cell line mutation-phenotype relationships support oncogenicity scoring
- **OncoKB Impact**:
  - **Target vulnerability**: DepMap mutation profiles inform therapeutic target assessment
  - **Functional context**: Mutation-response relationships validate OncoKB therapeutic annotations
- **Canned Text Types**:
  - **Variant Dx Interpretation**: Functional validation from cell line models enhances variant interpretation
  - **Gene Dx Interpretation**: Cell line mutation profiles support gene-cancer mechanism descriptions
- **Implementation**: Functional impact validation, cell line model selection, mutation-dependency correlation

#### 26. DepMap Gene Effects (200MB)  
**Purpose**: CRISPR screen dependency data
**Somatic Use**: Powerful functional evidence - shows how essential a gene is for a cancer cell line's survival based on CRISPR screens
**Tools Using Resource**: OpenCRAVAT, Custom research pipelines

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I-II clincher**: High dependency score + existing targeted therapy = enhanced tier assignment confidence
  - **Tier III assignment**: High dependency but no current therapy = strong Tier III candidate
  - **Target prioritization**: Dependency scores identify most promising therapeutic targets
  - **Evidence levels**: Pan-cancer dependency > lineage-specific dependency > cell line specific
  - **Context**: Applicable to both tumor-only and tumor-normal; functional validation focus
- **VICC/CGC 2022 Impact**:
  - **OVS1** (+8 points): Strong dependency validates tumor suppressor essentiality
  - **Functional validation**: CRISPR dependency provides functional evidence for oncogenicity
- **OncoKB Impact**:
  - **Target vulnerability**: DepMap identifies which genes are most therapeutically tractable
  - **Synthetic lethality**: Dependency data reveals therapeutic opportunities beyond direct targeting
- **Canned Text Types**:
  - **Gene Dx Interpretation**: High dependency scores trigger discussion of gene essentiality in cancer
  - **Variant Dx Interpretation**: Dependency context enhances therapeutic targeting discussions
- **Implementation**: Gene dependency scoring, therapeutic target prioritization, lineage-specific analysis

### **OncoVI Curated Resources (Advanced Clinical Interpretation)**

#### 27. OncoVI Tumor Suppressors (1KB)
**Purpose**: Union of COSMIC CGC + OncoKB TSGs
**Somatic Use**: Curated lists for VICC oncogenicity scoring - definitive tumor suppressor classification
**Tools Using Resource**: OpenCRAVAT, custom annotation scripts

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I clincher**: Null variant in OncoVI TSG + FDA-approved therapy = definitive Tier I
  - **Tier II clincher**: Loss-of-function in OncoVI TSG + investigational therapy = solid Tier II
  - **Tier III assignment**: Null variant in OncoVI TSG but no targeted therapy = Tier III
  - **Evidence validation**: OncoVI union provides highest confidence TSG classification
  - **Context**: Applicable to both tumor-only and tumor-normal; gene-level classification
- **VICC/CGC 2022 Impact**:
  - **OVS1** (+8 points): Definitive TSG classification for null variants - highest confidence score
  - **Gold standard**: OncoVI TSG list represents consensus across major cancer gene databases
- **OncoKB Impact**:
  - **TSG validation**: OncoVI cross-validates OncoKB tumor suppressor classifications
  - **Therapeutic context**: TSG status informs therapeutic strategies for loss-of-function variants
- **Canned Text Types**:
  - **Gene Dx Interpretation**: Definitive TSG classification triggers detailed tumor suppressor mechanism text
  - **Variant Dx Interpretation**: Loss-of-function in TSG increases therapeutic interpretation likelihood
- **Implementation**: Authoritative TSG classification, highest-confidence OVS1 application

#### 28. OncoVI Oncogenes (1KB)
**Purpose**: Union of COSMIC CGC + OncoKB oncogenes  
**Somatic Use**: Curated lists for VICC oncogenicity scoring - definitive oncogene classification
**Tools Using Resource**: OpenCRAVAT, custom annotation scripts

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I clincher**: Activating variant in OncoVI oncogene + FDA-approved therapy = definitive Tier I
  - **Tier II clincher**: Gain-of-function in OncoVI oncogene + investigational therapy = solid Tier II
  - **Tier III assignment**: Activating variant in OncoVI oncogene but no targeted therapy = Tier III
  - **Evidence validation**: OncoVI union provides highest confidence oncogene classification
  - **Context**: Applicable to both tumor-only and tumor-normal; gene-level classification
- **VICC/CGC 2022 Impact**:
  - **OS1** (+4 points): Definitive oncogene classification for activating variants
  - **Gold standard**: OncoVI oncogene list represents consensus across major cancer gene databases
- **OncoKB Impact**:
  - **Oncogene validation**: OncoVI cross-validates OncoKB oncogene classifications
  - **Therapeutic context**: Oncogene status informs therapeutic strategies for gain-of-function variants
- **Canned Text Types**:
  - **Gene Dx Interpretation**: Definitive oncogene classification triggers detailed activation mechanism text
  - **Variant Dx Interpretation**: Gain-of-function in oncogene increases therapeutic interpretation likelihood
- **Implementation**: Authoritative oncogene classification, highest-confidence OS1 application

#### 29. OncoVI Single Residue Hotspots (5MB)
**Purpose**: Detailed mutation frequency data from cancerhotspots.org
**Somatic Use**: A curated set of cancer mutation hotspots used to identify likely driver mutations
**Tools Using Resource**: OpenCRAVAT, Custom annotation scripts

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I clincher**: OncoVI hotspot + targeted therapy available = strong Tier I evidence
  - **Tier II clincher**: High-frequency OncoVI hotspot + investigational therapy = solid Tier II
  - **Tier III assignment**: OncoVI hotspot in cancer gene without therapy = Tier III
  - **Evidence levels**: High-frequency (>20 samples) > moderate (10-20) > low frequency (3-10)
  - **Context**: Applicable to both tumor-only and tumor-normal; residue-specific precision
- **VICC/CGC 2022 Impact**:
  - **OS3** (+4 points): High-frequency validated hotspots (>20 occurrences)
  - **OM3** (+2 points): Moderate-frequency hotspots (10-20 occurrences)
  - **Residue precision**: Exact amino acid position matching for highest confidence
- **OncoKB Impact**:
  - **Hotspot validation**: OncoVI provides independent frequency validation for OncoKB hotspots
  - **Therapeutic relevance**: High-frequency hotspots more likely to have therapeutic implications
- **Canned Text Types**:
  - **Variant Dx Interpretation**: High-frequency hotspots trigger detailed driver mechanism descriptions
  - **General Variant Info**: Hotspot frequency data included in variant context
- **Implementation**: Frequency-based hotspot scoring, residue-level precision, cancer-type-specific frequencies

#### 30. OncoVI Indel Hotspots (1MB)
**Purpose**: In-frame indel hotspot annotations
**Somatic Use**: Specialized resource for insertions/deletions that maintain reading frame but alter protein function
**Tools Using Resource**: OpenCRAVAT, Custom annotation scripts

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I clincher**: In-frame indel hotspot + targeted therapy = strong Tier I evidence
  - **Tier II assignment**: In-frame indel in cancer gene + investigational therapy = Tier II
  - **Tier III assignment**: In-frame indel hotspot but no therapy = Tier III consideration
  - **Evidence levels**: Recurrent exact indel > similar length indels > novel in-frame indels
  - **Context**: Applicable to both tumor-only and tumor-normal; length-preserving variant focus
- **VICC/CGC 2022 Impact**:
  - **OM3** (+2 points): In-frame indel hotspots provide moderate oncogenic evidence
  - **Functional relevance**: Length-preserving indels more likely to have functional consequences
- **OncoKB Impact**:
  - **Indel validation**: OncoVI provides specialized annotation for complex variants
  - **Therapeutic context**: In-frame indels assessed for therapeutic relevance
- **Canned Text Types**:
  - **Variant Dx Interpretation**: In-frame indel hotspots trigger specialized variant mechanism descriptions
  - **Technical Comments**: Complex variant annotation included in technical notes
- **Implementation**: In-frame indel hotspot identification, length-preserving variant scoring, recurrence validation

#### 31. OncoVI Protein Domains (2MB)
**Purpose**: Processed UniProt domain annotations
**Somatic Use**: Pre-processed domain lookup for rapid variant-to-domain mapping
**Tools Using Resource**: OpenCRAVAT, custom annotation scripts

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I-II enhancement**: Critical domain variants with domain-targeted therapy = higher tier potential
  - **Tier III assignment**: Important domain disruption without specific therapy = Tier III
  - **Functional validation**: Domain context validates variant functional impact for tier assignment
  - **Evidence levels**: Kinase domains > DNA-binding domains > other functional domains > linker regions
  - **Context**: Applicable to both tumor-only and tumor-normal; domain-level functional assessment
- **VICC/CGC 2022 Impact**:
  - **OM1** (+2 points): Critical functional domain disruption in cancer genes
  - **Domain criticality**: Established functional domains provide moderate oncogenic evidence
- **OncoKB Impact**:
  - **Domain-targeted therapy**: Some therapeutic strategies specifically target protein domains
  - **Functional context**: Domain information supports variant therapeutic assessment
- **Canned Text Types**:
  - **Variant Dx Interpretation**: Critical domain variants trigger domain-specific mechanism descriptions
  - **General Variant Info**: Protein domain context included in variant functional annotations
- **Implementation**: Pre-processed domain lookup, criticality scoring, rapid variant-to-domain mapping
  - **Context**: Applicable to both tumor-only and tumor-normal; domain-level assessment
- **VICC/CGC 2022 Impact**:
  - **OM1** (+2 points): Variants in critical functional domains (pre-processed for efficiency)
  - **Domain criticality**: OncoVI pre-processing enables rapid domain impact scoring
- **OncoKB Impact**:
  - **Domain targeting**: Identifies variants amenable to domain-specific therapeutic strategies
  - **Functional classification**: Domain context enhances OncoKB variant interpretation
- **Canned Text Types**:
  - **Variant Dx Interpretation**: Critical domain location increases functional impact descriptions
  - **General Variant Info**: Domain context automatically included in variant annotations
- **Implementation**: Pre-processed domain lookup, criticality scoring, rapid domain boundary checking

#### 32. OncoVI CGI Mutations (3MB)
**Purpose**: Cancer Genome Interpreter validated mutations
**Somatic Use**: Professional validation of oncogenic mutations with clinical interpretation
**Tools Using Resource**: OpenCRAVAT, Custom annotation scripts

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I-II enhancement**: CGI-validated mutations provide professional validation for therapeutic tier assignment
  - **Evidence strengthening**: Expert validation increases confidence in tier assignment
  - **Quality validation**: CGI professional review supports higher-tier assignments
  - **Evidence levels**: Expert panel validation > automated validation > no validation
  - **Context**: Applicable to both tumor-only and tumor-normal; professional validation focus
- **VICC/CGC 2022 Impact**:
  - **OS2** (+4 points): Professional guideline validation provides strong oncogenic evidence
  - **Quality assurance**: CGI validation strengthens oncogenicity scoring confidence
- **OncoKB Impact**:
  - **Cross-validation**: CGI validation cross-validates OncoKB therapeutic variant significance
  - **Professional consensus**: Expert review provides additional confidence layer
- **Canned Text Types**:
  - **Variant Dx Interpretation**: Professionally validated variants receive enhanced interpretation confidence
  - **Technical Comments**: Validation status included in technical annotation notes
- **Implementation**: Validated oncogenic mutation lookup, professional guideline support, quality scoring

#### 33. OncoVI OS2 Criteria (1KB)
**Purpose**: Manually curated ClinVar significance mappings
**Somatic Use**: Automated mapping of ClinVar clinical significance terms to VICC scoring criteria
**Tools Using Resource**: OpenCRAVAT, Custom annotation scripts

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier assignment support**: ClinVar significance terms provide clinical validation for tier assignment
  - **Professional validation**: Expert-reviewed significance enhances tier confidence
  - **Evidence levels**: Expert panel assertions > multiple submitters > single submitters
  - **Context**: Applicable to both tumor-only and tumor-normal; clinical significance focus
- **VICC/CGC 2022 Impact**:
  - **OS2** (+4 points): Professional guideline significance provides strong oncogenic evidence through automated mapping
  - **Consistency**: Standardized mapping ensures consistent OS2 application
- **OncoKB Impact**:
  - **Clinical validation**: ClinVar significance supports OncoKB therapeutic context assessment
  - **Quality filtering**: Significance terms filter for high-quality clinical evidence
- **Canned Text Types**:
  - **Variant Dx Interpretation**: Clinical significance terms enhance variant interpretation messages
  - **Technical Comments**: Significance mapping status included in technical notes
- **Implementation**: ClinVar significance term mapping, OS2 rule automation, quality-based scoring

#### 34. OncoVI Amino Acid Dictionary (1KB)
**Purpose**: 3-letter to 1-letter amino acid conversion
**Somatic Use**: Technical infrastructure for variant nomenclature standardization and parsing
**Tools Using Resource**: All annotation tools requiring amino acid conversion

- **AMP/ASCO/CAP 2017 Impact**:
  - **Technical enablement**: Standardized nomenclature ensures consistent tier assignment across variant descriptions
  - **Quality assurance**: Proper amino acid conversion prevents interpretation errors
  - **Context**: Essential infrastructure for both tumor-only and tumor-normal analysis
- **VICC/CGC 2022 Impact**:
  - **Technical utility**: Enables consistent variant description parsing for VICC scoring
  - **Quality control**: Standardized nomenclature prevents scoring errors
- **OncoKB Impact**:
  - **Nomenclature matching**: Ensures consistent variant nomenclature for OncoKB lookup
  - **Technical accuracy**: Prevents therapy matching errors due to nomenclature inconsistencies
- **Canned Text Types**:
  - **All variant-related text**: Ensures consistent amino acid nomenclature across all text types
  - **Technical Comments**: Standardized nomenclature in technical documentation
- **Implementation**: HGVS nomenclature parsing, amino acid conversion, nomenclature standardization

#### 35. OncoVI Grantham Distance Matrix (5KB)
**Purpose**: Amino acid substitution scoring matrix
**Somatic Use**: Quantitative assessment of amino acid substitution impact for variant functional prediction
**Tools Using Resource**: OpenCRAVAT, Custom annotation scripts for functional prediction

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier II-III support**: High Grantham scores provide functional evidence supporting therapeutic tier assignment
  - **Functional validation**: Quantitative amino acid impact assessment supports tier confidence
  - **Evidence levels**: Grantham score >100 (radical) > 50-100 (moderate) > <50 (conservative)
  - **Context**: Applicable to both tumor-only and tumor-normal; missense variant focus
- **VICC/CGC 2022 Impact**:
  - **OP1** (+1 point): High Grantham distance provides supporting oncogenic evidence for radical substitutions
  - **SBP1** (-1 point): Low Grantham distance suggests conservative substitution with benign impact
- **OncoKB Impact**:
  - **Functional context**: Grantham scoring provides quantitative functional impact for therapeutic assessment
  - **Substitution severity**: Radical substitutions more likely to have therapeutic relevance
- **Canned Text Types**:
  - **Variant Dx Interpretation**: High Grantham scores increase likelihood of detailed functional interpretation
  - **Technical Comments**: Amino acid substitution severity included in technical notes
- **Implementation**: Amino acid substitution scoring, conservation analysis, functional impact quantification

### **VEP Plugin Data (Computational Predictions)**

#### 36. dbNSFP (VEP Plugin)
**Purpose**: SIFT, PolyPhen, CADD, REVEL functional predictions
**Somatic Use**: Computational functional prediction supporting variant pathogenicity and oncogenicity assessment
**Tools Using Resource**: Ensembl VEP (plugin), Annovar, OpenCRAVAT, PCGR

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier II-III support**: Strong computational predictions provide functional evidence supporting therapeutic tier assignment
  - **Functional validation**: Multiple algorithm consensus enhances tier assignment confidence
  - **Evidence levels**: 4+ algorithms concordant > 3 algorithms > 2 algorithms > single algorithm
  - **Context**: Applicable to both tumor-only and tumor-normal; missense variant focus
- **VICC/CGC 2022 Impact**:
  - **OP1** (+1 point): Multiple computational tools predicting damaging effect provide supporting oncogenic evidence
  - **SBP1** (-1 point): Consensus benign prediction provides supporting benign evidence
- **OncoKB Impact**:
  - **Functional context**: Computational predictions provide functional impact context for therapeutic assessment
  - **Variant filtering**: Strong benign predictions may reduce therapeutic relevance
- **Canned Text Types**:
  - **Variant Dx Interpretation**: Strong computational predictions increase likelihood of functional interpretation discussion
  - **Technical Comments**: Computational prediction scores included in technical notes
- **Implementation**: Multi-algorithm consensus scoring, threshold-based classification, confidence weighting

#### 37. AlphaMissense (VEP Plugin)
**Purpose**: DeepMind protein structure-based predictions
**Somatic Use**: Structure-informed functional prediction with high accuracy for missense variants
**Tools Using Resource**: Ensembl VEP (plugin), Research pipelines

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier II-III support**: High-confidence AlphaMissense predictions provide strong functional evidence for tier assignment
  - **Structure-based validation**: Protein structure context enhances functional impact assessment
  - **Evidence levels**: High confidence (>0.8) > medium confidence (0.5-0.8) > low confidence (<0.5)
  - **Context**: Applicable to both tumor-only and tumor-normal; missense variant specialization
- **VICC/CGC 2022 Impact**:
  - **OP1** (+1 point): High-confidence pathogenic prediction provides supporting oncogenic evidence
  - **SBP1** (-1 point): High-confidence benign prediction provides supporting benign evidence
- **OncoKB Impact**:
  - **Structure-based assessment**: AlphaMissense provides structure-informed functional context for therapeutic relevance
  - **High accuracy**: DeepMind predictions offer enhanced confidence for variant assessment
- **Canned Text Types**:
  - **Variant Dx Interpretation**: High-confidence predictions increase likelihood of detailed functional discussion
  - **Technical Comments**: Structure-based prediction scores included in technical annotation
- **Implementation**: Structure-informed functional prediction, confidence thresholding, AlphaFold integration

#### 38. SpliceAI (VEP Plugin)
**Purpose**: Deep learning splice site predictions
**Somatic Use**: Identifies variants that disrupt splicing, potentially creating null alleles in tumor suppressors
**Tools Using Resource**: Ensembl VEP (plugin), SpliceAI standalone

- **AMP/ASCO/CAP 2017 Impact**:
  - **Tier I-II clincher**: Splice-disrupting variant in tumor suppressor + targeted therapy = strong tier assignment
  - **Tier III assignment**: Splice disruption in cancer gene without therapy = Tier III consideration
  - **Evidence levels**: SpliceAI score >0.8 (high) > 0.5-0.8 (moderate) > 0.2-0.5 (low) > <0.2 (minimal)
  - **Context**: Critical for both tumor-only and tumor-normal; splice site variant focus
- **VICC/CGC 2022 Impact**:
  - **OVS1** (+8 points): High-confidence splice disruption creates null variant in tumor suppressor
  - **OP1** (+1 point): Moderate splice impact provides supporting oncogenic evidence
- **OncoKB Impact**:
  - **Splice impact assessment**: SpliceAI identifies therapeutically relevant splice-disrupting variants
  - **Null variant identification**: Splice disruption may create loss-of-function with therapeutic implications
- **Canned Text Types**:
  - **Variant Dx Interpretation**: High splice disruption scores trigger detailed splicing mechanism descriptions
  - **Technical Comments**: SpliceAI prediction scores included in technical splice analysis
- **Implementation**: Splice score thresholding, canonical splice site analysis, deep learning prediction integration

### **Technical Infrastructure & Standards**

#### 39-42. Index Files (gnomAD, ClinVar, Cancer Hotspots indices)
**Purpose**: Technical files for rapid database access
**Somatic Use**: Infrastructure enablement for rapid variant lookup across all major knowledge bases
**Tools Using Resource**: All annotation tools requiring indexed database access

- **AMP/ASCO/CAP 2017 Impact**:
  - **Performance enablement**: Rapid database access ensures efficient tier assignment processing
  - **Quality assurance**: Indexed lookup prevents query timeouts and ensures complete annotation
  - **Context**: Essential infrastructure for both tumor-only and tumor-normal analysis
- **VICC/CGC 2022 Impact**:
  - **Technical enablement**: Enables rapid hotspot and frequency rule application for oncogenicity scoring
  - **Performance optimization**: Indexed access supports comprehensive VICC rule evaluation
- **OncoKB Impact**:
  - **Lookup efficiency**: Technical infrastructure enables rapid OncoKB therapeutic annotation
  - **Performance scaling**: Indexed access supports high-throughput therapeutic assessment
- **Canned Text Types**:
  - **All text types**: Technical infrastructure enables rapid annotation supporting all text generation
  - **Performance quality**: Fast annotation ensures comprehensive text generation
- **Implementation**: Database indexing, query optimization, performance monitoring, access efficiency

---

## Coverage Gaps and Limitations

### **Currently Well-Addressed**

✅ **Population Frequencies**: Comprehensive gnomAD coverage  
✅ **Hotspot Detection**: Multiple high-quality sources with frequency data  
✅ **Gene Classifications**: Authoritative TSG/oncogene lists from multiple sources  
✅ **Clinical Evidence**: ClinVar + CIViC + OncoKB comprehensive coverage  
✅ **Functional Domains**: UniProt + Pfam + OncoVI processed annotations  
✅ **Computational Predictions**: Multi-algorithm VEP plugin coverage  

### **Partially Addressed**

⚠️ **Functional Studies (ACMG PM1, VICC OM4)**:
- **Current**: Literature mining from CancerMine, some CIViC evidence
- **Gap**: No systematic functional study database
- **Impact**: Manual curation required for functional evidence

⚠️ **Segregation Data (ACMG PP1, PS4)**:
- **Current**: Limited family history context
- **Gap**: No systematic segregation database
- **Impact**: Primarily applicable to germline analysis

⚠️ **De Novo Evidence (ACMG PS2, PM6)**:
- **Current**: Not systematically captured
- **Gap**: No de novo mutation database
- **Impact**: Case-by-case analysis required

### **Not Currently Addressed**

❌ **Allele-Specific Expression (ACMG PM3)**:
- **Required**: RNA-seq based allele expression data
- **Current Status**: Not implemented
- **Recommendation**: Add GTEx or similar expression database

❌ **Protein Truncation Studies (ACMG PS3)**:
- **Required**: Systematic protein truncation experimental data
- **Current Status**: Limited to literature references
- **Recommendation**: Manual curation or specialized database

❌ **Rescue Studies (ACMG BS3)**:
- **Required**: Functional rescue experimental data  
- **Current Status**: Not systematically available
- **Recommendation**: Manual literature review

### **Future Enhancement Priorities**

1. **High Priority**:
   - GTEx expression data for allele-specific expression analysis
   - Systematic functional study database integration
   
2. **Medium Priority**:
   - Enhanced family segregation data sources
   - Protein-level functional study compilation
   
3. **Low Priority**:
   - De novo mutation systematic collection
   - Rescue study experimental database

---

## Implementation Notes

### **Rule Application Hierarchy**

1. **Very Strong Evidence**: PVS1, OVS1 (8+ points)
2. **Strong Evidence**: PS1-PS4, OS1-OS3 (4+ points)  
3. **Moderate Evidence**: PM1-PM6, OM1-OM4 (2+ points)
4. **Supporting Evidence**: PP1-PP5, OP1-OP4 (1+ point)

### **Quality Control Requirements**

- **Population Frequency**: Minimum 10,000 alleles for reliable frequency estimates
- **Hotspot Evidence**: Minimum 3 independent observations for OS3 classification
- **Clinical Evidence**: Expert panel or equivalent review status required
- **Computational Predictions**: Minimum 2 algorithms concordant for PP3/BP4

### **Therapeutic Context Integration**

- **OncoKB Level 1**: FDA-approved biomarkers
- **OncoKB Level 2**: Standard-of-care in specific cancer types  
- **OncoKB Level 3**: Clinical evidence for treatment
- **OncoKB Level 4**: Biological evidence for treatment

This comprehensive mapping ensures systematic and evidence-based application of clinical guidelines across all 42 knowledge bases.