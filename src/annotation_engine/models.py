from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any, Literal
from enum import Enum
from datetime import datetime


class AnalysisType(str, Enum):
    """Analysis workflow type based on input samples"""
    TUMOR_NORMAL = "TUMOR_NORMAL"    # Paired tumor-normal analysis
    TUMOR_ONLY = "TUMOR_ONLY"        # Tumor-only analysis


class AMPTierLevel(str, Enum):
    """AMP/ASCO/CAP 2017 granular tier levels with evidence strength"""
    TIER_IA = "Tier IA"    # Strong Clinical Significance (Highest Evidence)
    TIER_IB = "Tier IB"    # Strong Clinical Significance (Consensus-Driven)
    TIER_IIC = "Tier IIC"  # Potential Clinical Significance (Emerging Evidence)
    TIER_IID = "Tier IID"  # Potential Clinical Significance (Limited Evidence)
    TIER_IIE = "Tier IIE"  # Investigational/Emerging Evidence
    TIER_III = "Tier III"  # Variants of Unknown Clinical Significance (VUS)
    TIER_IV = "Tier IV"    # Benign or Likely Benign Variants


class ActionabilityType(str, Enum):
    """Clinical context for variant actionability"""
    THERAPEUTIC = "therapeutic"    # Treatment/therapy guidance
    DIAGNOSTIC = "diagnostic"      # Disease diagnosis
    PROGNOSTIC = "prognostic"      # Disease outcome prediction


class EvidenceStrength(str, Enum):
    """Evidence strength hierarchy for AMP tier assignment"""
    FDA_APPROVED = "FDA_approved"                    # FDA-approved biomarkers
    PROFESSIONAL_GUIDELINES = "guidelines"           # Professional society guidelines  
    META_ANALYSIS = "meta_analysis"                  # Meta-analyses, systematic reviews
    WELL_POWERED_RCT = "well_powered_rct"           # Well-powered RCTs, clinical studies
    EXPERT_CONSENSUS = "expert_consensus"            # Expert consensus from multiple studies
    MULTIPLE_SMALL_STUDIES = "multiple_studies"     # Multiple small published studies
    CASE_REPORTS = "case_reports"                   # Case reports, individual observations
    PRECLINICAL = "preclinical"                     # In vitro, in vivo preclinical studies


class VICCOncogenicity(str, Enum):
    """VICC/CGC 2022 oncogenicity classifications"""
    ONCOGENIC = "Oncogenic"
    LIKELY_ONCOGENIC = "Likely Oncogenic"
    UNCERTAIN_SIGNIFICANCE = "Uncertain Significance"
    LIKELY_BENIGN = "Likely Benign"
    BENIGN = "Benign"


class OncoKBLevel(str, Enum):
    """OncoKB therapeutic evidence levels"""
    LEVEL_1 = "Level 1"    # FDA-approved biomarker
    LEVEL_2A = "Level 2A"  # Standard care biomarker
    LEVEL_2B = "Level 2B"  # Standard care biomarker for different indication
    LEVEL_3A = "Level 3A"  # Clinical evidence
    LEVEL_3B = "Level 3B"  # Clinical evidence for different indication
    LEVEL_4 = "Level 4"    # Biological evidence
    LEVEL_R1 = "Level R1"  # FDA-approved resistance
    LEVEL_R2 = "Level R2"  # Clinical evidence of resistance


class CannedTextType(str, Enum):
    """Types of canned text for clinical interpretation"""
    GENERAL_GENE_INFO = "General Gene Info"
    GENE_DX_INTERPRETATION = "Gene Dx Interpretation"
    GENERAL_VARIANT_INFO = "General Variant Info"
    VARIANT_DX_INTERPRETATION = "Variant Dx Interpretation"
    INCIDENTAL_SECONDARY_FINDINGS = "Incidental/Secondary Findings"
    CHROMOSOMAL_ALTERATION_INTERPRETATION = "Chromosomal Alteration Interpretation"
    PERTINENT_NEGATIVES = "Pertinent Negatives"
    BIOMARKERS = "Biomarkers"
    TECHNICAL_COMMENTS = "Technical Comments"
    TUMOR_ONLY_DISCLAIMERS = "Tumor-Only Analysis Disclaimers"


