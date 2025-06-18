"""
GA4GH Standards Integration Module

Implements Global Alliance for Genomics and Health standards:
- VRS (Variation Representation Specification) for variant identification
- Phenopackets for clinical data exchange
- VA (Variant Annotation) for standardized annotations
- Service Info for discoverability

This module enhances the annotation engine with international interoperability.
"""

try:
    from .vrs_handler import VRSHandler, VRSNormalizer
    from .phenopacket_builder import PhenopacketBuilder, CancerPhenopacketCreator
    from .variant_annotation import GA4GHVariantAnnotation, AnnotationExporter
    from .vicc_integration import VICCMetaKnowledgebaseClient
    from .service_info import ServiceInfoProvider
    from .clinical_context import ClinicalContextExtractor
    GA4GH_AVAILABLE = True
except ImportError:
    # GA4GH dependencies not available - provide minimal fallbacks
    GA4GH_AVAILABLE = False
    
    class VRSHandler:
        def __init__(self, *args, **kwargs):
            self.vrs_available = False
        def get_vrs_id(self, *args, **kwargs):
            return None
            
    class PhenopacketBuilder:
        def __init__(self, *args, **kwargs):
            pass
            
    class AnnotationExporter:
        def __init__(self, *args, **kwargs):
            pass
            
    class ClinicalContextExtractor:
        def __init__(self, *args, **kwargs):
            pass

__all__ = [
    'VRSHandler',
    'VRSNormalizer', 
    'PhenopacketBuilder',
    'CancerPhenopacketCreator',
    'GA4GHVariantAnnotation',
    'AnnotationExporter',
    'VICCMetaKnowledgebaseClient',
    'ServiceInfoProvider',
    'ClinicalContextExtractor'
]

# Version info
__version__ = '1.0.0'
GA4GH_SPEC_VERSIONS = {
    'VRS': '1.3.0',
    'Phenopackets': '2.0.0',
    'VA': '0.2.0',
    'ServiceInfo': '1.0.0'
}