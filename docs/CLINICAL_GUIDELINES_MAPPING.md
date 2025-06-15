# Clinical Guidelines Mapping for 42 Knowledge Bases

This document provides comprehensive mapping of all 42 knowledge bases to specific clinical classification guidelines: ACMG/AMP (2015), VICC/CGC (2022), and OncoKB therapeutic tiers.

## Framework Abbreviations
- **ACMG/AMP**: American College of Medical Genetics and Genomics / Association for Molecular Pathology
- **VICC/CGC**: Variant Interpretation for Cancer Consortium / Cancer Gene Census  
- **OncoKB**: Memorial Sloan Kettering precision oncology knowledge base

---

## Complete Knowledge Base to Clinical Rule Mapping

### **Population Frequencies & Variant Context**

#### 1. gnomAD Exomes (20GB)
**Purpose**: Population allele frequencies for rare variant assessment
- **ACMG/AMP Rules**:
  - **BA1** (Benign Stand-alone): VAF >5% in any continental population → Benign
  - **BS1** (Benign Strong): VAF greater than expected for disorder prevalence → Likely Benign  
  - **PM2** (Pathogenic Moderate): Absent/extremely rare (VAF <0.0001%) in controls → Supporting Pathogenic
- **VICC/CGC Rules**:
  - **SBVS1** (Strong Benign Very Strong): VAF >5% → Strong Evidence Against Oncogenicity (-8 points)
  - **OP4** (Oncogenic Supporting): Absent from population databases → Supporting Oncogenic (+1 point)
- **OncoKB**: Not directly used; supports contextual interpretation
- **Implementation**: Query VAF by ancestry group, apply population-specific thresholds

#### 2. gnomAD Genomes (150GB) + Indices (1GB + 200MB)
**Purpose**: Comprehensive population frequencies including structural variants
- **Same rule mapping as gnomAD Exomes**
- **Additional**: Structural variant population frequencies for CNV interpretation
- **Implementation**: Primary source for VAF lookups due to broader coverage

#### 3. dbSNP (25GB)
**Purpose**: Variant identifiers and common variant flagging
- **ACMG/AMP Rules**: 
  - **Supporting evidence** for established variant nomenclature
  - **BA1/BS1** confirmation when paired with frequency data
- **VICC/CGC Rules**: 
  - **SBVS1** supporting evidence for common variants
- **OncoKB**: Reference for variant standardization
- **Implementation**: rsID lookup and common variant flagging

### **Clinical Evidence & Pathogenicity**

#### 4. ClinVar VCF (200MB) + Index (1MB) + TSV (150MB)
**Purpose**: Clinical significance classifications and prior observations
- **ACMG/AMP Rules**:
  - **PS1** (Pathogenic Strong): Same amino acid change as established pathogenic variant
  - **PM5** (Pathogenic Moderate): Novel missense at residue with different pathogenic change
  - **PP5** (Pathogenic Supporting): Reputable source reports pathogenic
  - **BP2** (Benign Supporting): Observed in healthy individuals
  - **BP6** (Benign Supporting): Reputable source reports benign
- **VICC/CGC Rules**:
  - **OS2** (Oncogenic Strong): Well-established in professional guidelines (+4 points)
  - **SBS2** (Strong Benign Supporting): Functional studies show no oncogenic effect (-4 points)
- **OncoKB**: Cross-reference for variant-level evidence
- **Implementation**: Parse review status, prioritize expert panel assertions

#### 5. CIViC Variants (5MB) + Hotspots (10MB)
**Purpose**: Clinical evidence summaries for cancer variants
- **ACMG/AMP Rules**:
  - **PS1/PM5** supporting evidence for pathogenic classifications
  - **PP5** when high-quality clinical evidence exists
- **VICC/CGC Rules**:
  - **OS2** (Oncogenic Strong): Published clinical evidence (+4 points)
  - **OM4** (Oncogenic Moderate): Mutation in gene with oncogenic role (+2 points)
- **OncoKB**: 
  - **Level 1-4** evidence integration for therapeutic actionability
  - Cross-validation of clinical assertions
- **Implementation**: Evidence tier mapping, therapeutic context integration

