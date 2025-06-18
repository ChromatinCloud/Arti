"""
CGC/VICC 2022 Oncogenicity Classification Implementation

Implements the Clinical Genome Resource (ClinGen) Cancer Variant Curation Expert Panel (CG-CV-VCEP)
and Variant Interpretation for Cancer Consortium (VICC) oncogenicity classification framework.

Based on: https://pubmed.ncbi.nlm.nih.gov/36063163/
"The ClinGen/CGC/VICC variant curation expert panel consensus recommendation for PTEN variant classification"
and subsequent expansions for general cancer variant classification.

This implementation leverages all available knowledge bases in .refs/ directory.
"""

from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd
import json
import logging

from .models import (
    VariantAnnotation, Evidence, PopulationFrequency, 
    HotspotEvidence, FunctionalEvidence
)

logger = logging.getLogger(__name__)


class OncogenicityCriteria(str, Enum):
    """CGC/VICC oncogenicity criteria codes"""
    # Oncogenic criteria
    OVS1 = "OVS1"  # Very Strong
    OS1 = "OS1"    # Strong
    OS2 = "OS2"    # Strong
    OS3 = "OS3"    # Strong
    OM1 = "OM1"    # Moderate
    OM2 = "OM2"    # Moderate
    OM3 = "OM3"    # Moderate
    OM4 = "OM4"    # Moderate
    OP1 = "OP1"    # Supporting
    OP2 = "OP2"    # Supporting
    OP3 = "OP3"    # Supporting
    OP4 = "OP4"    # Supporting
    
    # Benign criteria
    SBVS1 = "SBVS1"  # Benign Very Strong
    SBS1 = "SBS1"    # Benign Strong
    SBS2 = "SBS2"    # Benign Strong
    SBP1 = "SBP1"    # Benign Supporting
    SBP2 = "SBP2"    # Benign Supporting


class OncogenicityClassification(str, Enum):
    """Final oncogenicity classifications per CGC/VICC"""
    ONCOGENIC = "Oncogenic"
    LIKELY_ONCOGENIC = "Likely Oncogenic"
    VUS = "Variant of Uncertain Significance"
    LIKELY_BENIGN = "Likely Benign"
    BENIGN = "Benign"


@dataclass
class CriterionEvidence:
    """Evidence for a specific CGC/VICC criterion"""
    criterion: OncogenicityCriteria
    is_met: bool
    strength: str  # "Very Strong", "Strong", "Moderate", "Supporting"
    evidence_sources: List[Dict[str, any]] = field(default_factory=list)
    confidence: float = 0.0
    notes: Optional[str] = None


@dataclass
class OncogenicityResult:
    """Complete result of CGC/VICC oncogenicity classification"""
    classification: OncogenicityClassification
    criteria_met: List[CriterionEvidence]
    evidence_summary: Dict[str, int]
    confidence_score: float
    classification_rationale: str
    metadata: Dict[str, any] = field(default_factory=dict)


