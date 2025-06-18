"""
Narrative Generation and Citation Management System

This module handles:
1. Weaving information from multiple sources into coherent narratives
2. Adding proper citations based on source databases
3. Managing evidence quality and confidence
4. Creating flowing, readable clinical text
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import re
import logging

from .models import Evidence, CannedText, CannedTextType

logger = logging.getLogger(__name__)


class SourceReliability(str, Enum):
    """Source reliability levels for evidence weighting"""
    FDA_APPROVED = "fda_approved"      # FDA labels, approvals
    PROFESSIONAL_GUIDELINES = "guidelines"  # NCCN, CAP, ASCO guidelines
    EXPERT_CURATED = "expert_curated"  # OncoKB, CIViC expert panels
    PEER_REVIEWED = "peer_reviewed"    # Literature with PMID
    COMPUTATIONAL = "computational"    # In silico predictions
    COMMUNITY = "community"            # COSMIC, crowd-sourced data


@dataclass
class EvidencePiece:
    """A piece of evidence with metadata for narrative building"""
    content: str
    source_db: str
    reliability: SourceReliability
    confidence: float
    evidence_type: str
    pmids: List[str] = field(default_factory=list)
    url: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    
@dataclass
class Citation:
    """Citation information for sources"""
    source_db: str
    citation_text: str
    reliability: SourceReliability
    pmids: List[str] = field(default_factory=list)
    url: Optional[str] = None
    access_date: Optional[str] = None


class NarrativeWeaver:
    """
    Weaves information from multiple sources into coherent narratives
    with proper citations and evidence synthesis
    """
    
    def __init__(self):
        self.source_priorities = self._initialize_source_priorities()
        self.citation_formats = self._initialize_citation_formats()
        self.narrative_templates = self._initialize_narrative_templates()
        
    def _initialize_source_priorities(self) -> Dict[str, Tuple[SourceReliability, int]]:
        """Initialize source reliability and priority rankings"""
        return {
            # FDA and regulatory (highest priority)
            "FDA": (SourceReliability.FDA_APPROVED, 10),
            "EMA": (SourceReliability.FDA_APPROVED, 10),
            
            # Professional guidelines
            "NCCN": (SourceReliability.PROFESSIONAL_GUIDELINES, 9),
            "CAP": (SourceReliability.PROFESSIONAL_GUIDELINES, 9),
            "ASCO": (SourceReliability.PROFESSIONAL_GUIDELINES, 9),
            "ESMO": (SourceReliability.PROFESSIONAL_GUIDELINES, 9),
            
            # Expert curated databases
            "ONCOKB": (SourceReliability.EXPERT_CURATED, 8),
            "CIVIC": (SourceReliability.EXPERT_CURATED, 8),
            "CLINGEN": (SourceReliability.EXPERT_CURATED, 8),
            "CLINVAR": (SourceReliability.EXPERT_CURATED, 7),
            
            # Literature and clinical studies
            "PUBMED": (SourceReliability.PEER_REVIEWED, 6),
            "LITERATURE": (SourceReliability.PEER_REVIEWED, 6),
            
            # Computational predictions
            "ALPHAMISSENSE": (SourceReliability.COMPUTATIONAL, 5),
            "REVEL": (SourceReliability.COMPUTATIONAL, 5),
            "CADD": (SourceReliability.COMPUTATIONAL, 5),
            "SIFT": (SourceReliability.COMPUTATIONAL, 4),
            "POLYPHEN": (SourceReliability.COMPUTATIONAL, 4),
            
            # Community databases
            "COSMIC": (SourceReliability.COMMUNITY, 6),
            "CANCER_HOTSPOTS": (SourceReliability.COMMUNITY, 6),
            "GNOMAD": (SourceReliability.COMMUNITY, 7),
            
            # Other databases
            "UNIPROT": (SourceReliability.EXPERT_CURATED, 7),
            "NCBI_GENE": (SourceReliability.EXPERT_CURATED, 7),
            "HGNC": (SourceReliability.EXPERT_CURATED, 8)
        }
    
    def _initialize_citation_formats(self) -> Dict[str, str]:
        """Initialize citation format templates for different sources"""
        return {
            "ONCOKB": "OncoKB Precision Oncology Knowledge Base (accessed {date})",
            "CIVIC": "Clinical Interpretation of Variants in Cancer (CIViC) database",
            "CLINVAR": "ClinVar database, National Center for Biotechnology Information",
            "COSMIC": "Catalogue of Somatic Mutations in Cancer (COSMIC)",
            "FDA": "U.S. Food and Drug Administration",
            "NCCN": "National Comprehensive Cancer Network Guidelines",
            "GNOMAD": "Genome Aggregation Database (gnomAD)",
            "ALPHAMISSENSE": "AlphaMissense: accurate prediction of protein variant effects",
            "CANCER_HOTSPOTS": "Cancer Hotspots database (Memorial Sloan Kettering)",
            "UNIPROT": "UniProt Knowledgebase",
            "NCBI_GENE": "NCBI Gene database",
            "PUBMED": "PubMed PMID: {pmids}",
            "DEFAULT": "{source_db} database"
        }
    
    def _initialize_narrative_templates(self) -> Dict[str, List[str]]:
        """Initialize narrative flow templates"""
        return {
            "evidence_integration": [
                "Multiple lines of evidence support {conclusion}.",
                "Converging evidence from {sources} indicates {conclusion}.",
                "Both {source1} and {source2} demonstrate {conclusion}.",
                "Consistent with findings from {sources}, {conclusion}."
            ],
            
            "hierarchy_statements": [
                "FDA-approved indications show {statement}.",
                "Professional guidelines recommend {statement}.",
                "Expert-curated databases indicate {statement}.",
                "Computational predictions suggest {statement}.",
                "Literature reports describe {statement}."
            ],
            
            "confidence_qualifiers": [
                "Strong evidence demonstrates",      # High confidence
                "Multiple studies support",         # High confidence  
                "Evidence suggests",                # Medium confidence
                "Limited data indicates",           # Lower confidence
                "Preliminary reports suggest"       # Low confidence
            ],
            
            "therapeutic_flow": [
                "{drug} is {approval_status} for {indication} based on {evidence_level} evidence.",
                "Clinical studies demonstrate {response} to {drug} in patients with {biomarker}.",
                "Response rates of {rate} have been reported with {drug} therapy.",
                "Resistance to {drug} may occur through {mechanism}."
            ]
        }
    
    def generate_narrative(self,
                         evidence_list: List[Evidence],
                         text_type: CannedTextType,
                         context: Dict[str, Any]) -> Tuple[str, List[Citation], float]:
        """
        Generate a cohesive narrative from multiple evidence sources
        
        Returns:
            Tuple of (narrative_text, citations, confidence_score)
        """
        # Convert evidence to structured pieces
        evidence_pieces = self._process_evidence(evidence_list)
        
        # Group evidence by theme/topic
        themed_evidence = self._group_evidence_by_theme(evidence_pieces, text_type)
        
        # Synthesize evidence within themes
        synthesized_themes = {}
        for theme, pieces in themed_evidence.items():
            synthesized_themes[theme] = self._synthesize_evidence_group(pieces)
        
        # Build narrative flow
        narrative = self._build_narrative_flow(synthesized_themes, text_type, context)
        
        # Generate citations
        citations = self._generate_citations(evidence_pieces)
        
        # Calculate overall confidence
        confidence = self._calculate_narrative_confidence(evidence_pieces)
        
        return narrative, citations, confidence
    
    def _process_evidence(self, evidence_list: List[Evidence]) -> List[EvidencePiece]:
        """Convert Evidence objects to EvidencePiece objects with metadata"""
        pieces = []
        
        for evidence in evidence_list:
            # Determine source reliability
            reliability, priority = self.source_priorities.get(
                evidence.source_kb, 
                (SourceReliability.COMMUNITY, 3)
            )
            
            # Extract PMIDs if available
            pmids = []
            if evidence.metadata and "pmids" in evidence.metadata:
                pmids = evidence.metadata["pmids"]
            elif evidence.metadata and "pmid" in evidence.metadata:
                pmids = [evidence.metadata["pmid"]]
            
            # Create evidence piece
            piece = EvidencePiece(
                content=evidence.description,
                source_db=evidence.source_kb,
                reliability=reliability,
                confidence=evidence.score / 10.0,  # Normalize to 0-1
                evidence_type=evidence.evidence_type,
                pmids=pmids,
                details=evidence.metadata or {}
            )
            
            pieces.append(piece)
        
        return pieces
    
    def _group_evidence_by_theme(self,
                                evidence_pieces: List[EvidencePiece],
                                text_type: CannedTextType) -> Dict[str, List[EvidencePiece]]:
        """Group evidence pieces by thematic content"""
        themes = {
            "gene_function": [],
            "therapeutic": [],
            "diagnostic": [],
            "prognostic": [],
            "population_frequency": [],
            "computational_prediction": [],
            "hotspot": [],
            "clinical_significance": [],
            "resistance": [],
            "other": []
        }
        
        for piece in evidence_pieces:
            # Classify by evidence type
            evidence_type = piece.evidence_type.lower()
            
            if "therapeutic" in evidence_type or "treatment" in piece.content.lower():
                if "resistance" in piece.content.lower():
                    themes["resistance"].append(piece)
                else:
                    themes["therapeutic"].append(piece)
            elif "diagnostic" in evidence_type:
                themes["diagnostic"].append(piece)
            elif "prognostic" in evidence_type:
                themes["prognostic"].append(piece)
            elif "function" in evidence_type or piece.source_db in ["UNIPROT", "NCBI_GENE"]:
                themes["gene_function"].append(piece)
            elif "population" in evidence_type or piece.source_db == "GNOMAD":
                themes["population_frequency"].append(piece)
            elif piece.source_db in ["ALPHAMISSENSE", "REVEL", "CADD", "SIFT", "POLYPHEN"]:
                themes["computational_prediction"].append(piece)
            elif "hotspot" in evidence_type or piece.source_db == "CANCER_HOTSPOTS":
                themes["hotspot"].append(piece)
            elif piece.source_db in ["CLINVAR", "CIVIC"]:
                themes["clinical_significance"].append(piece)
            else:
                themes["other"].append(piece)
        
        # Remove empty themes
        return {k: v for k, v in themes.items() if v}
    
    def _synthesize_evidence_group(self, pieces: List[EvidencePiece]) -> Dict[str, Any]:
        """Synthesize a group of evidence pieces into a coherent statement"""
        if not pieces:
            return {}
        
        # Sort by reliability and confidence
        sorted_pieces = sorted(
            pieces,
            key=lambda p: (self.source_priorities.get(p.source_db, (SourceReliability.COMMUNITY, 0))[1], p.confidence),
            reverse=True
        )
        
        # Extract key information
        primary_piece = sorted_pieces[0]
        supporting_pieces = sorted_pieces[1:]
        
        # Check for consensus
        consensus_level = self._assess_consensus(sorted_pieces)
        
        # Build synthesized statement
        if consensus_level > 0.8:
            synthesis_prefix = "Multiple sources consistently show"
        elif consensus_level > 0.6:
            synthesis_prefix = "Evidence supports"
        else:
            synthesis_prefix = "Available data suggests"
        
        # Generate synthesis
        synthesis = {
            "primary_statement": primary_piece.content,
            "primary_source": primary_piece.source_db,
            "supporting_sources": [p.source_db for p in supporting_pieces],
            "consensus_level": consensus_level,
            "synthesis_prefix": synthesis_prefix,
            "confidence": max(p.confidence for p in pieces),
            "all_pieces": pieces
        }
        
        return synthesis
    
    def _assess_consensus(self, pieces: List[EvidencePiece]) -> float:
        """Assess level of consensus among evidence pieces"""
        if len(pieces) <= 1:
            return 1.0
        
        # Simple consensus based on similar conclusions
        primary = pieces[0].content.lower()
        
        agreement_count = 0
        for piece in pieces[1:]:
            content = piece.content.lower()
            
            # Check for key agreement indicators
            if any(word in primary and word in content for word in 
                   ["pathogenic", "oncogenic", "sensitive", "resistance", "benign"]):
                agreement_count += 1
        
        return agreement_count / (len(pieces) - 1) if len(pieces) > 1 else 1.0
    
    def _build_narrative_flow(self,
                            synthesized_themes: Dict[str, Dict[str, Any]],
                            text_type: CannedTextType,
                            context: Dict[str, Any]) -> str:
        """Build flowing narrative from synthesized themes"""
        
        narrative_parts = []
        
        # Define narrative order based on text type
        if text_type == CannedTextType.GENE_DX_INTERPRETATION:
            theme_order = ["gene_function", "clinical_significance", "therapeutic", "prognostic"]
        elif text_type == CannedTextType.VARIANT_DX_INTERPRETATION:
            theme_order = ["clinical_significance", "therapeutic", "hotspot", "computational_prediction", "resistance"]
        elif text_type == CannedTextType.GENERAL_VARIANT_INFO:
            theme_order = ["population_frequency", "computational_prediction", "hotspot"]
        else:
            theme_order = list(synthesized_themes.keys())
        
        # Build narrative section by section
        for theme in theme_order:
            if theme not in synthesized_themes:
                continue
                
            synthesis = synthesized_themes[theme]
            section = self._build_theme_section(theme, synthesis, context)
            if section:
                narrative_parts.append(section)
        
        # Connect sections with appropriate transitions
        narrative = self._add_narrative_transitions(narrative_parts)
        
        return narrative
    
    def _build_theme_section(self,
                           theme: str,
                           synthesis: Dict[str, Any],
                           context: Dict[str, Any]) -> str:
        """Build a narrative section for a specific theme"""
        
        prefix = synthesis.get("synthesis_prefix", "Evidence indicates")
        primary_statement = synthesis.get("primary_statement", "")
        primary_source = synthesis.get("primary_source", "")
        supporting_sources = synthesis.get("supporting_sources", [])
        
        # Theme-specific narrative building
        if theme == "therapeutic":
            section = self._build_therapeutic_narrative(synthesis, context)
        elif theme == "gene_function":
            section = self._build_gene_function_narrative(synthesis, context)
        elif theme == "clinical_significance":
            section = self._build_clinical_significance_narrative(synthesis, context)
        elif theme == "computational_prediction":
            section = self._build_computational_narrative(synthesis, context)
        elif theme == "population_frequency":
            section = self._build_population_narrative(synthesis, context)
        elif theme == "hotspot":
            section = self._build_hotspot_narrative(synthesis, context)
        else:
            # Generic narrative
            section = f"{prefix} that {primary_statement.lower()}"
        
        # Add source attribution
        if supporting_sources:
            all_sources = [primary_source] + supporting_sources[:2]  # Limit to 3 sources
            source_text = ", ".join(all_sources)
            section += f" (based on {source_text})"
        else:
            section += f" (based on {primary_source})"
        
        return section
    
    def _build_therapeutic_narrative(self,
                                   synthesis: Dict[str, Any],
                                   context: Dict[str, Any]) -> str:
        """Build therapeutic-specific narrative"""
        pieces = synthesis["all_pieces"]
        
        # Extract therapeutic details
        therapies = []
        evidence_levels = []
        
        for piece in pieces:
            if "therapy" in piece.details:
                therapies.append(piece.details["therapy"])
            if "evidence_level" in piece.details:
                evidence_levels.append(piece.details["evidence_level"])
        
        # Build narrative based on evidence strength
        if any("FDA" in level or "Level 1" in level for level in evidence_levels):
            narrative = f"This variant has FDA-approved therapeutic implications"
        elif any("Level 2" in level or "guideline" in level.lower() for level in evidence_levels):
            narrative = f"Professional guidelines support therapeutic targeting of this variant"
        else:
            narrative = f"Therapeutic targeting may be considered for this variant"
        
        # Add specific therapies if available
        if therapies:
            unique_therapies = list(set(therapies))
            if len(unique_therapies) == 1:
                narrative += f" with {unique_therapies[0]}"
            elif len(unique_therapies) <= 3:
                narrative += f" with agents including {', '.join(unique_therapies)}"
            else:
                narrative += f" with multiple targeted agents"
        
        return narrative
    
    def _build_gene_function_narrative(self,
                                     synthesis: Dict[str, Any],
                                     context: Dict[str, Any]) -> str:
        """Build gene function narrative"""
        pieces = synthesis["all_pieces"]
        
        # Extract functional information
        functions = []
        pathways = []
        
        for piece in pieces:
            if "protein_function" in piece.details:
                functions.append(piece.details["protein_function"])
            if "pathway" in piece.details:
                pathways.append(piece.details["pathway"])
        
        gene_symbol = context.get("gene_symbol", "This gene")
        
        if functions:
            function_text = functions[0]  # Use primary function
            narrative = f"{gene_symbol} encodes {function_text}"
        else:
            narrative = f"{gene_symbol} plays an important role in cellular function"
        
        if pathways:
            pathway_text = pathways[0]
            narrative += f" and is involved in {pathway_text}"
        
        return narrative
    
    def _build_clinical_significance_narrative(self,
                                             synthesis: Dict[str, Any],
                                             context: Dict[str, Any]) -> str:
        """Build clinical significance narrative"""
        confidence = synthesis.get("confidence", 0.5)
        consensus = synthesis.get("consensus_level", 0.5)
        
        if confidence > 0.8 and consensus > 0.8:
            narrative = "There is strong clinical evidence for the significance of this variant"
        elif confidence > 0.6:
            narrative = "Clinical evidence supports the significance of this variant"
        else:
            narrative = "Limited clinical evidence is available for this variant"
        
        # Add cancer type context if available
        cancer_type = context.get("cancer_type")
        if cancer_type:
            narrative += f" in {cancer_type}"
        
        return narrative
    
    def _build_computational_narrative(self,
                                     synthesis: Dict[str, Any],
                                     context: Dict[str, Any]) -> str:
        """Build computational prediction narrative"""
        pieces = synthesis["all_pieces"]
        
        # Extract prediction scores and classifications
        predictions = []
        scores = []
        
        for piece in pieces:
            if "classification" in piece.details:
                predictions.append(f"{piece.source_db}: {piece.details['classification']}")
            if "score" in piece.details:
                scores.append(f"{piece.source_db} score: {piece.details['score']}")
        
        if predictions:
            prediction_text = predictions[0]  # Use top prediction
            narrative = f"Computational analysis predicts this variant to be {prediction_text.split(': ')[1]}"
        else:
            narrative = "Computational predictions suggest potential functional impact"
        
        # Add consensus if multiple predictions agree
        if len(predictions) > 1:
            narrative += f", with supporting predictions from {len(predictions)} algorithms"
        
        return narrative
    
    def _build_population_narrative(self,
                                  synthesis: Dict[str, Any],
                                  context: Dict[str, Any]) -> str:
        """Build population frequency narrative"""
        pieces = synthesis["all_pieces"]
        
        for piece in pieces:
            if piece.source_db == "GNOMAD" and "af" in piece.details:
                af = piece.details["af"]
                if af == 0:
                    return "This variant is absent from population databases"
                elif af < 0.0001:
                    return f"This variant is extremely rare in the general population (AF: {af:.2e})"
                elif af < 0.01:
                    return f"This variant is rare in the general population (AF: {af:.1%})"
                else:
                    return f"This variant is present in {af:.1%} of the general population"
        
        return "Population frequency data is not available for this variant"
    
    def _build_hotspot_narrative(self,
                               synthesis: Dict[str, Any],
                               context: Dict[str, Any]) -> str:
        """Build hotspot narrative"""
        pieces = synthesis["all_pieces"]
        
        for piece in pieces:
            if "sample_count" in piece.details:
                count = piece.details["sample_count"]
                if count > 100:
                    return f"This position is a statistically significant mutational hotspot, observed in {count} samples"
                else:
                    return f"This position shows recurrent mutations ({count} samples)"
        
        return "This variant occurs at a known mutational hotspot"
    
    def _add_narrative_transitions(self, narrative_parts: List[str]) -> str:
        """Add smooth transitions between narrative sections"""
        if not narrative_parts:
            return ""
        
        if len(narrative_parts) == 1:
            return narrative_parts[0] + "."
        
        # Define transition words/phrases
        transitions = [
            "Additionally,",
            "Furthermore,", 
            "In terms of clinical significance,",
            "Regarding therapeutic implications,",
            "From a functional perspective,",
            "Notably,",
            "Moreover,"
        ]
        
        # Build connected narrative
        result = narrative_parts[0]
        
        for i, part in enumerate(narrative_parts[1:], 1):
            if i < len(transitions):
                transition = transitions[i-1]
            else:
                transition = "Furthermore,"
            
            result += f". {transition} {part.lower()}"
        
        return result + "."
    
    def _generate_citations(self, evidence_pieces: List[EvidencePiece]) -> List[Citation]:
        """Generate formatted citations for all sources"""
        citations = []
        seen_sources = set()
        
        # Sort pieces by reliability for citation order
        sorted_pieces = sorted(
            evidence_pieces,
            key=lambda p: self.source_priorities.get(p.source_db, (SourceReliability.COMMUNITY, 0))[1],
            reverse=True
        )
        
        for piece in sorted_pieces:
            if piece.source_db in seen_sources:
                continue
            
            seen_sources.add(piece.source_db)
            
            # Get citation format
            citation_format = self.citation_formats.get(
                piece.source_db,
                self.citation_formats["DEFAULT"]
            )
            
            # Format citation
            if piece.pmids:
                citation_text = citation_format.format(
                    pmids=", ".join(piece.pmids),
                    date="current",
                    source_db=piece.source_db
                )
            else:
                citation_text = citation_format.format(
                    date="current",
                    source_db=piece.source_db
                )
            
            citation = Citation(
                source_db=piece.source_db,
                citation_text=citation_text,
                reliability=piece.reliability,
                pmids=piece.pmids,
                url=piece.url
            )
            
            citations.append(citation)
        
        return citations
    
    def _calculate_narrative_confidence(self, evidence_pieces: List[EvidencePiece]) -> float:
        """Calculate overall confidence score for the narrative"""
        if not evidence_pieces:
            return 0.0
        
        # Weight by source reliability
        reliability_weights = {
            SourceReliability.FDA_APPROVED: 1.0,
            SourceReliability.PROFESSIONAL_GUIDELINES: 0.9,
            SourceReliability.EXPERT_CURATED: 0.8,
            SourceReliability.PEER_REVIEWED: 0.7,
            SourceReliability.COMPUTATIONAL: 0.5,
            SourceReliability.COMMUNITY: 0.6
        }
        
        weighted_scores = []
        for piece in evidence_pieces:
            weight = reliability_weights.get(piece.reliability, 0.5)
            weighted_score = piece.confidence * weight
            weighted_scores.append(weighted_score)
        
        # Calculate weighted average
        base_confidence = sum(weighted_scores) / len(weighted_scores)
        
        # Boost confidence if multiple high-quality sources agree
        high_quality_count = sum(1 for p in evidence_pieces 
                               if p.reliability in [SourceReliability.FDA_APPROVED,
                                                  SourceReliability.PROFESSIONAL_GUIDELINES,
                                                  SourceReliability.EXPERT_CURATED])
        
        if high_quality_count >= 2:
            base_confidence *= 1.2
        elif high_quality_count >= 3:
            base_confidence *= 1.4
        
        return min(base_confidence, 1.0)


def format_citations_for_report(citations: List[Citation]) -> str:
    """Format citations for inclusion in clinical report"""
    if not citations:
        return ""
    
    citation_text = "## References\n\n"
    
    for i, citation in enumerate(citations, 1):
        citation_text += f"{i}. {citation.citation_text}\n"
    
    return citation_text


def create_narrative_with_citations(evidence_list: List[Evidence],
                                   text_type: CannedTextType,
                                   context: Dict[str, Any]) -> CannedText:
    """
    Create a canned text with narrative weaving and proper citations
    
    This is the main entry point for narrative generation
    """
    weaver = NarrativeWeaver()
    
    narrative, citations, confidence = weaver.generate_narrative(
        evidence_list, text_type, context
    )
    
    # Format citations as superscript numbers in text
    citation_markers = {}
    for i, citation in enumerate(citations, 1):
        citation_markers[citation.source_db] = f"^{i}"
    
    # Add citation markers to narrative
    marked_narrative = narrative
    for source, marker in citation_markers.items():
        # Add marker after mentions of the source
        marked_narrative = re.sub(
            f"\\(based on [^)]*{source}[^)]*\\)",
            lambda m: m.group(0)[:-1] + marker + ")",
            marked_narrative
        )
    
    # Create citation footer
    citation_footer = "\n\n" + format_citations_for_report(citations)
    
    # Extract evidence support codes
    evidence_support = [f"{e.source_kb}:{e.evidence_type}" for e in evidence_list]
    
    return CannedText(
        text_type=text_type,
        content=marked_narrative + citation_footer,
        confidence=confidence,
        evidence_support=evidence_support,
        triggered_by=[f"Narrative synthesis from {len(evidence_list)} sources"]
    )