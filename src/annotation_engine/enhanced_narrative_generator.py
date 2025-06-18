"""
Enhanced Deterministic Narrative Generator

This module provides sophisticated deterministic narrative generation with:
1. Reliable citation insertion and management
2. Intelligent source ordering and prioritization
3. Evidence synthesis with proper attribution
4. Quality assurance and consistency checks
"""

from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import re
import logging
import hashlib
from collections import defaultdict, OrderedDict

from .models import Evidence, CannedText, CannedTextType

logger = logging.getLogger(__name__)


@dataclass
class SourceMetadata:
    """Comprehensive metadata for evidence sources"""
    source_name: str
    reliability_tier: int  # 1=highest, 5=lowest
    citation_format: str
    url_pattern: Optional[str] = None
    typical_evidence_types: List[str] = field(default_factory=list)
    requires_date: bool = True
    pmid_support: bool = False
    description: str = ""


@dataclass
class EvidenceCluster:
    """Group of evidence pieces supporting the same conclusion"""
    conclusion: str
    evidence_pieces: List[Evidence]
    primary_source: str
    supporting_sources: List[str]
    confidence_score: float
    citation_numbers: List[int]


class EnhancedNarrativeGenerator:
    """
    Enhanced deterministic narrative generator with robust citation management
    and intelligent evidence synthesis
    """
    
    def __init__(self, enable_caching: bool = True):
        self.source_catalog = self._initialize_source_catalog()
        self.narrative_patterns = self._initialize_narrative_patterns()
        self.citation_registry = {}  # Track all citations used
        self.source_counter = 0
        self.enable_caching = enable_caching
        
        # Performance optimization caches
        self._evidence_cluster_cache = {}  # Cache clustered evidence by hash
        self._template_cache = {}  # Cache compiled templates
        self._narrative_cache = {}  # Cache generated narratives
        
    def _initialize_source_catalog(self) -> Dict[str, SourceMetadata]:
        """Comprehensive catalog of all evidence sources with metadata"""
        return {
            # Tier 1: Regulatory/FDA
            "FDA": SourceMetadata(
                source_name="U.S. Food and Drug Administration",
                reliability_tier=1,
                citation_format="U.S. Food and Drug Administration. {title}. {date}.",
                url_pattern="https://www.fda.gov/",
                typical_evidence_types=["THERAPEUTIC", "APPROVAL"],
                description="Regulatory approvals and guidance"
            ),
            
            "EMA": SourceMetadata(
                source_name="European Medicines Agency", 
                reliability_tier=1,
                citation_format="European Medicines Agency. {title}. {date}.",
                typical_evidence_types=["THERAPEUTIC", "APPROVAL"]
            ),
            
            # Tier 2: Professional Guidelines
            "NCCN": SourceMetadata(
                source_name="National Comprehensive Cancer Network",
                reliability_tier=2,
                citation_format="NCCN Clinical Practice Guidelines in Oncology. {guideline}. Version {version}. {date}.",
                url_pattern="https://www.nccn.org/",
                typical_evidence_types=["THERAPEUTIC", "DIAGNOSTIC", "GUIDELINE"]
            ),
            
            "CAP": SourceMetadata(
                source_name="College of American Pathologists",
                reliability_tier=2,
                citation_format="College of American Pathologists. {title}. {date}.",
                typical_evidence_types=["DIAGNOSTIC", "GUIDELINE"]
            ),
            
            "ASCO": SourceMetadata(
                source_name="American Society of Clinical Oncology",
                reliability_tier=2,
                citation_format="American Society of Clinical Oncology. {title}. {journal}. {date}.",
                typical_evidence_types=["THERAPEUTIC", "GUIDELINE"]
            ),
            
            "ESMO": SourceMetadata(
                source_name="European Society for Medical Oncology",
                reliability_tier=2,
                citation_format="European Society for Medical Oncology. {title}. {date}.",
                typical_evidence_types=["THERAPEUTIC", "GUIDELINE"]
            ),
            
            # Tier 3: Expert Curated Databases
            "ONCOKB": SourceMetadata(
                source_name="OncoKB",
                reliability_tier=3,
                citation_format="Chakravarty D, et al. OncoKB: A Precision Oncology Knowledge Base. JCO Precis Oncol. 2017.",
                url_pattern="https://www.oncokb.org/",
                typical_evidence_types=["THERAPEUTIC", "ONCOGENIC", "CLINICAL_SIGNIFICANCE"],
                description="Memorial Sloan Kettering precision oncology knowledge base"
            ),
            
            "CIVIC": SourceMetadata(
                source_name="CIViC", 
                reliability_tier=3,
                citation_format="Griffith M, et al. CIViC: a community knowledgebase for expert crowdsourcing the clinical interpretation of variants in cancer. Nat Genet. 2017.",
                url_pattern="https://civicdb.org/",
                typical_evidence_types=["THERAPEUTIC", "DIAGNOSTIC", "PROGNOSTIC"],
                description="Clinical Interpretation of Variants in Cancer"
            ),
            
            "CLINGEN": SourceMetadata(
                source_name="ClinGen",
                reliability_tier=3,
                citation_format="Rehm HL, et al. ClinGen--the Clinical Genome Resource. N Engl J Med. 2015.",
                typical_evidence_types=["GENE_VALIDITY", "DOSAGE_SENSITIVITY"],
                description="Clinical Genome Resource"
            ),
            
            "CLINVAR": SourceMetadata(
                source_name="ClinVar",
                reliability_tier=3,
                citation_format="Landrum MJ, et al. ClinVar: improving access to variant interpretations and supporting evidence. Nucleic Acids Res. 2018.",
                url_pattern="https://www.ncbi.nlm.nih.gov/clinvar/",
                typical_evidence_types=["CLINICAL_SIGNIFICANCE", "PATHOGENICITY"],
                pmid_support=True,
                description="NCBI database of genetic variants and clinical significance"
            ),
            
            # Tier 4: Literature/Research
            "PUBMED": SourceMetadata(
                source_name="PubMed",
                reliability_tier=4,
                citation_format="PMID: {pmids}",
                pmid_support=True,
                typical_evidence_types=["LITERATURE", "RESEARCH"]
            ),
            
            # Tier 4: Community/Research Databases  
            "COSMIC": SourceMetadata(
                source_name="COSMIC",
                reliability_tier=4,
                citation_format="Tate JG, et al. COSMIC: the Catalogue Of Somatic Mutations In Cancer. Nucleic Acids Res. 2019.",
                url_pattern="https://cancer.sanger.ac.uk/",
                typical_evidence_types=["SOMATIC_MUTATION", "CANCER_CENSUS"],
                description="Catalogue of Somatic Mutations in Cancer"
            ),
            
            "CANCER_HOTSPOTS": SourceMetadata(
                source_name="Cancer Hotspots",
                reliability_tier=4,
                citation_format="Chang MT, et al. Identifying recurrent mutations in cancer reveals widespread lineage diversity and mutational specificity. Nat Biotechnol. 2016.",
                typical_evidence_types=["HOTSPOT", "RECURRENCE"]
            ),
            
            "GNOMAD": SourceMetadata(
                source_name="gnomAD",
                reliability_tier=4,
                citation_format="Karczewski KJ, et al. The mutational constraint spectrum quantified from variation in 141,456 humans. Nature. 2020.",
                url_pattern="https://gnomad.broadinstitute.org/",
                typical_evidence_types=["POPULATION_FREQUENCY"],
                description="Genome Aggregation Database"
            ),
            
            # Tier 5: Computational Predictions
            "ALPHAMISSENSE": SourceMetadata(
                source_name="AlphaMissense",
                reliability_tier=5,
                citation_format="Cheng J, et al. Accurate proteome-wide missense variant effect prediction with AlphaMissense. Science. 2023.",
                typical_evidence_types=["COMPUTATIONAL", "PATHOGENICITY_PREDICTION"]
            ),
            
            "REVEL": SourceMetadata(
                source_name="REVEL",
                reliability_tier=5,
                citation_format="Ioannidis NM, et al. REVEL: An Ensemble Method for Predicting the Pathogenicity of Rare Missense Variants. Am J Hum Genet. 2016.",
                typical_evidence_types=["COMPUTATIONAL", "PATHOGENICITY_PREDICTION"]
            ),
            
            "CADD": SourceMetadata(
                source_name="CADD",
                reliability_tier=5,
                citation_format="Rentzsch P, et al. CADD: predicting the deleteriousness of variants throughout the human genome. Nucleic Acids Res. 2019.",
                typical_evidence_types=["COMPUTATIONAL", "DELETERIOUSNESS"]
            ),
            
            "SIFT": SourceMetadata(
                source_name="SIFT",
                reliability_tier=5,
                citation_format="Ng PC, Henikoff S. SIFT: Predicting amino acid changes that affect protein function. Nucleic Acids Res. 2003.",
                typical_evidence_types=["COMPUTATIONAL", "FUNCTION_PREDICTION"]
            ),
            
            "POLYPHEN": SourceMetadata(
                source_name="PolyPhen-2",
                reliability_tier=5,
                citation_format="Adzhubei IA, et al. A method and server for predicting damaging missense mutations. Nat Methods. 2010.",
                typical_evidence_types=["COMPUTATIONAL", "DAMAGE_PREDICTION"]
            ),
            
            # Gene/Protein Databases
            "UNIPROT": SourceMetadata(
                source_name="UniProt",
                reliability_tier=3,
                citation_format="UniProt Consortium. UniProt: the universal protein knowledgebase in 2021. Nucleic Acids Res. 2021.",
                url_pattern="https://www.uniprot.org/",
                typical_evidence_types=["PROTEIN_FUNCTION", "GENE_FUNCTION"]
            ),
            
            "NCBI_GENE": SourceMetadata(
                source_name="NCBI Gene",
                reliability_tier=3,
                citation_format="NCBI Gene Database. National Center for Biotechnology Information.",
                url_pattern="https://www.ncbi.nlm.nih.gov/gene/",
                typical_evidence_types=["GENE_INFO", "GENE_FUNCTION"]
            ),
            
            "HGNC": SourceMetadata(
                source_name="HGNC",
                reliability_tier=3,
                citation_format="Braschi B, et al. Genenames.org: the HGNC and VGNC resources in 2019. Nucleic Acids Res. 2019.",
                typical_evidence_types=["GENE_NOMENCLATURE"]
            )
        }
    
    def _initialize_narrative_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize sophisticated narrative patterns for different contexts"""
        return {
            "evidence_strength": {
                "tier_1_2": [  # FDA/Guidelines
                    "is established by {sources}",
                    "has been validated through {sources}",
                    "is supported by regulatory guidance from {sources}",
                    "is documented in {sources}"
                ],
                "tier_3": [  # Expert curated
                    "is supported by expert curation in {sources}",
                    "has been evaluated by {sources}",
                    "is documented in {sources}",
                    "shows evidence in {sources}"
                ],
                "tier_4_5": [  # Research/computational
                    "is suggested by {sources}",
                    "shows evidence in {sources}",
                    "is indicated by analysis in {sources}",
                    "demonstrates patterns in {sources}"
                ]
            },
            
            "evidence_synthesis": {
                "strong_consensus": [
                    "Multiple authoritative sources, including {primary_sources}, consistently demonstrate {conclusion}",
                    "Converging evidence from {primary_sources} and additional studies establishes {conclusion}",
                    "Both regulatory guidance and expert curation support {conclusion}",
                    "Strong consensus across {source_count} independent sources indicates {conclusion}"
                ],
                "moderate_consensus": [
                    "Evidence from {primary_sources} supports {conclusion}",
                    "Multiple sources, including {primary_sources}, suggest {conclusion}",
                    "Clinical data from {primary_sources} indicates {conclusion}"
                ],
                "limited_evidence": [
                    "Available evidence from {primary_sources} suggests {conclusion}",
                    "Limited data from {primary_sources} indicates {conclusion}",
                    "Preliminary evidence suggests {conclusion}"
                ]
            },
            
            "therapeutic_implications": {
                "fda_approved": [
                    "FDA-approved therapies are available",
                    "Regulatory-approved treatments include",
                    "FDA-recognized therapeutic options comprise"
                ],
                "guideline_recommended": [
                    "Professional guidelines recommend",
                    "Clinical practice guidelines support",
                    "Expert consensus guidelines indicate"
                ],
                "investigational": [
                    "Investigational therapies may include",
                    "Clinical trials are evaluating",
                    "Potential therapeutic approaches include"
                ]
            },
            
            "transitions": {
                "additive": ["Additionally", "Furthermore", "Moreover", "In addition"],
                "elaborative": ["Specifically", "Notably", "In particular", "Of significance"],
                "contrastive": ["However", "Conversely", "In contrast", "Nevertheless"],
                "consequential": ["Therefore", "Consequently", "As a result", "Thus"]
            }
        }
    
    def generate_enhanced_narrative(self,
                                  evidence_list: List[Evidence],
                                  text_type: CannedTextType,
                                  context: Dict[str, Any]) -> CannedText:
        """
        Generate enhanced narrative with reliable citations and source ordering
        
        Process:
        1. Check cache for existing narrative
        2. Clean and validate evidence
        3. Cluster evidence by conclusion/theme
        4. Order sources by reliability
        5. Generate narrative with inline citations
        6. Add comprehensive reference list
        7. Cache and validate output quality
        """
        
        # Step 0: Check cache for existing narrative
        evidence_hash = self._hash_evidence_list(evidence_list)
        context_str = f"{text_type.value}:{context.get('gene_symbol', '')}:{context.get('cancer_type', '')}"
        cache_key = f"{evidence_hash}:{hashlib.md5(context_str.encode()).hexdigest()[:8]}"
        
        cached_narrative = self._get_cached_narrative(cache_key)
        if cached_narrative:
            logger.debug(f"Using cached narrative for {text_type}")
            return cached_narrative
        
        # Reset citation tracking for this narrative
        self.citation_registry = {}
        self.source_counter = 0
        
        # Step 1: Process and validate evidence
        processed_evidence = self._process_and_validate_evidence(evidence_list)
        
        if not processed_evidence:
            return self._create_minimal_narrative(text_type, context)
        
        # Step 2: Cluster evidence by themes/conclusions
        evidence_clusters = self._cluster_evidence_by_conclusion(processed_evidence, text_type)
        
        # Step 3: Order and assign citations
        ordered_clusters = self._order_clusters_by_reliability(evidence_clusters)
        self._assign_citation_numbers(ordered_clusters)
        
        # Step 4: Generate narrative sections
        narrative_sections = []
        for cluster in ordered_clusters:
            section = self._generate_cluster_narrative(cluster, text_type, context)
            if section:
                narrative_sections.append(section)
        
        # Step 5: Combine sections with transitions
        main_narrative = self._combine_sections_with_transitions(narrative_sections, text_type)
        
        # Step 6: Add citations and references
        narrative_with_citations = self._add_inline_citations(main_narrative, ordered_clusters)
        reference_section = self._generate_reference_section()
        
        final_content = narrative_with_citations + "\n\n" + reference_section
        
        # Step 7: Calculate confidence and validate
        confidence = self._calculate_narrative_confidence(ordered_clusters)
        
        # Step 8: Extract evidence support
        evidence_support = [
            f"{e.source_kb}:{e.evidence_type}" 
            for cluster in ordered_clusters 
            for e in cluster.evidence_pieces
        ]
        
        # Create final narrative
        narrative = CannedText(
            text_type=text_type,
            content=final_content,
            confidence=confidence,
            evidence_support=list(set(evidence_support)),
            triggered_by=[f"Enhanced narrative from {len(processed_evidence)} sources"]
        )
        
        # Cache the generated narrative for future use
        self._cache_narrative(cache_key, narrative)
        
        return narrative
    
    def _process_and_validate_evidence(self, evidence_list: List[Evidence]) -> List[Evidence]:
        """Clean and validate evidence for narrative generation"""
        
        processed = []
        
        for evidence in evidence_list:
            # Skip if missing critical information
            if not evidence.source_kb or not evidence.description:
                logger.debug(f"Skipping evidence with missing information: {evidence}")
                continue
            
            # Normalize source names
            normalized_source = self._normalize_source_name(evidence.source_kb)
            evidence.source_kb = normalized_source
            
            # Validate source is known
            if normalized_source not in self.source_catalog:
                logger.warning(f"Unknown source: {normalized_source}")
                # Add to catalog with default metadata
                self.source_catalog[normalized_source] = SourceMetadata(
                    source_name=normalized_source,
                    reliability_tier=4,
                    citation_format=f"{normalized_source} database",
                    typical_evidence_types=["UNKNOWN"]
                )
            
            processed.append(evidence)
        
        return processed
    
    def _normalize_source_name(self, source_name: str) -> str:
        """Normalize source names to standard catalog keys"""
        
        # Common variations and mappings
        normalizations = {
            "ONCO_KB": "ONCOKB",
            "ONCO-KB": "ONCOKB", 
            "OncoKB": "ONCOKB",
            "CIViC": "CIVIC",
            "civic": "CIVIC",
            "ClinVar": "CLINVAR",
            "clinvar": "CLINVAR",
            "gnomAD": "GNOMAD",
            "gnomad": "GNOMAD",
            "AlphaMissense": "ALPHAMISSENSE",
            "COSMIC_CGC": "COSMIC",
            "cosmic": "COSMIC",
            "Cancer_Hotspots": "CANCER_HOTSPOTS",
            "MSK_Hotspots": "CANCER_HOTSPOTS",
            "UniProt": "UNIPROT",
            "uniprot": "UNIPROT",
            "NCBI_Gene": "NCBI_GENE",
            "ncbi_gene": "NCBI_GENE"
        }
        
        return normalizations.get(source_name, source_name.upper())
    
    def _cluster_evidence_by_conclusion(self,
                                      evidence_list: List[Evidence],
                                      text_type: CannedTextType) -> List[EvidenceCluster]:
        """Group evidence pieces that support similar conclusions"""
        
        # Define clustering strategies by text type
        if text_type == CannedTextType.VARIANT_DX_INTERPRETATION:
            return self._cluster_variant_interpretation_evidence(evidence_list)
        elif text_type == CannedTextType.GENE_DX_INTERPRETATION:
            return self._cluster_gene_interpretation_evidence(evidence_list)
        elif text_type == CannedTextType.GENERAL_VARIANT_INFO:
            return self._cluster_variant_info_evidence(evidence_list)
        elif text_type == CannedTextType.BIOMARKERS:
            return self._cluster_biomarker_evidence(evidence_list)
        else:
            return self._cluster_generic_evidence(evidence_list)
    
    def _cluster_variant_interpretation_evidence(self, evidence_list: List[Evidence]) -> List[EvidenceCluster]:
        """Cluster evidence for variant clinical interpretation"""
        
        clusters = []
        
        # Group by evidence theme
        therapeutic_evidence = []
        pathogenicity_evidence = []
        resistance_evidence = []
        population_evidence = []
        computational_evidence = []
        
        for evidence in evidence_list:
            evidence_type = evidence.evidence_type.lower()
            description = evidence.description.lower()
            
            if "therapeutic" in evidence_type or any(word in description for word in ["therapy", "treatment", "drug", "inhibitor"]):
                if "resistance" in description:
                    resistance_evidence.append(evidence)
                else:
                    therapeutic_evidence.append(evidence)
            elif any(word in evidence_type for word in ["pathogenic", "oncogenic", "clinical_significance"]):
                pathogenicity_evidence.append(evidence)
            elif "population" in evidence_type or evidence.source_kb == "GNOMAD":
                population_evidence.append(evidence)
            elif evidence.source_kb in ["ALPHAMISSENSE", "REVEL", "CADD", "SIFT", "POLYPHEN"]:
                computational_evidence.append(evidence)
            else:
                # Default to pathogenicity cluster
                pathogenicity_evidence.append(evidence)
        
        # Create clusters
        if therapeutic_evidence:
            clusters.append(self._create_evidence_cluster(
                "therapeutic significance",
                therapeutic_evidence,
                "Therapeutic implications"
            ))
        
        if pathogenicity_evidence:
            clusters.append(self._create_evidence_cluster(
                "clinical significance", 
                pathogenicity_evidence,
                "Clinical significance"
            ))
        
        if resistance_evidence:
            clusters.append(self._create_evidence_cluster(
                "therapeutic resistance",
                resistance_evidence, 
                "Resistance mechanisms"
            ))
        
        if population_evidence:
            clusters.append(self._create_evidence_cluster(
                "population frequency",
                population_evidence,
                "Population context"
            ))
        
        if computational_evidence:
            clusters.append(self._create_evidence_cluster(
                "computational prediction",
                computational_evidence,
                "Functional predictions"
            ))
        
        return clusters
    
    def _cluster_gene_interpretation_evidence(self, evidence_list: List[Evidence]) -> List[EvidenceCluster]:
        """Cluster evidence for gene clinical interpretation"""
        
        function_evidence = []
        cancer_role_evidence = []
        therapeutic_evidence = []
        
        for evidence in evidence_list:
            evidence_type = evidence.evidence_type.lower()
            
            if any(word in evidence_type for word in ["function", "protein", "pathway"]):
                function_evidence.append(evidence)
            elif any(word in evidence_type for word in ["cancer", "oncogene", "tumor_suppressor"]):
                cancer_role_evidence.append(evidence)
            elif "therapeutic" in evidence_type:
                therapeutic_evidence.append(evidence)
            else:
                # Default based on source
                if evidence.source_kb in ["UNIPROT", "NCBI_GENE"]:
                    function_evidence.append(evidence)
                elif evidence.source_kb in ["COSMIC", "ONCOKB"]:
                    cancer_role_evidence.append(evidence)
                else:
                    function_evidence.append(evidence)
        
        clusters = []
        
        if function_evidence:
            clusters.append(self._create_evidence_cluster(
                "gene function",
                function_evidence,
                "Molecular function"
            ))
        
        if cancer_role_evidence:
            clusters.append(self._create_evidence_cluster(
                "cancer role",
                cancer_role_evidence,
                "Role in cancer"
            ))
        
        if therapeutic_evidence:
            clusters.append(self._create_evidence_cluster(
                "therapeutic relevance",
                therapeutic_evidence,
                "Therapeutic context"
            ))
        
        return clusters
    
    def _cluster_variant_info_evidence(self, evidence_list: List[Evidence]) -> List[EvidenceCluster]:
        """Cluster evidence for general variant information"""
        
        frequency_evidence = []
        consequence_evidence = []
        hotspot_evidence = []
        prediction_evidence = []
        
        for evidence in evidence_list:
            if evidence.source_kb == "GNOMAD":
                frequency_evidence.append(evidence)
            elif "hotspot" in evidence.evidence_type.lower():
                hotspot_evidence.append(evidence)
            elif evidence.source_kb in ["ALPHAMISSENSE", "REVEL", "CADD", "SIFT", "POLYPHEN"]:
                prediction_evidence.append(evidence)
            else:
                consequence_evidence.append(evidence)
        
        clusters = []
        
        if frequency_evidence:
            clusters.append(self._create_evidence_cluster(
                "population frequency",
                frequency_evidence,
                "Population frequency"
            ))
        
        if hotspot_evidence:
            clusters.append(self._create_evidence_cluster(
                "recurrence pattern",
                hotspot_evidence,
                "Mutational hotspot"
            ))
        
        if prediction_evidence:
            clusters.append(self._create_evidence_cluster(
                "functional impact",
                prediction_evidence,
                "Predicted functional impact"
            ))
        
        if consequence_evidence:
            clusters.append(self._create_evidence_cluster(
                "molecular consequence",
                consequence_evidence,
                "Molecular consequence"
            ))
        
        return clusters
    
    def _cluster_biomarker_evidence(self, evidence_list: List[Evidence]) -> List[EvidenceCluster]:
        """Cluster evidence for biomarker interpretation"""
        
        # For biomarkers, typically each piece is its own cluster
        clusters = []
        
        for evidence in evidence_list:
            clusters.append(self._create_evidence_cluster(
                f"biomarker evidence",
                [evidence],
                f"Biomarker assessment"
            ))
        
        return clusters
    
    def _cluster_generic_evidence(self, evidence_list: List[Evidence]) -> List[EvidenceCluster]:
        """Generic clustering for other text types"""
        
        # Simple clustering by source reliability
        high_tier = []
        mid_tier = []
        low_tier = []
        
        for evidence in evidence_list:
            source_meta = self.source_catalog.get(evidence.source_kb)
            if source_meta:
                if source_meta.reliability_tier <= 2:
                    high_tier.append(evidence)
                elif source_meta.reliability_tier <= 3:
                    mid_tier.append(evidence)
                else:
                    low_tier.append(evidence)
            else:
                mid_tier.append(evidence)
        
        clusters = []
        
        if high_tier:
            clusters.append(self._create_evidence_cluster(
                "authoritative evidence",
                high_tier,
                "Regulatory and guideline evidence"
            ))
        
        if mid_tier:
            clusters.append(self._create_evidence_cluster(
                "expert evidence",
                mid_tier,
                "Expert-curated evidence"
            ))
        
        if low_tier:
            clusters.append(self._create_evidence_cluster(
                "research evidence",
                low_tier,
                "Research and computational evidence"
            ))
        
        return clusters
    
    def _create_evidence_cluster(self,
                               conclusion: str,
                               evidence_pieces: List[Evidence],
                               cluster_label: str) -> EvidenceCluster:
        """Create an evidence cluster with proper source ordering"""
        
        if not evidence_pieces:
            raise ValueError("Cannot create cluster with no evidence")
        
        # Sort evidence by reliability
        sorted_evidence = sorted(
            evidence_pieces,
            key=lambda e: (
                self.source_catalog.get(e.source_kb, SourceMetadata("", 5, "")).reliability_tier,
                -e.score  # Higher score first within same tier
            )
        )
        
        primary_source = sorted_evidence[0].source_kb
        supporting_sources = [e.source_kb for e in sorted_evidence[1:]]
        
        # Calculate cluster confidence
        confidence = self._calculate_cluster_confidence(sorted_evidence)
        
        return EvidenceCluster(
            conclusion=conclusion,
            evidence_pieces=sorted_evidence,
            primary_source=primary_source,
            supporting_sources=supporting_sources,
            confidence_score=confidence,
            citation_numbers=[]  # Will be assigned later
        )
    
    def _calculate_cluster_confidence(self, evidence_pieces: List[Evidence]) -> float:
        """Calculate confidence score for an evidence cluster"""
        
        if not evidence_pieces:
            return 0.0
        
        # Base confidence from evidence scores
        scores = [e.score for e in evidence_pieces]
        base_confidence = sum(scores) / (len(scores) * 10)  # Normalize to 0-1
        
        # Boost for multiple high-tier sources
        tier_1_2_count = sum(
            1 for e in evidence_pieces
            if self.source_catalog.get(e.source_kb, SourceMetadata("", 5, "")).reliability_tier <= 2
        )
        
        tier_3_count = sum(
            1 for e in evidence_pieces  
            if self.source_catalog.get(e.source_kb, SourceMetadata("", 5, "")).reliability_tier == 3
        )
        
        # Apply boosts
        if tier_1_2_count >= 2:
            base_confidence *= 1.3
        elif tier_1_2_count >= 1:
            base_confidence *= 1.2
        
        if tier_3_count >= 2:
            base_confidence *= 1.1
        
        return min(base_confidence, 1.0)
    
    def _order_clusters_by_reliability(self, clusters: List[EvidenceCluster]) -> List[EvidenceCluster]:
        """Order clusters by evidence reliability and clinical importance"""
        
        return sorted(clusters, key=lambda c: (
            # Primary sort: highest tier of primary source
            self.source_catalog.get(c.primary_source, SourceMetadata("", 5, "")).reliability_tier,
            # Secondary sort: confidence (descending)
            -c.confidence_score,
            # Tertiary sort: number of supporting sources (descending)
            -len(c.supporting_sources)
        ))
    
    def _assign_citation_numbers(self, ordered_clusters: List[EvidenceCluster]) -> None:
        """Assign citation numbers to all sources across clusters"""
        
        citation_counter = 1
        
        for cluster in ordered_clusters:
            cluster_citations = []
            
            # Process all sources in the cluster
            all_sources = [cluster.primary_source] + cluster.supporting_sources
            
            for source in all_sources:
                if source not in self.citation_registry:
                    self.citation_registry[source] = citation_counter
                    citation_counter += 1
                
                cluster_citations.append(self.citation_registry[source])
            
            cluster.citation_numbers = cluster_citations
    
    def _generate_cluster_narrative(self,
                                  cluster: EvidenceCluster,
                                  text_type: CannedTextType,
                                  context: Dict[str, Any]) -> str:
        """Generate narrative text for a single evidence cluster"""
        
        primary_source = cluster.primary_source
        primary_meta = self.source_catalog.get(primary_source)
        
        if not primary_meta:
            return ""
        
        # Determine narrative style based on source tier
        if primary_meta.reliability_tier <= 2:
            # High authority sources
            narrative_patterns = self.narrative_patterns["evidence_strength"]["tier_1_2"]
        elif primary_meta.reliability_tier == 3:
            # Expert curated
            narrative_patterns = self.narrative_patterns["evidence_strength"]["tier_3"]
        else:
            # Research/computational
            narrative_patterns = self.narrative_patterns["evidence_strength"]["tier_4_5"]
        
        # Select pattern based on cluster content
        pattern = narrative_patterns[0]  # Default to first pattern
        
        # Build narrative content based on cluster type
        if "therapeutic" in cluster.conclusion:
            content = self._build_therapeutic_narrative_content(cluster, context)
        elif "clinical significance" in cluster.conclusion or "pathogenic" in cluster.conclusion:
            content = self._build_significance_narrative_content(cluster, context)
        elif "function" in cluster.conclusion:
            content = self._build_function_narrative_content(cluster, context)
        elif "frequency" in cluster.conclusion:
            content = self._build_frequency_narrative_content(cluster, context)
        elif "computational" in cluster.conclusion or "prediction" in cluster.conclusion:
            content = self._build_computational_narrative_content(cluster, context)
        else:
            content = self._build_generic_narrative_content(cluster, context)
        
        # Build source attribution
        if cluster.supporting_sources:
            all_sources = [primary_source] + cluster.supporting_sources[:2]  # Limit to 3 sources
            source_text = ", ".join(all_sources)
        else:
            source_text = primary_source
        
        # Combine into narrative
        narrative = f"{content} {pattern.format(sources=source_text)}"
        
        return narrative
    
    def _build_therapeutic_narrative_content(self,
                                           cluster: EvidenceCluster,
                                           context: Dict[str, Any]) -> str:
        """Build therapeutic-specific narrative content"""
        
        # Extract therapeutic details from evidence
        therapies = []
        evidence_levels = []
        
        for evidence in cluster.evidence_pieces:
            if evidence.metadata:
                if "therapy" in evidence.metadata:
                    therapies.append(evidence.metadata["therapy"])
                if "evidence_level" in evidence.metadata:
                    evidence_levels.append(evidence.metadata["evidence_level"])
        
        # Determine therapeutic statement
        if any("FDA" in level or "Level 1" in level for level in evidence_levels):
            base_statement = "This variant has FDA-approved therapeutic implications"
        elif any("Level 2" in level or "guideline" in level.lower() for level in evidence_levels):
            base_statement = "Professional guidelines support therapeutic targeting of this variant"
        elif any("Level 3" in level for level in evidence_levels):
            base_statement = "Clinical evidence supports potential therapeutic benefit"
        else:
            base_statement = "Therapeutic targeting may be considered for this variant"
        
        # Add specific therapies
        if therapies:
            unique_therapies = list(set(therapies))
            if len(unique_therapies) == 1:
                base_statement += f" with {unique_therapies[0]}"
            elif len(unique_therapies) <= 3:
                base_statement += f" with agents including {', '.join(unique_therapies)}"
            else:
                base_statement += " with multiple targeted agents"
        
        return base_statement
    
    def _build_significance_narrative_content(self,
                                            cluster: EvidenceCluster,
                                            context: Dict[str, Any]) -> str:
        """Build clinical significance narrative content"""
        
        # Extract significance information
        classifications = []
        for evidence in cluster.evidence_pieces:
            desc_lower = evidence.description.lower()
            if "pathogenic" in desc_lower:
                classifications.append("pathogenic")
            elif "oncogenic" in desc_lower:
                classifications.append("oncogenic")
            elif "benign" in desc_lower:
                classifications.append("benign")
            elif "significant" in desc_lower:
                classifications.append("clinically significant")
        
        # Build significance statement
        if cluster.confidence_score > 0.8:
            confidence_phrase = "Strong evidence demonstrates"
        elif cluster.confidence_score > 0.6:
            confidence_phrase = "Evidence supports"
        else:
            confidence_phrase = "Available data suggests"
        
        if classifications:
            primary_classification = classifications[0]
            statement = f"{confidence_phrase} this variant is {primary_classification}"
        else:
            statement = f"{confidence_phrase} clinical significance"
        
        # Add cancer type context
        cancer_type = context.get("cancer_type")
        if cancer_type and cancer_type != "cancer":
            statement += f" in {cancer_type}"
        
        return statement
    
    def _build_function_narrative_content(self,
                                        cluster: EvidenceCluster,
                                        context: Dict[str, Any]) -> str:
        """Build gene function narrative content"""
        
        # Extract functional information
        functions = []
        pathways = []
        
        for evidence in cluster.evidence_pieces:
            if evidence.metadata:
                if "protein_function" in evidence.metadata:
                    functions.append(evidence.metadata["protein_function"])
                if "pathway" in evidence.metadata:
                    pathways.append(evidence.metadata["pathway"])
        
        gene_symbol = context.get("gene_symbol", "This gene")
        
        if functions:
            function_text = functions[0]
            statement = f"{gene_symbol} encodes {function_text}"
        else:
            statement = f"{gene_symbol} plays an important role in cellular processes"
        
        if pathways:
            pathway_text = pathways[0]
            statement += f" and is involved in {pathway_text}"
        
        return statement
    
    def _build_frequency_narrative_content(self,
                                         cluster: EvidenceCluster,
                                         context: Dict[str, Any]) -> str:
        """Build population frequency narrative content"""
        
        for evidence in cluster.evidence_pieces:
            if evidence.source_kb == "GNOMAD" and evidence.metadata:
                if "af" in evidence.metadata:
                    af = evidence.metadata["af"]
                    if af == 0:
                        return "This variant is absent from population databases"
                    elif af < 0.0001:
                        return f"This variant is extremely rare in the general population (AF: {af:.2e})"
                    elif af < 0.01:
                        return f"This variant is rare in the general population (AF: {af:.1%})"
                    else:
                        return f"This variant is present in {af:.1%} of the general population"
        
        return "Population frequency information is available"
    
    def _build_computational_narrative_content(self,
                                             cluster: EvidenceCluster,
                                             context: Dict[str, Any]) -> str:
        """Build computational prediction narrative content"""
        
        predictions = []
        scores = []
        
        for evidence in cluster.evidence_pieces:
            if evidence.metadata:
                if "classification" in evidence.metadata:
                    predictions.append(f"{evidence.source_kb}: {evidence.metadata['classification']}")
                if "score" in evidence.metadata:
                    scores.append(f"{evidence.source_kb}: {evidence.metadata['score']}")
        
        if predictions:
            primary_pred = predictions[0].split(": ")[1]
            statement = f"Computational analysis predicts this variant to be {primary_pred}"
        else:
            statement = "Computational predictions suggest functional impact"
        
        if len(predictions) > 1:
            statement += f", with consistent predictions from {len(predictions)} algorithms"
        
        return statement
    
    def _build_generic_narrative_content(self,
                                       cluster: EvidenceCluster,
                                       context: Dict[str, Any]) -> str:
        """Build generic narrative content"""
        
        primary_evidence = cluster.evidence_pieces[0]
        
        # Use the primary evidence description as base
        base_content = primary_evidence.description
        
        # Clean up and standardize
        if base_content.endswith('.'):
            base_content = base_content[:-1]
        
        return f"Analysis indicates {base_content.lower()}"
    
    def _combine_sections_with_transitions(self,
                                         sections: List[str],
                                         text_type: CannedTextType) -> str:
        """Combine narrative sections with appropriate transitions"""
        
        if not sections:
            return ""
        
        if len(sections) == 1:
            return sections[0]
        
        # Select transitions based on text type
        transitions = self.narrative_patterns["transitions"]["additive"]
        
        result = sections[0]
        
        for i, section in enumerate(sections[1:]):
            transition = transitions[min(i, len(transitions) - 1)]
            result += f". {transition}, {section.lower()}"
        
        return result
    
    def _add_inline_citations(self,
                            narrative: str,
                            clusters: List[EvidenceCluster]) -> str:
        """Add inline citation numbers to narrative"""
        
        narrative_with_citations = narrative
        
        for cluster in clusters:
            primary_source = cluster.primary_source
            citation_num = self.citation_registry.get(primary_source)
            
            if citation_num:
                # Add citation after source mention
                pattern = rf'\b{re.escape(primary_source)}\b'
                replacement = f"{primary_source}^{citation_num}"
                narrative_with_citations = re.sub(
                    pattern, replacement, narrative_with_citations, count=1
                )
        
        return narrative_with_citations
    
    def _generate_reference_section(self) -> str:
        """Generate comprehensive reference section"""
        
        if not self.citation_registry:
            return ""
        
        reference_lines = ["References:"]
        
        # Sort by citation number
        sorted_citations = sorted(
            self.citation_registry.items(),
            key=lambda x: x[1]
        )
        
        for source, number in sorted_citations:
            source_meta = self.source_catalog.get(source)
            if source_meta:
                citation_text = source_meta.citation_format
                
                # Handle special formatting
                if source_meta.pmid_support and "{pmids}" in citation_text:
                    # Would need PMIDs from evidence metadata
                    citation_text = citation_text.replace("{pmids}", "multiple")
                
                citation_text = citation_text.replace("{date}", "accessed 2024")
                citation_text = citation_text.replace("{title}", f"{source} data")
                citation_text = citation_text.replace("{version}", "current")
                citation_text = citation_text.replace("{guideline}", f"{source} guidelines")
                citation_text = citation_text.replace("{journal}", "multiple sources")
                
                reference_lines.append(f"{number}. {citation_text}")
            else:
                reference_lines.append(f"{number}. {source} database.")
        
        return "\n".join(reference_lines)
    
    def _calculate_narrative_confidence(self, clusters: List[EvidenceCluster]) -> float:
        """Calculate overall narrative confidence"""
        
        if not clusters:
            return 0.0
        
        # Weight clusters by reliability
        weighted_scores = []
        total_weight = 0
        
        for cluster in clusters:
            primary_meta = self.source_catalog.get(cluster.primary_source)
            if primary_meta:
                # Higher weight for more reliable sources
                weight = 6 - primary_meta.reliability_tier  # Tier 1 gets weight 5, tier 5 gets weight 1
                weighted_scores.append(cluster.confidence_score * weight)
                total_weight += weight
            else:
                weighted_scores.append(cluster.confidence_score)
                total_weight += 1
        
        if total_weight == 0:
            return 0.0
        
        base_confidence = sum(weighted_scores) / total_weight
        
        # Boost for multiple high-quality clusters
        high_quality_clusters = sum(
            1 for cluster in clusters
            if cluster.confidence_score > 0.7 and 
            self.source_catalog.get(cluster.primary_source, SourceMetadata("", 5, "")).reliability_tier <= 3
        )
        
        if high_quality_clusters >= 3:
            base_confidence *= 1.3
        elif high_quality_clusters >= 2:
            base_confidence *= 1.2
        
        return min(base_confidence, 1.0)
    
    def _create_minimal_narrative(self,
                                text_type: CannedTextType,
                                context: Dict[str, Any]) -> CannedText:
        """Create minimal narrative when no evidence is available"""
        
        content = "Limited information is available for this variant."
        
        return CannedText(
            text_type=text_type,
            content=content,
            confidence=0.1,
            evidence_support=[],
            triggered_by=["Minimal narrative - no evidence"]
        )
    
    # Performance optimization methods
    
    def _hash_evidence_list(self, evidence_list: List[Evidence]) -> str:
        """Create hash of evidence list for caching"""
        if not evidence_list:
            return "empty"
        
        # Create stable hash based on evidence content
        evidence_strings = []
        for evidence in evidence_list:
            evidence_str = f"{evidence.source_kb}:{evidence.evidence_type}:{evidence.description[:100]}"
            evidence_strings.append(evidence_str)
        
        # Sort for consistent hashing
        evidence_strings.sort()
        import hashlib
        return hashlib.md5("||".join(evidence_strings).encode()).hexdigest()[:16]
    
    def _get_cached_narrative(self, cache_key: str) -> Optional[CannedText]:
        """Get cached narrative if available"""
        if not self.enable_caching:
            return None
        return self._narrative_cache.get(cache_key)
    
    def _cache_narrative(self, cache_key: str, narrative: CannedText) -> None:
        """Cache generated narrative"""
        if not self.enable_caching:
            return
        
        # Limit cache size to prevent memory issues
        if len(self._narrative_cache) > 1000:
            # Remove oldest entries (simple LRU)
            keys_to_remove = list(self._narrative_cache.keys())[:100]
            for key in keys_to_remove:
                del self._narrative_cache[key]
        
        self._narrative_cache[cache_key] = narrative
    
    def clear_caches(self) -> None:
        """Clear all performance caches"""
        self._evidence_cluster_cache.clear()
        self._template_cache.clear()
        self._narrative_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache usage statistics"""
        return {
            "evidence_clusters_cached": len(self._evidence_cluster_cache),
            "templates_cached": len(self._template_cache),
            "narratives_cached": len(self._narrative_cache)
        }