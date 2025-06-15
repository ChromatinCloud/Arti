"""
Tumor Purity Estimation Module

Implements tumor purity estimation functionality adapted from HMF PURPLE
approach for integration with the annotation engine. Provides VAF-based
purity estimation for tumor-only analysis and DSC calculation.
"""

import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from statistics import median, mean

from .models import VariantAnnotation, AnalysisType
from .validation.error_handler import ValidationError

logger = logging.getLogger(__name__)


@dataclass
class PurityEstimate:
    """Tumor purity estimation result"""
    purity: float  # Estimated tumor purity (0.0-1.0)
    confidence: float  # Confidence in estimate (0.0-1.0)
    method: str  # Method used for estimation
    supporting_variants: int  # Number of variants used in estimation
    vaf_distribution: Dict[str, float]  # VAF distribution statistics
    quality_metrics: Dict[str, Any]  # Quality assessment metrics
    
    def __post_init__(self):
        """Validate purity estimate"""
        if not 0.0 <= self.purity <= 1.0:
            raise ValueError(f"Purity must be between 0.0 and 1.0, got {self.purity}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


class VAFBasedPurityEstimator:
    """
    VAF-based tumor purity estimation adapted from HMF PURPLE methodology
    
    Estimates tumor purity from the distribution of somatic variant VAFs,
    particularly using high-confidence somatic variants that are likely
    heterozygous in the main tumor clone.
    """
    
    def __init__(self, 
                 min_variants: int = 10,
                 min_vaf: float = 0.05,
                 max_vaf: float = 0.95,
                 min_depth: int = 20):
        """
        Initialize VAF-based purity estimator
        
        Args:
            min_variants: Minimum variants required for reliable estimation
            min_vaf: Minimum VAF threshold for analysis
            max_vaf: Maximum VAF threshold for analysis
            min_depth: Minimum read depth for variant inclusion
        """
        self.min_variants = min_variants
        self.min_vaf = min_vaf
        self.max_vaf = max_vaf
        self.min_depth = min_depth
        self.logger = logging.getLogger(__name__)
    
    def estimate_purity(self, 
                       variant_annotations: List[VariantAnnotation],
                       analysis_type: AnalysisType,
                       prior_purity: Optional[float] = None) -> PurityEstimate:
        """
        Estimate tumor purity from variant VAF distribution
        
        Args:
            variant_annotations: List of annotated variants
            analysis_type: Analysis workflow type
            prior_purity: Prior purity estimate if available
            
        Returns:
            PurityEstimate with purity, confidence, and quality metrics
        """
        logger.info(f"Starting purity estimation for {len(variant_annotations)} variants")
        
        # Filter variants suitable for purity estimation
        suitable_variants = self._filter_variants_for_purity(variant_annotations, analysis_type)
        
        if len(suitable_variants) < self.min_variants:
            return self._create_low_confidence_estimate(
                suitable_variants, 
                f"Insufficient variants ({len(suitable_variants)} < {self.min_variants})"
            )
        
        # Extract VAF values
        vafs = [v.vaf for v in suitable_variants if v.vaf is not None]
        
        if len(vafs) < self.min_variants:
            return self._create_low_confidence_estimate(
                suitable_variants,
                "Insufficient variants with VAF data"
            )
        
        # Estimate purity using multiple methods and select best
        estimates = []
        
        # Method 1: Heterozygous peak method (main approach)
        het_estimate = self._estimate_purity_heterozygous_peak(vafs, suitable_variants)
        estimates.append(het_estimate)
        
        # Method 2: Quantile-based method (backup)
        quantile_estimate = self._estimate_purity_quantile_method(vafs, suitable_variants)
        estimates.append(quantile_estimate)
        
        # Select best estimate based on confidence
        best_estimate = max(estimates, key=lambda x: x.confidence)
        
        # Apply prior information if available
        if prior_purity is not None:
            best_estimate = self._incorporate_prior_purity(best_estimate, prior_purity)
        
        logger.info(f"Purity estimation complete: {best_estimate.purity:.3f} (confidence: {best_estimate.confidence:.3f})")
        return best_estimate
    
    def _filter_variants_for_purity(self, 
                                   variants: List[VariantAnnotation],
                                   analysis_type: AnalysisType) -> List[VariantAnnotation]:
        """Filter variants suitable for purity estimation"""
        
        suitable_variants = []
        
        for variant in variants:
            # Basic quality filters
            if not self._passes_purity_quality_filters(variant):
                continue
            
            # Analysis-type specific filters
            if analysis_type == AnalysisType.TUMOR_ONLY:
                if not self._suitable_for_tumor_only_purity(variant):
                    continue
            elif analysis_type == AnalysisType.TUMOR_NORMAL:
                if not self._suitable_for_tumor_normal_purity(variant):
                    continue
            
            suitable_variants.append(variant)
        
        return suitable_variants
    
    def _passes_purity_quality_filters(self, variant: VariantAnnotation) -> bool:
        """Check if variant passes basic quality filters for purity estimation"""
        
        # Check VAF bounds
        if variant.vaf is None:
            return False
        if not (self.min_vaf <= variant.vaf <= self.max_vaf):
            return False
        
        # Check read depth
        if variant.total_depth is None or variant.total_depth < self.min_depth:
            return False
        
        # Check filter status
        if 'PASS' not in variant.filter_status:
            return False
        
        # Prefer SNVs for purity estimation (more reliable VAF)
        if variant.consequence and 'insertion' in variant.consequence[0].lower():
            return False
        if variant.consequence and 'deletion' in variant.consequence[0].lower():
            return False
        
        return True
    
    def _suitable_for_tumor_only_purity(self, variant: VariantAnnotation) -> bool:
        """Check if variant is suitable for tumor-only purity estimation"""
        
        # Prefer variants with evidence of somatic origin
        has_hotspot_evidence = len(variant.hotspot_evidence) > 0
        
        # Check population frequency (lower is better for somatic confidence)
        if variant.population_frequencies:
            max_pop_freq = max(pf.allele_frequency or 0.0 for pf in variant.population_frequencies)
            if max_pop_freq > 0.05:  # Only exclude very common variants (5%)
                return False
        
        # Prefer variants in cancer genes
        if variant.is_oncogene or variant.is_tumor_suppressor or variant.cancer_gene_census:
            return True
        
        # For purity estimation, we can be more permissive than clinical annotation
        # Include variants with hotspot evidence or reasonable functional impact
        if has_hotspot_evidence:
            return True
        
        # Include missense and more impactful variants even without hotspot evidence
        if variant.consequence:
            impactful_consequences = {
                'missense_variant', 'stop_gained', 'frameshift_variant', 
                'splice_donor_variant', 'splice_acceptor_variant', 'start_lost'
            }
            if any(cons in impactful_consequences for cons in variant.consequence):
                return True
        
        return False
    
    def _suitable_for_tumor_normal_purity(self, variant: VariantAnnotation) -> bool:
        """Check if variant is suitable for tumor-normal purity estimation"""
        
        # For tumor-normal, we have higher confidence in somatic status
        # so we can be less restrictive about variant selection
        
        # Still prefer high-quality variants
        return True
    
    def _estimate_purity_heterozygous_peak(self, 
                                         vafs: List[float],
                                         variants: List[VariantAnnotation]) -> PurityEstimate:
        """
        Estimate purity using heterozygous peak method
        
        Assumes that most somatic variants are heterozygous in the main clone,
        so purity ≈ 2 * median(VAF) for diploid regions.
        """
        
        # Calculate VAF statistics
        vaf_median = median(vafs)
        vaf_mean = mean(vafs)
        vaf_std = np.std(vafs)
        
        # Find the main VAF peak (likely heterozygous variants)
        # Use kernel density estimation or simple binning
        main_peak_vaf = self._find_main_vaf_peak(vafs)
        
        # Estimate purity assuming heterozygous variants in diploid regions
        # purity = 2 * VAF for heterozygous variants
        estimated_purity = min(2.0 * main_peak_vaf, 1.0)
        
        # Calculate confidence based on data quality
        confidence = self._calculate_purity_confidence(
            vafs, variants, estimated_purity, method="heterozygous_peak"
        )
        
        return PurityEstimate(
            purity=estimated_purity,
            confidence=confidence,
            method="heterozygous_peak",
            supporting_variants=len(variants),
            vaf_distribution={
                "median": vaf_median,
                "mean": vaf_mean,
                "std": vaf_std,
                "main_peak": main_peak_vaf,
                "min": min(vafs),
                "max": max(vafs)
            },
            quality_metrics={
                "vaf_consistency": 1.0 - (vaf_std / vaf_mean) if vaf_mean > 0 else 0.0,
                "variant_count": len(variants),
                "vaf_range": max(vafs) - min(vafs)
            }
        )
    
    def _estimate_purity_quantile_method(self,
                                       vafs: List[float],
                                       variants: List[VariantAnnotation]) -> PurityEstimate:
        """
        Estimate purity using quantile-based method
        
        Uses upper quantiles of VAF distribution as backup method.
        """
        
        vafs_array = np.array(vafs)
        
        # Use 75th percentile as estimate for heterozygous variants
        p75_vaf = np.percentile(vafs_array, 75)
        estimated_purity = min(2.0 * p75_vaf, 1.0)
        
        # Calculate confidence (generally lower than peak method)
        confidence = self._calculate_purity_confidence(
            vafs, variants, estimated_purity, method="quantile"
        ) * 0.8  # Reduce confidence for backup method
        
        return PurityEstimate(
            purity=estimated_purity,
            confidence=confidence,
            method="quantile_based",
            supporting_variants=len(variants),
            vaf_distribution={
                "p25": np.percentile(vafs_array, 25),
                "p50": np.percentile(vafs_array, 50),
                "p75": np.percentile(vafs_array, 75),
                "p90": np.percentile(vafs_array, 90)
            },
            quality_metrics={
                "method": "backup_quantile",
                "variant_count": len(variants)
            }
        )
    
    def _find_main_vaf_peak(self, vafs: List[float]) -> float:
        """Find the main VAF peak using simple binning approach"""
        
        # Create VAF bins
        bins = np.linspace(self.min_vaf, self.max_vaf, 20)
        hist, bin_edges = np.histogram(vafs, bins=bins)
        
        # Find bin with maximum count
        max_bin_idx = np.argmax(hist)
        
        # Return center of the bin with maximum density
        return (bin_edges[max_bin_idx] + bin_edges[max_bin_idx + 1]) / 2
    
    def _calculate_purity_confidence(self,
                                   vafs: List[float],
                                   variants: List[VariantAnnotation],
                                   estimated_purity: float,
                                   method: str) -> float:
        """Calculate confidence in purity estimate"""
        
        confidence_factors = []
        
        # Factor 1: Number of supporting variants
        variant_count_factor = min(len(variants) / 50.0, 1.0)  # More variants = higher confidence
        confidence_factors.append(variant_count_factor)
        
        # Factor 2: VAF distribution consistency
        vaf_std = np.std(vafs)
        vaf_mean = mean(vafs)
        if vaf_mean > 0:
            consistency_factor = 1.0 - min(vaf_std / vaf_mean, 1.0)
            confidence_factors.append(consistency_factor)
        
        # Factor 3: Biological plausibility
        if 0.1 <= estimated_purity <= 0.9:
            plausibility_factor = 1.0
        elif 0.05 <= estimated_purity < 0.1 or 0.9 < estimated_purity <= 0.95:
            plausibility_factor = 0.7
        else:
            plausibility_factor = 0.3
        confidence_factors.append(plausibility_factor)
        
        # Factor 4: Method-specific adjustments
        if method == "heterozygous_peak":
            method_factor = 1.0
        elif method == "quantile":
            method_factor = 0.8
        else:
            method_factor = 0.6
        confidence_factors.append(method_factor)
        
        # Combined confidence (geometric mean to avoid overconfidence)
        overall_confidence = np.prod(confidence_factors) ** (1.0 / len(confidence_factors))
        
        return min(overall_confidence, 0.95)  # Cap at 95% confidence
    
    def _create_low_confidence_estimate(self,
                                      variants: List[VariantAnnotation],
                                      reason: str) -> PurityEstimate:
        """Create a low-confidence purity estimate when data is insufficient"""
        
        logger.warning(f"Creating low-confidence purity estimate: {reason}")
        
        # Use default purity of 0.5 with low confidence
        return PurityEstimate(
            purity=0.5,  # Conservative default
            confidence=0.2,  # Low confidence
            method="insufficient_data",
            supporting_variants=len(variants),
            vaf_distribution={},
            quality_metrics={"warning": reason}
        )
    
    def _incorporate_prior_purity(self,
                                 estimate: PurityEstimate,
                                 prior_purity: float) -> PurityEstimate:
        """Incorporate prior purity information using Bayesian updating"""
        
        # Simple weighted average between estimate and prior
        prior_weight = 0.3  # Weight given to prior information
        estimate_weight = 1.0 - prior_weight
        
        adjusted_purity = (estimate_weight * estimate.purity + 
                          prior_weight * prior_purity)
        
        # Slightly increase confidence when prior agrees with estimate
        agreement = 1.0 - abs(estimate.purity - prior_purity)
        confidence_boost = agreement * 0.1
        adjusted_confidence = min(estimate.confidence + confidence_boost, 0.95)
        
        return PurityEstimate(
            purity=adjusted_purity,
            confidence=adjusted_confidence,
            method=f"{estimate.method}_with_prior",
            supporting_variants=estimate.supporting_variants,
            vaf_distribution=estimate.vaf_distribution,
            quality_metrics={
                **estimate.quality_metrics,
                "prior_purity": prior_purity,
                "prior_weight": prior_weight
            }
        )


class PurityMetadataIntegrator:
    """
    Integrates tumor purity from various sources including metadata,
    external tools (HMF PURPLE), and VAF-based estimation.
    """
    
    def __init__(self):
        self.vaf_estimator = VAFBasedPurityEstimator()
        self.logger = logging.getLogger(__name__)
    
    def get_tumor_purity(self,
                        variant_annotations: List[VariantAnnotation],
                        analysis_type: AnalysisType,
                        metadata: Optional[Dict[str, Any]] = None,
                        purple_output_path: Optional[Path] = None) -> PurityEstimate:
        """
        Get tumor purity from best available source
        
        Priority:
        1. HMF PURPLE output (if available)
        2. Metadata purity value
        3. VAF-based estimation
        
        Args:
            variant_annotations: Variant data for VAF-based estimation
            analysis_type: Analysis workflow type
            metadata: Analysis metadata potentially containing purity
            purple_output_path: Path to PURPLE output files
            
        Returns:
            PurityEstimate from best available source
        """
        
        # Method 1: Try to load from PURPLE output
        if purple_output_path and purple_output_path.exists():
            try:
                purple_estimate = self._load_purple_purity(purple_output_path)
                logger.info(f"Using PURPLE purity estimate: {purple_estimate.purity:.3f}")
                return purple_estimate
            except Exception as e:
                logger.warning(f"Failed to load PURPLE purity: {e}")
        
        # Method 2: Check metadata for purity value
        if metadata and 'tumor_purity' in metadata:
            try:
                metadata_purity = float(metadata['tumor_purity'])
                if 0.0 <= metadata_purity <= 1.0:
                    logger.info(f"Using metadata purity: {metadata_purity:.3f}")
                    return PurityEstimate(
                        purity=metadata_purity,
                        confidence=0.8,  # High confidence in provided metadata
                        method="metadata",
                        supporting_variants=0,
                        vaf_distribution={},
                        quality_metrics={"source": "metadata"}
                    )
            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid metadata purity value: {e}")
        
        # Method 3: VAF-based estimation (fallback)
        logger.info("Performing VAF-based purity estimation")
        return self.vaf_estimator.estimate_purity(
            variant_annotations, analysis_type
        )
    
    def _load_purple_purity(self, purple_output_path: Path) -> PurityEstimate:
        """Load purity estimate from PURPLE output files"""
        
        # Look for PURPLE purity file (typically *.purple.purity.tsv)
        purity_files = list(purple_output_path.glob("*.purple.purity.tsv"))
        
        if not purity_files:
            raise FileNotFoundError("No PURPLE purity files found")
        
        purity_file = purity_files[0]
        
        # Parse PURPLE purity output
        # Format: sample purity normFactor score diploidProportion ploidy
        with open(purity_file, 'r') as f:
            header = f.readline().strip().split('\t')
            data = f.readline().strip().split('\t')
        
        if len(data) < 3:
            raise ValueError("Invalid PURPLE purity file format")
        
        purity = float(data[1])
        score = float(data[3]) if len(data) > 3 else 1.0
        
        # Convert PURPLE score to confidence (0-1 scale)
        # PURPLE score is typically 0-1, with 1 being best fit
        confidence = min(score, 0.95)
        
        return PurityEstimate(
            purity=purity,
            confidence=confidence,
            method="purple_hmf",
            supporting_variants=0,  # PURPLE uses multiple data types
            vaf_distribution={},
            quality_metrics={
                "purple_score": score,
                "source_file": str(purity_file)
            }
        )


def estimate_tumor_purity(variant_annotations: List[VariantAnnotation],
                         analysis_type: AnalysisType,
                         metadata: Optional[Dict[str, Any]] = None,
                         purple_output_path: Optional[Path] = None) -> PurityEstimate:
    """
    Convenience function to estimate tumor purity
    
    Args:
        variant_annotations: List of variant annotations
        analysis_type: Analysis workflow type
        metadata: Analysis metadata
        purple_output_path: Path to PURPLE output
        
    Returns:
        PurityEstimate with purity, confidence, and quality metrics
    """
    integrator = PurityMetadataIntegrator()
    return integrator.get_tumor_purity(
        variant_annotations, analysis_type, metadata, purple_output_path
    )