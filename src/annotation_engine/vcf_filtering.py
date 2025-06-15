"""
VCF Filtering Logic for Tumor-Normal vs Tumor-Only Analysis

Implements separate filtering strategies based on analysis type per TN_VERSUS_TO.md:
- Tumor-Normal: Direct subtraction (variants in normal are filtered out)
- Tumor-Only: Population AF + Panel of Normals filtering
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
import pysam

from .models import AnalysisType
from .validation.error_handler import ValidationError
from .vcf_parser import VCFFieldExtractor

logger = logging.getLogger(__name__)


class BaseVCFFilter(ABC):
    """Base class for VCF filtering strategies"""
    
    def __init__(self):
        self.vcf_extractor = VCFFieldExtractor()
        self.filtered_count = 0
        self.passed_count = 0
        self.filter_reasons = {}
    
    @abstractmethod
    def filter_variants(self, tumor_vcf_path: Path, normal_vcf_path: Optional[Path] = None) -> List[Dict[str, Any]]:
        """Filter variants based on analysis type"""
        pass
    
    def get_filter_summary(self) -> Dict[str, Any]:
        """Get filtering summary statistics"""
        return {
            "total_variants": self.filtered_count + self.passed_count,
            "passed_variants": self.passed_count,
            "filtered_variants": self.filtered_count,
            "filter_reasons": self.filter_reasons
        }


class TumorNormalFilter(BaseVCFFilter):
    """
    Tumor-Normal filtering: Direct subtraction approach
    
    Variants present in normal sample at significant VAF (>5%) are filtered as germline.
    This provides highest confidence somatic calling.
    """
    
    def __init__(self, min_normal_vaf_threshold: float = 0.05):
        super().__init__()
        self.min_normal_vaf_threshold = min_normal_vaf_threshold
    
    def filter_variants(self, tumor_vcf_path: Path, normal_vcf_path: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Filter tumor variants by subtracting normal variants
        
        Args:
            tumor_vcf_path: Path to tumor VCF
            normal_vcf_path: Path to matched normal VCF
            
        Returns:
            List of somatic variants (tumor variants not in normal)
        """
        if normal_vcf_path is None:
            raise ValueError("Tumor-Normal filtering requires normal VCF path")
        
        logger.info(f"Starting Tumor-Normal filtering: {tumor_vcf_path} vs {normal_vcf_path}")
        
        # Extract variants from both files
        tumor_variants = self.vcf_extractor.extract_variant_bundle(tumor_vcf_path)
        normal_variants = self.vcf_extractor.extract_variant_bundle(normal_vcf_path)
        
        # Build normal variant lookup for efficient filtering
        normal_lookup = self._build_variant_lookup(normal_variants)
        
        # Filter tumor variants
        somatic_variants = []
        self.filter_reasons = {
            "germline_in_normal": 0,
            "low_quality": 0,
            "passed_somatic": 0
        }
        
        for tumor_var in tumor_variants:
            filter_reason = self._evaluate_tumor_variant(tumor_var, normal_lookup)
            
            if filter_reason == "passed":
                somatic_variants.append(tumor_var)
                self.passed_count += 1
                self.filter_reasons["passed_somatic"] += 1
            else:
                self.filtered_count += 1
                self.filter_reasons[filter_reason] += 1
        
        logger.info(f"TN filtering complete: {self.passed_count} somatic, {self.filtered_count} filtered")
        return somatic_variants
    
    def _build_variant_lookup(self, normal_variants: List[Dict[str, Any]]) -> Set[Tuple[str, int, str, str]]:
        """Build efficient lookup set for normal variants"""
        lookup = set()
        
        for variant in normal_variants:
            # Check if variant has significant VAF in normal
            normal_vaf = self._get_normal_vaf(variant)
            if normal_vaf and normal_vaf >= self.min_normal_vaf_threshold:
                key = (
                    variant['chromosome'],
                    variant['position'], 
                    variant['reference'],
                    variant['alternate']
                )
                lookup.add(key)
        
        return lookup
    
    def _get_normal_vaf(self, variant: Dict[str, Any]) -> Optional[float]:
        """Extract VAF from normal sample"""
        if not variant.get('samples'):
            return None
        
        # Assuming single normal sample (could extend for multi-sample)
        sample = variant['samples'][0]
        return sample.get('variant_allele_frequency')
    
    def _evaluate_tumor_variant(self, tumor_var: Dict[str, Any], normal_lookup: Set[Tuple[str, int, str, str]]) -> str:
        """Evaluate if tumor variant should be filtered"""
        
        # Create variant key
        var_key = (
            tumor_var['chromosome'],
            tumor_var['position'],
            tumor_var['reference'], 
            tumor_var['alternate']
        )
        
        # Check basic quality filters
        if not self._passes_basic_quality(tumor_var):
            return "low_quality"
        
        # Check if variant exists in normal at significant VAF
        if var_key in normal_lookup:
            return "germline_in_normal"
        
        return "passed"
    
    def _passes_basic_quality(self, variant: Dict[str, Any]) -> bool:
        """Basic quality filters for tumor variants"""
        # Check FILTER field
        if 'PASS' not in variant.get('filter_status', []):
            return False
        
        # Check minimum depth (if available)
        if variant.get('total_depth') and variant['total_depth'] < 10:
            return False
        
        return True


