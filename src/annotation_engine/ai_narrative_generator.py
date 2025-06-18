"""
AI-Powered Narrative Generation (Alternative Implementation)

This module demonstrates how narrative generation could work using
Large Language Models for more natural text generation while maintaining
clinical accuracy and proper citations.
"""

from typing import Dict, List, Optional, Any
import json
import logging
from dataclasses import dataclass

from .models import Evidence, CannedText, CannedTextType
from .narrative_generator import Citation, EvidencePiece, SourceReliability

logger = logging.getLogger(__name__)


@dataclass
class AIPromptTemplate:
    """Template for AI narrative generation prompts"""
    system_prompt: str
    user_prompt_template: str
    required_fields: List[str]
    output_format: Dict[str, Any]


class AITextGenerator:
    """
    AI-powered text generator with clinical safety guardrails
    
    Note: This is a demonstration of how AI could be integrated.
    Production use would require careful validation and safety measures.
    """
    
    def __init__(self, model_name: str = "clinical-llm"):
        self.model_name = model_name
        self.prompt_templates = self._initialize_prompts()
        self.safety_filters = self._initialize_safety_filters()
        
    def _initialize_prompts(self) -> Dict[CannedTextType, AIPromptTemplate]:
        """Initialize AI prompts for each text type"""
        return {
            CannedTextType.GENE_DX_INTERPRETATION: AIPromptTemplate(
                system_prompt=(
                    "You are a clinical molecular pathologist generating standardized "
                    "gene interpretation text for cancer genomics reports. Your text must be:\n"
                    "- Clinically accurate and evidence-based\n"
                    "- Appropriate for oncologists and pathologists\n" 
                    "- Include proper source attribution\n"
                    "- Follow standard medical writing conventions\n"
                    "- Be concise (2-3 sentences maximum)\n\n"
                    "CRITICAL: Only state information directly supported by the provided evidence. "
                    "Do not extrapolate or add information not present in the sources."
                ),
                user_prompt_template=(
                    "Generate a clinical interpretation for the gene {gene_symbol} in {cancer_type}.\n\n"
                    "Available Evidence:\n{evidence_summary}\n\n"
                    "Source Priority Ranking:\n{source_ranking}\n\n"
                    "Required: Include inline citations using source names. "
                    "Format as: [SourceName]. Focus on the most reliable sources first."
                ),
                required_fields=["gene_symbol", "cancer_type", "evidence_summary", "source_ranking"],
                output_format={
                    "narrative_text": "string",
                    "confidence_assessment": "float (0-1)",
                    "primary_sources_used": "list",
                    "clinical_recommendations": "string"
                }
            ),
            
            CannedTextType.VARIANT_DX_INTERPRETATION: AIPromptTemplate(
                system_prompt=(
                    "You are generating clinical variant interpretation text for oncology reports. "
                    "Focus on:\n"
                    "- Clinical significance (pathogenic/benign/VUS)\n"
                    "- Therapeutic implications\n"
                    "- Evidence quality and strength\n"
                    "- Appropriate clinical context\n\n"
                    "Use precise medical terminology. Be conservative in claims - only state "
                    "what is directly supported by evidence."
                ),
                user_prompt_template=(
                    "Interpret the clinical significance of {variant_description} in {gene_symbol} "
                    "for a patient with {cancer_type}.\n\n"
                    "Evidence Summary:\n{evidence_summary}\n\n"
                    "Tier Assignment: {tier_info}\n\n"
                    "Therapeutic Context: {therapeutic_context}\n\n"
                    "Generate interpretation with inline citations [SourceName]."
                ),
                required_fields=["variant_description", "gene_symbol", "cancer_type", 
                               "evidence_summary", "tier_info"],
                output_format={
                    "clinical_interpretation": "string",
                    "therapeutic_recommendations": "string", 
                    "evidence_strength": "string",
                    "confidence_score": "float"
                }
            ),
            
            CannedTextType.BIOMARKERS: AIPromptTemplate(
                system_prompt=(
                    "Generate biomarker interpretation text for precision oncology. "
                    "Include:\n"
                    "- Biomarker values and categories\n" 
                    "- Clinical thresholds and interpretation\n"
                    "- Therapeutic implications\n"
                    "- Guideline recommendations\n\n"
                    "Be specific about cutoffs and cite appropriate guidelines."
                ),
                user_prompt_template=(
                    "Interpret biomarker results for {cancer_type}:\n\n"
                    "Biomarker Data:\n{biomarker_data}\n\n"
                    "Clinical Guidelines:\n{guidelines}\n\n"
                    "Generate clinical interpretation with appropriate citations."
                ),
                required_fields=["cancer_type", "biomarker_data"],
                output_format={
                    "biomarker_interpretation": "string",
                    "therapy_recommendations": "string",
                    "guideline_citations": "list"
                }
            )
        }
    
    def _initialize_safety_filters(self) -> List[str]:
        """Initialize safety filters for clinical text"""
        return [
            # Prohibited phrases that could be dangerous
            "definitely causes",
            "guarantees response", 
            "cures cancer",
            "100% effective",
            "no side effects",
            
            # Phrases requiring qualification
            "always responds",
            "never fails",
            "completely safe",
            "permanent cure"
        ]
    
    def generate_ai_narrative(self,
                            evidence_list: List[Evidence],
                            text_type: CannedTextType,
                            context: Dict[str, Any],
                            use_fallback: bool = True) -> Optional[CannedText]:
        """
        Generate narrative using AI with clinical safety guardrails
        
        Args:
            evidence_list: Source evidence
            text_type: Type of text to generate
            context: Clinical context (gene, cancer type, etc.)
            use_fallback: Whether to use deterministic fallback if AI fails
            
        Returns:
            CannedText with AI-generated narrative or None
        """
        
        # Check if we have a prompt template for this text type
        if text_type not in self.prompt_templates:
            if use_fallback:
                return self._deterministic_fallback(evidence_list, text_type, context)
            return None
        
        try:
            # Prepare AI prompt
            prompt_data = self._prepare_ai_prompt(evidence_list, text_type, context)
            
            # Generate text using AI (mock implementation)
            ai_response = self._call_ai_model(prompt_data)
            
            # Apply safety filters
            if not self._passes_safety_filters(ai_response["narrative_text"]):
                logger.warning("AI-generated text failed safety filters")
                if use_fallback:
                    return self._deterministic_fallback(evidence_list, text_type, context)
                return None
            
            # Validate against evidence
            if not self._validate_against_evidence(ai_response, evidence_list):
                logger.warning("AI-generated text not supported by evidence")
                if use_fallback:
                    return self._deterministic_fallback(evidence_list, text_type, context)
                return None
            
            # Format citations
            narrative_with_citations = self._format_ai_citations(
                ai_response["narrative_text"], 
                evidence_list
            )
            
            return CannedText(
                text_type=text_type,
                content=narrative_with_citations,
                confidence=ai_response.get("confidence_score", 0.8),
                evidence_support=[f"{e.source_kb}:{e.evidence_type}" for e in evidence_list],
                triggered_by=["AI narrative generation", f"Model: {self.model_name}"]
            )
            
        except Exception as e:
            logger.error(f"AI narrative generation failed: {e}")
            if use_fallback:
                return self._deterministic_fallback(evidence_list, text_type, context)
            return None
    
    def _prepare_ai_prompt(self,
                          evidence_list: List[Evidence],
                          text_type: CannedTextType,
                          context: Dict[str, Any]) -> Dict[str, str]:
        """Prepare structured prompt for AI model"""
        
        template = self.prompt_templates[text_type]
        
        # Create evidence summary
        evidence_summary = self._create_evidence_summary(evidence_list)
        
        # Create source ranking
        source_ranking = self._create_source_ranking(evidence_list)
        
        # Prepare template data
        prompt_data = {
            "system_prompt": template.system_prompt,
            "evidence_summary": evidence_summary,
            "source_ranking": source_ranking,
            **context  # Add all context fields
        }
        
        # Fill user prompt template
        user_prompt = template.user_prompt_template.format(**prompt_data)
        
        return {
            "system_prompt": template.system_prompt,
            "user_prompt": user_prompt,
            "output_format": json.dumps(template.output_format, indent=2)
        }
    
    def _create_evidence_summary(self, evidence_list: List[Evidence]) -> str:
        """Create structured evidence summary for AI"""
        
        summary_parts = []
        
        for i, evidence in enumerate(evidence_list, 1):
            # Determine evidence strength
            strength = "Strong" if evidence.score >= 8 else "Moderate" if evidence.score >= 6 else "Limited"
            
            # Format evidence piece
            evidence_text = (
                f"{i}. {evidence.source_kb} ({strength} evidence): {evidence.description}"
            )
            
            # Add metadata if available
            if evidence.metadata:
                key_metadata = []
                for key in ["therapy", "disease", "evidence_level", "classification"]:
                    if key in evidence.metadata:
                        key_metadata.append(f"{key}: {evidence.metadata[key]}")
                        
                if key_metadata:
                    evidence_text += f" [{', '.join(key_metadata)}]"
            
            summary_parts.append(evidence_text)
        
        return "\n".join(summary_parts)
    
    def _create_source_ranking(self, evidence_list: List[Evidence]) -> str:
        """Create source reliability ranking for AI"""
        
        source_priorities = {
            "FDA": "Highest (Regulatory)",
            "ONCOKB": "High (Expert Curated)",
            "CIVIC": "High (Expert Curated)", 
            "CLINVAR": "High (Expert Curated)",
            "NCCN": "High (Professional Guidelines)",
            "COSMIC": "Moderate (Community)",
            "ALPHAMISSENSE": "Moderate (Computational)",
            "GNOMAD": "Moderate (Population Data)"
        }
        
        sources_present = list(set(e.source_kb for e in evidence_list))
        ranked_sources = []
        
        for source in sources_present:
            priority = source_priorities.get(source, "Standard")
            ranked_sources.append(f"- {source}: {priority}")
        
        return "\n".join(ranked_sources)
    
    def _call_ai_model(self, prompt_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Mock AI model call - replace with actual LLM API
        
        In production, this would call:
        - OpenAI GPT-4
        - Anthropic Claude
        - Custom fine-tuned medical model
        - Local model via Ollama/vLLM
        """
        
        # Mock response for demonstration
        # In practice, this would be an actual API call
        mock_response = {
            "narrative_text": (
                "Based on expert curation from OncoKB and clinical evidence from CIViC, "
                "this variant demonstrates strong therapeutic significance. "
                "FDA-approved targeted therapies are available for patients with this alteration."
            ),
            "confidence_score": 0.85,
            "primary_sources_used": ["OncoKB", "CIViC", "FDA"],
            "clinical_recommendations": "Consider targeted therapy evaluation"
        }
        
        return mock_response
    
    def _passes_safety_filters(self, text: str) -> bool:
        """Check text against clinical safety filters"""
        
        text_lower = text.lower()
        
        # Check prohibited phrases
        for phrase in self.safety_filters:
            if phrase in text_lower:
                logger.warning(f"Safety filter triggered: '{phrase}' in generated text")
                return False
        
        # Check for overly definitive language without qualifiers
        definitive_words = ["always", "never", "definitely", "guaranteed", "certain"]
        qualifier_words = ["may", "might", "potentially", "likely", "suggests", "indicates"]
        
        has_definitive = any(word in text_lower for word in definitive_words)
        has_qualifiers = any(word in text_lower for word in qualifier_words)
        
        if has_definitive and not has_qualifiers:
            logger.warning("Text contains definitive language without appropriate qualifiers")
            return False
        
        return True
    
    def _validate_against_evidence(self,
                                 ai_response: Dict[str, Any],
                                 evidence_list: List[Evidence]) -> bool:
        """Validate that AI response is supported by evidence"""
        
        narrative = ai_response.get("narrative_text", "").lower()
        
        # Check that mentioned sources are actually in evidence
        mentioned_sources = ai_response.get("primary_sources_used", [])
        available_sources = [e.source_kb for e in evidence_list]
        
        for source in mentioned_sources:
            if source not in available_sources:
                logger.warning(f"AI mentioned source '{source}' not in evidence")
                return False
        
        # Check that therapeutic claims are supported
        if "fda-approved" in narrative or "therapeutic" in narrative:
            has_therapeutic_evidence = any(
                e.evidence_type == "THERAPEUTIC" for e in evidence_list
            )
            if not has_therapeutic_evidence:
                logger.warning("AI made therapeutic claims without therapeutic evidence")
                return False
        
        return True
    
    def _format_ai_citations(self,
                           narrative: str,
                           evidence_list: List[Evidence]) -> str:
        """Add proper citations to AI-generated narrative"""
        
        # Extract source mentions from narrative
        source_mentions = {}
        sources_in_evidence = [e.source_kb for e in evidence_list]
        
        for source in sources_in_evidence:
            if source.lower() in narrative.lower():
                source_mentions[source] = len(source_mentions) + 1
        
        # Add citation numbers
        formatted_narrative = narrative
        for source, citation_num in source_mentions.items():
            # Replace source mentions with citations
            formatted_narrative = formatted_narrative.replace(
                source, f"{source}^{citation_num}"
            )
        
        # Add citation footer
        if source_mentions:
            citation_footer = "\n\nReferences:\n"
            for source, num in source_mentions.items():
                # Find evidence for this source to get details
                source_evidence = [e for e in evidence_list if e.source_kb == source][0]
                citation_footer += f"{num}. {source} database"
                
                if source_evidence.metadata and "pmids" in source_evidence.metadata:
                    pmids = source_evidence.metadata["pmids"]
                    citation_footer += f" (PMID: {', '.join(map(str, pmids))})"
                
                citation_footer += "\n"
            
            formatted_narrative += citation_footer
        
        return formatted_narrative
    
    def _deterministic_fallback(self,
                              evidence_list: List[Evidence],
                              text_type: CannedTextType,
                              context: Dict[str, Any]) -> Optional[CannedText]:
        """Fallback to deterministic generation if AI fails"""
        
        # Import here to avoid circular imports
        from .narrative_generator import create_narrative_with_citations
        
        return create_narrative_with_citations(evidence_list, text_type, context)


# Hybrid approach: AI + Deterministic
class HybridNarrativeGenerator:
    """
    Combines AI narrative generation with deterministic validation
    and fallback for maximum safety and quality
    """
    
    def __init__(self):
        self.ai_generator = AITextGenerator()
        
    def generate_narrative(self,
                         evidence_list: List[Evidence],
                         text_type: CannedTextType,
                         context: Dict[str, Any],
                         prefer_ai: bool = True) -> CannedText:
        """
        Generate narrative using hybrid approach
        
        Strategy:
        1. Try AI generation first (if enabled)
        2. Validate AI output against evidence
        3. Fall back to deterministic if AI fails/unsafe
        4. Always validate final output
        """
        
        # Try AI first if preferred and available
        if prefer_ai:
            ai_result = self.ai_generator.generate_ai_narrative(
                evidence_list, text_type, context, use_fallback=False
            )
            
            if ai_result and self._validate_final_output(ai_result, evidence_list):
                logger.info("Using AI-generated narrative")
                return ai_result
            else:
                logger.info("AI generation failed validation, using deterministic fallback")
        
        # Use deterministic approach
        from .narrative_generator import create_narrative_with_citations
        deterministic_result = create_narrative_with_citations(
            evidence_list, text_type, context
        )
        
        return deterministic_result
    
    def _validate_final_output(self,
                             canned_text: CannedText,
                             evidence_list: List[Evidence]) -> bool:
        """Final validation of generated text"""
        
        # Check minimum quality requirements
        if len(canned_text.content) < 50:  # Too short
            return False
        
        if canned_text.confidence < 0.3:  # Too low confidence
            return False
        
        # Check that all evidence sources are represented
        content_lower = canned_text.content.lower()
        evidence_sources = [e.source_kb for e in evidence_list]
        
        # At least one high-priority source should be mentioned
        high_priority_sources = ["ONCOKB", "FDA", "NCCN", "CIVIC", "CLINVAR"]
        mentioned_high_priority = any(
            source.lower() in content_lower 
            for source in high_priority_sources 
            if source in evidence_sources
        )
        
        if not mentioned_high_priority and any(s in evidence_sources for s in high_priority_sources):
            logger.warning("High-priority sources not mentioned in narrative")
            return False
        
        return True


# Example usage demonstrating both approaches
def compare_approaches_example():
    """
    Example comparing AI vs deterministic narrative generation
    """
    
    # Sample evidence
    evidence_list = [
        Evidence(
            evidence_type="THERAPEUTIC",
            evidence_level="LEVEL_1",
            source_kb="ONCOKB",
            description="BRAF V600E confers sensitivity to vemurafenib",
            score=10,
            metadata={"therapy": "vemurafenib", "disease": "melanoma"}
        ),
        Evidence(
            evidence_type="CLINICAL_SIGNIFICANCE",
            evidence_level="HIGH",
            source_kb="CIVIC",
            description="Strong evidence for oncogenic role",
            score=9
        )
    ]
    
    context = {
        "gene_symbol": "BRAF",
        "cancer_type": "melanoma",
        "variant_description": "p.V600E"
    }
    
    # Compare approaches
    hybrid_generator = HybridNarrativeGenerator()
    
    # AI approach
    ai_result = hybrid_generator.generate_narrative(
        evidence_list, 
        CannedTextType.VARIANT_DX_INTERPRETATION,
        context,
        prefer_ai=True
    )
    
    # Deterministic approach  
    deterministic_result = hybrid_generator.generate_narrative(
        evidence_list,
        CannedTextType.VARIANT_DX_INTERPRETATION, 
        context,
        prefer_ai=False
    )
    
    print("AI Approach:")
    print(f"Text: {ai_result.content}")
    print(f"Confidence: {ai_result.confidence}")
    print()
    
    print("Deterministic Approach:")
    print(f"Text: {deterministic_result.content}")
    print(f"Confidence: {deterministic_result.confidence}")