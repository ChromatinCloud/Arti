"""
GA4GH VRS (Variation Representation Specification) Handler

Provides comprehensive VRS implementation for:
- Variant normalization and identification
- Computed identifier generation
- Integration with reference sequences
- Support for complex variants (CNVs, fusions)
"""

from typing import Dict, List, Optional, Union
from dataclasses import dataclass
import hashlib
import json
import logging
from pathlib import Path

try:
    from ga4gh.vrs import models, normalize
    from ga4gh.core import ga4gh_identify, sha512t24u
    from biocommons.seqrepo import SeqRepo
    VRS_AVAILABLE = True
except ImportError:
    # Make VRS optional for basic functionality
    VRS_AVAILABLE = False
    models = None
    normalize = None
    ga4gh_identify = None
    sha512t24u = None
    SeqRepo = None

from ..models import VariantAnnotation, StructuralVariant

logger = logging.getLogger(__name__)


@dataclass
class VRSConfig:
    """Configuration for VRS handling"""
    seqrepo_dir: Optional[Path] = None
    use_refget: bool = True
    normalize_variants: bool = True
    assembly: str = "GRCh38"
    
    # Reference sequence accessions
    refseq_accessions: Dict[str, Dict[str, str]] = None
    
    def __post_init__(self):
        if self.refseq_accessions is None:
            self.refseq_accessions = {
                "GRCh38": {
                    "1": "NC_000001.11", "2": "NC_000002.12", "3": "NC_000003.12",
                    "4": "NC_000004.12", "5": "NC_000005.10", "6": "NC_000006.12",
                    "7": "NC_000007.14", "8": "NC_000008.11", "9": "NC_000009.12",
                    "10": "NC_000010.11", "11": "NC_000011.10", "12": "NC_000012.12",
                    "13": "NC_000013.11", "14": "NC_000014.9", "15": "NC_000015.10",
                    "16": "NC_000016.10", "17": "NC_000017.11", "18": "NC_000018.10",
                    "19": "NC_000019.10", "20": "NC_000020.11", "21": "NC_000021.9",
                    "22": "NC_000022.11", "X": "NC_000023.11", "Y": "NC_000024.10",
                    "MT": "NC_012920.1"
                },
                "GRCh37": {
                    "1": "NC_000001.10", "2": "NC_000002.11", "3": "NC_000003.11",
                    "4": "NC_000004.11", "5": "NC_000005.9", "6": "NC_000006.11",
                    "7": "NC_000007.13", "8": "NC_000008.10", "9": "NC_000009.11",
                    "10": "NC_000010.10", "11": "NC_000011.9", "12": "NC_000012.11",
                    "13": "NC_000013.10", "14": "NC_000014.8", "15": "NC_000015.9",
                    "16": "NC_000016.9", "17": "NC_000017.10", "18": "NC_000018.9",
                    "19": "NC_000019.9", "20": "NC_000020.10", "21": "NC_000021.8",
                    "22": "NC_000022.10", "X": "NC_000023.10", "Y": "NC_000024.9",
                    "MT": "NC_012920.1"
                }
            }