#### 6. OncoKB Genes (1MB)
**Purpose**: Curated cancer gene lists and actionability framework
- **ACMG/AMP Rules**:
  - **PVS1** mechanism validation (gene-disease relationship)
  - **PP2** (Pathogenic Supporting): Variant in gene with established disease association
- **VICC/CGC Rules**:
  - **OVS1** (Oncogenic Very Strong): Null variant in tumor suppressor (+8 points)
  - **OS1** (Oncogenic Strong): Activating variant in oncogene (+4 points)
- **OncoKB**: 
  - **Core framework** for therapeutic tier assignment (Level 1-4)
  - **Gene-level actionability** classification
- **Implementation**: Gene classification lookup, therapeutic context assignment

#### 7. CancerMine (20MB)
**Purpose**: Literature-mined oncogenes and tumor suppressors
- **ACMG/AMP Rules**:
  - **PP2** supporting evidence for gene-disease relationships
- **VICC/CGC Rules**:
  - **Supporting evidence** for OS1/OVS1 when primary sources unavailable
- **OncoKB**: Cross-validation of gene classifications
- **Implementation**: Literature support for gene role classifications

### **Cancer Hotspots & Recurrent Mutations**

#### 8. Cancer Hotspots VCF (5MB) + Index (1MB)
**Purpose**: Memorial Sloan Kettering recurrent mutations
- **ACMG/AMP Rules**:
  - **PS1** when exact amino acid change observed
  - **PM5** when different change at same residue
- **VICC/CGC Rules**:
  - **OS3** (Oncogenic Strong): Well-established hotspot with significant recurrence (+4 points)
  - **OM3** (Oncogenic Moderate): Hotspot with moderate evidence (+2 points)
- **OncoKB**: Evidence for variant-level therapeutic significance
- **Implementation**: Position-based lookup with recurrence threshold

#### 9. MSK SNV Hotspots (10MB) + Indel Hotspots (5MB)
**Purpose**: cBioPortal comprehensive hotspot data
- **Same rule mapping as Cancer Hotspots VCF**
- **Additional**: Indel hotspot support for complex variants
- **Implementation**: Extended hotspot coverage beyond point mutations

#### 10. MSK 3D Hotspots (5MB)
**Purpose**: Protein structure-based hotspot predictions
- **ACMG/AMP Rules**:
  - **PM1** (Pathogenic Moderate): Variant in critical functional domain
- **VICC/CGC Rules**:
  - **OM1** (Oncogenic Moderate): Located in critical functional domain (+2 points)
- **OncoKB**: Structural context for variant interpretation
- **Implementation**: 3D structure-based domain criticality assessment

#### 11. COSMIC Cancer Gene Census (2MB)
**Purpose**: Curated cancer gene classifications
- **ACMG/AMP Rules**:
  - **PVS1** gene mechanism validation
  - **PP2** gene-disease relationship support
- **VICC/CGC Rules**:
  - **OVS1/OS1** primary source for tumor suppressor/oncogene classification
  - **Core framework** for VICC rule implementation
- **OncoKB**: Gene classification cross-validation
- **Implementation**: Authoritative gene role assignment (TSG vs. oncogene vs. fusion)

### **Gene Function & Protein Domains**

#### 12. UniProt Swiss-Prot (300MB)
**Purpose**: Curated protein sequences and functional annotations
- **ACMG/AMP Rules**:
  - **PM1** (Pathogenic Moderate): Variant in critical functional domain
  - **PVS1** mechanism validation for protein function
  - **BP1** (Benign Supporting): Variant in non-functional domain
- **VICC/CGC Rules**:
  - **OM1** (Oncogenic Moderate): Critical functional domain (+2 points)
  - **SBP1** (Supporting Benign): Non-critical domain (-1 point)
- **OncoKB**: Protein function context for therapeutic relevance
- **Implementation**: Domain boundary mapping, functional consequence prediction

#### 13. Pfam Domains (100MB)
**Purpose**: Protein family and domain classifications
- **Same rule mapping as UniProt Swiss-Prot**
- **Additional**: Family-level conservation analysis
- **Implementation**: Domain family criticality assessment

#### 14. NCBI Gene Info (200MB)
**Purpose**: Comprehensive gene annotations and mappings
- **ACMG/AMP Rules**:
  - **PP2** gene-disease relationship validation
  - **Gene symbol standardization** for rule application
