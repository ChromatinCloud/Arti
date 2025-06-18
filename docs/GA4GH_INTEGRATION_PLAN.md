# GA4GH Integration Plan for Annotation Engine

## Executive Summary

The Global Alliance for Genomics and Health (GA4GH) provides crucial standards that can significantly enhance your annotation engine. As a VICC member (which is a GA4GH Driver Project), you're already aligned with GA4GH principles. Here's how to leverage GA4GH standards to improve interoperability, standardization, and clinical utility.

## Key GA4GH Standards Relevant to Your Project

### 1. **VRS (Variation Representation Specification)** - HIGHEST PRIORITY
**What it does**: Provides standardized, computable identifiers for variants
**Why you need it**: 
- Enables unambiguous variant identification across systems
- VICC already uses VRS identifiers in their meta-knowledgebase
- Allows integration with international variant databases

### 2. **Phenopackets**
**What it does**: Standardizes clinical and phenotypic data representation
**Why you need it**:
- Capture complete clinical context for variant interpretation
- Support cancer-specific features in v2.0
- Enable data exchange with clinical systems

### 3. **VA (Variant Annotation)**
**What it does**: Standardizes how variant annotations are represented
**Why you need it**:
- Consistent annotation format across different sources
- Interoperability with other GA4GH-compliant tools

### 4. **DUO (Data Use Ontology)**
**What it does**: Standardizes consent and data use terms
**Why you need it**:
- Ensure compliant data usage
- Automate access control decisions

## Implementation Strategy

### Phase 1: VRS Integration (Weeks 1-2)

#### 1.1 Install VRS Python Library
```bash
pip install ga4gh.vrs
```

#### 1.2 Create VRS Wrapper Module
```python
# src/annotation_engine/ga4gh/vrs_handler.py
from ga4gh.vrs import models, normalize, identify
from ga4gh.core import ga4gh_identify
import json

class VRSHandler:
    """
    Handles GA4GH VRS variant representation and identification
    """
    
    def __init__(self):
        self.data_proxy = self._setup_data_proxy()
    
    def create_allele(self, chrom: str, pos: int, ref: str, alt: str, 
                     assembly: str = "GRCh38") -> models.Allele:
        """
        Create a VRS Allele object from variant coordinates
        """
        # Create sequence location
        location = models.SequenceLocation(
            sequence_id=f"ga4gh:SQ.{self._get_refseq_id(chrom, assembly)}",
            interval=models.SequenceInterval(
                start=models.Number(value=pos - 1),  # VRS uses 0-based
                end=models.Number(value=pos - 1 + len(ref))
            )
        )
        
        # Create allele
        allele = models.Allele(
            location=location,
            state=models.SequenceState(sequence=alt)
        )
        
        # Normalize
        allele = normalize(allele, self.data_proxy)
        
        return allele
    
    def get_vrs_id(self, variant: VariantAnnotation) -> str:
        """
        Get VRS computed identifier for a variant
        """
        allele = self.create_allele(
            variant.chromosome,
            variant.position,
            variant.reference,
            variant.alternate,
            variant.assembly or "GRCh38"
        )
        
        # Generate computed identifier
        vrs_id = ga4gh_identify(allele)
        
        return vrs_id
    
    def query_vicc_by_vrs(self, vrs_id: str) -> Dict:
        """
        Query VICC meta-knowledgebase using VRS ID
        """
        # VICC supports VRS queries
        url = f"https://search.cancervariants.org/api/v1/associations"
        params = {"q": vrs_id, "size": 10}
        
        # Make request (simplified - add error handling)
        response = requests.get(url, params=params)
        return response.json()
```

#### 1.3 Enhance Variant Model
```python
# Update models.py
@dataclass
class VariantAnnotation:
    # Existing fields...
    
    # GA4GH additions
    vrs_id: Optional[str] = None
    vrs_allele: Optional[Dict] = None  # Serialized VRS Allele
    ga4gh_variant_id: Optional[str] = None  # For cross-referencing
```

### Phase 2: Phenopackets Integration (Weeks 3-4)

#### 2.1 Install Phenopackets
```bash
pip install phenopackets
```

#### 2.2 Create Phenopacket Builder
```python
# src/annotation_engine/ga4gh/phenopacket_builder.py
from phenopackets import Phenopacket, Individual, Disease, Variant
from google.protobuf.timestamp_pb2 import Timestamp
import datetime

class PhenopacketBuilder:
    """
    Builds GA4GH Phenopackets for cancer cases
    """
    
    def create_cancer_phenopacket(self,
                                 patient_id: str,
                                 cancer_type: str,
                                 variants: List[VariantAnnotation],
                                 tier_results: List[TierResult]) -> Phenopacket:
        """
        Create a phenopacket for a cancer case with variants
        """
        # Create individual
        individual = Individual(
            id=patient_id,
            sex=Individual.UNKNOWN_SEX  # Update based on actual data
        )
        
        # Create disease (cancer)
        disease = Disease(
            term={
                "id": self._get_oncotree_id(cancer_type),
                "label": cancer_type
            },
            disease_stage=[{
                "id": "NCIT:C48732",
                "label": "Cancer stage"
            }]
        )
        
        # Create interpretations
        interpretations = []
        for variant, tier_result in zip(variants, tier_results):
            interpretation = self._create_interpretation(variant, tier_result)
            interpretations.append(interpretation)
        
        # Build phenopacket
        phenopacket = Phenopacket(
            id=f"{patient_id}_phenopacket",
            subject=individual,
            diseases=[disease],
            interpretations=interpretations,
            meta_data=self._create_metadata()
        )
        
        return phenopacket
    
    def _create_interpretation(self, variant: VariantAnnotation, 
                             tier_result: TierResult) -> Dict:
        """
        Create GA4GH-compliant interpretation
        """
        return {
            "id": f"interpretation_{variant.vrs_id}",
            "variant": {
                "variation_descriptor": {
                    "id": variant.vrs_id,
                    "variation": {
                        "allele": variant.vrs_allele
                    },
                    "molecule_context": "genomic"
                }
            },
            "acmg_pathogenicity_classification": tier_result.amp_scoring.tier.value,
            "therapeutic_actionability": {
                "level": tier_result.oncokb_scoring.therapeutic_level.value
                if tier_result.oncokb_scoring else None
            }
        }
```