class Evidence(BaseModel):
    """Evidence item supporting variant classification"""
    code: str = Field(..., description="Evidence code (e.g., OVS1, OS1, OM1)")
    score: int = Field(..., description="Numeric score for this evidence")
    guideline: Literal["AMP_2017", "VICC_2022", "OncoKB"] = Field(..., description="Source guideline")
    source_kb: str = Field(..., description="Knowledge base source (e.g., OncoKB, CIViC)")
    description: str = Field(..., description="Human-readable evidence description")
    data: Dict[str, Any] = Field(default_factory=dict, description="Supporting data")
    confidence: Optional[float] = Field(None, description="Confidence score 0-1")
    analysis_type_adjusted: bool = Field(default=False, description="Whether confidence was adjusted for analysis type")
    created_at: datetime = Field(default_factory=datetime.now)


class PopulationFrequency(BaseModel):
    """Population allele frequency data"""
    database: str = Field(..., description="Source database (gnomAD, etc.)")
    population: str = Field(..., description="Population group")
    allele_frequency: Optional[float] = Field(None, description="Allele frequency")
    allele_count: Optional[int] = Field(None, description="Allele count")
    allele_number: Optional[int] = Field(None, description="Total alleles")
    homozygote_count: Optional[int] = Field(None, description="Homozygote count")


class HotspotEvidence(BaseModel):
    """Cancer hotspot evidence"""
    source: str = Field(..., description="Hotspot database source")
    samples_observed: int = Field(..., description="Number of samples with this hotspot")
    cancer_types: List[str] = Field(default_factory=list, description="Cancer types where observed")
    recurrence_rank: Optional[int] = Field(None, description="Recurrence ranking")
    hotspot_type: Literal["single_residue", "indel", "structural"] = Field(..., description="Type of hotspot")


class FunctionalPrediction(BaseModel):
    """Computational functional prediction"""
    algorithm: str = Field(..., description="Prediction algorithm")
    score: Optional[float] = Field(None, description="Prediction score")
    prediction: Optional[str] = Field(None, description="Categorical prediction")
    confidence: Optional[float] = Field(None, description="Confidence in prediction")


class TherapeuticImplication(BaseModel):
    """Therapeutic actionability information"""
    drug_name: str = Field(..., description="Drug or therapy name")
    indication: str = Field(..., description="Cancer indication")
    evidence_level: str = Field(..., description="Evidence level")
    approval_status: Literal["FDA_approved", "investigational", "preclinical"] = Field(..., description="Approval status")
    source: str = Field(..., description="Source database")
    clinical_trials: List[str] = Field(default_factory=list, description="Related clinical trial IDs")