- **VICC/CGC Rules**:
  - **Gene context** for all oncogenicity assessments
- **OncoKB**: Gene-level therapeutic context
- **Implementation**: Gene symbol mapping, cross-database coordination

#### 15. HGNC Mappings (5MB)
**Purpose**: Official gene symbol standardization
- **ACMG/AMP Rules**:
  - **Essential for all rules** - ensures consistent gene identification
- **VICC/CGC Rules**:
  - **Essential for all rules** - standardized gene nomenclature
- **OncoKB**: Gene symbol standardization for therapeutic mapping
- **Implementation**: Primary gene symbol authority, alias resolution

### **Clinical Biomarkers & Thresholds**

#### 16. Clinical Biomarkers (2MB)
**Purpose**: Curated biomarker definitions and clinical thresholds
- **ACMG/AMP Rules**:
  - **Not directly applicable** (focuses on single variants)
- **VICC/CGC Rules**:
  - **Not directly applicable** (variant-level classification)
- **OncoKB**: 
  - **Level 1** biomarkers for FDA-approved therapies
  - **Level 2-4** biomarkers for investigational/off-label use
- **Implementation**: TMB, MSI, HRD threshold application for therapeutic decisions

#### 17. OncoTree Classifications (1MB)
**Purpose**: Cancer type taxonomies for context-specific interpretation
- **ACMG/AMP Rules**:
  - **Context for penetrance** assessment (cancer-specific disease prevalence)
- **VICC/CGC Rules**:
  - **Tumor type context** for oncogenicity assessment
- **OncoKB**: 
  - **Primary framework** for therapeutic indication matching
  - **Level assignment** based on cancer type specificity
- **Implementation**: Cancer type standardization, therapeutic context matching

### **Gene Dosage Sensitivity**

#### 18. ClinGen Gene Curation (2MB)
**Purpose**: Expert-curated gene-disease relationships
- **ACMG/AMP Rules**:
  - **PVS1** (Pathogenic Very Strong): Primary authority for LoF mechanism
  - **Gene-level evidence** for pathogenicity assessment
- **VICC/CGC Rules**:
  - **OVS1** supporting evidence for tumor suppressor classification
- **OncoKB**: Gene-level therapeutic relevance validation
- **Implementation**: Authoritative source for gene-disease mechanisms

#### 19. ClinGen Haploinsufficiency (1MB)
**Purpose**: Genes sensitive to single-copy loss
- **ACMG/AMP Rules**:
  - **PVS1** application: Null variants in haploinsufficient genes
  - **Haploinsufficiency score** integration
- **VICC/CGC Rules**:
  - **OVS1** supporting evidence for tumor suppressors
- **OncoKB**: Dosage sensitivity context for therapeutic planning
- **Implementation**: Haploinsufficiency scoring, LoF variant prioritization

#### 20. ClinGen Triplosensitivity (1MB)
**Purpose**: Genes sensitive to extra copies
- **ACMG/AMP Rules**:
  - **Context for copy number** variant interpretation
- **VICC/CGC Rules**:
  - **OS1** supporting evidence for oncogenes (amplification sensitivity)
- **OncoKB**: Copy number alteration therapeutic relevance
- **Implementation**: CNV significance assessment, amplification scoring

### **Drug-Target Associations**

#### 21. Open Targets Platform (500MB)
**Purpose**: Disease-target and drug-target associations
- **ACMG/AMP Rules**:
  - **PP2** supporting evidence for gene-disease relationships
- **VICC/CGC Rules**:
  - **Supporting context** for oncogene/tumor suppressor classification
- **OncoKB**: 
  - **Level 3-4** evidence for investigational therapies
  - **Drug-target mechanism** validation
- **Implementation**: Therapeutic target validation, drug mechanism context

#### 22. DGIdb Interactions (50MB)
**Purpose**: Drug-gene interaction database
- **ACMG/AMP Rules**:
  - **Limited direct application** (focuses on germline pathogenicity)
- **VICC/CGC Rules**:
  - **Limited direct application** (variant-level oncogenicity)
- **OncoKB**: 
  - **Level 2-4** evidence for targeted therapy matching
  - **Drug-gene interaction** validation
