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
        
        # Load population frequency sources (handled by API clients)
        
        _KB_LOADED = True
        logger.info("Knowledge bases loaded successfully")
    
    def _load_oncokb_genes(self) -> Dict[str, Any]:
        """Load OncoKB gene annotations"""
        oncokb_path = self.kb_base_path / "oncokb"
        
        genes = {}
        if (oncokb_path / "cancerGeneList.txt").exists():
            df = pd.read_csv(oncokb_path / "cancerGeneList.txt", sep='\t')
            for _, row in df.iterrows():
                gene = row['Hugo Symbol']
                genes[gene] = {
                    'is_oncogene': 'Oncogene' in str(row.get('Oncogene', '')),
                    'is_tsg': 'TSG' in str(row.get('TSG', '')),
                    'oncokb_annotated': True
                }
        
        return genes
    
    def _load_oncokb_variants(self) -> List[Dict[str, Any]]:
        """Load OncoKB variant annotations"""
        # This would load from OncoKB allAnnotatedVariants.txt if available
        # For now, return empty list - will be populated by API calls
        return []
    
    def _load_civic_variants(self) -> Dict[str, Any]:
        """Load CIViC variant summaries"""
        civic_path = self.kb_base_path / "civic"
        variants = {}
        
        if (civic_path / "01-Jan-2024-VariantSummaries.tsv").exists():
            df = pd.read_csv(civic_path / "01-Jan-2024-VariantSummaries.tsv", sep='\t')
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
        civic_path = self.kb_base_path / "civic"
        evidence = {}
        
        if (civic_path / "01-Jan-2024-ClinicalEvidenceSummaries.tsv").exists():
            df = pd.read_csv(civic_path / "01-Jan-2024-ClinicalEvidenceSummaries.tsv", sep='\t')
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
        cosmic_path = self.kb_base_path / "cosmic"
        genes = {}
        
        if (cosmic_path / "cancer_gene_census.csv").exists():
            df = pd.read_csv(cosmic_path / "cancer_gene_census.csv")
            for _, row in df.iterrows():
                gene = row['Gene Symbol']
                genes[gene] = {
                    'role_in_cancer': row.get('Role in Cancer', ''),
                    'mutation_types': row.get('Mutation Types', ''),
                    'tumour_types_somatic': row.get('Tumour Types(Somatic)', ''),
                    'tumour_types_germline': row.get('Tumour Types(Germline)', ''),
                    'is_oncogene': 'oncogene' in str(row.get('Role in Cancer', '')).lower(),
                    'is_tsg': 'tsg' in str(row.get('Role in Cancer', '')).lower()
                }
        
        return genes
    
    def _load_cosmic_hotspots(self) -> List[Dict[str, Any]]:
        """Load COSMIC hotspots data"""
        cosmic_path = self.kb_base_path / "cancer_hotspots"
        hotspots = []
        
        # Load from multiple hotspot sources
        hotspot_files = [
            "hotspots_v2.xls",
            "hotspots_v2_indels.xls"
        ]
        
        for filename in hotspot_files:
            filepath = cosmic_path / filename
            if filepath.exists():
                try:
                    df = pd.read_excel(filepath)
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
        oncovi_path = self.kb_base_path / "oncovi"
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
        oncovi_path = self.kb_base_path / "oncovi"
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
        oncovi_path = self.kb_base_path / "oncovi"
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
        oncovi_path = self.kb_base_path / "oncovi"
        domains = {}
        
        if (oncovi_path / "protein_domains.tsv").exists():
            df = pd.read_csv(oncovi_path / "protein_domains.tsv", sep='\t')
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
        oncovi_path = self.kb_base_path / "oncovi"
        matrix = {}
        
        if (oncovi_path / "grantham_distance_matrix.txt").exists():
            with open(oncovi_path / "grantham_distance_matrix.txt", 'r') as f:
                lines = f.readlines()
                # Parse the matrix format
                # This would depend on the exact format of the file
                pass
        
        return matrix


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
                           tumor_purity: Optional[float] = None) -> DynamicSomaticConfidence:
        """
        Calculate Dynamic Somatic Confidence score using multiple evidence modules
        
        Args:
            variant: Variant annotation with population frequencies, etc.
            evidence_list: Evidence from knowledge bases
            tumor_purity: Estimated tumor purity (0-1)
            
        Returns:
            DynamicSomaticConfidence scoring object
        """
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
        """Module 1: VAF/Purity consistency scoring"""
        if tumor_purity is None or not hasattr(variant, 'vaf') or variant.vaf is None:
            return None
        
        vaf = variant.vaf
        purity = tumor_purity
        
        # Expected VAF for heterozygous somatic mutation
        expected_het_vaf = purity / 2
        # Expected VAF for homozygous/LOH somatic mutation
        expected_hom_vaf = purity
        
        # Calculate deviation from expected somatic VAF patterns
        het_deviation = abs(vaf - expected_het_vaf) / expected_het_vaf if expected_het_vaf > 0 else 1.0
        hom_deviation = abs(vaf - expected_hom_vaf) / expected_hom_vaf if expected_hom_vaf > 0 else 1.0
        
        # Take the better match (het or hom)
        min_deviation = min(het_deviation, hom_deviation)
        
        # Score based on deviation (lower deviation = higher confidence)
        if min_deviation < 0.2:  # Very close match
            return 0.9
        elif min_deviation < 0.5:  # Good match
            return 0.7
        elif min_deviation < 1.0:  # Moderate match (subclonal)
            return 0.5
        else:  # Poor match - suspicious
            return 0.2
    
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
        """Combine module scores into final DSC score"""
        scores = [prior_prob]  # Always have prior probability
        weights = [0.6]  # Base weight for prior probability
        
        if vaf_purity is not None:
            scores.append(vaf_purity)
            weights.append(0.3)  # VAF/purity gets significant weight
            weights[0] = 0.4  # Reduce prior prob weight
        
        if genomic_context is not None:
            scores.append(genomic_context)
            weights.append(0.2)
            # Adjust other weights proportionally
            total_weight = sum(weights)
            weights = [w * 0.8 / total_weight for w in weights]
            weights.append(0.2)
        
        # Weighted average
        return sum(score * weight for score, weight in zip(scores, weights))
    
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
        self.loader.load_all_kbs()
        self.dsc_calculator = DynamicSomaticConfidenceCalculator()
    
    def aggregate_evidence(self, variant_annotation: VariantAnnotation, cancer_type: str, 
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
        """Generate functional prediction evidence"""
        evidence = []
        
        # Aggregate computational predictions
        damaging_count = 0
        benign_count = 0
        total_predictions = 0
        
        for pred in variant.functional_predictions:
            total_predictions += 1
            
            if pred.prediction:
                if pred.prediction.lower() in ['damaging', 'deleterious', 'pathogenic']:
                    damaging_count += 1
                elif pred.prediction.lower() in ['benign', 'tolerated', 'neutral']:
                    benign_count += 1
        
        if total_predictions >= 2:  # Require at least 2 predictions
            # VICC OP1: Computational evidence supports damaging effect
            if damaging_count >= (total_predictions * 0.6):  # 60% consensus
                evidence.append(Evidence(
                    code="OP1",
                    score=1,
                    guideline="VICC_2022",
                    source_kb="Computational_Predictions",
                    description=f"Computational evidence supports damaging effect ({damaging_count}/{total_predictions} tools)",
                    data={"damaging_count": damaging_count, "total_predictions": total_predictions},
                    confidence=0.7
                ))
            
            # VICC SBP1: Computational evidence suggests benign
            elif benign_count >= (total_predictions * 0.6):  # 60% consensus
                evidence.append(Evidence(
                    code="SBP1",
                    score=-1,
                    guideline="VICC_2022",
                    source_kb="Computational_Predictions",
                    description=f"Computational evidence suggests benign effect ({benign_count}/{total_predictions} tools)",
                    data={"benign_count": benign_count, "total_predictions": total_predictions},
                    confidence=0.7
                ))
        
        return evidence
    
    def _get_clinical_evidence(self, variant: VariantAnnotation, cancer_type: str, analysis_type: AnalysisType) -> List[Evidence]:
        """Generate clinical evidence from CIViC and OncoKB"""
        evidence = []
        
        # CIViC evidence
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
        
        # OncoKB evidence
        if variant.oncokb_evidence:
            oncokb_level = variant.oncokb_evidence.get('therapeutic_level')
            if oncokb_level:
                if oncokb_level == 'Level 1':
                    evidence.append(Evidence(
                        code="FDA_APPROVED",
                        score=0,  # AMP scoring, not VICC
                        guideline="AMP_2017",
                        source_kb="OncoKB",
                        description="FDA-approved therapy available for this variant",
                        data={"oncokb_level": oncokb_level},
                        confidence=0.95
                    ))
                
                elif oncokb_level in ['Level 2A', 'Level 2B']:
                    evidence.append(Evidence(
                        code="STANDARD_CARE",
                        score=0,  # AMP scoring
                        guideline="AMP_2017",
                        source_kb="OncoKB",
                        description="Standard of care therapy available",
                        data={"oncokb_level": oncokb_level},
                        confidence=0.9
                    ))
        
        return evidence
    
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
    
    def calculate_oncokb_score(self, evidence_list: List[Evidence], oncokb_data: Optional[Dict[str, Any]]) -> OncoKBScoring:
        """Calculate OncoKB therapeutic actionability score"""
        scoring = OncoKBScoring()
        
        if oncokb_data:
            # Extract OncoKB information
            scoring.oncogenicity = oncokb_data.get('oncogenicity')
            
            # Map therapeutic level
            level_str = oncokb_data.get('therapeutic_level', '')
            if level_str:
                try:
                    scoring.therapeutic_level = OncoKBLevel(level_str)
                except ValueError:
                    pass  # Invalid level
            
            # Extract therapy information
            scoring.fda_approved_therapy = oncokb_data.get('fda_approved_drugs', [])
            scoring.off_label_therapy = oncokb_data.get('off_label_drugs', [])
            scoring.investigational_therapy = oncokb_data.get('investigational_drugs', [])
            
            scoring.cancer_type_specific = oncokb_data.get('cancer_type_specific', False)
        
        return scoring


# Global instance
evidence_aggregator = EvidenceAggregator()