class VariantAnnotation(BaseModel):
    """Comprehensive variant annotation"""
    # Variant identification
    chromosome: str
    position: int
    reference: str
    alternate: str
    gene_symbol: str
    transcript_id: Optional[str] = None
    hgvs_c: Optional[str] = None
    hgvs_p: Optional[str] = None
    
    # Quality metrics from VCF filtering
    quality_score: Optional[float] = None
    filter_status: List[str] = Field(default_factory=list)
    total_depth: Optional[int] = None
    vaf: Optional[float] = Field(None, description="Variant allele frequency")
    tumor_purity: Optional[float] = Field(None, description="Estimated tumor purity")
    
    # VEP annotations
    consequence: List[str] = Field(default_factory=list)
    impact: Optional[str] = None
    biotype: Optional[str] = None
    
    # Population frequencies
    population_frequencies: List[PopulationFrequency] = Field(default_factory=list)
    
    # Cancer evidence
    hotspot_evidence: List[HotspotEvidence] = Field(default_factory=list)
    
    # Functional predictions
    functional_predictions: List[FunctionalPrediction] = Field(default_factory=list)
    
    # Clinical evidence
    civic_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    oncokb_evidence: Optional[Dict[str, Any]] = None
    clinvar_significance: Optional[str] = None
    
    # Gene context
    is_oncogene: bool = False
    is_tumor_suppressor: bool = False
    cancer_gene_census: bool = False
    
    # Therapeutic implications
    therapeutic_implications: List[TherapeuticImplication] = Field(default_factory=list)
    
    # VEP plugin data (raw data for evidence aggregation)
    plugin_data: Dict[str, Any] = Field(default_factory=dict, description="Raw VEP plugin outputs")
    
    # Annotation metadata
    vep_version: Optional[str] = None
    annotation_source: str = "VEP"


class VICCScoring(BaseModel):
    """VICC/CGC 2022 oncogenicity scoring"""
    # Very Strong evidence (8 points)
    ovs1_score: int = Field(default=0, description="OVS1: Null variant in tumor suppressor")
    
    # Strong evidence (4 points)
    os1_score: int = Field(default=0, description="OS1: Activating variant in oncogene")
    os2_score: int = Field(default=0, description="OS2: Well-established in guidelines")
    os3_score: int = Field(default=0, description="OS3: Well-established hotspot")
    
    # Moderate evidence (2 points)
    om1_score: int = Field(default=0, description="OM1: Critical functional domain")
    om2_score: int = Field(default=0, description="OM2: Functional studies")
    om3_score: int = Field(default=0, description="OM3: Hotspot with moderate evidence")
    om4_score: int = Field(default=0, description="OM4: Mutation in oncogenic gene")
    
    # Supporting evidence (1 point)
    op1_score: int = Field(default=0, description="OP1: Computational evidence")
    op2_score: int = Field(default=0, description="OP2: Somatic in multiple tumors")
    op3_score: int = Field(default=0, description="OP3: Located in hotspot region")
    op4_score: int = Field(default=0, description="OP4: Absent from population DBs")
    
    # Benign evidence (negative scores)
    sbvs1_score: int = Field(default=0, description="SBVS1: High population frequency")
    sbs1_score: int = Field(default=0, description="SBS1: Silent with no impact")
    sbs2_score: int = Field(default=0, description="SBS2: Functional studies show benign")
    sbp1_score: int = Field(default=0, description="SBP1: Computational evidence benign")
    
    total_score: int = Field(default=0, description="Total VICC score")
    classification: VICCOncogenicity = Field(default=VICCOncogenicity.UNCERTAIN_SIGNIFICANCE)


class ContextSpecificTierAssignment(BaseModel):
    """AMP tier assignment for a specific actionability context"""
    actionability_type: ActionabilityType = Field(..., description="Actionability context (therapeutic/diagnostic/prognostic)")
    tier_level: AMPTierLevel = Field(..., description="Assigned tier level for this context")
    evidence_strength: EvidenceStrength = Field(..., description="Strongest evidence supporting this tier")
    evidence_score: float = Field(..., description="Quantitative evidence score for this context")
    confidence_score: float = Field(..., description="Confidence in this tier assignment 0-1")
    
    # Context-specific evidence flags
    fda_approved: bool = Field(default=False, description="FDA-approved for this context")
    guideline_included: bool = Field(default=False, description="Included in professional guidelines")
    expert_consensus: bool = Field(default=False, description="Expert consensus evidence")
    clinical_trial_eligible: bool = Field(default=False, description="Clinical trial inclusion criteria")
    cancer_type_specific: bool = Field(default=False, description="Evidence specific to this cancer type")
    
    # Supporting evidence details
    supporting_studies: List[str] = Field(default_factory=list, description="Supporting study types")
    evidence_summary: str = Field(default="", description="Brief evidence summary")