- **Implementation**: Targeted therapy identification, drug mechanism validation

### **Disease & Pathway Context**

#### 23. MONDO Disease Ontology (50MB)
**Purpose**: Structured disease classifications
- **ACMG/AMP Rules**:
  - **Disease terminology** standardization for pathogenicity assessment
  - **Penetrance context** for specific disorders
- **VICC/CGC Rules**:
  - **Cancer type classification** for oncogenicity context
- **OncoKB**: Disease-specific therapeutic context
- **Implementation**: Disease term standardization, clinical context mapping

#### 24. TCGA MC3 Mutations (200MB)
**Purpose**: Pan-cancer somatic mutation landscape
- **ACMG/AMP Rules**:
  - **Limited application** (primarily germline-focused)
- **VICC/CGC Rules**:
  - **OS3** supporting evidence for hotspot validation
  - **Population frequency** in cancer for oncogenicity assessment
- **OncoKB**: Mutation prevalence context for therapeutic relevance
- **Implementation**: Cancer mutation frequency analysis, hotspot validation

### **Cell Line & Functional Genomics**

#### 25. DepMap Mutations (100MB)
**Purpose**: Cell line somatic mutation profiles
- **ACMG/AMP Rules**:
  - **Functional context** for variant interpretation (research use)
- **VICC/CGC Rules**:
  - **Supporting evidence** for oncogenicity (functional impact)
- **OncoKB**: Functional validation for therapeutic target relevance
- **Implementation**: Functional impact validation, cell line model selection

#### 26. DepMap Gene Effects (200MB)  
**Purpose**: CRISPR screen dependency data
- **ACMG/AMP Rules**:
  - **Functional evidence** for gene importance (research context)
- **VICC/CGC Rules**:
  - **Supporting evidence** for tumor suppressor identification
- **OncoKB**: Target vulnerability assessment for therapeutic development
- **Implementation**: Gene dependency scoring, therapeutic target prioritization

### **OncoVI Curated Resources (Advanced Clinical Interpretation)**

#### 27. OncoVI Tumor Suppressors (1KB)
**Purpose**: Union of COSMIC CGC + OncoKB TSGs
- **ACMG/AMP Rules**:
  - **PVS1** primary gene list for null variant significance
- **VICC/CGC Rules**:
  - **OVS1** (Oncogenic Very Strong): Definitive TSG classification (+8 points)
- **OncoKB**: TSG therapeutic context validation
- **Implementation**: Authoritative TSG classification, PVS1/OVS1 application

#### 28. OncoVI Oncogenes (1KB)
**Purpose**: Union of COSMIC CGC + OncoKB oncogenes  
- **ACMG/AMP Rules**:
  - **Gene context** for activating variant interpretation
- **VICC/CGC Rules**:
  - **OS1** (Oncogenic Strong): Definitive oncogene classification (+4 points)
- **OncoKB**: Oncogene therapeutic targeting context
- **Implementation**: Authoritative oncogene classification, OS1 application

#### 29. OncoVI Single Residue Hotspots (5MB)
**Purpose**: Detailed mutation frequency data from cancerhotspots.org
- **ACMG/AMP Rules**:
  - **PS1** when exact match with frequency support
  - **PM5** when different change at hotspot residue
- **VICC/CGC Rules**:
  - **OS3** (Oncogenic Strong): Frequency-validated hotspots (+4 points)
  - **OM3** (Oncogenic Moderate): Moderate-frequency hotspots (+2 points)
- **OncoKB**: Hotspot therapeutic relevance assessment
- **Implementation**: Frequency-based hotspot scoring, residue-level precision

#### 30. OncoVI Indel Hotspots (1MB)
**Purpose**: In-frame indel hotspot annotations
- **ACMG/AMP Rules**:
  - **PS1/PM5** for recurrent in-frame indels
- **VICC/CGC Rules**:
  - **OM3** (Oncogenic Moderate): In-frame indel hotspots (+2 points)
- **OncoKB**: Indel therapeutic significance
- **Implementation**: In-frame indel hotspot identification, length-preserving variant scoring

#### 31. OncoVI Protein Domains (2MB)
**Purpose**: Processed UniProt domain annotations
- **ACMG/AMP Rules**:
  - **PM1** (Pathogenic Moderate): Critical functional domain (+2 points)
  - **BP1** (Benign Supporting): Non-functional domain context