class VRSHandler:
    """
    Comprehensive handler for GA4GH VRS operations
    """
    
    def __init__(self, config: Optional[VRSConfig] = None):
        self.config = config or VRSConfig()
        self.vrs_available = VRS_AVAILABLE
        if self.vrs_available:
            self._setup_sequence_repo()
        else:
            logger.warning("GA4GH VRS not available - VRS functionality will be limited")
            self.seqrepo = None
        
    def _setup_sequence_repo(self):
        """Setup sequence repository for normalization"""
        if self.config.seqrepo_dir:
            try:
                self.seqrepo = SeqRepo(str(self.config.seqrepo_dir))
                logger.info(f"Loaded SeqRepo from {self.config.seqrepo_dir}")
            except Exception as e:
                logger.warning(f"Failed to load SeqRepo: {e}")
                self.seqrepo = None
        else:
            self.seqrepo = None
            
    def get_refseq_accession(self, chrom: str, assembly: str = None) -> str:
        """Get RefSeq accession for chromosome"""
        assembly = assembly or self.config.assembly
        chrom = chrom.replace("chr", "")
        
        if assembly not in self.config.refseq_accessions:
            raise ValueError(f"Unknown assembly: {assembly}")
            
        if chrom not in self.config.refseq_accessions[assembly]:
            raise ValueError(f"Unknown chromosome: {chrom}")
            
        return self.config.refseq_accessions[assembly][chrom]
    
    def create_allele(self, 
                     chrom: str,
                     pos: int,
                     ref: str,
                     alt: str,
                     assembly: str = None) -> models.Allele:
        """
        Create a VRS Allele object with proper normalization
        
        Args:
            chrom: Chromosome (with or without 'chr' prefix)
            pos: Position (1-based, VCF-style)
            ref: Reference allele
            alt: Alternate allele
            assembly: Genome assembly (default: from config)
            
        Returns:
            Normalized VRS Allele object
        """
        assembly = assembly or self.config.assembly
        
        # Get RefSeq accession
        refseq_id = self.get_refseq_accession(chrom, assembly)
        
        # Create sequence location (VRS uses interbase coordinates)
        location = models.SequenceLocation(
            sequenceReference=models.SequenceReference(
                refgetAccession=f"SQ.{self._compute_refget_id(refseq_id)}"
            ),
            start=pos - 1,  # Convert to 0-based
            end=pos - 1 + len(ref)
        )
        
        # Create allele
        allele = models.Allele(
            location=location,
            state=models.LiteralSequenceExpression(sequence=alt)
        )
        
        # Normalize if configured
        if self.config.normalize_variants and self.seqrepo:
            try:
                allele = normalize(allele, self.seqrepo)
                logger.debug(f"Normalized allele: {allele}")
            except Exception as e:
                logger.warning(f"Normalization failed: {e}")
        
        return allele
    
    def _compute_refget_id(self, refseq_id: str) -> str:
        """Compute refget identifier for sequence"""
        # In production, this would query refget service
        # For now, return a placeholder
        return sha512t24u(refseq_id.encode())
    
    def get_vrs_id(self, variant: VariantAnnotation) -> str:
        """
        Generate VRS computed identifier for a variant
        
        Returns the globally unique GA4GH identifier
        """
        allele = self.create_allele(
            variant.chromosome,
            variant.position,
            variant.reference,
            variant.alternate,
            variant.assembly or self.config.assembly
        )
        
        # Generate computed identifier
        vrs_id = ga4gh_identify(allele)
        
        # Store in variant for future use
        variant.vrs_id = vrs_id
        variant.vrs_allele = allele.model_dump()
        
        logger.info(f"Generated VRS ID: {vrs_id} for {variant.gene_symbol}:{variant.hgvs_p}")
        
        return vrs_id
    
    def create_cnv(self,
                   chrom: str,
                   start: int,
                   end: int,
                   copy_number: int,
                   assembly: str = None) -> models.CopyNumberChange:
        """
        Create VRS CopyNumberChange for CNVs
        """
        assembly = assembly or self.config.assembly
        refseq_id = self.get_refseq_accession(chrom, assembly)
        
        # Create location
        location = models.SequenceLocation(
            sequenceReference=models.SequenceReference(
                refgetAccession=f"SQ.{self._compute_refget_id(refseq_id)}"
            ),
            start=start - 1,  # Convert to 0-based
            end=end
        )
        
        # Create copy number change
        cnv = models.CopyNumberChange(
            location=location,
            copyChange=models.CopyChange(
                copyNumber=models.Number(value=copy_number)
            )
        )
        
        return cnv
    
    def create_fusion(self,
                     gene1: str,
                     gene2: str,
                     breakpoint1: Optional[int] = None,
                     breakpoint2: Optional[int] = None) -> Dict:
        """
        Create representation for gene fusion
        
        Note: VRS 2.0 will have better fusion support
        For now, return structured representation
        """
        fusion = {
            "type": "GeneFusion",
            "gene5prime": gene1,
            "gene3prime": gene2,
            "breakpoint5prime": breakpoint1,
            "breakpoint3prime": breakpoint2,
            "id": f"fusion.{gene1}::{gene2}"
        }
        
        # Generate identifier
        fusion_str = json.dumps(fusion, sort_keys=True)
        fusion["computed_id"] = f"ga4gh:GF.{sha512t24u(fusion_str.encode())}"
        
        return fusion
    
    def batch_normalize_variants(self, 
                               variants: List[VariantAnnotation]) -> List[str]:
        """
        Batch process variants for VRS IDs
        
        Returns list of VRS IDs in same order as input
        """
        vrs_ids = []
        
        for variant in variants:
            try:
                vrs_id = self.get_vrs_id(variant)
                vrs_ids.append(vrs_id)
            except Exception as e:
                logger.error(f"Failed to generate VRS ID for {variant}: {e}")
                vrs_ids.append(None)
                
        return vrs_ids


class VRSNormalizer:
    """
    Advanced VRS normalization for complex cases
    """
    
    def __init__(self, vrs_handler: VRSHandler):
        self.vrs_handler = vrs_handler
        
    def normalize_variant_list(self, variants: List[VariantAnnotation]) -> Dict:
        """
        Normalize a list of variants and identify duplicates
        
        Returns:
            Dict with normalized variants and duplicate groups
        """
        normalized_groups = {}
        
        for variant in variants:
            try:
                vrs_id = self.vrs_handler.get_vrs_id(variant)
                
                if vrs_id not in normalized_groups:
                    normalized_groups[vrs_id] = []
                    
                normalized_groups[vrs_id].append(variant)
                
            except Exception as e:
                logger.error(f"Normalization failed for {variant}: {e}")
        
        # Identify duplicates
        duplicates = {
            vrs_id: variants 
            for vrs_id, variants in normalized_groups.items() 
            if len(variants) > 1
        }
        
        return {
            "normalized": normalized_groups,
            "duplicates": duplicates,
            "unique_count": len(normalized_groups),
            "total_count": len(variants)
        }
    
    def is_equivalent(self, var1: VariantAnnotation, var2: VariantAnnotation) -> bool:
        """
        Check if two variants are equivalent after normalization
        """
        try:
            vrs_id1 = self.vrs_handler.get_vrs_id(var1)
            vrs_id2 = self.vrs_handler.get_vrs_id(var2)
            return vrs_id1 == vrs_id2
        except Exception:
            return False