class AMPScoring(BaseModel):
    """AMP/ASCO/CAP 2017 comprehensive multi-context tier assignment"""
    
    # Context-specific tier assignments (a variant can have multiple)
    therapeutic_tier: Optional[ContextSpecificTierAssignment] = Field(None, description="Therapeutic actionability tier")
    diagnostic_tier: Optional[ContextSpecificTierAssignment] = Field(None, description="Diagnostic actionability tier") 
    prognostic_tier: Optional[ContextSpecificTierAssignment] = Field(None, description="Prognostic actionability tier")
    
    # Overall cancer type context
    cancer_type_specific: bool = Field(default=False, description="Evidence specific to this cancer type")
    related_cancer_types: List[str] = Field(default_factory=list, description="Related cancer types with evidence")
    
    # Overall confidence and completeness
    overall_confidence: float = Field(default=0.0, description="Overall confidence across all contexts 0-1")
    evidence_completeness: float = Field(default=0.0, description="Completeness of evidence review 0-1")
    
    def get_primary_tier(self) -> str:
        """Get the highest (most clinically significant) tier across all contexts"""
        tiers = []
        if self.therapeutic_tier:
            tiers.append(self.therapeutic_tier.tier_level)
        if self.diagnostic_tier:
            tiers.append(self.diagnostic_tier.tier_level)
        if self.prognostic_tier:
            tiers.append(self.prognostic_tier.tier_level)
        
        if not tiers:
            return AMPTierLevel.TIER_IV.value
        
        # Return highest tier (IA > IB > IIC > IID > IIE > III > IV)
        tier_priority = {
            AMPTierLevel.TIER_IA: 1,
            AMPTierLevel.TIER_IB: 2,
            AMPTierLevel.TIER_IIC: 3,
            AMPTierLevel.TIER_IID: 4,
            AMPTierLevel.TIER_IIE: 5,
            AMPTierLevel.TIER_III: 6,
            AMPTierLevel.TIER_IV: 7
        }
        
        highest_tier = min(tiers, key=lambda x: tier_priority[x])
        return highest_tier.value
    
    def get_context_tiers(self) -> Dict[str, str]:
        """Get tier assignments for each context"""
        result = {}
        if self.therapeutic_tier:
            result["therapeutic"] = self.therapeutic_tier.tier_level.value
        if self.diagnostic_tier:
            result["diagnostic"] = self.diagnostic_tier.tier_level.value
        if self.prognostic_tier:
            result["prognostic"] = self.prognostic_tier.tier_level.value
        return result
    
    @property
    def tier(self) -> str:
        """Legacy property for backward compatibility - returns primary tier"""
        return self.get_primary_tier()


class OncoKBScoring(BaseModel):
    """OncoKB therapeutic actionability scoring"""
    oncogenicity: Optional[str] = Field(None, description="OncoKB oncogenicity assessment")
    therapeutic_level: Optional[OncoKBLevel] = Field(None, description="Therapeutic evidence level")
    resistance_level: Optional[OncoKBLevel] = Field(None, description="Resistance evidence level")
    
    # Therapy information
    fda_approved_therapy: List[str] = Field(default_factory=list, description="FDA-approved therapies")
    off_label_therapy: List[str] = Field(default_factory=list, description="Off-label therapies")
    investigational_therapy: List[str] = Field(default_factory=list, description="Investigational therapies")
    
    cancer_type_specific: bool = Field(default=False, description="Cancer-type specific evidence")
    any_cancer_type: bool = Field(default=False, description="Evidence in any cancer type")


class CannedText(BaseModel):
    """Generated canned text for clinical interpretation"""
    text_type: CannedTextType
    content: str = Field(..., description="Generated text content")
    confidence: float = Field(..., description="Confidence in text generation 0-1")
    evidence_support: List[str] = Field(default_factory=list, description="Supporting evidence codes")
    triggered_by: List[str] = Field(default_factory=list, description="What triggered this text")