- **VICC/CGC Rules**:
  - **OM1** (Oncogenic Moderate): Critical functional domain (+2 points)
- **OncoKB**: Domain-level therapeutic target assessment
- **Implementation**: Pre-processed domain lookup, criticality scoring

#### 32. OncoVI CGI Mutations (3MB)
**Purpose**: Cancer Genome Interpreter validated mutations
- **ACMG/AMP Rules**:
  - **PS1** supporting evidence for established pathogenic variants
- **VICC/CGC Rules**:
  - **OS2** (Oncogenic Strong): Professionally validated (+4 points)
- **OncoKB**: Cross-validation of therapeutic variant significance
- **Implementation**: Validated oncogenic mutation lookup, professional guideline support

#### 33. OncoVI OS2 Criteria (1KB)
**Purpose**: Manually curated ClinVar significance mappings
- **ACMG/AMP Rules**:
  - **PP5** when significance maps to established pathogenic terms
- **VICC/CGC Rules**:
  - **OS2** (Oncogenic Strong): Professional guideline significance (+4 points)
- **OncoKB**: Clinical significance validation for therapeutic context
- **Implementation**: ClinVar significance term mapping, OS2 rule automation

#### 34. OncoVI Amino Acid Dictionary (1KB)
**Purpose**: 3-letter to 1-letter amino acid conversion
- **ACMG/AMP Rules**:
  - **Technical utility** for variant nomenclature standardization
- **VICC/CGC Rules**:
  - **Technical utility** for variant description parsing
- **OncoKB**: Variant nomenclature standardization
- **Implementation**: HGVS nomenclature parsing, amino acid conversion

#### 35. OncoVI Grantham Distance Matrix (5KB)
**Purpose**: Amino acid substitution scoring matrix
- **ACMG/AMP Rules**:
  - **PP3/BP4** supporting evidence for computational predictions
- **VICC/CGC Rules**:
  - **OP1/SBP1** supporting evidence for functional impact
- **OncoKB**: Functional impact context for therapeutic relevance
- **Implementation**: Amino acid substitution scoring, conservation analysis

### **VEP Plugin Data (Computational Predictions)**

#### 36. dbNSFP (VEP Plugin)
**Purpose**: SIFT, PolyPhen, CADD, REVEL functional predictions
- **ACMG/AMP Rules**:
  - **PP3** (Pathogenic Supporting): Multiple computational tools predict damaging
  - **BP4** (Benign Supporting): Multiple tools predict benign impact
- **VICC/CGC Rules**:
  - **OP1** (Oncogenic Supporting): Computational evidence supports damaging effect (+1 point)
  - **SBP1** (Supporting Benign): Computational evidence suggests benign (-1 point)
- **OncoKB**: Functional impact context for variant classification
- **Implementation**: Multi-algorithm consensus scoring, threshold-based classification

#### 37. AlphaMissense (VEP Plugin)
**Purpose**: DeepMind protein structure-based predictions
- **Same rule mapping as dbNSFP**
- **Additional**: Structure-based confidence scoring
- **Implementation**: Structure-informed functional prediction, confidence thresholding

#### 38. SpliceAI (VEP Plugin)
**Purpose**: Deep learning splice site predictions
- **ACMG/AMP Rules**:
  - **PVS1** supporting evidence for splice-disrupting variants
  - **PP3** when high splice disruption scores
  - **BP7** when splice prediction is benign
- **VICC/CGC Rules**:
  - **OVS1** supporting evidence for splice-disrupting null variants
  - **OP1** when moderate splice impact predicted
- **OncoKB**: Splice impact context for therapeutic relevance
- **Implementation**: Splice score thresholding, canonical splice site analysis

### **Technical Infrastructure & Standards**

#### 39-42. Index Files (gnomAD, ClinVar, Cancer Hotspots indices)
**Purpose**: Technical files for rapid database access
- **ACMG/AMP Rules**: Technical enablement for all population frequency rules
- **VICC/CGC Rules**: Technical enablement for all hotspot and frequency rules  
- **OncoKB**: Technical support for variant lookup efficiency
- **Implementation**: Database indexing, query optimization

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