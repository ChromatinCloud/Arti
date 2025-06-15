FilePath	Use_in_Somatic_Interp	Example_Implementations_Using_Resource
biomarkers/cgi.clinical.tsv.gz	Primary use. Catalogs cancer mutations to predict their role as drivers and potential therapeutic responses.	OpenCRAVAT, Personal Cancer Genome Reporter (PCGR), Custom interpretation pipelines
biomarkers/cgi.literature.tsv.gz	Primary use. Provides literature-based evidence for the role of cancer mutations.	OpenCRAVAT, Personal Cancer Genome Reporter (PCGR), Custom interpretation pipelines
biomarkers/cgi.variant.tsv.gz	Primary use. Provides a comprehensive list of interpreted cancer variants from the Cancer Genome Interpreter.	OpenCRAVAT, Personal Cancer Genome Reporter (PCGR), Custom interpretation pipelines
biomarkers/civic.clinical.tsv.gz	Primary use. Provides evidence-based interpretations of variants for diagnosis, prognosis, and therapy prediction.	Ensembl VEP (plugin), OpenCRAVAT, PCGR
biomarkers/civic.literature.tsv.gz	Primary use. Provides the underlying literature evidence for the clinical interpretations in CIViC.	Ensembl VEP (plugin), OpenCRAVAT, PCGR
biomarkers/civic.variant.tsv.gz	Primary use. A core dataset of somatic variants with detailed clinical interpretations.	Ensembl VEP (plugin), OpenCRAVAT, PCGR
biomarkers/.../depmap_tpm.tsv.gz	Used to assess the functional consequences of mutations by analyzing gene expression in cancer cell lines.	Custom analysis pipelines (e.g., for expression outlier analysis)
biomarkers/.../tcga_..._tpm.tsv.gz	Used as a reference cohort to compare a tumor's expression profile and identify abnormalities caused by mutations.	Custom analysis pipelines; Data portals like cBioPortal
biomarkers/.../treehouse_tpm.tsv.gz	Used to analyze gene expression in pediatric cancers to understand the effects of somatic mutations.	Custom analysis pipelines for pediatric oncology
cancer_hotspots/cancer_hotspots_v2.5.tsv	Core resource. Identifies recurrently mutated codons (hotspots) that are likely cancer drivers.	Ensembl VEP, Annovar, OpenCRAVAT, PCGR, vcf2maf
cancer_hotspots/civic_hotspots.tsv	Identifies hotspot mutations that have curated clinical interpretations in the CIViC database.	OpenCRAVAT, PCGR, Custom annotation scripts
cancer_hotspots/Cosmic_...Census...	Primary use. The Cancer Gene Census lists genes with causal roles in cancer.	Ensembl VEP, OpenCRAVAT, PCGR
cancer_hotspots/DepMap_...Hotspot.tsv.gz	Provides a list of mutation hotspots identified from sequencing cancer cell lines in the DepMap project.	OpenCRAVAT, Custom annotation scripts
cancer_hotspots/msk_3d_hotspots.txt	Identifies mutation hotspots clustered in 3D protein structures, providing functional evidence for driver status.	OpenCRAVAT, PCGR, Custom annotation scripts
cancer_hotspots/MSK_3D_Table_1.tsv.gz	The underlying data for the MSK 3D hotspots, listing recurrent mutations in protein structures.	OpenCRAVAT, PCGR, Custom annotation scripts
cancer_hotspots/msk_hotspots_indel.json	A curated list of insertion/deletion (indel) hotspots from MSK, indicating likely driver events.	Ensembl VEP, Annovar, OpenCRAVAT, PCGR, vcf2maf
cancer_hotspots/msk_hotspots_snv.json	A curated list of single nucleotide variant (SNV) hotspots from MSK, indicating likely driver events.	Ensembl VEP, Annovar, OpenCRAVAT, PCGR, vcf2maf
cancer_hotspots/MSK-INDEL...v2.tsv.gz	An updated, curated list of insertion/deletion (indel) hotspots from MSK.	Ensembl VEP, Annovar, OpenCRAVAT, PCGR, vcf2maf
cancer_hotspots/MSK-SNV...v2.tsv.gz	An updated, curated list of single nucleotide variant (SNV) hotspots from MSK.	Ensembl VEP, Annovar, OpenCRAVAT, PCGR, vcf2maf
cancermine/cancermine.tsv	Used to annotate genes with their cancer-related roles based on automated literature mining.	OpenCRAVAT, Custom annotation scripts
civic/civic_variant_summaries.tsv	Primary use. Provides detailed, evidence-based summaries for the clinical relevance of somatic variants.	Ensembl VEP (plugin), OpenCRAVAT, PCGR
civic/civic_variants.tsv	Core CIViC data. Lists somatic variants with curated clinical evidence.	Ensembl VEP (plugin), OpenCRAVAT, PCGR
clingen/clingen_genes_GRCh38.tsv	PCGR (for contextual gene information)	
clingen/clingen_haploinsufficiency...	PCGR (to add context to somatic loss-of-function mutations)	
clingen/clingen_triplosensitivity...	PCGR (to add context to somatic copy number gains)	
clinvar/clinvar.vcf.gz	Very useful. Also contains classifications for somatic variants and their clinical significance in cancer.	Ensembl VEP, Annovar, OpenCRAVAT, PCGR
clinvar/variant_summary.txt.gz	Very useful. Also contains summary information for somatic variants.	Ensembl VEP, Annovar, OpenCRAVAT, PCGR
cosmic/cancer_hotspots.tsv.gz	A list of mutation hotspots from the comprehensive COSMIC database.	Ensembl VEP, Annovar, OpenCRAVAT, PCGR
dbsnp/dbsnp_latest.vcf.gz	Used to annotate variants and help filter common germline polymorphisms in tumor-only sequencing.	Ensembl VEP, Annovar, GATK, bcftools
depmap/depmap_gene_effect.csv	Powerful functional evidence. Shows how essential a gene is for a cancer cell line's survival based on CRISPR screens.	OpenCRAVAT, Custom research pipelines
depmap/depmap_mutations.csv	Provides the mutational context for the cell lines in the DepMap project, linking genetics to gene dependency.	OpenCRAVAT, Custom research pipelines
fusion/depmap.fusions.tsv.gz	Lists gene fusions found in the DepMap cancer cell lines, used for interpreting structural variants.	Arriba, STAR-Fusion, FusionAnnotator, RNA-Rocket
fusion/mitelmandb.clinical.tsv.gz	A comprehensive database of chromosome aberrations and gene fusions in cancer, used to interpret structural variants.	Arriba, STAR-Fusion, FusionAnnotator, RNA-Rocket
gene_mappings/hgnc_complete_set.txt	Foundational dependency for all gene-based annotators (VEP, Annovar, etc.)	
gnomad/gnomad.exomes...vcf.bgz	Core filtering step. Used to remove common germline polymorphisms from somatic call sets, especially in tumor-only analysis.	Ensembl VEP, Annovar, OpenCRAVAT, PCGR, GATK FilterMutectCalls
oncokb/oncokb_curated_genes.txt	Primary use. Links specific somatic mutations to their oncogenic effects and associated therapies (clinical actionability).	OncoKB MafAnnotator, OpenCRAVAT, PCGR
oncokb/oncokb_genes.txt	A list of genes curated by OncoKB for their relevance in precision oncology.	OncoKB MafAnnotator, OpenCRAVAT, PCGR
oncotree/oncotree.json	Provides a standardized ontology for cancer types, which is essential for context-specific variant interpretation.	OncoKB MafAnnotator, cBioPortal data validation scripts
oncovi/oncovi_hotspots.json	A curated set of cancer mutation hotspots used to identify likely driver mutations.	OpenCRAVAT, Custom annotation scripts
open_targets/dgidb_interactions.tsv	Primary use. Used to find potential therapies by identifying drug-gene interactions for mutated genes.	OpenCRAVAT, PCGR
open_targets/open_targets.json.gz	Used to evaluate a gene's association with cancer, helping to prioritize potential somatic driver genes.	PCGR, Custom research pipelines
pfam/pfam_a.hmm.gz	Foundational. Used to annotate a variant's location within a protein's functional domains.	Ensembl VEP, Annovar, OpenCRAVAT
secondary_findings/ACMG_SF_v3.2.txt	Not its direct use, but the list is enriched for major cancer predisposition genes, providing context.	PCGR (for flagging genes with germline importance)
tcga/mc3.v0.2.8.PUBLIC.maf.gz	Used as a reference/comparison cohort for mutation frequencies or to build other annotation resources (e.g., hotspots).	maftools (R package for analysis), used as input to build resources for other tools
uniprot/uniprot_sprot.dat.gz	Foundational. Provides reference protein sequences and functional information to assess a variant's impact.	Ensembl VEP, Annovar, OpenCRAVAT
vep/cache/homo_sapiens_vep...	Foundational tool. Annotates variants with their molecular consequence and integrates data from many other resources.	Ensembl VEP (This is the data used by the tool itself)
Mondo Disease Ontology	Essential for standardization. In cancer, Mondo provides a hierarchical classification that links specific cancer types (e.g., lung adenocarcinoma, MONDO:0005239) to broader terms (lung non-small cell carcinoma, MONDO:0005097). This is critical for context-specific variant interpretation, as a variant's significance and therapeutic relevance can depend on the exact cancer diagnosis.	Foundational Mondo is a dependency for major resources and platforms like ClinGen/VICC frameworks: The standards for classifying somatic and germline variants rely on Mondo to define the associated disease.OncoKB & CIViC: These databases use Mondo (or mappings to it, like NCIt) to structure their evidence by disease type. Kids First DRC & Monarch Initiative