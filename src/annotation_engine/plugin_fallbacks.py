"""
Plugin Fallback System

Provides fallback mechanisms when VEP plugins are unavailable.
Uses standalone modules for AlphaMissense, GERP conservation, etc.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from .alpha_missense import get_alphamissense_loader
from .conservation import get_gerp_loader, get_phylop_loader
from .models import VariantAnnotation

logger = logging.getLogger(__name__)


class PluginFallbackManager:
    """Manages fallback mechanisms for missing VEP plugins"""
    
    def __init__(self, refs_dir: Optional[Path] = None):
        if refs_dir is None:
            refs_dir = Path(__file__).parent.parent.parent / ".refs"
        
        self.refs_dir = Path(refs_dir)
        
        # Initialize fallback loaders
        self.alphamissense_loader = get_alphamissense_loader(refs_dir)
        self.gerp_loader = get_gerp_loader(refs_dir)
        self.phylop_loader = get_phylop_loader(refs_dir)
        
        # Track which fallbacks are available
        self.available_fallbacks = self._check_available_fallbacks()
    
    def _check_available_fallbacks(self) -> Dict[str, bool]:
        """Check which fallback mechanisms are available"""
        available = {}
        
        # Check AlphaMissense
        available["alphamissense"] = (
            self.alphamissense_loader and 
            self.alphamissense_loader.get_stats()["available"]
        )
        
        # Check GERP conservation
        available["gerp"] = (
            self.gerp_loader and 
            self.gerp_loader.is_available()
        )
        
        # Check PhyloP conservation  
        available["phylop"] = (
            self.phylop_loader and
            self.phylop_loader.is_available()
        )
        
        logger.info(f"Available plugin fallbacks: {[k for k,v in available.items() if v]}")
        
        return available
    
    def enrich_variant_annotation(self, variant: VariantAnnotation) -> VariantAnnotation:
        """
        Enrich variant annotation with fallback data when VEP plugins are missing
        
        Args:
            variant: VariantAnnotation object from VEP
            
        Returns:
            Enriched VariantAnnotation with fallback data added to plugin_data
        """
        
        # Check if we need to add AlphaMissense scores
        if (self.available_fallbacks.get("alphamissense") and 
            "alphamissense" not in variant.plugin_data.get("pathogenicity_scores", {})):
            
            alphamissense_data = self.alphamissense_loader.lookup_variant(
                variant.chromosome,
                variant.position,
                variant.reference,
                variant.alternate
            )
            
            if alphamissense_data:
                if "pathogenicity_scores" not in variant.plugin_data:
                    variant.plugin_data["pathogenicity_scores"] = {}
                
                variant.plugin_data["pathogenicity_scores"]["alphamissense"] = {
                    "score": alphamissense_data["pathogenicity_score"],
                    "prediction": alphamissense_data["classification"],
                    "source": "fallback"
                }
                logger.debug(f"Added AlphaMissense fallback for {variant.chromosome}:{variant.position}")
        
        # Check if we need to add conservation scores
        if (self.available_fallbacks.get("gerp") and
            "gerp" not in variant.plugin_data.get("conservation_data", {})):
            
            gerp_score = self.gerp_loader.lookup_position(
                variant.chromosome,
                variant.position
            )
            
            if gerp_score is not None:
                if "conservation_data" not in variant.plugin_data:
                    variant.plugin_data["conservation_data"] = {}
                
                variant.plugin_data["conservation_data"]["gerp"] = gerp_score
                logger.debug(f"Added GERP fallback for {variant.chromosome}:{variant.position}")
        
        # Check if we need to add PhyloP scores
        if (self.available_fallbacks.get("phylop") and
            "phylop" not in variant.plugin_data.get("conservation_data", {})):
            
            phylop_score = self.phylop_loader.lookup_position(
                variant.chromosome,
                variant.position
            )
            
            if phylop_score is not None:
                if "conservation_data" not in variant.plugin_data:
                    variant.plugin_data["conservation_data"] = {}
                
                variant.plugin_data["conservation_data"]["phylop"] = phylop_score
                logger.debug(f"Added PhyloP fallback for {variant.chromosome}:{variant.position}")
        
        return variant
    
    def enrich_variant_list(self, variants: List[VariantAnnotation]) -> List[VariantAnnotation]:
        """
        Enrich a list of variants with fallback data
        
        Args:
            variants: List of VariantAnnotation objects
            
        Returns:
            List of enriched VariantAnnotation objects
        """
        logger.info(f"Enriching {len(variants)} variants with fallback data")
        
        enriched_variants = []
        for variant in variants:
            enriched_variants.append(self.enrich_variant_annotation(variant))
        
        return enriched_variants
    
    def get_fallback_stats(self) -> Dict[str, Any]:
        """Get statistics about available fallback mechanisms"""
        stats = {
            "available_fallbacks": self.available_fallbacks,
            "alphamissense_stats": self.alphamissense_loader.get_stats() if self.alphamissense_loader else {},
            "gerp_available": self.gerp_loader.is_available() if self.gerp_loader else False,
            "phylop_available": self.phylop_loader.is_available() if self.phylop_loader else False
        }
        
        return stats


# Global instance for efficient reuse
_fallback_manager = None

def get_fallback_manager(refs_dir: Optional[Path] = None) -> PluginFallbackManager:
    """Get global fallback manager instance"""
    global _fallback_manager
    if _fallback_manager is None:
        _fallback_manager = PluginFallbackManager(refs_dir)
    return _fallback_manager