class DynamicSomaticConfidence(BaseModel):
    """Dynamic Somatic Confidence (DSC) scoring for tumor-only analysis"""
    # Overall DSC score
    dsc_score: float = Field(..., ge=0.0, le=1.0, description="Dynamic Somatic Confidence score P(Somatic | evidence)")
    
    # Module scores
    vaf_purity_score: Optional[float] = Field(None, description="VAF/purity consistency score")
    prior_probability_score: float = Field(..., description="Somatic vs germline prior probability")
    genomic_context_score: Optional[float] = Field(None, description="Supporting genomic context evidence")
    
    # Evidence details
    tumor_purity: Optional[float] = Field(None, description="Estimated tumor purity")
    variant_vaf: Optional[float] = Field(None, description="Variant allele frequency")
    hotspot_evidence: bool = Field(False, description="Variant at known cancer hotspot")
    population_frequency: Optional[float] = Field(None, description="Population frequency from gnomAD")
    clinvar_germline: bool = Field(False, description="Known pathogenic germline variant in ClinVar")
    
    # Confidence in DSC calculation
    dsc_confidence: float = Field(default=1.0, description="Confidence in DSC score calculation")
    modules_available: List[str] = Field(default_factory=list, description="Which modules contributed to DSC")


class TierResult(BaseModel):
    """Complete variant tier assignment result"""
    # Variant identification
    variant_id: str = Field(..., description="Unique variant identifier")
    gene_symbol: str
    hgvs_p: Optional[str] = None
    
    # Analysis context
    analysis_type: AnalysisType = Field(..., description="Analysis workflow type")
    
    # Dynamic Somatic Confidence (for tumor-only analysis)
    dsc_scoring: Optional[DynamicSomaticConfidence] = Field(None, description="Dynamic Somatic Confidence scoring")
    
    # Tier assignments
    amp_scoring: AMPScoring
    vicc_scoring: VICCScoring
    oncokb_scoring: OncoKBScoring
    
    # Supporting evidence
    evidence: List[Evidence] = Field(default_factory=list)
    
    # Clinical context
    cancer_type: str
    tissue_type: Optional[str] = None
    
    # Generated text
    canned_texts: List[CannedText] = Field(default_factory=list)
    
    # Quality metrics
    confidence_score: float = Field(default=0.0, description="Overall confidence 0-1")
    annotation_completeness: float = Field(default=0.0, description="Completeness of annotation 0-1")
    
    # Metadata
    annotation_date: datetime = Field(default_factory=datetime.now)
    kb_versions: Dict[str, str] = Field(default_factory=dict, description="Knowledge base versions used")
    
    def get_primary_tier(self) -> str:
        """Get the primary tier assignment (AMP by default)"""
        return self.amp_scoring.tier.value
    
    def get_therapeutic_implications(self) -> List[str]:
        """Get list of therapeutic implications"""
        therapies = []
        therapies.extend(self.oncokb_scoring.fda_approved_therapy)
        therapies.extend(self.oncokb_scoring.off_label_therapy)
        therapies.extend(self.oncokb_scoring.investigational_therapy)
        return list(set(therapies))  # Remove duplicates
    
    def get_evidence_summary(self) -> Dict[str, int]:
        """Get summary of evidence by guideline"""
        summary = {"AMP_2017": 0, "VICC_2022": 0, "OncoKB": 0}
        for evidence in self.evidence:
            summary[evidence.guideline] += 1
        return summary


