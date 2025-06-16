"""
Evidence Aggregator for Somatic Variant Annotation

Loads and matches variants against knowledge bases to assemble evidence objects
following AMP/ASCO/CAP 2017, VICC/CGC 2022, and OncoKB guidelines.

Key responsibilities:
1. Load knowledge bases on first call (cache globally)
2. Match VEP variants against OncoKB, COSMIC, CIViC, etc.
3. Assemble evidence objects with proper scoring
4. Support both tumor-only and tumor-normal contexts
"""

import os
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import logging
from functools import lru_cache

from .models import (
    Evidence, VariantAnnotation, PopulationFrequency, HotspotEvidence,
    FunctionalPrediction, VICCScoring, AMPScoring, OncoKBScoring,
    VICCOncogenicity, AMPTierLevel, OncoKBLevel, ActionabilityType,
    EvidenceStrength, ContextSpecificTierAssignment, AnalysisType,
    DynamicSomaticConfidence
)
from .purity_estimation import estimate_tumor_purity, PurityEstimate

logger = logging.getLogger(__name__)

# Global caches for knowledge bases
_KB_CACHE: Dict[str, Any] = {}
_KB_LOADED = False


class KnowledgeBaseLoader:
    """Handles loading and caching of knowledge bases"""
    
    def __init__(self, kb_base_path: str = ".refs"):
        self.kb_base_path = Path(kb_base_path)
        
    def load_all_kbs(self) -> None:
        """Load all required knowledge bases into global cache"""
        global _KB_CACHE, _KB_LOADED
        
        if _KB_LOADED:
            return
            
        logger.info("Loading knowledge bases...")
        
        # Load OncoKB data
        _KB_CACHE['oncokb_genes'] = self._load_oncokb_genes()
        _KB_CACHE['oncokb_variants'] = self._load_oncokb_variants()
        _KB_CACHE['oncokb_evidence_levels'] = self._load_oncokb_evidence_levels()
        
        # Load CIViC data
        _KB_CACHE['civic_variants'] = self._load_civic_variants()
        _KB_CACHE['civic_evidence'] = self._load_civic_evidence()
        
        # Load COSMIC data
        _KB_CACHE['cosmic_cgc'] = self._load_cosmic_cgc()
        _KB_CACHE['cosmic_hotspots'] = self._load_cosmic_hotspots()
        
        # Load OncoVI curated resources
        _KB_CACHE['oncovi_tsg'] = self._load_oncovi_tumor_suppressors()
        _KB_CACHE['oncovi_oncogenes'] = self._load_oncovi_oncogenes()
        _KB_CACHE['oncovi_hotspots'] = self._load_oncovi_hotspots()
        _KB_CACHE['oncovi_domains'] = self._load_oncovi_domains()
        
        # Load functional prediction data
        _KB_CACHE['grantham_matrix'] = self._load_grantham_matrix()
        
        # Load OncoTree and ClinVar data
        _KB_CACHE['oncotree_data'] = self._load_oncotree_data()
        _KB_CACHE['clinvar_data'] = self._load_clinvar_data()
        
        # Load population frequency sources (handled by API clients)
        
        _KB_LOADED = True
        logger.info("Knowledge bases loaded successfully")
    
    def _load_oncokb_genes(self) -> Dict[str, Any]:
        """Load OncoKB gene annotations from comprehensive curated genes file"""
        oncokb_path = self.kb_base_path / "clinical_evidence" / "oncokb"
        
        genes = {}
        
        # Load from comprehensive curated_genes.tsv first (priority)
        if (oncokb_path / "curated_genes.tsv").exists():
            try:
                df = pd.read_csv(oncokb_path / "curated_genes.tsv", sep='\t')
                for _, row in df.iterrows():
                    gene = row['hugoSymbol']
                    genes[gene] = {
                        'is_oncogene': str(row.get('oncogene', '')).upper() == 'TRUE',
                        'is_tsg': str(row.get('tsg', '')).upper() == 'TRUE',
                        'oncokb_annotated': True,
                        'highest_sensitive_level': row.get('highestSensitiveLevel', ''),
                        'highest_resistance_level': row.get('highestResistanceLevel', ''),
                        'summary': row.get('summary', ''),
                        'background': row.get('background', ''),
                        'grch38_transcript': row.get('grch38Isoform', ''),
                        'grch38_refseq': row.get('grch38RefSeq', '')
                    }
                logger.info(f"Loaded {len(genes)} OncoKB curated genes")
            except Exception as e:
                logger.warning(f"Failed to load OncoKB curated genes: {e}")
        
        # Fallback to basic oncokb_genes.txt if curated file not available
        elif (oncokb_path / "oncokb_genes.txt").exists():
            try:
                df = pd.read_csv(oncokb_path / "oncokb_genes.txt", sep='\t')
                for _, row in df.iterrows():
                    gene = row['Hugo Symbol']
                    genes[gene] = {
                        'is_oncogene': 'Oncogene' in str(row.get('Oncogene', '')),
                        'is_tsg': 'TSG' in str(row.get('TSG', '')),
                        'oncokb_annotated': True
                    }
                logger.info(f"Loaded {len(genes)} OncoKB basic genes (fallback)")
            except Exception as e:
                logger.warning(f"Failed to load OncoKB basic genes: {e}")
        
        return genes
    
    def _load_oncokb_variants(self) -> Dict[str, Any]:
        """Load OncoKB variant-drug-cancer associations from biomarker file"""
        oncokb_path = self.kb_base_path / "clinical_evidence" / "oncokb"
        
        variants = {}
        
        # Load biomarker drug associations
        if (oncokb_path / "oncokb_biomarker_drug_associations.tsv").exists():
            try:
                df = pd.read_csv(oncokb_path / "oncokb_biomarker_drug_associations.tsv", sep='\t')
                
                for _, row in df.iterrows():
                    gene = row['Gene']
                    alteration = row['Alterations']
                    cancer_types = row['Cancer Types']
                    drugs = row['Drugs (for therapeutic implications only)']
                    level = row['Level']
                    
                    # Create variant key
                    variant_key = f"{gene}:{alteration}"
                    
                    if variant_key not in variants:
                        variants[variant_key] = {
                            'gene': gene,
                            'alteration': alteration,
                            'evidence_items': []
                        }
                    
                    # Add evidence item
                    evidence_item = {
                        'level': level,
                        'cancer_type': cancer_types,
                        'drugs': drugs,
                        'therapeutic_level': f"LEVEL_{level}" if level in ['1', '2', '3A', '3B', '4'] else f"LEVEL_{level}"
                    }
                    
                    variants[variant_key]['evidence_items'].append(evidence_item)
                
                logger.info(f"Loaded {len(variants)} OncoKB variant-drug associations")
                
            except Exception as e:
                logger.warning(f"Failed to load OncoKB biomarker associations: {e}")
        
        return variants
    
    def _load_oncokb_evidence_levels(self) -> Dict[str, Any]:
        """Load OncoKB evidence level definitions"""
        oncokb_path = self.kb_base_path / "clinical_evidence" / "oncokb"
        
        levels = {}
        
        if (oncokb_path / "levels_of_evidence.tsv").exists():
            try:
                df = pd.read_csv(oncokb_path / "levels_of_evidence.tsv", sep='\t')
                
                for _, row in df.iterrows():
                    level = row['levelOfEvidence']
                    levels[level] = {
                        'description': row['description'],
                        'html_description': row.get('htmlDescription', ''),
                        'color': row.get('colorHex', ''),
                        'therapeutic_significance': self._categorize_oncokb_level(level)
                    }
                
                logger.info(f"Loaded {len(levels)} OncoKB evidence levels")
                
            except Exception as e:
                logger.warning(f"Failed to load OncoKB evidence levels: {e}")
        
        return levels
    
    def _categorize_oncokb_level(self, level: str) -> str:
        """Categorize OncoKB level for therapeutic significance"""
        if level in ['LEVEL_1', 'LEVEL_2']:
            return 'high_therapeutic'
        elif level in ['LEVEL_3A', 'LEVEL_3B']:
            return 'moderate_therapeutic'  
        elif level == 'LEVEL_4':
            return 'biological_evidence'
        elif level.startswith('LEVEL_R'):
            return 'resistance'
        elif level.startswith('LEVEL_Dx'):
            return 'diagnostic'
        else:
            return 'other'
    
    def _load_civic_variants(self) -> Dict[str, Any]:
        """Load CIViC variant summaries"""
        civic_path = self.kb_base_path / "clinical_evidence" / "civic"
        variants = {}
        
        if (civic_path / "civic_variant_summaries.tsv").exists():
            df = pd.read_csv(civic_path / "civic_variant_summaries.tsv", sep='\t')
            for _, row in df.iterrows():
                variant_id = row.get('variant_id')
                if variant_id:
                    variants[variant_id] = {
                        'gene': row.get('gene'),
                        'variant': row.get('variant'),
                        'summary': row.get('variant_summary', ''),
                        'civic_score': row.get('civic_score', 0)
                    }
        
        return variants
    
    def _load_civic_evidence(self) -> Dict[str, Any]:
        """Load CIViC evidence items"""
        civic_path = self.kb_base_path / "clinical_evidence" / "civic"
        evidence = {}
        
        if (civic_path / "civic_variants.tsv").exists():
            df = pd.read_csv(civic_path / "civic_variants.tsv", sep='\t')
            for _, row in df.iterrows():
                evidence_id = row.get('evidence_id')
                if evidence_id:
                    evidence[evidence_id] = {
                        'variant_id': row.get('variant_id'),
                        'evidence_level': row.get('evidence_level'),
                        'evidence_type': row.get('evidence_type'),
                        'significance': row.get('significance'),
                        'disease': row.get('disease'),
                        'drugs': row.get('drugs', ''),
                        'rating': row.get('rating', 0)
                    }
        
        return evidence
    
    def _load_cosmic_cgc(self) -> Dict[str, Any]:
        """Load COSMIC Cancer Gene Census"""
        cosmic_path = self.kb_base_path / "cancer_genes" / "cosmic_cgc"
        genes = {}
        
        if (cosmic_path / "cancer_hotspots.tsv.gz").exists():
            try:
                df = pd.read_csv(cosmic_path / "cancer_hotspots.tsv.gz", sep='\t', compression='gzip')
            except Exception as e:
                logger.warning(f"Failed to load COSMIC CGC file: {e}")
                return genes
            for _, row in df.iterrows():
                gene = row['GENE_SYMBOL']
                genes[gene] = {
                    'role_in_cancer': row.get('ROLE_IN_CANCER', ''),
                    'mutation_types': row.get('MUTATION_TYPES', ''),
                    'tumour_types_somatic': row.get('TUMOUR_TYPES_SOMATIC', ''),
                    'tumour_types_germline': row.get('TUMOUR_TYPES_GERMLINE', ''),
                    'is_oncogene': 'oncogene' in str(row.get('ROLE_IN_CANCER', '')).lower(),
                    'is_tsg': 'tsg' in str(row.get('ROLE_IN_CANCER', '')).lower()
                }
        
        return genes
    
    def _load_cosmic_hotspots(self) -> List[Dict[str, Any]]:
        """Load COSMIC hotspots data"""
        cosmic_path = self.kb_base_path / "hotspots" / "msk_hotspots"
        hotspots = []
        
        # Load from multiple hotspot sources
        hotspot_files = [
            "MSK-SNV-hotspots-v2.tsv.gz",
            "MSK-INDEL-hotspots-v2.tsv.gz"
        ]
        
        for filename in hotspot_files:
            filepath = cosmic_path / filename
            if filepath.exists():
                try:
                    df = pd.read_csv(filepath, sep='\t', compression='gzip')
                    for _, row in df.iterrows():
                        hotspots.append({
                            'gene': row.get('Hugo_Symbol'),
                            'chromosome': row.get('Chromosome'),
                            'position': row.get('Start_Position'),
                            'reference': row.get('Reference_Allele'),
                            'variant': row.get('Tumor_Seq_Allele2'),
                            'samples': row.get('Mutation_Count', 0),
                            'source': 'MSK_hotspots'
                        })
                except Exception as e:
                    logger.warning(f"Could not load {filename}: {e}")
        
        return hotspots
    
    def _load_oncovi_tumor_suppressors(self) -> Set[str]:
        """Load OncoVI tumor suppressor gene list"""
        oncovi_path = self.kb_base_path / "cancer_genes" / "oncovi_lists"
        tsg_genes = set()
        
        if (oncovi_path / "tumor_suppressors.txt").exists():
            with open(oncovi_path / "tumor_suppressors.txt", 'r') as f:
                for line in f:
                    gene = line.strip()
                    if gene:
                        tsg_genes.add(gene)
        
        return tsg_genes
    
    def _load_oncovi_oncogenes(self) -> Set[str]:
        """Load OncoVI oncogene list"""
        oncovi_path = self.kb_base_path / "cancer_genes" / "oncovi_lists"
        oncogenes = set()
        
        if (oncovi_path / "oncogenes.txt").exists():
            with open(oncovi_path / "oncogenes.txt", 'r') as f:
                for line in f:
                    gene = line.strip()
                    if gene:
                        oncogenes.add(gene)
        
        return oncogenes
    
    def _load_oncovi_hotspots(self) -> Dict[str, Any]:
        """Load OncoVI hotspot data"""
        oncovi_path = self.kb_base_path / "hotspots" / "oncovi_hotspots"
        hotspots = {}
        
        # Load single residue hotspots
        if (oncovi_path / "single_residue_hotspots.tsv").exists():
            df = pd.read_csv(oncovi_path / "single_residue_hotspots.tsv", sep='\t')
            for _, row in df.iterrows():
                key = f"{row['gene']}:{row['residue']}"
                hotspots[key] = {
                    'gene': row['gene'],
                    'residue': row['residue'],
                    'samples': row.get('samples', 0),
                    'cancer_types': row.get('cancer_types', '').split(','),
                    'type': 'single_residue'
                }
        
        # Load indel hotspots
        if (oncovi_path / "indel_hotspots.tsv").exists():
            df = pd.read_csv(oncovi_path / "indel_hotspots.tsv", sep='\t')
            for _, row in df.iterrows():
                key = f"{row['gene']}:{row['position']}"
                hotspots[key] = {
                    'gene': row['gene'],
                    'position': row['position'],
                    'samples': row.get('samples', 0),
                    'type': 'indel'
                }
        
        return hotspots
    
    def _load_oncovi_domains(self) -> Dict[str, Any]:
        """Load OncoVI protein domain annotations"""
        oncovi_path = self.kb_base_path / "functional_predictions" / "plugin_data" / "protein_domains"
        domains = {}
        
        if (oncovi_path / "oncovi_domains.tsv").exists():
            df = pd.read_csv(oncovi_path / "oncovi_domains.tsv", sep='\t')
            for _, row in df.iterrows():
                gene = row['gene']
                if gene not in domains:
                    domains[gene] = []
                domains[gene].append({
                    'domain': row['domain'],
                    'start': row['start'],
                    'end': row['end'],
                    'importance': row.get('importance', 'unknown')
                })
        
        return domains
    
    def _load_grantham_matrix(self) -> Dict[Tuple[str, str], float]:
        """Load Grantham distance matrix"""
        oncovi_path = self.kb_base_path / "functional_predictions" / "plugin_data" / "amino_acid_matrices"
        matrix = {}
        
        if (oncovi_path / "grantham_distance.txt").exists():
            with open(oncovi_path / "grantham_distance.txt", 'r') as f:
                lines = f.readlines()
                # Parse the matrix format
                # This would depend on the exact format of the file
                pass
        
        return matrix
    
    def _load_oncotree_data(self) -> Dict[str, Any]:
        """Load OncoTree cancer type hierarchy from efficient TSV format"""
        oncotree_dir = self.kb_base_path / "clinical_context" / "oncotree"
        oncotree_tsv = oncotree_dir / "oncotree.tsv"
        
        if not oncotree_tsv.exists():
            logger.warning(f"OncoTree TSV file not found: {oncotree_tsv}")
            return {}
        
        try:
            import pandas as pd
            
            # Load main OncoTree TSV file
            df = pd.read_csv(oncotree_tsv, sep='\t')
            
            # Create lookup maps for efficient cancer type validation and hierarchy
            code_map = {}
            hierarchy_map = {}
            tissue_map = {}
            
            for _, row in df.iterrows():
                code = row['code']
                parent = row['parent'] if pd.notna(row['parent']) and row['parent'] != '' else None
                tissue = row['tissue']
                
                code_map[code] = {
                    'name': row['name'],
                    'main_type': row['mainType'],
                    'tissue': tissue,
                    'level': row['level'],
                    'parent': parent,
                    'external_references': row.get('external_references', '')
                }
                
                # Build hierarchy chain
                if parent and parent in code_map:
                    hierarchy_map[code] = hierarchy_map.get(parent, []) + [parent]
                else:
                    hierarchy_map[code] = []
                
                # Group by tissue for efficient tissue-specific lookups
                if tissue not in tissue_map:
                    tissue_map[tissue] = []
                tissue_map[tissue].append(code)
            
            # Load tissue-specific files for enhanced lookup (optional)
            tissue_files = {}
            for tissue_file in oncotree_dir.glob("oncotree_*.tsv"):
                tissue_name = tissue_file.stem.replace('oncotree_', '')
                if tissue_file.exists():
                    tissue_df = pd.read_csv(tissue_file, sep='\t')
                    tissue_files[tissue_name] = tissue_df.to_dict('records')
            
            logger.info(f"Loaded OncoTree data: {len(code_map)} cancer types, {len(tissue_files)} tissue files")
            return {
                'code_map': code_map,
                'hierarchy_map': hierarchy_map,
                'tissue_map': tissue_map,
                'tissue_files': tissue_files,
                'total_codes': len(code_map)
            }
            
        except Exception as e:
            logger.warning(f"Failed to load OncoTree TSV data: {e}")
            return {}
    
    def _load_clinvar_data(self) -> Dict[str, Any]:
        """Load ClinVar pathogenicity data for germline filtering and evidence"""
        clinvar_path = self.kb_base_path / "clinical_evidence" / "clinvar" / "variant_summary.txt.gz"
        
        if not clinvar_path.exists():
            logger.warning(f"ClinVar file not found: {clinvar_path}")
            return {}
        
        try:
            import pandas as pd
            
            # Load variant summary data
            df = pd.read_csv(clinvar_path, sep='\t', compression='gzip', 
                           usecols=['GeneSymbol', 'ClinicalSignificance', 'ReviewStatus', 
                                   'PhenotypeList', 'Assembly', 'Chromosome', 'Start', 'Stop',
                                   'ReferenceAllele', 'AlternateAllele', 'Type', 'Name'])
            
            # Filter for GRCh38 and pathogenic variants
            df_grch38 = df[df['Assembly'] == 'GRCh38']
            
            # Create pathogenic variant lookup
            pathogenic_variants = {}
            benign_variants = {}
            
            for _, row in df_grch38.iterrows():
                gene = row.get('GeneSymbol')
                if pd.isna(gene) or gene == '-':
                    continue
                
                significance = str(row.get('ClinicalSignificance', '')).lower()
                
                # Map ClinVar significance to evidence codes
                if any(term in significance for term in ['pathogenic', 'likely_pathogenic']):
                    if gene not in pathogenic_variants:
                        pathogenic_variants[gene] = []
                    pathogenic_variants[gene].append({
                        'significance': significance,
                        'review_status': row.get('ReviewStatus', ''),
                        'phenotype': row.get('PhenotypeList', ''),
                        'chromosome': row.get('Chromosome', ''),
                        'position': row.get('Start', ''),
                        'ref': row.get('ReferenceAllele', ''),
                        'alt': row.get('AlternateAllele', ''),
                        'variant_type': row.get('Type', ''),
                        'name': row.get('Name', '')
                    })
                
                elif any(term in significance for term in ['benign', 'likely_benign']):
                    if gene not in benign_variants:
                        benign_variants[gene] = []
                    benign_variants[gene].append({
                        'significance': significance,
                        'review_status': row.get('ReviewStatus', ''),
                        'chromosome': row.get('Chromosome', ''),
                        'position': row.get('Start', ''),
                        'ref': row.get('ReferenceAllele', ''),
                        'alt': row.get('AlternateAllele', '')
                    })
            
            logger.info(f"Loaded ClinVar data: {len(pathogenic_variants)} genes with pathogenic variants, "
                       f"{len(benign_variants)} genes with benign variants")
            
            return {
                'pathogenic_variants': pathogenic_variants,
                'benign_variants': benign_variants,
                'total_variants': len(df_grch38)
            }
            
        except Exception as e:
            logger.warning(f"Failed to load ClinVar data: {e}")
            return {}