class TumorOnlyFilter(BaseVCFFilter):
    """
    Tumor-Only filtering: Population AF + Panel of Normals approach
    
    Somatic status is inferred through in-silico germline filtering:
    1. Panel of Normals (PoN) - filters recurrent sequencing artifacts 
    2. Population AF databases - filters common germline variants
    """
    
    def __init__(self, 
                 max_population_af: float = 0.01,
                 pon_vcf_path: Optional[Path] = None,
                 gnomad_af_threshold: float = 0.01):
        super().__init__()
        self.max_population_af = max_population_af
        self.pon_vcf_path = pon_vcf_path
        self.gnomad_af_threshold = gnomad_af_threshold
        self.pon_lookup = None
        
        # Load Panel of Normals if provided
        if self.pon_vcf_path and self.pon_vcf_path.exists():
            self._load_panel_of_normals()
    
    def filter_variants(self, tumor_vcf_path: Path, normal_vcf_path: Optional[Path] = None) -> List[Dict[str, Any]]:
        """
        Filter tumor-only variants using population AF + PoN approach
        
        Args:
            tumor_vcf_path: Path to tumor VCF
            normal_vcf_path: Not used for tumor-only analysis
            
        Returns:
            List of likely somatic variants after germline filtering
        """
        logger.info(f"Starting Tumor-Only filtering: {tumor_vcf_path}")
        
        # Extract tumor variants
        tumor_variants = self.vcf_extractor.extract_variant_bundle(tumor_vcf_path)
        
        # Filter variants
        likely_somatic_variants = []
        self.filter_reasons = {
            "high_population_af": 0,
            "panel_of_normals": 0,
            "low_quality": 0,
            "low_vaf": 0,
            "passed_likely_somatic": 0
        }
        
        for variant in tumor_variants:
            filter_reason = self._evaluate_tumor_only_variant(variant)
            
            if filter_reason == "passed":
                likely_somatic_variants.append(variant)
                self.passed_count += 1
                self.filter_reasons["passed_likely_somatic"] += 1
            else:
                self.filtered_count += 1
                self.filter_reasons[filter_reason] += 1
        
        logger.info(f"TO filtering complete: {self.passed_count} likely somatic, {self.filtered_count} filtered")
        return likely_somatic_variants
    
    def _load_panel_of_normals(self):
        """Load Panel of Normals variants for filtering"""
        logger.info(f"Loading Panel of Normals: {self.pon_vcf_path}")
        
        try:
            pon_variants = self.vcf_extractor.extract_variant_bundle(self.pon_vcf_path)
            self.pon_lookup = set()
            
            for variant in pon_variants:
                key = (
                    variant['chromosome'],
                    variant['position'],
                    variant['reference'],
                    variant['alternate']
                )
                self.pon_lookup.add(key)
            
            logger.info(f"Loaded {len(self.pon_lookup)} PoN variants")
            
        except Exception as e:
            logger.warning(f"Failed to load Panel of Normals: {e}")
            self.pon_lookup = set()
    
    def _evaluate_tumor_only_variant(self, variant: Dict[str, Any]) -> str:
        """Evaluate if tumor-only variant should be filtered"""
        
        # Check basic quality filters
        if not self._passes_basic_quality(variant):
            return "low_quality"
        
        # Check minimum VAF for tumor-only analysis (higher threshold)
        tumor_vaf = self._get_tumor_vaf(variant)
        if tumor_vaf and tumor_vaf < 0.05:  # 5% minimum for TO
            return "low_vaf"
        
        # Check against Panel of Normals
        if self._is_in_panel_of_normals(variant):
            return "panel_of_normals"
        
        # Check population frequency (this would be enhanced with actual gnomAD lookup)
        if self._has_high_population_frequency(variant):
            return "high_population_af"
        
        return "passed"
    
    def _get_tumor_vaf(self, variant: Dict[str, Any]) -> Optional[float]:
        """Extract VAF from tumor sample"""
        if not variant.get('samples'):
            return None
        
        # Assuming single tumor sample
        sample = variant['samples'][0]
        return sample.get('variant_allele_frequency')
    
    def _is_in_panel_of_normals(self, variant: Dict[str, Any]) -> bool:
        """Check if variant is present in Panel of Normals"""
        if not self.pon_lookup:
            return False
        
        var_key = (
            variant['chromosome'],
            variant['position'],
            variant['reference'],
            variant['alternate']
        )
        
        return var_key in self.pon_lookup
    
    def _has_high_population_frequency(self, variant: Dict[str, Any]) -> bool:
        """
        Check if variant has high population frequency
        
        Note: This is a placeholder. In production, this would query:
        - gnomAD API or local database
        - dbSNP frequencies
        - Other population databases
        """
        # Placeholder logic - check if variant has dbSNP membership as proxy
        # In reality, this would be a proper AF lookup
        if variant.get('dbsnp_member'):
            # Very crude proxy - if in dbSNP, assume common
            # Real implementation would do proper AF lookup
            return True
        
        # Check if allele frequency is annotated in VCF (some pipelines include this)
        vcf_af = variant.get('allele_frequency')
        if vcf_af and vcf_af > self.max_population_af:
            return True
        
        return False
    
    def _passes_basic_quality(self, variant: Dict[str, Any]) -> bool:
        """Basic quality filters for tumor-only variants (more stringent)"""
        # Check FILTER field
        if 'PASS' not in variant.get('filter_status', []):
            return False
        
        # Higher depth requirement for tumor-only
        if variant.get('total_depth') and variant['total_depth'] < 20:
            return False
        
        # Check quality score
        if variant.get('quality_score') and variant['quality_score'] < 30:
            return False
        
        return True