### Phase 3: Enhanced Evidence Exchange (Weeks 5-6)

#### 3.1 Implement VA (Variant Annotation) Standard
```python
# src/annotation_engine/ga4gh/variant_annotation.py
class GA4GHVariantAnnotation:
    """
    Implements GA4GH Variant Annotation standard
    """
    
    def create_va_message(self, 
                         variant: VariantAnnotation,
                         evidence: List[Evidence]) -> Dict:
        """
        Create GA4GH VA-compliant annotation message
        """
        return {
            "version": "1.0",
            "variant": {
                "vrs_id": variant.vrs_id,
                "allele": variant.vrs_allele
            },
            "annotations": [
                self._evidence_to_annotation(e) for e in evidence
            ],
            "meta": {
                "generated_at": datetime.utcnow().isoformat(),
                "annotation_source": "annotation_engine",
                "version": "1.0.0"
            }
        }
    
    def _evidence_to_annotation(self, evidence: Evidence) -> Dict:
        """Convert internal evidence to GA4GH annotation"""
        return {
            "type": self._map_evidence_type(evidence),
            "assertion": {
                "code": evidence.code,
                "system": evidence.guideline,
                "display": evidence.description
            },
            "evidence_level": evidence.score,
            "source": evidence.source_kb,
            "confidence": evidence.confidence
        }
```

### Phase 4: Integration with Clinical Workflow (Weeks 7-8)

#### 4.1 Update CLI to Support GA4GH Formats
```python
# Update cli.py
parser.add_argument(
    '--output-format',
    choices=['json', 'tsv', 'phenopacket', 'ga4gh-va'],
    default='json',
    help='Output format (includes GA4GH standards)'
)

parser.add_argument(
    '--vrs-normalize',
    action='store_true',
    help='Normalize variants using GA4GH VRS'
)

parser.add_argument(
    '--phenopacket-input',
    type=Path,
    help='Input phenopacket file (GA4GH format)'
)
```

#### 4.2 Create GA4GH Service Info Endpoint
```python
# src/annotation_engine/ga4gh/service_info.py
class ServiceInfo:
    """
    Implements GA4GH Service Info specification
    """
    
    def get_service_info(self) -> Dict:
        """
        Return GA4GH-compliant service information
        """
        return {
            "id": "annotation-engine",
            "name": "Clinical Annotation Engine",
            "type": {
                "group": "org.ga4gh",
                "artifact": "annotation-service",
                "version": "1.0"
            },
            "description": "AMP/ASCO/CAP and CGC/VICC variant annotation",
            "organization": {
                "name": "Your Organization",
                "url": "https://your-org.com"
            },
            "version": "1.0.0",
            "environment": "production",
            "ga4gh": {
                "specifications": [
                    {"specification": "VRS", "version": "1.3"},
                    {"specification": "VA", "version": "0.2"},
                    {"specification": "Phenopackets", "version": "2.0"}
                ]
            }
        }
```

## Benefits of GA4GH Integration

### 1. **Immediate Benefits**
- Unambiguous variant identification via VRS IDs
- Direct querying of VICC meta-knowledgebase
- Standardized clinical data exchange

### 2. **Interoperability**
- Exchange data with other GA4GH-compliant systems
- Integration with international variant databases
- Compatibility with clinical decision support systems

### 3. **Future-Proofing**
- Aligned with international standards
- Ready for federated learning initiatives
- Prepared for cross-border data sharing

### 4. **Clinical Translation**
- EHR integration via Phenopackets
- Standardized reporting formats
- Machine-readable clinical interpretations

## Implementation Priorities

1. **High Priority**: VRS integration
   - Essential for variant identification
   - Enables VICC database queries
   - Required for modern variant exchange

2. **Medium Priority**: Phenopackets
   - Improves clinical context capture
   - Enables richer data exchange
   - Supports cancer-specific features

3. **Lower Priority**: Full VA implementation
   - Nice to have for complete standardization
   - Can be added incrementally

## Testing Strategy

### VRS Validation
```python
def test_vrs_implementation():
    # Test with known BRAF V600E
    variant = VariantAnnotation(
        chromosome="7",
        position=140453136,
        reference="A",
        alternate="T",
        assembly="GRCh38"
    )
    
    vrs_handler = VRSHandler()
    vrs_id = vrs_handler.get_vrs_id(variant)
    
    # Should match VICC's VRS ID for BRAF V600E
    expected = "ga4gh:VA.mJbjSsW541oOsOtBoX36Mppr6hMjbjFr"
    assert vrs_id == expected
```

## Resources and Documentation

- **VRS Python**: https://github.com/ga4gh/vrs-python
- **Phenopackets**: https://github.com/phenopackets/phenopacket-schema
- **VICC Meta-KB**: https://search.cancervariants.org/
- **GA4GH Starter Kit**: https://github.com/ga4gh/ga4gh-starter-kit

## Conclusion

GA4GH integration will transform your annotation engine from a standalone tool to a node in the global genomic data sharing network. Start with VRS for immediate benefits, then expand to other standards based on your clinical needs.