class DynamicSomaticConfidenceCalculator:
    """Calculates Dynamic Somatic Confidence (DSC) scores per TN_VERSUS_TO.md specification"""
    
    def __init__(self):
        # Cancer predisposition genes for ClinVar flagging
        self.predisposition_genes = {
            "BRCA1", "BRCA2", "TP53", "MLH1", "MSH2", "MSH6", "PMS2", "APC", 
            "PALB2", "CHEK2", "ATM", "CDKN2A", "PTEN", "CDH1", "STK11", "VHL"
        }
        
        # Known oncogenes and tumor suppressors
        self.oncogenes = {"KRAS", "BRAF", "EGFR", "PIK3CA", "IDH1", "IDH2", "KIT", "PDGFRA"}
        self.tumor_suppressors = {"TP53", "APC", "BRCA1", "BRCA2", "PTEN", "RB1", "VHL", "NF1"}
    
    def calculate_dsc_score(self, variant: VariantAnnotation, evidence_list: List[Evidence], 
                           tumor_purity: Optional[float] = None,
                           variant_annotations: Optional[List[VariantAnnotation]] = None,
                           analysis_type: AnalysisType = AnalysisType.TUMOR_ONLY,
                           metadata: Optional[Dict[str, Any]] = None) -> DynamicSomaticConfidence:
        """
        Calculate Dynamic Somatic Confidence score using multiple evidence modules
        
        Args:
            variant: Variant annotation with population frequencies, etc.
            evidence_list: Evidence from knowledge bases
            tumor_purity: Estimated tumor purity (0-1), if None will estimate from data
            variant_annotations: All variant annotations for purity estimation
            analysis_type: Analysis workflow type
            metadata: Analysis metadata potentially containing purity info
            
        Returns:
            DynamicSomaticConfidence scoring object
        """
        
        # If tumor purity is not provided, estimate it from available data
        if tumor_purity is None and variant_annotations is not None:
            try:
                purity_estimate = estimate_tumor_purity(
                    variant_annotations=variant_annotations,
                    analysis_type=analysis_type,
                    metadata=metadata
                )
                tumor_purity = purity_estimate.purity
                logger.info(f"Estimated tumor purity: {tumor_purity:.3f} (confidence: {purity_estimate.confidence:.3f})")
            except Exception as e:
                logger.warning(f"Failed to estimate tumor purity: {e}")
                tumor_purity = None
        modules_used = []
        
        # Module 1: VAF/Purity Consistency (if available)
        vaf_purity_score = self._calculate_vaf_purity_score(variant, tumor_purity)
        if vaf_purity_score is not None:
            modules_used.append("vaf_purity")
        
        # Module 2: Somatic vs Germline Prior Probability (always available)
        prior_prob_score = self._calculate_prior_probability_score(variant, evidence_list)
        modules_used.append("prior_probability")
        
        # Module 3: Genomic Context (advanced, placeholder for now)
        genomic_context_score = self._calculate_genomic_context_score(variant, evidence_list)
        if genomic_context_score is not None:
            modules_used.append("genomic_context")
        
        # Combine module scores into final DSC
        dsc_score = self._combine_module_scores(vaf_purity_score, prior_prob_score, genomic_context_score)
        
        # Extract key evidence details
        pop_freq = None
        if variant.population_frequencies:
            pop_freq = min(pf.allele_frequency for pf in variant.population_frequencies if pf.allele_frequency is not None)
        
        hotspot_evidence = any("hotspot" in e.description.lower() for e in evidence_list)
        clinvar_germline = any("clinvar" in e.source_kb.lower() and "pathogenic" in e.description.lower() for e in evidence_list)
        
        # Calculate confidence in DSC calculation
        dsc_confidence = self._calculate_dsc_confidence(modules_used, variant, evidence_list)
        
        return DynamicSomaticConfidence(
            dsc_score=dsc_score,
            vaf_purity_score=vaf_purity_score,
            prior_probability_score=prior_prob_score,
            genomic_context_score=genomic_context_score,
            tumor_purity=tumor_purity,
            variant_vaf=getattr(variant, 'vaf', None),
            hotspot_evidence=hotspot_evidence,
            population_frequency=pop_freq,
            clinvar_germline=clinvar_germline,
            dsc_confidence=dsc_confidence,
            modules_available=modules_used
        )
    
    def _calculate_vaf_purity_score(self, variant: VariantAnnotation, tumor_purity: Optional[float]) -> Optional[float]:
        """
        Module 1: VAF/Purity consistency scoring using HMF PURPLE-inspired methodology
        
        Evaluates if the variant's VAF is consistent with somatic origin given tumor purity.
        Considers heterozygous, homozygous/LOH, and subclonal patterns.
        """
        if tumor_purity is None or not hasattr(variant, 'vaf') or variant.vaf is None:
            return None
        
        vaf = variant.vaf
        purity = tumor_purity
        
        # Define expected VAF ranges for different scenarios
        # Account for copy number variations and subclonality
        
        # Scenario 1: Heterozygous somatic (most common)
        expected_het_vaf = purity / 2
        het_tolerance = 0.25  # ±25% tolerance (more permissive)
        
        # Scenario 2: Homozygous/LOH somatic 
        expected_hom_vaf = purity
        hom_tolerance = 0.30  # ±30% tolerance (more variable)
        
        # Scenario 3: Subclonal somatic (fraction of clone)
        # Expected range: 0.05 to purity/2
        subclonal_min = 0.05
        subclonal_max = expected_het_vaf
        
        # Scenario 4: Germline contamination (suspicious for somatic)
        # VAF around 0.5 * purity (diluted germline)
        germline_contamination_vaf = 0.5 * purity
        
        # Calculate consistency scores for each scenario
        scores = []
        
        # Heterozygous somatic score
        if expected_het_vaf > 0:
            het_deviation = abs(vaf - expected_het_vaf) / expected_het_vaf
            if het_deviation <= het_tolerance:
                het_score = 1.0 - (het_deviation / het_tolerance) * 0.1  # 0.9-1.0
                scores.append(("heterozygous", het_score))
        
        # Homozygous/LOH somatic score
        if expected_hom_vaf > 0 and vaf > 0.3:  # Only consider if VAF is reasonably high
            hom_deviation = abs(vaf - expected_hom_vaf) / expected_hom_vaf
            if hom_deviation <= hom_tolerance:
                hom_score = 0.95 - (hom_deviation / hom_tolerance) * 0.15  # 0.8-0.95
                scores.append(("homozygous_loh", hom_score))
        
        # Subclonal somatic score
        if subclonal_min <= vaf <= subclonal_max:
            # Score based on how well it fits subclonal pattern
            subclonal_score = 0.3 + 0.4 * (vaf / subclonal_max)  # 0.3-0.7
            scores.append(("subclonal", subclonal_score))
        
        # Check for suspicious patterns
        
        # Pattern 1: VAF too high for purity (suggests germline or copy gain)
        if vaf > purity + 0.1:
            if abs(vaf - 0.5) < 0.1:  # Close to 50% = likely germline
                return 0.1  # Very low somatic confidence
            else:
                # Could be copy number alteration, moderate penalty
                return 0.4
        
        # Pattern 2: VAF around pure germline level (close to 50%)
        if abs(vaf - 0.5) < 0.05 and vaf > 0.45:
            return 0.2  # Low somatic confidence - likely germline
        
        # Pattern 3: Very low VAF in high purity (artifacts/CHIP)
        if vaf < 0.05 and purity > 0.7:
            return 0.3  # Could be artifact or CHIP
        
        # Return best matching scenario score
        if scores:
            best_scenario, best_score = max(scores, key=lambda x: x[1])
            
            # Apply additional modifiers based on variant characteristics
            
            # Boost for variants in tumor suppressor genes (LOH more likely)
            if best_scenario == "homozygous_loh" and hasattr(variant, 'is_tumor_suppressor') and variant.is_tumor_suppressor:
                best_score = min(1.0, best_score + 0.1)
            
            # Boost for high-quality, high-depth variants
            if hasattr(variant, 'total_depth') and variant.total_depth and variant.total_depth > 100:
                best_score = min(1.0, best_score + 0.05)
            
            return best_score
        else:
            # No good match found - assign low score based on general plausibility
            if 0.05 <= vaf <= purity:
                return 0.3  # Plausible but not well-explained
            else:
                return 0.1  # Implausible for somatic origin
    
    def _calculate_prior_probability_score(self, variant: VariantAnnotation, evidence_list: List[Evidence]) -> float:
        """Module 2: Somatic vs Germline Prior Probability"""
        score = 0.5  # Start neutral
        
        gene = variant.gene_symbol
        
        # Strong positive evidence for somatic origin
        hotspot_evidence = [e for e in evidence_list if "hotspot" in e.description.lower()]
        if hotspot_evidence:
            # Boost based on hotspot strength
            for evidence in hotspot_evidence:
                if evidence.code == "OS3":  # Well-established hotspot
                    score = min(1.0, score + 0.4)
                elif evidence.code == "OM3":  # Moderate hotspot
                    score = min(1.0, score + 0.2)
        
        # OncoKB/CIViC evidence
        oncokb_civic_evidence = [e for e in evidence_list if e.source_kb in ["OncoKB", "CIViC"]]
        if oncokb_civic_evidence:
            score = min(1.0, score + 0.3)
        
        # Gene context boost
        if gene in self.oncogenes and any("missense" in cons for cons in variant.consequence):
            score = min(1.0, score + 0.2)
        elif gene in self.tumor_suppressors and any(cons in ["stop_gained", "frameshift_variant"] for cons in variant.consequence):
            score = min(1.0, score + 0.3)
        
        # Strong negative evidence for somatic origin (suggests germline)
        # Population frequency penalty
        if variant.population_frequencies:
            max_af = max(pf.allele_frequency for pf in variant.population_frequencies if pf.allele_frequency is not None)
            if max_af > 0.001:  # >0.1% in population
                penalty = min(0.4, max_af * 100)  # Scale penalty with frequency
                score = max(0.0, score - penalty)
        
        # ClinVar germline pathogenic penalty
        clinvar_germline = [e for e in evidence_list if "clinvar" in e.source_kb.lower() and "pathogenic" in e.description.lower()]
        if clinvar_germline:
            score = max(0.0, score - 0.3)
        
        # Predisposition gene penalty
        if gene in self.predisposition_genes:
            score = max(0.0, score - 0.1)  # Small penalty for being in predisposition gene
        
        return max(0.0, min(1.0, score))
    
    def _calculate_genomic_context_score(self, variant: VariantAnnotation, evidence_list: List[Evidence]) -> Optional[float]:
        """Module 3: Genomic Context (placeholder for advanced features like LOH, mutational signatures)"""
        # This is a placeholder for future implementation
        # Would incorporate:
        # - Loss of Heterozygosity (LOH) analysis
        # - Mutational signature compatibility
        # - Co-occurring somatic events
        # - Tumor mutational burden context
        
        # For now, return None to indicate this module is not implemented
        return None
    
    def _combine_module_scores(self, vaf_purity: Optional[float], prior_prob: float, 
                              genomic_context: Optional[float]) -> float:
        """Combine module scores into final DSC score with synergistic effects"""
        scores = [prior_prob]  # Always have prior probability
        weights = [0.6]  # Base weight for prior probability
        
        if vaf_purity is not None:
            scores.append(vaf_purity)
            weights.append(0.4)  # VAF/purity gets significant weight
            weights[0] = 0.6  # Keep prior prob weight high
        
        if genomic_context is not None:
            scores.append(genomic_context)
            weights.append(0.2)
            # Adjust other weights proportionally
            total_weight = sum(weights)
            weights = [w * 0.8 / total_weight for w in weights]
            weights.append(0.2)
        
        # Calculate base weighted average
        base_score = sum(score * weight for score, weight in zip(scores, weights))
        
        # Apply synergistic boost when both VAF/purity and prior are high
        if vaf_purity is not None and vaf_purity > 0.8 and prior_prob > 0.8:
            synergy_boost = 0.1 * min(vaf_purity, prior_prob)
            base_score = min(1.0, base_score + synergy_boost)
        
        return base_score
    
    def _calculate_dsc_confidence(self, modules_used: List[str], variant: VariantAnnotation, 
                                 evidence_list: List[Evidence]) -> float:
        """Calculate confidence in the DSC score itself"""
        confidence = 0.5  # Base confidence
        
        # More modules = higher confidence
        confidence += len(modules_used) * 0.2
        
        # High-quality evidence boosts confidence
        if any(e.confidence and e.confidence > 0.9 for e in evidence_list):
            confidence += 0.2
        
        # Population frequency data boosts confidence
        if variant.population_frequencies:
            confidence += 0.1
        
        return max(0.1, min(1.0, confidence))