class VCFFilterFactory:
    """Factory for creating appropriate VCF filter based on analysis type"""
    
    @staticmethod
    def create_filter(analysis_type: AnalysisType, **kwargs) -> BaseVCFFilter:
        """
        Create appropriate filter for analysis type
        
        Args:
            analysis_type: TUMOR_NORMAL or TUMOR_ONLY
            **kwargs: Filter-specific parameters
            
        Returns:
            Appropriate filter instance
        """
        if analysis_type == AnalysisType.TUMOR_NORMAL:
            return TumorNormalFilter(
                min_normal_vaf_threshold=kwargs.get('min_normal_vaf_threshold', 0.05)
            )
        elif analysis_type == AnalysisType.TUMOR_ONLY:
            return TumorOnlyFilter(
                max_population_af=kwargs.get('max_population_af', 0.01),
                pon_vcf_path=kwargs.get('pon_vcf_path'),
                gnomad_af_threshold=kwargs.get('gnomad_af_threshold', 0.01)
            )
        else:
            raise ValueError(f"Unsupported analysis type: {analysis_type}")


def filter_vcf_by_analysis_type(tumor_vcf_path: Path, 
                               analysis_type: AnalysisType,
                               normal_vcf_path: Optional[Path] = None,
                               **filter_kwargs) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Convenience function to filter VCF based on analysis type
    
    Args:
        tumor_vcf_path: Path to tumor VCF
        analysis_type: Analysis workflow type
        normal_vcf_path: Path to normal VCF (required for TN analysis)
        **filter_kwargs: Additional filtering parameters
        
    Returns:
        Tuple of (filtered_variants, filter_summary)
    """
    # Create appropriate filter
    vcf_filter = VCFFilterFactory.create_filter(analysis_type, **filter_kwargs)
    
    # Apply filtering
    filtered_variants = vcf_filter.filter_variants(tumor_vcf_path, normal_vcf_path)
    filter_summary = vcf_filter.get_filter_summary()
    
    return filtered_variants, filter_summary