class CGCVICCClassifier:
    """
    Implements CGC/VICC 2022 oncogenicity classification framework
    using all available knowledge bases
    """
    
    def __init__(self, kb_path: Path = Path("./.refs")):
        self.kb_path = kb_path
        self._load_knowledge_bases()
        
    def _load_knowledge_bases(self):
        """Load all relevant knowledge bases for classification"""
        logger.info("Loading knowledge bases for CGC/VICC classification")
        
        # Cancer hotspots
        self.hotspots = self._load_hotspots()
        
        # Population frequencies
        self.population_dbs = self._load_population_frequencies()
        
        # Clinical evidence
        self.clinical_evidence = self._load_clinical_evidence()
        
        # Cancer gene census
        self.cancer_genes = self._load_cancer_genes()
        
        # Functional predictions
        self.functional_predictions = self._load_functional_predictions()
        
    def _load_hotspots(self) -> Dict:
        """Load cancer hotspot databases"""
        hotspots = {}
        
        # MSK Cancer Hotspots
        msk_path = self.kb_path / "hotspots/msk_hotspots/cancer_hotspots_v2.5.tsv"
        if msk_path.exists():
            hotspots['msk'] = pd.read_csv(msk_path, sep='\t')
            logger.info(f"Loaded MSK hotspots: {len(hotspots['msk'])} entries")
        
        # OncoVI hotspots
        oncovi_single = self.kb_path / "hotspots/oncovi_hotspots/single_residue_hotspots.tsv"
        if oncovi_single.exists():
            hotspots['oncovi_single'] = pd.read_csv(oncovi_single, sep='\t')
            
        oncovi_indel = self.kb_path / "hotspots/oncovi_hotspots/indel_hotspots.tsv"
        if oncovi_indel.exists():
            hotspots['oncovi_indel'] = pd.read_csv(oncovi_indel, sep='\t')
            
        # COSMIC hotspots (if available)
        cosmic_path = self.kb_path / "cosmic/cosmic_hotspots.tsv"
        if cosmic_path.exists():
            hotspots['cosmic'] = pd.read_csv(cosmic_path, sep='\t')
            
        return hotspots
    
    def _load_population_frequencies(self) -> Dict:
        """Load population frequency databases"""
        pop_dbs = {}
        
        # gnomAD - the gold standard
        gnomad_path = self.kb_path / "population_frequencies/gnomad"
        if gnomad_path.exists():
            # Would load gnomAD VCF or processed files here
            pop_dbs['gnomad'] = {"path": gnomad_path, "loaded": True}
            
        return pop_dbs
    
    def _load_clinical_evidence(self) -> Dict:
        """Load clinical evidence databases"""
        clinical = {}
        
        # OncoKB
        oncokb_path = self.kb_path / "clinical_evidence/oncokb/oncokb_data/oncokb_all_annotated_variants.tsv"
        if oncokb_path.exists():
            clinical['oncokb'] = pd.read_csv(oncokb_path, sep='\t')
            
        # CIViC
        civic_path = self.kb_path / "clinical_evidence/civic/civic_variants.tsv"
        if civic_path.exists():
            clinical['civic'] = pd.read_csv(civic_path, sep='\t')
            
        # ClinVar (somatic)
        clinvar_path = self.kb_path / "clinical_evidence/clinvar/clinvar_filtered_variants.tsv"
        if clinvar_path.exists():
            clinical['clinvar'] = pd.read_csv(clinvar_path, sep='\t')
            
        return clinical
    
    def _load_cancer_genes(self) -> Dict:
        """Load cancer gene databases"""
        genes = {}
        
        # COSMIC Cancer Gene Census
        cgc_path = self.kb_path / "cgc"
        if cgc_path.exists():
            # Load CGC data
            genes['cgc'] = {"path": cgc_path}
            
        # OncoKB cancer genes
        oncokb_genes = self.kb_path / "clinical_evidence/oncokb/oncokb_curated_genes.txt"
        if oncokb_genes.exists():
            with open(oncokb_genes) as f:
                genes['oncokb_genes'] = set(line.strip() for line in f)
                
        return genes
    
    def _load_functional_predictions(self) -> Dict:
        """Load functional prediction scores"""
        predictions = {}
        
        # AlphaMissense
        am_path = self.kb_path / "alphamissense"
        if am_path.exists():
            predictions['alphamissense'] = {"path": am_path}
            
        # SpliceAI
        spliceai_path = self.kb_path / "spliceai"
        if spliceai_path.exists():
            predictions['spliceai'] = {"path": spliceai_path}
            
        return predictions
    
    def classify_variant(self, 
                        variant: VariantAnnotation,
                        cancer_type: Optional[str] = None) -> OncogenicityResult:
        """
        Classify variant oncogenicity using CGC/VICC framework
        
        Args:
            variant: Variant annotation with all available data
            cancer_type: Specific cancer type for context
            
        Returns:
            OncogenicityResult with classification and evidence
        """
        # Evaluate all criteria
        criteria_results = self._evaluate_all_criteria(variant, cancer_type)
        
        # Apply combination rules to determine classification
        classification = self._apply_combination_rules(criteria_results)
        
        # Calculate confidence based on evidence strength
        confidence = self._calculate_confidence(criteria_results)
        
        # Generate classification rationale
        rationale = self._generate_rationale(classification, criteria_results)
        
        # Summarize evidence
        evidence_summary = self._summarize_evidence(criteria_results)
        
        return OncogenicityResult(
            classification=classification,
            criteria_met=[c for c in criteria_results if c.is_met],
            evidence_summary=evidence_summary,
            confidence_score=confidence,
            classification_rationale=rationale,
            metadata={
                "classifier_version": "CGC/VICC 2022",
                "cancer_type": cancer_type,
                "variant": f"{variant.gene_symbol}:{variant.hgvs_p}"
            }
        )
    
    def _evaluate_all_criteria(self, 
                              variant: VariantAnnotation,
                              cancer_type: Optional[str]) -> List[CriterionEvidence]:
        """Evaluate all CGC/VICC criteria for the variant"""
        results = []
        
        # Oncogenic criteria
        results.append(self._evaluate_OVS1(variant))
        results.append(self._evaluate_OS1(variant))
        results.append(self._evaluate_OS2(variant))
        results.append(self._evaluate_OS3(variant, cancer_type))
        results.append(self._evaluate_OM1(variant))
        results.append(self._evaluate_OM2(variant))
        results.append(self._evaluate_OM3(variant, cancer_type))
        results.append(self._evaluate_OM4(variant))
        results.append(self._evaluate_OP1(variant))
        results.append(self._evaluate_OP2(variant))
        results.append(self._evaluate_OP3(variant, cancer_type))
        results.append(self._evaluate_OP4(variant))
        
        # Benign criteria
        results.append(self._evaluate_SBVS1(variant))
        results.append(self._evaluate_SBS1(variant))
        results.append(self._evaluate_SBS2(variant))
        results.append(self._evaluate_SBP1(variant))
        results.append(self._evaluate_SBP2(variant))
        
        return [r for r in results if r is not None]
    
    def _evaluate_OVS1(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        OVS1: Null variant in tumor suppressor gene with LOF as a mechanism
        """
        is_null = any(c in ["stop_gained", "frameshift_variant", "splice_acceptor_variant", 
                           "splice_donor_variant"] for c in variant.consequence)
        
        is_tsg = (variant.is_tumor_suppressor or 
                 variant.gene_symbol in self.cancer_genes.get('tsg_list', []))
        
        if is_null and is_tsg:
            return CriterionEvidence(
                criterion=OncogenicityCriteria.OVS1,
                is_met=True,
                strength="Very Strong",
                evidence_sources=[{
                    "source": "VEP + CGC",
                    "consequence": variant.consequence,
                    "tsg_evidence": "Known tumor suppressor"
                }],
                confidence=0.95
            )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OVS1,
            is_met=False,
            strength="Very Strong"
        )
    
    def _evaluate_OS1(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        OS1: Same amino acid change as established oncogenic variant
        """
        # Check OncoKB for same amino acid change
        if 'oncokb' in self.clinical_evidence and variant.hgvs_p:
            oncokb_df = self.clinical_evidence['oncokb']
            
            # Extract amino acid change (e.g., p.V600E -> V600E)
            aa_change = variant.hgvs_p.replace('p.', '') if variant.hgvs_p else None
            
            if aa_change:
                matches = oncokb_df[
                    (oncokb_df['gene'] == variant.gene_symbol) &
                    (oncokb_df['alteration'].str.contains(aa_change, na=False))
                ]
                
                oncogenic_matches = matches[
                    matches['oncogenicity'].isin(['Oncogenic', 'Likely Oncogenic'])
                ]
                
                if not oncogenic_matches.empty:
                    return CriterionEvidence(
                        criterion=OncogenicityCriteria.OS1,
                        is_met=True,
                        strength="Strong",
                        evidence_sources=[{
                            "source": "OncoKB",
                            "oncogenicity": oncogenic_matches.iloc[0]['oncogenicity'],
                            "variant": f"{variant.gene_symbol} {aa_change}"
                        }],
                        confidence=0.9
                    )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OS1,
            is_met=False,
            strength="Strong"
        )
    
    def _evaluate_OS2(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        OS2: Protein length changes due to in-frame indels or nonsense variants
        in oncogenes or tumor suppressors
        """
        length_changing = any(c in ["inframe_insertion", "inframe_deletion", "stop_gained"] 
                             for c in variant.consequence)
        
        is_cancer_gene = (variant.is_oncogene or variant.is_tumor_suppressor or
                         variant.gene_symbol in self.cancer_genes.get('oncokb_genes', set()))
        
        if length_changing and is_cancer_gene:
            return CriterionEvidence(
                criterion=OncogenicityCriteria.OS2,
                is_met=True,
                strength="Strong",
                evidence_sources=[{
                    "source": "VEP + Cancer Gene Census",
                    "consequence": variant.consequence,
                    "gene_role": "oncogene" if variant.is_oncogene else "tumor_suppressor"
                }],
                confidence=0.85
            )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OS2,
            is_met=False,
            strength="Strong"
        )
    
    def _evaluate_OS3(self, variant: VariantAnnotation, cancer_type: Optional[str]) -> CriterionEvidence:
        """
        OS3: Located at a well-established cancer hotspot
        """
        hotspot_evidence = []
        
        # Check MSK hotspots
        if 'msk' in self.hotspots:
            msk_df = self.hotspots['msk']
            matches = msk_df[
                (msk_df['Hugo_Symbol'] == variant.gene_symbol) &
                (msk_df['Amino_Acid_Position'] == self._extract_position(variant.hgvs_p))
            ]
            
            if not matches.empty and matches.iloc[0].get('qvalue', 1.0) < 0.01:
                hotspot_evidence.append({
                    "source": "MSK Cancer Hotspots",
                    "q_value": matches.iloc[0]['qvalue'],
                    "samples": matches.iloc[0].get('Variant_Count', 'N/A')
                })
        
        # Check OncoVI hotspots
        if 'oncovi_single' in self.hotspots:
            oncovi_df = self.hotspots['oncovi_single']
            matches = oncovi_df[
                (oncovi_df['gene'] == variant.gene_symbol) &
                (oncovi_df['position'] == self._extract_position(variant.hgvs_p))
            ]
            
            if not matches.empty:
                hotspot_evidence.append({
                    "source": "OncoVI Hotspots",
                    "cancer_types": matches.iloc[0].get('cancer_types', 'N/A'),
                    "frequency": matches.iloc[0].get('frequency', 'N/A')
                })
        
        # Check variant's own hotspot evidence
        if variant.hotspot_evidence:
            for he in variant.hotspot_evidence:
                if he.samples_observed >= 50:  # Well-established threshold
                    hotspot_evidence.append({
                        "source": he.source,
                        "samples": he.samples_observed,
                        "cancer_types": he.cancer_types
                    })
        
        if hotspot_evidence:
            return CriterionEvidence(
                criterion=OncogenicityCriteria.OS3,
                is_met=True,
                strength="Strong",
                evidence_sources=hotspot_evidence,
                confidence=0.9,
                notes=f"Well-established hotspot in {cancer_type or 'multiple cancer types'}"
            )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OS3,
            is_met=False,
            strength="Strong"
        )
    
    def _evaluate_OM1(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        OM1: Missense in gene for which missense variants are common mechanism of oncogenicity
        """
        is_missense = "missense_variant" in variant.consequence
        
        # Genes where missense is common oncogenic mechanism
        missense_oncogenes = {
            'BRAF', 'KRAS', 'NRAS', 'HRAS', 'PIK3CA', 'AKT1', 'EGFR', 
            'FGFR1', 'FGFR2', 'FGFR3', 'KIT', 'PDGFRA', 'RET', 'MET',
            'ALK', 'ROS1', 'ERBB2', 'IDH1', 'IDH2', 'FLT3', 'JAK2'
        }
        
        if is_missense and variant.gene_symbol in missense_oncogenes:
            return CriterionEvidence(
                criterion=OncogenicityCriteria.OM1,
                is_met=True,
                strength="Moderate",
                evidence_sources=[{
                    "source": "Expert knowledge",
                    "rationale": f"{variant.gene_symbol} is known oncogene with missense mechanism"
                }],
                confidence=0.8
            )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OM1,
            is_met=False,
            strength="Moderate"
        )
    
    def _evaluate_OM2(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        OM2: Frameshift or stop gain in tumor suppressor gene without proven LOF mechanism
        """
        is_truncating = any(c in ["frameshift_variant", "stop_gained"] 
                           for c in variant.consequence)
        
        # TSGs where LOF is not definitively proven
        uncertain_lof_tsgs = {'NOTCH1', 'NOTCH2', 'FBXW7', 'CIC', 'ARID1B'}
        
        if is_truncating and variant.gene_symbol in uncertain_lof_tsgs:
            return CriterionEvidence(
                criterion=OncogenicityCriteria.OM2,
                is_met=True,
                strength="Moderate",
                evidence_sources=[{
                    "source": "Expert curation",
                    "note": "Truncating variant in TSG with uncertain LOF mechanism"
                }],
                confidence=0.7
            )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OM2,
            is_met=False,
            strength="Moderate"
        )
    
    def _evaluate_OM3(self, variant: VariantAnnotation, cancer_type: Optional[str]) -> CriterionEvidence:
        """
        OM3: Located at a cancer hotspot with lower evidence threshold
        """
        hotspot_evidence = []
        
        # Similar to OS3 but with lower thresholds
        if 'msk' in self.hotspots:
            msk_df = self.hotspots['msk']
            matches = msk_df[
                (msk_df['Hugo_Symbol'] == variant.gene_symbol) &
                (msk_df['Amino_Acid_Position'] == self._extract_position(variant.hgvs_p))
            ]
            
            if not matches.empty and matches.iloc[0].get('qvalue', 1.0) < 0.1:  # Less stringent
                hotspot_evidence.append({
                    "source": "MSK Cancer Hotspots",
                    "q_value": matches.iloc[0]['qvalue']
                })
        
        # Check for moderate hotspot evidence
        if variant.hotspot_evidence:
            for he in variant.hotspot_evidence:
                if 10 <= he.samples_observed < 50:  # Moderate evidence
                    hotspot_evidence.append({
                        "source": he.source,
                        "samples": he.samples_observed
                    })
        
        if hotspot_evidence:
            return CriterionEvidence(
                criterion=OncogenicityCriteria.OM3,
                is_met=True,
                strength="Moderate",
                evidence_sources=hotspot_evidence,
                confidence=0.7
            )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OM3,
            is_met=False,
            strength="Moderate"
        )
    
    def _evaluate_OM4(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        OM4: Missense variant in gene with low rate of benign missense variation
        """
        is_missense = "missense_variant" in variant.consequence
        
        # Check gene constraint scores if available
        if is_missense and hasattr(variant, 'gene_constraint_score'):
            if variant.gene_constraint_score > 0.8:  # High constraint
                return CriterionEvidence(
                    criterion=OncogenicityCriteria.OM4,
                    is_met=True,
                    strength="Moderate",
                    evidence_sources=[{
                        "source": "Gene constraint",
                        "score": variant.gene_constraint_score
                    }],
                    confidence=0.75
                )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OM4,
            is_met=False,
            strength="Moderate"
        )
    
    def _evaluate_OP1(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        OP1: Computational evidence supports oncogenic impact
        """
        computational_evidence = []
        
        # Check various prediction scores
        if hasattr(variant, 'cadd_phred') and variant.cadd_phred > 25:
            computational_evidence.append({
                "tool": "CADD",
                "score": variant.cadd_phred,
                "interpretation": "Deleterious"
            })
        
        if hasattr(variant, 'revel_score') and variant.revel_score > 0.7:
            computational_evidence.append({
                "tool": "REVEL",
                "score": variant.revel_score,
                "interpretation": "Pathogenic"
            })
        
        # Check AlphaMissense if available
        if hasattr(variant, 'alphamissense_score') and variant.alphamissense_score > 0.7:
            computational_evidence.append({
                "tool": "AlphaMissense",
                "score": variant.alphamissense_score,
                "interpretation": "Pathogenic"
            })
        
        if len(computational_evidence) >= 2:  # Multiple tools agree
            return CriterionEvidence(
                criterion=OncogenicityCriteria.OP1,
                is_met=True,
                strength="Supporting",
                evidence_sources=computational_evidence,
                confidence=0.6
            )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OP1,
            is_met=False,
            strength="Supporting"
        )
    
    def _evaluate_OP2(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        OP2: Somatic variant in tumor with oncogenic signature
        """
        # Check if variant has somatic evidence
        if variant.somatic_status == "Somatic" and variant.tumor_vaf > 0.1:
            # Check for oncogenic mutational signatures
            signature_evidence = []
            
            # UV signature for melanoma
            if variant.reference == 'C' and variant.alternate == 'T':
                signature_evidence.append({
                    "signature": "UV",
                    "cancer_type": "Melanoma"
                })
            
            # Tobacco signature for lung cancer
            if variant.gene_symbol in ['TP53', 'KRAS', 'STK11']:
                signature_evidence.append({
                    "signature": "Tobacco",
                    "cancer_type": "Lung"
                })
            
            if signature_evidence:
                return CriterionEvidence(
                    criterion=OncogenicityCriteria.OP2,
                    is_met=True,
                    strength="Supporting",
                    evidence_sources=signature_evidence,
                    confidence=0.5
                )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OP2,
            is_met=False,
            strength="Supporting"
        )
    
    def _evaluate_OP3(self, variant: VariantAnnotation, cancer_type: Optional[str]) -> CriterionEvidence:
        """
        OP3: Located at a cancer hotspot with minimal evidence
        """
        # Very low threshold hotspot evidence
        if variant.hotspot_evidence:
            for he in variant.hotspot_evidence:
                if he.samples_observed >= 3:  # Very minimal threshold
                    return CriterionEvidence(
                        criterion=OncogenicityCriteria.OP3,
                        is_met=True,
                        strength="Supporting",
                        evidence_sources=[{
                            "source": he.source,
                            "samples": he.samples_observed
                        }],
                        confidence=0.4
                    )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OP3,
            is_met=False,
            strength="Supporting"
        )
    
    def _evaluate_OP4(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        OP4: Absent from population databases
        """
        # Check gnomAD frequency
        if variant.population_frequencies:
            max_af = max(pf.allele_frequency for pf in variant.population_frequencies)
            
            if max_af < 0.00001:  # Extremely rare
                return CriterionEvidence(
                    criterion=OncogenicityCriteria.OP4,
                    is_met=True,
                    strength="Supporting",
                    evidence_sources=[{
                        "source": "gnomAD",
                        "max_af": max_af
                    }],
                    confidence=0.5
                )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.OP4,
            is_met=False,
            strength="Supporting"
        )
    
    def _evaluate_SBVS1(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        SBVS1: Minor allele frequency >5% in population databases
        """
        if variant.population_frequencies:
            max_af = max(pf.allele_frequency for pf in variant.population_frequencies)
            
            if max_af > 0.05:  # Common variant
                return CriterionEvidence(
                    criterion=OncogenicityCriteria.SBVS1,
                    is_met=True,
                    strength="Very Strong",
                    evidence_sources=[{
                        "source": "gnomAD",
                        "max_af": max_af,
                        "interpretation": "Common polymorphism"
                    }],
                    confidence=0.99
                )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.SBVS1,
            is_met=False,
            strength="Very Strong"
        )
    
    def _evaluate_SBS1(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        SBS1: Minor allele frequency >1% in population databases
        """
        if variant.population_frequencies:
            max_af = max(pf.allele_frequency for pf in variant.population_frequencies)
            
            if 0.01 < max_af <= 0.05:  # Uncommon but present
                return CriterionEvidence(
                    criterion=OncogenicityCriteria.SBS1,
                    is_met=True,
                    strength="Strong",
                    evidence_sources=[{
                        "source": "gnomAD",
                        "max_af": max_af,
                        "interpretation": "Polymorphism"
                    }],
                    confidence=0.9
                )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.SBS1,
            is_met=False,
            strength="Strong"
        )
    
    def _evaluate_SBS2(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        SBS2: Synonymous variant with no predicted splicing effect
        """
        is_synonymous = "synonymous_variant" in variant.consequence
        
        # Check SpliceAI predictions if available
        no_splice_effect = True
        if hasattr(variant, 'spliceai_scores'):
            max_splice_score = max(variant.spliceai_scores.values())
            no_splice_effect = max_splice_score < 0.2
        
        if is_synonymous and no_splice_effect:
            return CriterionEvidence(
                criterion=OncogenicityCriteria.SBS2,
                is_met=True,
                strength="Strong",
                evidence_sources=[{
                    "source": "VEP + SpliceAI",
                    "consequence": "synonymous",
                    "splice_prediction": "No effect"
                }],
                confidence=0.85
            )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.SBS2,
            is_met=False,
            strength="Strong"
        )
    
    def _evaluate_SBP1(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        SBP1: Missense variant in gene with high rate of benign missense variation
        """
        is_missense = "missense_variant" in variant.consequence
        
        # Genes tolerant to missense variation
        tolerant_genes = {'TTN', 'MUC16', 'OBSCN', 'NEB', 'RYR1', 'RYR2'}
        
        if is_missense and variant.gene_symbol in tolerant_genes:
            return CriterionEvidence(
                criterion=OncogenicityCriteria.SBP1,
                is_met=True,
                strength="Supporting",
                evidence_sources=[{
                    "source": "Gene tolerance",
                    "gene": variant.gene_symbol,
                    "note": "Gene with high benign missense rate"
                }],
                confidence=0.6
            )
        
        return CriterionEvidence(
            criterion=OncogenicityCriteria.SBP1,
            is_met=False,
            strength="Supporting"
        )
    
    def _evaluate_SBP2(self, variant: VariantAnnotation) -> CriterionEvidence:
        """
        SBP2: In cis with a pathogenic variant
        """
        # This would require phasing information
        # Placeholder for when such data is available
        return CriterionEvidence(
            criterion=OncogenicityCriteria.SBP2,
            is_met=False,
            strength="Supporting"
        )
    
    def _apply_combination_rules(self, criteria: List[CriterionEvidence]) -> OncogenicityClassification:
        """
        Apply CGC/VICC combination rules to determine final classification
        Based on Table 2 from the manuscript
        """
        # Count met criteria by strength
        oncogenic_met = [c for c in criteria if c.is_met and c.criterion.value.startswith('O')]
        benign_met = [c for c in criteria if c.is_met and c.criterion.value.startswith('S')]
        
        # Count by strength for oncogenic
        ovs_count = sum(1 for c in oncogenic_met if c.strength == "Very Strong")
        os_count = sum(1 for c in oncogenic_met if c.strength == "Strong")
        om_count = sum(1 for c in oncogenic_met if c.strength == "Moderate")
        op_count = sum(1 for c in oncogenic_met if c.strength == "Supporting")
        
        # Count by strength for benign
        sbvs_count = sum(1 for c in benign_met if c.strength == "Very Strong")
        sbs_count = sum(1 for c in benign_met if c.strength == "Strong")
        sbp_count = sum(1 for c in benign_met if c.strength == "Supporting")
        
        # Check for conflicting evidence
        if ovs_count > 0 and sbvs_count > 0:
            # Strong conflict - return VUS
            return OncogenicityClassification.VUS
        
        # Apply combination rules for Oncogenic
        if ovs_count >= 1 and sbs_count == 0:
            return OncogenicityClassification.ONCOGENIC
        
        if os_count >= 2 and sbs_count == 0:
            return OncogenicityClassification.ONCOGENIC
        
        if os_count == 1 and om_count >= 2:
            return OncogenicityClassification.ONCOGENIC
        
        if os_count == 1 and om_count == 1 and op_count >= 2:
            return OncogenicityClassification.ONCOGENIC
        
        # Apply combination rules for Likely Oncogenic
        if os_count == 1 and om_count == 1:
            return OncogenicityClassification.LIKELY_ONCOGENIC
        
        if os_count == 1 and op_count >= 2:
            return OncogenicityClassification.LIKELY_ONCOGENIC
        
        if om_count >= 3:
            return OncogenicityClassification.LIKELY_ONCOGENIC
        
        if om_count == 2 and op_count >= 2:
            return OncogenicityClassification.LIKELY_ONCOGENIC
        
        # Apply combination rules for Benign
        if sbvs_count >= 1:
            return OncogenicityClassification.BENIGN
        
        if sbs_count >= 2:
            return OncogenicityClassification.BENIGN
        
        # Apply combination rules for Likely Benign
        if sbs_count == 1 and sbp_count >= 1:
            return OncogenicityClassification.LIKELY_BENIGN
        
        if sbp_count >= 2:
            return OncogenicityClassification.LIKELY_BENIGN
        
        # Default to VUS if no rules met
        return OncogenicityClassification.VUS
    
    def _calculate_confidence(self, criteria: List[CriterionEvidence]) -> float:
        """Calculate confidence score based on evidence strength and concordance"""
        if not criteria:
            return 0.0
        
        met_criteria = [c for c in criteria if c.is_met]
        if not met_criteria:
            return 0.1  # Low confidence for no evidence
        
        # Weight by evidence strength
        strength_weights = {
            "Very Strong": 1.0,
            "Strong": 0.8,
            "Moderate": 0.5,
            "Supporting": 0.3
        }
        
        total_weight = sum(strength_weights.get(c.strength, 0) * c.confidence 
                          for c in met_criteria)
        max_possible = sum(strength_weights.get(c.strength, 0) 
                          for c in met_criteria)
        
        if max_possible == 0:
            return 0.5
        
        base_confidence = total_weight / max_possible
        
        # Boost confidence for multiple concordant evidence
        evidence_count_bonus = min(0.2, len(met_criteria) * 0.05)
        
        return min(0.99, base_confidence + evidence_count_bonus)
    
    def _generate_rationale(self, 
                           classification: OncogenicityClassification,
                           criteria: List[CriterionEvidence]) -> str:
        """Generate human-readable rationale for classification"""
        met_criteria = [c for c in criteria if c.is_met]
        
        if not met_criteria:
            return f"Classified as {classification.value} due to lack of evidence meeting CGC/VICC criteria."
        
        # Group by evidence direction
        oncogenic_criteria = [c for c in met_criteria if c.criterion.value.startswith('O')]
        benign_criteria = [c for c in met_criteria if c.criterion.value.startswith('S')]
        
        rationale_parts = []
        
        if oncogenic_criteria:
            criteria_list = ", ".join([c.criterion.value for c in oncogenic_criteria])
            rationale_parts.append(f"Oncogenic evidence: {criteria_list}")
        
        if benign_criteria:
            criteria_list = ", ".join([c.criterion.value for c in benign_criteria])
            rationale_parts.append(f"Benign evidence: {criteria_list}")
        
        rationale = f"Classified as {classification.value} based on CGC/VICC criteria. "
        rationale += "; ".join(rationale_parts) + "."
        
        return rationale
    
    def _summarize_evidence(self, criteria: List[CriterionEvidence]) -> Dict[str, int]:
        """Summarize evidence by strength and direction"""
        summary = {
            "oncogenic_very_strong": 0,
            "oncogenic_strong": 0,
            "oncogenic_moderate": 0,
            "oncogenic_supporting": 0,
            "benign_very_strong": 0,
            "benign_strong": 0,
            "benign_supporting": 0,
            "total_criteria_evaluated": len(criteria),
            "total_criteria_met": sum(1 for c in criteria if c.is_met)
        }
        
        for criterion in criteria:
            if not criterion.is_met:
                continue
                
            if criterion.criterion.value.startswith('O'):
                if criterion.strength == "Very Strong":
                    summary["oncogenic_very_strong"] += 1
                elif criterion.strength == "Strong":
                    summary["oncogenic_strong"] += 1
                elif criterion.strength == "Moderate":
                    summary["oncogenic_moderate"] += 1
                elif criterion.strength == "Supporting":
                    summary["oncogenic_supporting"] += 1
            else:  # Benign evidence
                if criterion.strength == "Very Strong":
                    summary["benign_very_strong"] += 1
                elif criterion.strength == "Strong":
                    summary["benign_strong"] += 1
                elif criterion.strength == "Supporting":
                    summary["benign_supporting"] += 1
        
        return summary
    
    def _extract_position(self, hgvs_p: Optional[str]) -> Optional[int]:
        """Extract amino acid position from HGVS protein notation"""
        if not hgvs_p:
            return None
        
        import re
        # Match patterns like p.V600E, p.Val600Glu
        match = re.search(r'p\.[A-Za-z]+(\d+)', hgvs_p)
        if match:
            return int(match.group(1))
        
        return None


def create_cgc_vicc_evidence(classifier_result: OncogenicityResult) -> List[Evidence]:
    """
    Convert CGC/VICC classification result to Evidence objects
    for integration with the tiering engine
    """
    evidence_list = []
    
    # Create main classification evidence
    if classifier_result.classification in [OncogenicityClassification.ONCOGENIC, 
                                          OncogenicityClassification.LIKELY_ONCOGENIC]:
        score = 8 if classifier_result.classification == OncogenicityClassification.ONCOGENIC else 6
        evidence_list.append(Evidence(
            code="CGC_VICC_ONCOGENIC",
            score=score,
            guideline="CGC/VICC 2022",
            source_kb="CGC/VICC Classifier",
            description=f"Variant classified as {classifier_result.classification.value}",
            evidence_type="ONCOGENICITY",
            confidence=classifier_result.confidence_score
        ))
    
    # Add individual criteria as evidence
    for criterion in classifier_result.criteria_met:
        # Map criterion strength to score
        score_map = {
            "Very Strong": 4,
            "Strong": 3,
            "Moderate": 2,
            "Supporting": 1
        }
        
        evidence_list.append(Evidence(
            code=criterion.criterion.value,
            score=score_map.get(criterion.strength, 1),
            guideline="CGC/VICC 2022",
            source_kb=criterion.evidence_sources[0]["source"] if criterion.evidence_sources else "CGC/VICC",
            description=f"{criterion.criterion.value}: {criterion.notes or 'Criterion met'}",
            evidence_type="ONCOGENICITY_CRITERION",
            confidence=criterion.confidence
        ))
    
    return evidence_list