"""
Variant Processing Pipeline

Coordinates VCF filtering, variant annotation, and evidence aggregation
to create complete VariantAnnotation objects ready for tiering.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .models import VariantAnnotation, AnalysisType
from .vcf_filtering import filter_vcf_by_analysis_type
from .validation.error_handler import ValidationError
from .vep_runner import annotate_vcf_with_vep, VEPConfiguration

logger = logging.getLogger(__name__)


class VariantProcessor:
    """
    Main variant processing pipeline
    
    Coordinates filtering → annotation → evidence aggregation
    """
    
    def __init__(self, vep_config: Optional[VEPConfiguration] = None):
        self.logger = logging.getLogger(__name__)
        self.vep_config = vep_config
    
    def process_variants(self, 
                        tumor_vcf_path: Path,
                        analysis_type: AnalysisType,
                        normal_vcf_path: Optional[Path] = None,
                        cancer_type: str = "unknown",
                        **filter_kwargs) -> Tuple[List[VariantAnnotation], Dict[str, Any]]:
        """
        Complete variant processing pipeline
        
        Args:
            tumor_vcf_path: Path to tumor VCF
            analysis_type: Analysis workflow type
            normal_vcf_path: Path to normal VCF (for TN analysis)
            cancer_type: Cancer type context
            **filter_kwargs: Additional filtering parameters
            
        Returns:
            Tuple of (variant_annotations, processing_summary)
        """
        
        logger.info(f"Starting variant processing: {analysis_type.value}")
        
        # Step 1: Apply VCF filtering based on analysis type
        filtered_variants, filter_summary = self._apply_vcf_filtering(
            tumor_vcf_path, analysis_type, normal_vcf_path, **filter_kwargs
        )
        
        # Step 2: Run VEP annotation on filtered variants
        variant_annotations = self._annotate_variants_with_vep(
            filtered_variants, tumor_vcf_path, analysis_type, cancer_type
        )
        
        # Step 3: Basic quality control and validation
        validated_variants = self._apply_quality_control(variant_annotations)
        
        # Create processing summary
        processing_summary = {
            "analysis_type": analysis_type.value,
            "input_files": {
                "tumor_vcf": str(tumor_vcf_path),
                "normal_vcf": str(normal_vcf_path) if normal_vcf_path else None
            },
            "filtering": filter_summary,
            "annotation": {
                "total_variants": len(variant_annotations),
                "validated_variants": len(validated_variants),
                "cancer_type": cancer_type
            }
        }
        
        logger.info(f"Variant processing complete: {len(validated_variants)} variants ready for tiering")
        
        return validated_variants, processing_summary
    
    def _apply_vcf_filtering(self, 
                           tumor_vcf_path: Path,
                           analysis_type: AnalysisType,
                           normal_vcf_path: Optional[Path],
                           **filter_kwargs) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Apply analysis-type-specific VCF filtering"""
        
        try:
            filtered_variants, filter_summary = filter_vcf_by_analysis_type(
                tumor_vcf_path=tumor_vcf_path,
                analysis_type=analysis_type,
                normal_vcf_path=normal_vcf_path,
                **filter_kwargs
            )
            
            logger.info(f"VCF filtering complete: {filter_summary['passed_variants']} variants passed")
            return filtered_variants, filter_summary
            
        except Exception as e:
            raise ValidationError(
                error_type="vcf_filtering_error",
                message=f"VCF filtering failed: {str(e)}",
                details={
                    "tumor_vcf": str(tumor_vcf_path),
                    "normal_vcf": str(normal_vcf_path) if normal_vcf_path else None,
                    "analysis_type": analysis_type.value,
                    "error": str(e)
                }
            )
    
    def _annotate_variants_with_vep(self, 
                                   filtered_variants: List[Dict[str, Any]],
                                   original_vcf_path: Path,
                                   analysis_type: AnalysisType,
                                   cancer_type: str) -> List[VariantAnnotation]:
        """Annotate filtered variants using VEP"""
        
        # If no variants after filtering, return empty list
        if not filtered_variants:
            logger.info("No variants to annotate after filtering")
            return []
        
        # Create temporary VCF with filtered variants
        temp_vcf_path = self._create_temp_vcf(filtered_variants, original_vcf_path)
        
        try:
            # Run VEP annotation
            logger.info(f"Running VEP annotation on {len(filtered_variants)} filtered variants")
            variant_annotations = annotate_vcf_with_vep(
                input_vcf=temp_vcf_path,
                output_format="annotations",
                config=self.vep_config
            )
            
            # Enhance annotations with VCF quality data
            enhanced_annotations = self._enhance_annotations_with_vcf_data(
                variant_annotations, filtered_variants
            )
            
            logger.info(f"VEP annotation complete: {len(enhanced_annotations)} variants annotated")
            return enhanced_annotations
            
        except Exception as e:
            logger.error(f"VEP annotation failed: {e}")
            # Fall back to basic annotation without VEP
            logger.warning("Falling back to basic annotation without VEP")
            return self._create_basic_annotations(filtered_variants)
        
        finally:
            # Clean up temporary VCF
            if temp_vcf_path.exists():
                temp_vcf_path.unlink()
    
    def _create_temp_vcf(self, filtered_variants: List[Dict[str, Any]], original_vcf_path: Path) -> Path:
        """Create temporary VCF file with filtered variants"""
        
        import tempfile
        
        # Create temporary VCF file
        temp_fd, temp_vcf_path = tempfile.mkstemp(suffix='.vcf', prefix='filtered_')
        temp_vcf_path = Path(temp_vcf_path)
        
        try:
            with open(temp_vcf_path, 'w') as temp_vcf:
                # Copy header from original VCF
                with open(original_vcf_path, 'r') as orig_vcf:
                    for line in orig_vcf:
                        if line.startswith('#'):
                            temp_vcf.write(line)
                        else:
                            break  # Stop at first data line
                
                # Write filtered variants
                for variant in filtered_variants:
                    # Format VCF line
                    vcf_line = "\t".join([
                        str(variant.get('chromosome', '.')),
                        str(variant.get('position', '.')),
                        variant.get('id', '.'),
                        variant.get('reference', '.'),
                        variant.get('alternate', '.'),
                        str(variant.get('quality_score', '.')),
                        variant.get('filter_status', 'PASS'),
                        variant.get('info', '.'),
                        variant.get('format', '.'),
                        variant.get('sample_data', '.')
                    ])
                    temp_vcf.write(vcf_line + '\n')
            
            return temp_vcf_path
            
        except Exception as e:
            if temp_vcf_path.exists():
                temp_vcf_path.unlink()
            raise ValidationError(
                error_type="temp_vcf_creation_error",
                message=f"Failed to create temporary VCF: {e}",
                details={"original_vcf": str(original_vcf_path), "error": str(e)}
            )
    
    def _enhance_annotations_with_vcf_data(self, 
                                         variant_annotations: List[VariantAnnotation],
                                         filtered_variants: List[Dict[str, Any]]) -> List[VariantAnnotation]:
        """Enhance VEP annotations with VCF quality data"""
        
        # Create lookup for VCF data by position
        vcf_lookup = {}
        for variant in filtered_variants:
            key = f"{variant.get('chromosome')}:{variant.get('position')}"
            vcf_lookup[key] = variant
        
        enhanced_annotations = []
        
        for annotation in variant_annotations:
            key = f"{annotation.chromosome}:{annotation.position}"
            vcf_data = vcf_lookup.get(key, {})
            
            # Update annotation with VCF quality data
            annotation.quality_score = vcf_data.get('quality_score', annotation.quality_score)
            annotation.filter_status = vcf_data.get('filter_status', annotation.filter_status) or ['PASS']
            annotation.total_depth = vcf_data.get('total_depth', annotation.total_depth)
            annotation.vaf = self._extract_vaf(vcf_data) or annotation.vaf
            
            enhanced_annotations.append(annotation)
        
        return enhanced_annotations
    
    def _create_basic_annotations(self, filtered_variants: List[Dict[str, Any]]) -> List[VariantAnnotation]:
        """Create basic VariantAnnotation objects without VEP (fallback)"""
        
        variant_annotations = []
        
        for vcf_record in filtered_variants:
            try:
                # Extract basic variant information
                variant_annotation = VariantAnnotation(
                    chromosome=vcf_record['chromosome'],
                    position=vcf_record['position'],
                    reference=vcf_record['reference'],
                    alternate=vcf_record['alternate'],
                    gene_symbol=self._extract_gene_symbol(vcf_record),
                    
                    # Quality metrics from VCF
                    quality_score=vcf_record.get('quality_score'),
                    filter_status=vcf_record.get('filter_status', ['PASS']),
                    total_depth=vcf_record.get('total_depth'),
                    vaf=self._extract_vaf(vcf_record),
                    
                    # Basic annotations (without VEP)
                    consequence=self._extract_consequence(vcf_record),
                    impact=vcf_record.get('impact'),
                    
                    # Placeholder for population frequencies (to be filled by evidence aggregator)
                    population_frequencies=[],
                    hotspot_evidence=[],
                    functional_predictions=[],
                    civic_evidence=[],
                    therapeutic_implications=[],
                    
                    # Metadata
                    annotation_source="basic_annotation"
                )
                
                variant_annotations.append(variant_annotation)
                
            except Exception as e:
                logger.warning(f"Failed to create basic annotation for variant: {e}")
                continue
        
        return variant_annotations
    
    def _extract_gene_symbol(self, vcf_record: Dict[str, Any]) -> str:
        """
        Extract gene symbol from VCF record
        
        This is a placeholder - in production would use VEP annotations
        """
        # Check if gene is annotated in INFO field
        # This is very basic - real implementation would use VEP
        
        # For now, use chromosome:position as placeholder
        return f"CHR{vcf_record['chromosome']}_{vcf_record['position']}"
    
    def _extract_vaf(self, vcf_record: Dict[str, Any]) -> Optional[float]:
        """Extract variant allele frequency from VCF record"""
        
        # Try INFO field first
        if vcf_record.get('allele_frequency'):
            return vcf_record['allele_frequency']
        
        # Try sample data
        if vcf_record.get('samples'):
            sample = vcf_record['samples'][0]  # First sample (tumor)
            return sample.get('variant_allele_frequency')
        
        return None
    
    def _extract_consequence(self, vcf_record: Dict[str, Any]) -> List[str]:
        """
        Extract consequence information from VCF record
        
        Placeholder - real implementation would use VEP annotations
        """
        # This is a very basic placeholder
        # Real implementation would parse VEP CSQ field
        
        # For now, infer basic consequence from variant type
        ref = vcf_record['reference']
        alt = vcf_record['alternate']
        
        if not alt:
            return ['unknown']
        
        if len(ref) == 1 and len(alt) == 1:
            return ['missense_variant']  # SNV
        elif len(alt) > len(ref):
            return ['insertion']
        elif len(alt) < len(ref):
            return ['deletion']
        else:
            return ['complex_variant']
    
    def _apply_quality_control(self, variant_annotations: List[VariantAnnotation]) -> List[VariantAnnotation]:
        """Apply final quality control filters"""
        
        validated_variants = []
        
        for variant in variant_annotations:
            # Basic validation
            if self._passes_final_qc(variant):
                validated_variants.append(variant)
            else:
                logger.debug(f"Variant failed final QC: {variant.chromosome}:{variant.position}")
        
        return validated_variants
    
    def _passes_final_qc(self, variant: VariantAnnotation) -> bool:
        """Final quality control checks"""
        
        # Check required fields
        if not all([variant.chromosome, variant.position, variant.reference, variant.alternate]):
            return False
        
        # Check filter status
        if 'PASS' not in variant.filter_status:
            return False
        
        # Additional QC can be added here
        
        return True


def create_variant_annotations_from_vcf(tumor_vcf_path: Path,
                                       analysis_type: AnalysisType,
                                       normal_vcf_path: Optional[Path] = None,
                                       cancer_type: str = "unknown",
                                       vep_config: Optional[VEPConfiguration] = None,
                                       **kwargs) -> Tuple[List[VariantAnnotation], Dict[str, Any]]:
    """
    Convenience function to create variant annotations from VCF files
    
    Args:
        tumor_vcf_path: Path to tumor VCF
        analysis_type: Analysis workflow type
        normal_vcf_path: Path to normal VCF (for TN analysis)
        cancer_type: Cancer type context
        vep_config: VEP configuration (optional)
        **kwargs: Additional processing parameters
        
    Returns:
        Tuple of (variant_annotations, processing_summary)
    """
    processor = VariantProcessor(vep_config=vep_config)
    return processor.process_variants(
        tumor_vcf_path=tumor_vcf_path,
        analysis_type=analysis_type,
        normal_vcf_path=normal_vcf_path,
        cancer_type=cancer_type,
        **kwargs
    )