class EvidenceWeights(BaseModel):
    """Configurable evidence strength weights for empirical tuning"""
    fda_approved: float = Field(default=1.0, description="Weight for FDA-approved evidence")
    professional_guidelines: float = Field(default=0.95, description="Weight for guideline evidence")
    meta_analysis: float = Field(default=0.9, description="Weight for meta-analyses/systematic reviews")
    well_powered_rct: float = Field(default=0.85, description="Weight for well-powered RCTs")
    expert_consensus: float = Field(default=0.8, description="Weight for expert consensus")
    multiple_small_studies: float = Field(default=0.6, description="Weight for multiple small studies")
    case_reports: float = Field(default=0.4, description="Weight for case reports")
    preclinical: float = Field(default=0.3, description="Weight for preclinical studies")
    
    # Context-specific modifiers
    cancer_type_specific_bonus: float = Field(default=0.1, description="Bonus for cancer-type-specific evidence")
    off_label_penalty: float = Field(default=0.2, description="Penalty for off-label indications")
    clinical_trial_bonus: float = Field(default=0.05, description="Bonus for clinical trial inclusion criteria")


class AnnotationConfig(BaseModel):
    """Configuration for annotation engine"""
    # Knowledge base paths
    kb_base_path: str = Field(..., description="Base path to knowledge bases")
    
    # Quality thresholds
    min_population_frequency: float = Field(default=0.01, description="Max population frequency for rare variants")
    min_hotspot_samples: int = Field(default=3, description="Minimum samples for hotspot evidence")
    min_functional_score: float = Field(default=0.5, description="Minimum functional prediction score")
    
    # Scoring thresholds
    vicc_oncogenic_threshold: int = Field(default=7, description="VICC score threshold for oncogenic")
    vicc_likely_oncogenic_threshold: int = Field(default=4, description="VICC score threshold for likely oncogenic")
    vicc_likely_benign_threshold: int = Field(default=-2, description="VICC score threshold for likely benign")
    vicc_benign_threshold: int = Field(default=-6, description="VICC score threshold for benign")
    
    # AMP tier assignment thresholds (empirically tunable)
    amp_tier_ia_threshold: float = Field(default=0.9, description="Evidence score threshold for Tier IA (FDA/Guidelines)")
    amp_tier_ib_threshold: float = Field(default=0.8, description="Evidence score threshold for Tier IB (Expert consensus)")
    amp_tier_iic_threshold: float = Field(default=0.6, description="Evidence score threshold for Tier IIC (Multiple studies)")
    amp_tier_iid_threshold: float = Field(default=0.4, description="Evidence score threshold for Tier IID (Limited evidence)")
    
    # Evidence weighting configuration
    evidence_weights: EvidenceWeights = Field(default_factory=EvidenceWeights, description="Configurable evidence weights")
    
    # Text generation settings
    enable_canned_text: bool = Field(default=True, description="Enable canned text generation")
    text_confidence_threshold: float = Field(default=0.7, description="Minimum confidence for text generation")
    
    # Multi-context tier assignment settings
    enable_multi_context_tiers: bool = Field(default=True, description="Enable multiple context-specific tier assignments")
    require_cancer_type_specificity: bool = Field(default=False, description="Require cancer-type-specific evidence for higher tiers")
    
    # Empirical validation settings
    use_empirical_weights: bool = Field(default=True, description="Use configurable evidence weights")
    validation_mode: str = Field(default="amp_2017", description="Validation approach: amp_2017, flat, binary, custom")
    
    # Tumor-Only vs Tumor-Normal specific settings
    tumor_only_confidence_penalty: float = Field(default=0.2, description="Confidence reduction for tumor-only analysis (0-1)")
    tumor_only_tier_cap: AMPTierLevel = Field(default=AMPTierLevel.TIER_IIC, description="Maximum tier level for tumor-only analysis")
    tumor_only_population_af_threshold: float = Field(default=0.01, description="Population AF threshold for tumor-only germline filtering")
    enable_tumor_only_disclaimers: bool = Field(default=True, description="Enable mandatory disclaimers for tumor-only reports")
    
    # Cancer type mappings
    oncotree_mappings: Dict[str, str] = Field(default_factory=dict, description="OncoTree code mappings")