class EvidenceAggregator:
    """Main class for aggregating evidence from knowledge bases"""
    
    def __init__(self, kb_base_path: str = ".refs"):
        self.loader = KnowledgeBaseLoader(kb_base_path)
        # Load KBs on first use to avoid startup errors
        self.dsc_calculator = DynamicSomaticConfidenceCalculator()
    
    def aggregate_evidence(self, variant_annotation: VariantAnnotation, cancer_type: str = "unknown", 
                         analysis_type: AnalysisType = AnalysisType.TUMOR_ONLY) -> List[Evidence]:
        """
        Aggregate evidence from all knowledge bases for a variant
        
        Args:
            variant_annotation: VEP-annotated variant
            cancer_type: Cancer type context
            analysis_type: Analysis workflow type for confidence modulation
            
        Returns:
            List of evidence items supporting classification
        """
        # Load knowledge bases on first use
        global _KB_LOADED
        if not _KB_LOADED:
            try:
                self.loader.load_all_kbs()
            except Exception as e:
                logger.warning(f"Some knowledge bases failed to load: {e}")
        
        evidence_list = []
        
        # Population frequency evidence (critical for TO, contextual for TN)
        evidence_list.extend(self._get_population_frequency_evidence(variant_annotation, analysis_type))
        
        # Hotspot evidence
        evidence_list.extend(self._get_hotspot_evidence(variant_annotation, analysis_type))
        
        # Gene context evidence
        evidence_list.extend(self._get_gene_context_evidence(variant_annotation, analysis_type))
        
        # Functional prediction evidence
        evidence_list.extend(self._get_functional_prediction_evidence(variant_annotation, analysis_type))
        
        # Clinical evidence (ambiguous interpretation for TO)
        evidence_list.extend(self._get_clinical_evidence(variant_annotation, cancer_type, analysis_type))
        
        # Domain evidence
        evidence_list.extend(self._get_domain_evidence(variant_annotation, analysis_type))
        
        # ClinVar evidence for germline filtering and pathogenicity
        evidence_list.extend(self._get_clinvar_evidence(variant_annotation, analysis_type))
        
        return evidence_list
    
    def calculate_dsc_score(self, variant: VariantAnnotation, evidence_list: List[Evidence], 
                           tumor_purity: Optional[float] = None) -> DynamicSomaticConfidence:
        """Calculate Dynamic Somatic Confidence score for tumor-only analysis"""
        return self.dsc_calculator.calculate_dsc_score(variant, evidence_list, tumor_purity)
    
    def _get_population_frequency_evidence(self, variant: VariantAnnotation, analysis_type: AnalysisType) -> List[Evidence]:
        """Generate population frequency evidence"""
        evidence = []
        
        for pop_freq in variant.population_frequencies:
            if pop_freq.allele_frequency is not None:
                # Base confidence modulated by analysis type
                base_confidence_high = 0.9 if analysis_type == AnalysisType.TUMOR_NORMAL else 0.95  # Higher for TO (critical filter)
                base_confidence_med = 0.8 if analysis_type == AnalysisType.TUMOR_NORMAL else 0.85
                base_confidence_low = 0.85 if analysis_type == AnalysisType.TUMOR_NORMAL else 0.9
                
                # VICC SBVS1: High population frequency (>5%) - stronger evidence for TO
                if pop_freq.allele_frequency > 0.05:
                    description = f"High population frequency ({pop_freq.allele_frequency:.4f}) suggests germline variant"
                    if analysis_type == AnalysisType.TUMOR_ONLY:
                        description += " (CRITICAL FILTER for tumor-only analysis)"
                    
                    evidence.append(Evidence(
                        code="SBVS1",
                        score=-8,
                        guideline="VICC_2022",
                        source_kb=pop_freq.database,
                        description=description,
                        data={"frequency": pop_freq.allele_frequency, "population": pop_freq.population, "analysis_critical": analysis_type == AnalysisType.TUMOR_ONLY},
                        confidence=base_confidence_high
                    ))
                
                # VICC OP4: Absent from population databases (<0.0001%)
                elif pop_freq.allele_frequency < 0.0001:
                    description = f"Very rare in population ({pop_freq.allele_frequency:.6f})"
                    if analysis_type == AnalysisType.TUMOR_ONLY:
                        description += " (supports somatic origin in tumor-only analysis)"
                    
                    evidence.append(Evidence(
                        code="OP4",
                        score=1,
                        guideline="VICC_2022", 
                        source_kb=pop_freq.database,
                        description=description,
                        data={"frequency": pop_freq.allele_frequency, "population": pop_freq.population},
                        confidence=base_confidence_med
                    ))
                
                # AMP Tier IV assignment for common variants
                if pop_freq.allele_frequency > 0.01:
                    description = f"Common variant (MAF {pop_freq.allele_frequency:.4f}) likely benign/germline"
                    if analysis_type == AnalysisType.TUMOR_ONLY:
                        description += " (primary germline filter for tumor-only)"
                    
                    evidence.append(Evidence(
                        code="COMMON_VARIANT",
                        score=0,
                        guideline="AMP_2017",
                        source_kb=pop_freq.database,
                        description=description,
                        data={"frequency": pop_freq.allele_frequency},
                        confidence=base_confidence_low
                    ))
        
        return evidence
    
    def _get_hotspot_evidence(self, variant: VariantAnnotation, analysis_type: AnalysisType) -> List[Evidence]:
        """Generate hotspot evidence"""
        evidence = []
        
        for hotspot in variant.hotspot_evidence:
            # VICC OS3: Well-established hotspot (>20 samples)
            if hotspot.samples_observed >= 20:
                evidence.append(Evidence(
                    code="OS3",
                    score=4,
                    guideline="VICC_2022",
                    source_kb=hotspot.source,
                    description=f"Well-established hotspot ({hotspot.samples_observed} samples)",
                    data={"samples": hotspot.samples_observed, "cancer_types": hotspot.cancer_types},
                    confidence=0.9
                ))
            
            # VICC OM3: Moderate hotspot evidence (10-20 samples)
            elif hotspot.samples_observed >= 10:
                evidence.append(Evidence(
                    code="OM3",
                    score=2,
                    guideline="VICC_2022",
                    source_kb=hotspot.source,
                    description=f"Moderate hotspot evidence ({hotspot.samples_observed} samples)",
                    data={"samples": hotspot.samples_observed},
                    confidence=0.8
                ))
            
            # VICC OP3: Located in hotspot region (3-10 samples)
            elif hotspot.samples_observed >= 3:
                evidence.append(Evidence(
                    code="OP3",
                    score=1,
                    guideline="VICC_2022",
                    source_kb=hotspot.source,
                    description=f"Located in hotspot region ({hotspot.samples_observed} samples)",
                    data={"samples": hotspot.samples_observed},
                    confidence=0.7
                ))
        
        return evidence
    
    def _get_gene_context_evidence(self, variant: VariantAnnotation, analysis_type: AnalysisType) -> List[Evidence]:
        """Generate gene context evidence"""
        evidence = []
        gene = variant.gene_symbol
        
        # Check OncoVI tumor suppressor genes
        if gene in _KB_CACHE.get('oncovi_tsg', set()):
            # Check if this is a null variant (nonsense, frameshift, splice)
            null_consequences = ['stop_gained', 'frameshift_variant', 'splice_donor_variant', 'splice_acceptor_variant']
            if any(cons in variant.consequence for cons in null_consequences):
                evidence.append(Evidence(
                    code="OVS1",
                    score=8,
                    guideline="VICC_2022",
                    source_kb="OncoVI_TSG",
                    description=f"Null variant in established tumor suppressor gene {gene}",
                    data={"gene_role": "tumor_suppressor", "consequences": variant.consequence},
                    confidence=0.95
                ))
        
        # Check OncoVI oncogenes
        if gene in _KB_CACHE.get('oncovi_oncogenes', set()):
            # Check for activating variants
            activating_consequences = ['missense_variant', 'inframe_insertion', 'inframe_deletion']
            if any(cons in variant.consequence for cons in activating_consequences):
                evidence.append(Evidence(
                    code="OS1",
                    score=4,
                    guideline="VICC_2022",
                    source_kb="OncoVI_Oncogenes",
                    description=f"Potential activating variant in established oncogene {gene}",
                    data={"gene_role": "oncogene", "consequences": variant.consequence},
                    confidence=0.8
                ))
        
        # COSMIC Cancer Gene Census
        cosmic_gene = _KB_CACHE.get('cosmic_cgc', {}).get(gene)
        if cosmic_gene:
            evidence.append(Evidence(
                code="OM4",
                score=2,
                guideline="VICC_2022",
                source_kb="COSMIC_CGC",
                description=f"Mutation in gene with established role in cancer: {cosmic_gene['role_in_cancer']}",
                data={"role_in_cancer": cosmic_gene['role_in_cancer']},
                confidence=0.85
            ))
        
        return evidence
    
    def _get_functional_prediction_evidence(self, variant: VariantAnnotation, analysis_type: AnalysisType) -> List[Evidence]:
        """Generate functional prediction evidence from VEP plugin data"""
        evidence = []
        
        if not variant.plugin_data:
            return evidence
            
        # Extract pathogenicity scores with evidence-based weights
        pathogenicity_scores = variant.plugin_data.get("pathogenicity_scores", {})
        splicing_scores = variant.plugin_data.get("splicing_scores", {})
        conservation_data = variant.plugin_data.get("conservation_data", {})
        
        # Process high-evidence pathogenicity predictors
        evidence.extend(self._process_high_evidence_predictors(pathogenicity_scores, analysis_type))
        
        # Process splicing predictions
        evidence.extend(self._process_splicing_predictions(splicing_scores, analysis_type))
        
        # Process conservation evidence
        evidence.extend(self._process_conservation_evidence(conservation_data, analysis_type))
        
        # Generate consensus evidence if we have multiple predictors
        evidence.extend(self._generate_consensus_evidence(pathogenicity_scores, analysis_type))
        
        return evidence
    
    def _process_high_evidence_predictors(self, pathogenicity_scores: Dict[str, Any], analysis_type: AnalysisType) -> List[Evidence]:
        """Process high-evidence pathogenicity predictors (AlphaMissense, REVEL, EVE, etc.)"""
        evidence = []
        
        # High evidence predictors with specific thresholds
        high_evidence_predictors = {
            "alphamissense": {"pathogenic_threshold": 0.564, "confidence": 0.9},
            "revel": {"pathogenic_threshold": 0.5, "confidence": 0.85},
            "eve": {"pathogenic_threshold": 0.5, "confidence": 0.85},
            "varity": {"pathogenic_threshold": 0.5, "confidence": 0.8}
        }
        
        for predictor, config in high_evidence_predictors.items():
            if predictor in pathogenicity_scores:
                score_data = pathogenicity_scores[predictor]
                score = score_data.get("score")
                
                if score is not None:
                    try:
                        score_val = float(score)
                        
                        if score_val >= config["pathogenic_threshold"]:
                            evidence.append(Evidence(
                                code="OP1_HIGH",
                                score=2,  # Higher weight for high-evidence predictors
                                guideline="VICC_2022_ENHANCED",
                                source_kb=f"{predictor.upper()}_VEP",
                                description=f"{predictor.upper()} predicts pathogenic effect (score: {score_val:.3f})",
                                data={"score": score_val, "threshold": config["pathogenic_threshold"]},
                                confidence=config["confidence"]
                            ))
                        elif score_val <= (1 - config["pathogenic_threshold"]):  # Conservative benign threshold
                            evidence.append(Evidence(
                                code="SBP1_HIGH", 
                                score=-2,
                                guideline="VICC_2022_ENHANCED",
                                source_kb=f"{predictor.upper()}_VEP",
                                description=f"{predictor.upper()} predicts benign effect (score: {score_val:.3f})",
                                data={"score": score_val, "threshold": config["pathogenic_threshold"]},
                                confidence=config["confidence"]
                            ))
                    except (ValueError, TypeError):
                        continue
                        
        return evidence
    
    def _process_splicing_predictions(self, splicing_scores: Dict[str, Any], analysis_type: AnalysisType) -> List[Evidence]:
        """Process splicing predictions (SpliceAI, dbscSNV)"""
        evidence = []
        
        # SpliceAI processing (high evidence)
        if "spliceai" in splicing_scores:
            spliceai_data = splicing_scores["spliceai"]
            
            # Find maximum delta score
            delta_scores = []
            for key in ["ds_ag", "ds_al", "ds_dg", "ds_dl"]:
                if key in spliceai_data:
                    try:
                        delta_scores.append(float(spliceai_data[key]))
                    except (ValueError, TypeError):
                        continue
                        
            if delta_scores:
                max_delta = max(delta_scores)
                
                if max_delta >= 0.8:  # High confidence splicing disruption
                    evidence.append(Evidence(
                        code="OP2_SPLICE",
                        score=2,
                        guideline="VICC_2022_ENHANCED", 
                        source_kb="SpliceAI_VEP",
                        description=f"SpliceAI predicts high splicing disruption (max Δ: {max_delta:.3f})",
                        data={"max_delta_score": max_delta, "all_scores": spliceai_data},
                        confidence=0.9
                    ))
                elif max_delta >= 0.2:  # Moderate splicing impact
                    evidence.append(Evidence(
                        code="OP2_SPLICE",
                        score=1,
                        guideline="VICC_2022_ENHANCED",
                        source_kb="SpliceAI_VEP", 
                        description=f"SpliceAI predicts moderate splicing disruption (max Δ: {max_delta:.3f})",
                        data={"max_delta_score": max_delta, "all_scores": spliceai_data},
                        confidence=0.75
                    ))
                    
        # dbscSNV processing (moderate evidence)
        if "dbscsnv" in splicing_scores:
            dbscsnv_data = splicing_scores["dbscsnv"]
            ada_score = dbscsnv_data.get("ada_score")
            rf_score = dbscsnv_data.get("rf_score")
            
            if ada_score is not None and rf_score is not None:
                try:
                    ada_val = float(ada_score)
                    rf_val = float(rf_score)
                    
                    if ada_val >= 0.6 and rf_val >= 0.6:  # Both models agree
                        evidence.append(Evidence(
                            code="OP2_SPLICE",
                            score=1,
                            guideline="VICC_2022_ENHANCED",
                            source_kb="dbscSNV_VEP",
                            description=f"dbscSNV predicts splicing disruption (ADA: {ada_val:.3f}, RF: {rf_val:.3f})",
                            data={"ada_score": ada_val, "rf_score": rf_val},
                            confidence=0.7
                        ))
                except (ValueError, TypeError):
                    pass
                    
        return evidence
    
    def _process_conservation_evidence(self, conservation_data: Dict[str, Any], analysis_type: AnalysisType) -> List[Evidence]:
        """Process conservation and constraint evidence"""
        evidence = []
        
        # GERP conservation
        gerp_score = conservation_data.get("gerp")
        if gerp_score is not None:
            try:
                gerp_val = float(gerp_score)
                if gerp_val >= 4.0:  # Highly conserved
                    evidence.append(Evidence(
                        code="OP3_CONSERVATION",
                        score=1,
                        guideline="VICC_2022_ENHANCED",
                        source_kb="GERP_VEP",
                        description=f"Highly conserved position (GERP: {gerp_val:.2f})",
                        data={"gerp_score": gerp_val},
                        confidence=0.7
                    ))
            except (ValueError, TypeError):
                pass
                
        # LoFtool gene constraint
        loftool_score = conservation_data.get("loftool")
        if loftool_score is not None:
            try:
                loftool_val = float(loftool_score)
                if loftool_val <= 0.1:  # Loss-of-function intolerant gene
                    evidence.append(Evidence(
                        code="OP4_GENE_CONSTRAINT",
                        score=1,
                        guideline="VICC_2022_ENHANCED",
                        source_kb="LoFtool_VEP",
                        description=f"Gene is loss-of-function intolerant (LoFtool: {loftool_val:.3f})",
                        data={"loftool_score": loftool_val},
                        confidence=0.8
                    ))
            except (ValueError, TypeError):
                pass
                
        return evidence
    
    def _generate_consensus_evidence(self, pathogenicity_scores: Dict[str, Any], analysis_type: AnalysisType) -> List[Evidence]:
        """Generate consensus evidence from multiple predictors"""
        evidence = []
        
        # Count pathogenic vs benign predictions
        pathogenic_predictors = []
        benign_predictors = []
        
        predictor_thresholds = {
            "alphamissense": 0.564,
            "revel": 0.5, 
            "primateai": 0.8,
            "eve": 0.5,
            "varity": 0.5,
            "bayesdel": 0.5,
            "clinpred": 0.5
        }
        
        for predictor, threshold in predictor_thresholds.items():
            if predictor in pathogenicity_scores:
                score_data = pathogenicity_scores[predictor]
                score = score_data.get("score")
                
                if score is not None:
                    try:
                        score_val = float(score)
                        if score_val >= threshold:
                            pathogenic_predictors.append(predictor)
                        elif score_val <= (1 - threshold):
                            benign_predictors.append(predictor)
                    except (ValueError, TypeError):
                        continue
                        
        total_predictors = len(pathogenic_predictors) + len(benign_predictors)
        
        if total_predictors >= 3:  # Require at least 3 predictors for consensus
            pathogenic_ratio = len(pathogenic_predictors) / total_predictors
            
            if pathogenic_ratio >= 0.75:  # Strong consensus pathogenic
                evidence.append(Evidence(
                    code="OP1_CONSENSUS",
                    score=2,
                    guideline="VICC_2022_ENHANCED",
                    source_kb="Consensus_Pathogenicity",
                    description=f"Strong consensus for pathogenic effect ({len(pathogenic_predictors)}/{total_predictors} predictors)",
                    data={"pathogenic_predictors": pathogenic_predictors, "total_predictors": total_predictors},
                    confidence=0.85
                ))
            elif pathogenic_ratio <= 0.25:  # Strong consensus benign
                evidence.append(Evidence(
                    code="SBP1_CONSENSUS",
                    score=-2,
                    guideline="VICC_2022_ENHANCED", 
                    source_kb="Consensus_Pathogenicity",
                    description=f"Strong consensus for benign effect ({len(benign_predictors)}/{total_predictors} predictors)",
                    data={"benign_predictors": benign_predictors, "total_predictors": total_predictors},
                    confidence=0.85
                ))
                
        return evidence
    
    def _get_clinical_evidence(self, variant: VariantAnnotation, cancer_type: str, analysis_type: AnalysisType) -> List[Evidence]:
        """Generate clinical evidence from CIViC and OncoKB with comprehensive variant matching"""
        evidence = []
        
        # CIViC evidence (existing logic)
        for civic_item in variant.civic_evidence:
            evidence_level = civic_item.get('evidence_level', '')
            
            if evidence_level in ['A', 'B']:  # High-level evidence
                evidence.append(Evidence(
                    code="OS2",
                    score=4,
                    guideline="VICC_2022",
                    source_kb="CIViC",
                    description=f"High-level clinical evidence (Level {evidence_level}) from CIViC",
                    data={"civic_evidence": civic_item},
                    confidence=0.9
                ))
            
            elif evidence_level in ['C', 'D']:  # Lower-level evidence
                evidence.append(Evidence(
                    code="OM2",
                    score=2,
                    guideline="VICC_2022",
                    source_kb="CIViC",
                    description=f"Clinical evidence (Level {evidence_level}) from CIViC",
                    data={"civic_evidence": civic_item},
                    confidence=0.7
                ))
        
        # Enhanced OncoKB evidence using new variant-drug-cancer associations
        oncokb_evidence = self._get_oncokb_variant_evidence(variant, cancer_type)
        evidence.extend(oncokb_evidence)
        
        return evidence
    
    def _get_oncokb_variant_evidence(self, variant: VariantAnnotation, cancer_type: str) -> List[Evidence]:
        """Generate comprehensive OncoKB evidence using variant-drug-cancer associations"""
        evidence = []
        
        # Get OncoKB variant data from cache
        oncokb_variants = _KB_CACHE.get('oncokb_variants', {})
        oncokb_levels = _KB_CACHE.get('oncokb_evidence_levels', {})
        
        gene = variant.gene_symbol
        hgvs_p = variant.hgvs_p or ""
        
        # Try to match variant using different strategies
        matched_variants = []
        
        # Strategy 1: Direct HGVS protein match
        if hgvs_p:
            # Extract change from HGVS (e.g., p.Val600Glu -> V600E)
            hgvs_simplified = self._simplify_hgvs(hgvs_p)
            variant_key = f"{gene}:{hgvs_simplified}"
            if variant_key in oncokb_variants:
                matched_variants.append((variant_key, oncokb_variants[variant_key], "exact_hgvs"))
        
        # Strategy 2: Common variant name patterns  
        if hgvs_p:
            # Try V600E style notation
            alt_notation = self._hgvs_to_short_form(hgvs_p)
            if alt_notation:
                variant_key = f"{gene}:{alt_notation}"
                if variant_key in oncokb_variants:
                    matched_variants.append((variant_key, oncokb_variants[variant_key], "short_form"))
        
        # Strategy 3: Gene-level mutations (broader matching)
        gene_patterns = [
            f"{gene}:Activating Mutations",
            f"{gene}:Oncogenic Mutations", 
            f"{gene}:Mutation",
            f"{gene}:Any"
        ]
        
        for pattern in gene_patterns:
            if pattern in oncokb_variants:
                matched_variants.append((pattern, oncokb_variants[pattern], "gene_level"))
                break  # Take first match to avoid duplicates
        
        # Generate evidence for each match
        for variant_key, variant_data, match_type in matched_variants:
            evidence_items = variant_data.get('evidence_items', [])
            
            for item in evidence_items:
                level = item.get('level', '')
                item_cancer_type = item.get('cancer_type', '').lower()
                drugs = item.get('drugs', '')
                
                # Check cancer type match (exact or broad)
                cancer_match = (
                    cancer_type.lower() in item_cancer_type or
                    item_cancer_type in cancer_type.lower() or
                    'all tumors' in item_cancer_type or
                    'all solid tumors' in item_cancer_type
                )
                
                # Create evidence based on OncoKB level
                if level == '1' and cancer_match:
                    evidence.append(Evidence(
                        code="ONCOKB_LEVEL_1",
                        score=0,  # AMP tier assignment
                        guideline="OncoKB",
                        source_kb="OncoKB",
                        description=f"FDA-approved therapy: {drugs} for {gene} {variant_data['alteration']} in {item_cancer_type}",
                        data={
                            "oncokb_level": "LEVEL_1",
                            "alteration": variant_data['alteration'],
                            "drugs": drugs,
                            "cancer_type": item_cancer_type,
                            "match_type": match_type
                        },
                        confidence=0.95
                    ))
                
                elif level == '2' and cancer_match:
                    evidence.append(Evidence(
                        code="ONCOKB_LEVEL_2",
                        score=0,  # AMP tier assignment
                        guideline="OncoKB", 
                        source_kb="OncoKB",
                        description=f"Standard care therapy: {drugs} for {gene} {variant_data['alteration']} in {item_cancer_type}",
                        data={
                            "oncokb_level": "LEVEL_2",
                            "alteration": variant_data['alteration'],
                            "drugs": drugs,
                            "cancer_type": item_cancer_type,
                            "match_type": match_type
                        },
                        confidence=0.9
                    ))
                
                elif level in ['3A', '3B'] and cancer_match:
                    evidence.append(Evidence(
                        code="ONCOKB_LEVEL_3",
                        score=2,  # VICC moderate evidence
                        guideline="OncoKB",
                        source_kb="OncoKB", 
                        description=f"Clinical evidence: {drugs} for {gene} {variant_data['alteration']} in {item_cancer_type}",
                        data={
                            "oncokb_level": f"LEVEL_{level}",
                            "alteration": variant_data['alteration'],
                            "drugs": drugs,
                            "cancer_type": item_cancer_type,
                            "match_type": match_type
                        },
                        confidence=0.8
                    ))
                
                elif level == '4':
                    evidence.append(Evidence(
                        code="ONCOKB_LEVEL_4", 
                        score=1,  # VICC supporting evidence
                        guideline="OncoKB",
                        source_kb="OncoKB",
                        description=f"Biological evidence: {drugs} for {gene} {variant_data['alteration']}",
                        data={
                            "oncokb_level": "LEVEL_4",
                            "alteration": variant_data['alteration'],
                            "drugs": drugs,
                            "match_type": match_type
                        },
                        confidence=0.7
                    ))
        
        return evidence
    
    def _simplify_hgvs(self, hgvs_p: str) -> str:
        """Simplify HGVS protein notation for matching"""
        if not hgvs_p:
            return ""
        
        # Remove p. prefix and transcript info
        simplified = hgvs_p
        if ":" in simplified:
            simplified = simplified.split(":")[-1]
        if simplified.startswith("p."):
            simplified = simplified[2:]
        
        return simplified
    
    def _hgvs_to_short_form(self, hgvs_p: str) -> str:
        """Convert HGVS to short form (e.g., p.Val600Glu -> V600E)"""
        import re
        
        if not hgvs_p:
            return ""
        
        # Extract from HGVS like p.Val600Glu
        match = re.search(r'p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})', hgvs_p)
        if match:
            aa_from_long, pos, aa_to_long = match.groups()
            
            # Convert to single letter amino acid codes
            aa_map = {
                'Ala': 'A', 'Arg': 'R', 'Asn': 'N', 'Asp': 'D', 'Cys': 'C',
                'Glu': 'E', 'Gln': 'Q', 'Gly': 'G', 'His': 'H', 'Ile': 'I',
                'Leu': 'L', 'Lys': 'K', 'Met': 'M', 'Phe': 'F', 'Pro': 'P',
                'Ser': 'S', 'Thr': 'T', 'Trp': 'W', 'Tyr': 'Y', 'Val': 'V'
            }
            
            aa_from = aa_map.get(aa_from_long, aa_from_long)
            aa_to = aa_map.get(aa_to_long, aa_to_long)
            
            return f"{aa_from}{pos}{aa_to}"
        
        return ""
    
    def _get_domain_evidence(self, variant: VariantAnnotation, analysis_type: AnalysisType) -> List[Evidence]:
        """Generate protein domain evidence"""
        evidence = []
        
        gene = variant.gene_symbol
        domains = _KB_CACHE.get('oncovi_domains', {}).get(gene, [])
        
        if variant.hgvs_p and domains:
            # Extract amino acid position from HGVS
            # This is a simplified extraction - would need more robust parsing
            try:
                import re
                pos_match = re.search(r'(\d+)', variant.hgvs_p)
                if pos_match:
                    aa_position = int(pos_match.group(1))
                    
                    for domain in domains:
                        if domain['start'] <= aa_position <= domain['end']:
                            importance = domain.get('importance', 'unknown')
                            
                            if importance == 'critical':
                                evidence.append(Evidence(
                                    code="OM1",
                                    score=2,
                                    guideline="VICC_2022",
                                    source_kb="OncoVI_Domains",
                                    description=f"Variant in critical functional domain: {domain['domain']}",
                                    data={"domain": domain['domain'], "position": aa_position},
                                    confidence=0.8
                                ))
                            break
            except Exception:
                pass  # Skip domain analysis if parsing fails
        
        return evidence
    
    def _apply_tumor_only_confidence_penalty(self, evidence_list: List[Evidence]) -> List[Evidence]:
        """
        Apply confidence penalty for tumor-only analysis per TN_VERSUS_TO.md specifications
        
        Args:
            evidence_list: List of evidence items
            
        Returns:
            Evidence list with adjusted confidence scores
        """
        penalty_rate = 0.2  # 20% confidence reduction for TO as per config
        
        for evidence in evidence_list:
            if evidence.confidence is not None:
                # Different penalties based on evidence type
                if evidence.source_kb in ["gnomAD", "dbSNP"]:
                    # Population frequency remains high confidence (critical filter)
                    continue
                elif evidence.source_kb in ["ClinVar"]:
                    # ClinVar ambiguous interpretation - larger penalty
                    evidence.confidence = max(0.1, evidence.confidence - 0.3)
                    evidence.description += " (AMBIGUOUS INTERPRETATION in tumor-only analysis)"
                elif evidence.source_kb in ["OncoKB", "CIViC", "COSMIC"]:
                    # Somatic/cancer-specific - standard penalty
                    evidence.confidence = max(0.1, evidence.confidence - penalty_rate)
                    evidence.description += " (assuming somatic origin)"
                else:
                    # General penalty for other sources
                    evidence.confidence = max(0.1, evidence.confidence - penalty_rate)
                
                evidence.analysis_type_adjusted = True
        
        return evidence_list
    
    def calculate_vicc_score(self, evidence_list: List[Evidence]) -> VICCScoring:
        """Calculate VICC/CGC 2022 oncogenicity score"""
        scoring = VICCScoring()
        
        for evidence in evidence_list:
            if evidence.guideline == "VICC_2022":
                # Map evidence codes to scoring fields
                if evidence.code == "OVS1":
                    scoring.ovs1_score = evidence.score
                elif evidence.code == "OS1":
                    scoring.os1_score = evidence.score
                elif evidence.code == "OS2":
                    scoring.os2_score = evidence.score
                elif evidence.code == "OS3":
                    scoring.os3_score = evidence.score
                elif evidence.code == "OM1":
                    scoring.om1_score = evidence.score
                elif evidence.code == "OM2":
                    scoring.om2_score = evidence.score
                elif evidence.code == "OM3":
                    scoring.om3_score = evidence.score
                elif evidence.code == "OM4":
                    scoring.om4_score = evidence.score
                elif evidence.code == "OP1":
                    scoring.op1_score = evidence.score
                elif evidence.code == "OP2":
                    scoring.op2_score = evidence.score
                elif evidence.code == "OP3":
                    scoring.op3_score = evidence.score
                elif evidence.code == "OP4":
                    scoring.op4_score = evidence.score
                elif evidence.code == "SBVS1":
                    scoring.sbvs1_score = evidence.score
                elif evidence.code == "SBS1":
                    scoring.sbs1_score = evidence.score
                elif evidence.code == "SBS2":
                    scoring.sbs2_score = evidence.score
                elif evidence.code == "SBP1":
                    scoring.sbp1_score = evidence.score
        
        # Calculate total score
        scoring.total_score = (
            scoring.ovs1_score + scoring.os1_score + scoring.os2_score + scoring.os3_score +
            scoring.om1_score + scoring.om2_score + scoring.om3_score + scoring.om4_score +
            scoring.op1_score + scoring.op2_score + scoring.op3_score + scoring.op4_score +
            scoring.sbvs1_score + scoring.sbs1_score + scoring.sbs2_score + scoring.sbp1_score
        )
        
        # Assign classification based on total score
        if scoring.total_score >= 7:
            scoring.classification = VICCOncogenicity.ONCOGENIC
        elif scoring.total_score >= 4:
            scoring.classification = VICCOncogenicity.LIKELY_ONCOGENIC
        elif scoring.total_score <= -6:
            scoring.classification = VICCOncogenicity.BENIGN
        elif scoring.total_score <= -2:
            scoring.classification = VICCOncogenicity.LIKELY_BENIGN
        else:
            scoring.classification = VICCOncogenicity.UNCERTAIN_SIGNIFICANCE
        
        return scoring
    
    def calculate_amp_score(self, evidence_list: List[Evidence], cancer_type: str) -> AMPScoring:
        """Calculate AMP/ASCO/CAP 2017 multi-context therapeutic actionability score"""
        
        # Analyze evidence for each actionability context
        therapeutic_evidence = [e for e in evidence_list if self._is_evidence_relevant_to_context(e, ActionabilityType.THERAPEUTIC)]
        diagnostic_evidence = [e for e in evidence_list if self._is_evidence_relevant_to_context(e, ActionabilityType.DIAGNOSTIC)]
        prognostic_evidence = [e for e in evidence_list if self._is_evidence_relevant_to_context(e, ActionabilityType.PROGNOSTIC)]
        
        # Determine cancer type specificity
        cancer_type_specific = self._is_evidence_cancer_type_specific(evidence_list, cancer_type)
        related_cancer_types = self._get_related_cancer_types(evidence_list)
        
        # Calculate context-specific tier assignments
        therapeutic_tier = None
        diagnostic_tier = None
        prognostic_tier = None
        
        if therapeutic_evidence:
            therapeutic_tier = self._calculate_context_tier(therapeutic_evidence, ActionabilityType.THERAPEUTIC, cancer_type_specific)
        
        if diagnostic_evidence:
            diagnostic_tier = self._calculate_context_tier(diagnostic_evidence, ActionabilityType.DIAGNOSTIC, cancer_type_specific)
        
        if prognostic_evidence:
            prognostic_tier = self._calculate_context_tier(prognostic_evidence, ActionabilityType.PROGNOSTIC, cancer_type_specific)
        
        # Calculate overall confidence and completeness
        overall_confidence = self._calculate_overall_confidence([therapeutic_tier, diagnostic_tier, prognostic_tier])
        evidence_completeness = self._calculate_evidence_completeness(evidence_list)
        
        return AMPScoring(
            therapeutic_tier=therapeutic_tier,
            diagnostic_tier=diagnostic_tier, 
            prognostic_tier=prognostic_tier,
            cancer_type_specific=cancer_type_specific,
            related_cancer_types=related_cancer_types,
            overall_confidence=overall_confidence,
            evidence_completeness=evidence_completeness
        )
    
    def _is_evidence_relevant_to_context(self, evidence: Evidence, context: ActionabilityType) -> bool:
        """Determine if evidence is relevant to a specific actionability context"""
        description = evidence.description.lower()
        
        if context == ActionabilityType.THERAPEUTIC:
            return any(term in description for term in ["therapy", "therapeutic", "treatment", "drug", "response", "resistance"])
        elif context == ActionabilityType.DIAGNOSTIC:
            return any(term in description for term in ["diagnostic", "diagnosis", "classification", "subtype"])
        elif context == ActionabilityType.PROGNOSTIC:
            return any(term in description for term in ["prognosis", "prognostic", "outcome", "survival", "recurrence"])
        
        # Default: therapeutic evidence
        return context == ActionabilityType.THERAPEUTIC
    
    def _is_evidence_cancer_type_specific(self, evidence_list: List[Evidence], cancer_type: str) -> bool:
        """Check if evidence is specific to the given cancer type"""
        cancer_specific_evidence = [e for e in evidence_list 
                                  if cancer_type.lower() in e.description.lower() 
                                  or e.data.get("cancer_type_specific", False)]
        return len(cancer_specific_evidence) > 0
    
    def _get_related_cancer_types(self, evidence_list: List[Evidence]) -> List[str]:
        """Extract related cancer types from evidence"""
        cancer_types = set()
        for evidence in evidence_list:
            if "cancer_types" in evidence.data and isinstance(evidence.data["cancer_types"], list):
                cancer_types.update(evidence.data["cancer_types"])
        return list(cancer_types)
    
    def _calculate_context_tier(self, context_evidence: List[Evidence], context: ActionabilityType, cancer_type_specific: bool) -> ContextSpecificTierAssignment:
        """Calculate tier assignment for a specific context"""
        
        # Analyze evidence strength
        has_fda_approved = any("FDA" in e.description or e.code == "FDA_APPROVED" for e in context_evidence)
        has_guidelines = any("guideline" in e.description.lower() or e.code == "STANDARD_CARE" for e in context_evidence)
        has_expert_consensus = any("expert consensus" in e.description.lower() for e in context_evidence)
        has_multiple_studies = any("multiple studies" in e.description.lower() for e in context_evidence)
        has_case_reports = any("case report" in e.description.lower() for e in context_evidence)
        has_investigational = any(term in e.description.lower() for e in context_evidence for term in ["investigational", "clinical trial", "experimental"])
        
        # Determine evidence strength and tier level
        if has_fda_approved:
            evidence_strength = EvidenceStrength.FDA_APPROVED
            tier_level = AMPTierLevel.TIER_IA
            confidence = 0.95
        elif has_guidelines:
            evidence_strength = EvidenceStrength.PROFESSIONAL_GUIDELINES
            tier_level = AMPTierLevel.TIER_IA
            confidence = 0.9
        elif has_expert_consensus:
            evidence_strength = EvidenceStrength.EXPERT_CONSENSUS
            tier_level = AMPTierLevel.TIER_IB
            confidence = 0.85
        elif has_multiple_studies:
            evidence_strength = EvidenceStrength.MULTIPLE_SMALL_STUDIES
            tier_level = AMPTierLevel.TIER_IIC
            confidence = 0.75
        elif has_case_reports:
            evidence_strength = EvidenceStrength.CASE_REPORTS
            tier_level = AMPTierLevel.TIER_IID
            confidence = 0.6
        elif has_investigational:
            evidence_strength = EvidenceStrength.MULTIPLE_SMALL_STUDIES  # Investigational evidence
            tier_level = AMPTierLevel.TIER_IIE
            confidence = 0.65
        else:
            evidence_strength = EvidenceStrength.PRECLINICAL
            tier_level = AMPTierLevel.TIER_III
            confidence = 0.5
        
        # Calculate evidence score
        evidence_score = len(context_evidence) / 10.0  # Normalize by expected evidence count
        evidence_score = min(1.0, evidence_score)
        
        # Adjust confidence based on cancer type specificity
        if cancer_type_specific:
            confidence = min(1.0, confidence + 0.05)
        
        return ContextSpecificTierAssignment(
            actionability_type=context,
            tier_level=tier_level,
            evidence_strength=evidence_strength,
            evidence_score=evidence_score,
            confidence_score=confidence,
            fda_approved=has_fda_approved,
            guideline_included=has_guidelines,
            expert_consensus=has_expert_consensus,
            cancer_type_specific=cancer_type_specific,
            supporting_studies=[e.description for e in context_evidence[:3]],
            evidence_summary=f"{len(context_evidence)} evidence items for {context.value} context"
        )
    
    def _calculate_overall_confidence(self, tier_assignments: List[Optional[ContextSpecificTierAssignment]]) -> float:
        """Calculate overall confidence across all context-specific tier assignments"""
        valid_assignments = [t for t in tier_assignments if t is not None]
        if not valid_assignments:
            return 0.0
        
        confidence_scores = [t.confidence_score for t in valid_assignments]
        return sum(confidence_scores) / len(confidence_scores)
    
    def _calculate_evidence_completeness(self, evidence_list: List[Evidence]) -> float:
        """Calculate evidence completeness across all contexts"""
        contexts = [ActionabilityType.THERAPEUTIC, ActionabilityType.DIAGNOSTIC, ActionabilityType.PROGNOSTIC]
        context_coverage = 0
        
        for context in contexts:
            relevant_evidence = [e for e in evidence_list if self._is_evidence_relevant_to_context(e, context)]
            if relevant_evidence:
                context_coverage += 1
        
        return context_coverage / len(contexts)
    
    def calculate_oncokb_score(self, evidence_list: List[Evidence], oncokb_data: Optional[Dict[str, Any]] = None) -> OncoKBScoring:
        """Calculate OncoKB therapeutic actionability score from evidence"""
        scoring = OncoKBScoring()
        
        # Extract OncoKB evidence from evidence list
        oncokb_evidence = [e for e in evidence_list if e.source_kb == "OncoKB"]
        
        if oncokb_evidence:
            # Find highest level evidence
            level_hierarchy = {
                "ONCOKB_LEVEL_1": (OncoKBLevel.LEVEL_1, 1),
                "ONCOKB_LEVEL_2": (OncoKBLevel.LEVEL_2A, 2), 
                "ONCOKB_LEVEL_3": (OncoKBLevel.LEVEL_3A, 3),
                "ONCOKB_LEVEL_4": (OncoKBLevel.LEVEL_4, 4)
            }
            
            highest_level = None
            highest_priority = 99
            fda_approved = []
            off_label = []
            investigational = []
            cancer_specific = False
            
            for evidence in oncokb_evidence:
                code = evidence.code
                if code in level_hierarchy:
                    level, priority = level_hierarchy[code]
                    if priority < highest_priority:
                        highest_level = level
                        highest_priority = priority
                
                # Extract therapy information from evidence data
                evidence_data = evidence.data or {}
                drugs = evidence_data.get('drugs', '')
                oncokb_level = evidence_data.get('oncokb_level', '')
                cancer_type = evidence_data.get('cancer_type', '')
                
                # Categorize therapies by level
                if oncokb_level == "LEVEL_1":
                    if drugs and drugs not in fda_approved:
                        fda_approved.append(drugs)
                    cancer_specific = True
                elif oncokb_level in ["LEVEL_2", "LEVEL_3A"]: 
                    if drugs and drugs not in off_label:
                        off_label.append(drugs)
                    cancer_specific = True
                elif oncokb_level in ["LEVEL_3B", "LEVEL_4"]:
                    if drugs and drugs not in investigational:
                        investigational.append(drugs)
                
                # Check for cancer type specificity
                if cancer_type and cancer_type.lower() not in ['all tumors', 'all solid tumors']:
                    cancer_specific = True
            
            # Set scoring properties
            scoring.therapeutic_level = highest_level
            scoring.fda_approved_therapy = fda_approved
            scoring.off_label_therapy = off_label  
            scoring.investigational_therapy = investigational
            scoring.cancer_type_specific = cancer_specific
            scoring.any_cancer_type = not cancer_specific
            
            # Set oncogenicity based on level
            if highest_level in [OncoKBLevel.LEVEL_1, OncoKBLevel.LEVEL_2A]:
                scoring.oncogenicity = "Oncogenic"
            elif highest_level in [OncoKBLevel.LEVEL_3A, OncoKBLevel.LEVEL_3B]:
                scoring.oncogenicity = "Likely Oncogenic"
            else:
                scoring.oncogenicity = "Unknown Significance"
        
        # Fallback to legacy method if provided
        elif oncokb_data:
            scoring.oncogenicity = oncokb_data.get('oncogenicity')
            
            level_str = oncokb_data.get('therapeutic_level', '')
            if level_str:
                try:
                    scoring.therapeutic_level = OncoKBLevel(level_str)
                except ValueError:
                    pass
            
            scoring.fda_approved_therapy = oncokb_data.get('fda_approved_drugs', [])
            scoring.off_label_therapy = oncokb_data.get('off_label_drugs', [])
            scoring.investigational_therapy = oncokb_data.get('investigational_drugs', [])
            scoring.cancer_type_specific = oncokb_data.get('cancer_type_specific', False)
        
        return scoring
    
    def validate_cancer_type(self, cancer_type: str) -> Dict[str, Any]:
        """Validate cancer type against OncoTree TSV data with enhanced tissue-specific matching"""
        oncotree_data = _KB_CACHE.get('oncotree_data', {})
        if not oncotree_data:
            return {'valid': False, 'message': 'OncoTree data not available'}
        
        code_map = oncotree_data.get('code_map', {})
        hierarchy_map = oncotree_data.get('hierarchy_map', {})
        tissue_map = oncotree_data.get('tissue_map', {})
        tissue_files = oncotree_data.get('tissue_files', {})
        
        # Check direct match (case-insensitive)
        cancer_upper = cancer_type.upper()
        if cancer_upper in code_map:
            return {
                'valid': True,
                'code': cancer_upper,
                'name': code_map[cancer_upper]['name'],
                'main_type': code_map[cancer_upper]['main_type'],
                'tissue': code_map[cancer_upper]['tissue'],
                'level': code_map[cancer_upper]['level'],
                'hierarchy': hierarchy_map.get(cancer_upper, []),
                'external_references': code_map[cancer_upper].get('external_references', ''),
                'matched_by': 'code'
            }
        
        # Check name-based matching with priority scoring
        best_match = None
        best_score = 0
        
        for code, info in code_map.items():
            score = 0
            cancer_lower = cancer_type.lower()
            
            # Exact name match (highest priority)
            if cancer_lower == info['name'].lower():
                score = 100
            # Main type exact match
            elif cancer_lower == info['main_type'].lower():
                score = 90
            # Tissue exact match  
            elif cancer_lower == info['tissue'].lower():
                score = 80
            # Partial name match
            elif cancer_lower in info['name'].lower():
                score = 70
            # Partial main type match
            elif cancer_lower in info['main_type'].lower():
                score = 60
            # Partial tissue match
            elif cancer_lower in info['tissue'].lower():
                score = 50
            
            if score > best_score:
                best_score = score
                best_match = {
                    'valid': True,
                    'code': code,
                    'name': info['name'],
                    'main_type': info['main_type'],
                    'tissue': info['tissue'],
                    'level': info['level'],
                    'hierarchy': hierarchy_map.get(code, []),
                    'external_references': info.get('external_references', ''),
                    'matched_by': 'name_similarity',
                    'match_score': score
                }
        
        if best_match and best_score >= 50:
            return best_match
        
        # Check tissue-specific files for additional context
        suggestions = []
        for tissue, codes in tissue_map.items():
            if cancer_type.lower() in tissue.lower():
                suggestions.extend(codes[:3])  # Top 3 suggestions per tissue
        
        return {
            'valid': False, 
            'message': f'Cancer type "{cancer_type}" not found in OncoTree',
            'suggestions': suggestions[:5],  # Top 5 suggestions total
            'total_available_types': len(code_map)
        }
    
    def get_tissue_cancer_types(self, tissue: str) -> Dict[str, Any]:
        """Get all cancer types for a specific tissue using tissue-specific TSV files"""
        oncotree_data = _KB_CACHE.get('oncotree_data', {})
        if not oncotree_data:
            return {'tissue': tissue, 'cancer_types': [], 'message': 'OncoTree data not available'}
        
        tissue_files = oncotree_data.get('tissue_files', {})
        tissue_map = oncotree_data.get('tissue_map', {})
        
        # Find exact tissue match in tissue files
        tissue_upper = tissue.upper()
        if tissue_upper in tissue_files:
            tissue_data = tissue_files[tissue_upper]
            return {
                'tissue': tissue,
                'cancer_types': tissue_data,
                'count': len(tissue_data),
                'source': f'tissue_file_{tissue_upper}'
            }
        
        # Fallback to tissue map
        matching_tissues = []
        for tissue_name, codes in tissue_map.items():
            if tissue.lower() in tissue_name.lower():
                code_map = oncotree_data.get('code_map', {})
                tissue_types = []
                for code in codes:
                    if code in code_map:
                        tissue_types.append({
                            'code': code,
                            'name': code_map[code]['name'],
                            'main_type': code_map[code]['main_type'],
                            'level': code_map[code]['level']
                        })
                matching_tissues.append({
                    'tissue_name': tissue_name,
                    'cancer_types': tissue_types
                })
        
        return {
            'tissue': tissue,
            'matching_tissues': matching_tissues,
            'count': sum(len(t['cancer_types']) for t in matching_tissues)
        }
    
    def _get_clinvar_evidence(self, variant: VariantAnnotation, analysis_type: AnalysisType) -> List[Evidence]:
        """Generate ClinVar clinical significance evidence for tumor-only germline filtering"""
        evidence = []
        
        clinvar_data = _KB_CACHE.get('clinvar_data', {})
        if not clinvar_data:
            return evidence
        
        gene_symbol = variant.gene_symbol
        if not gene_symbol:
            return evidence
        
        pathogenic_variants = clinvar_data.get('pathogenic_variants', {})
        benign_variants = clinvar_data.get('benign_variants', {})
        
        # Check for pathogenic variants in this gene
        if gene_symbol in pathogenic_variants:
            pathogenic_count = len(pathogenic_variants[gene_symbol])
            
            # For tumor-only analysis, flag potential germline pathogenic variants
            if analysis_type == AnalysisType.TUMOR_ONLY:
                evidence.append(Evidence(
                    code="SBVS1",  # Strong benign supporting - tumor-only context
                    score=-2,  # Negative score for potential germline contamination
                    guideline="AMP_2017",
                    source_kb="ClinVar",
                    description=f"Gene {gene_symbol} has {pathogenic_count} pathogenic variants in ClinVar - "
                               f"potential germline contamination in tumor-only analysis",
                    data={
                        "pathogenic_variant_count": pathogenic_count,
                        "analysis_type": "tumor_only",
                        "germline_risk": True
                    },
                    confidence=0.6  # Lower confidence due to tumor-only limitations
                ))
            else:
                # For matched analysis, provide supporting evidence
                evidence.append(Evidence(
                    code="SP1",  # Supporting pathogenic
                    score=1,
                    guideline="AMP_2017", 
                    source_kb="ClinVar",
                    description=f"Gene {gene_symbol} has known pathogenic variants in ClinVar",
                    data={
                        "pathogenic_variant_count": pathogenic_count,
                        "analysis_type": "matched_normal"
                    },
                    confidence=0.8
                ))
        
        # Check for benign variants (generally supportive of variant tolerance)
        if gene_symbol in benign_variants:
            benign_count = len(benign_variants[gene_symbol])
            evidence.append(Evidence(
                code="SBP1",  # Supporting benign
                score=-1,
                guideline="AMP_2017",
                source_kb="ClinVar",
                description=f"Gene {gene_symbol} has {benign_count} benign variants in ClinVar",
                data={"benign_variant_count": benign_count},
                confidence=0.5
            ))
        
        return evidence


# Global instance
# Remove automatic initialization to prevent startup errors
# evidence_aggregator = EvidenceAggregator()