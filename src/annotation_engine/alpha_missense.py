"""
AlphaMissense Pathogenicity Prediction Integration

Provides lookup functionality for AlphaMissense pathogenicity scores
using flat file TSV format for fast variant annotation.
"""

import gzip
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Any
import pandas as pd
from functools import lru_cache

logger = logging.getLogger(__name__)


class AlphaMissenseLoader:
    """Load and query AlphaMissense pathogenicity predictions"""
    
    def __init__(self, refs_dir: Optional[Path] = None):
        if refs_dir is None:
            refs_dir = Path(__file__).parent.parent.parent / ".refs"
        
        self.refs_dir = Path(refs_dir)
        self.alphamissense_dir = self.refs_dir / "alphamissense"
        self.data_file = self.alphamissense_dir / "AlphaMissense_hg38.tsv.gz"
        
        # Cache for loaded data
        self._data_cache = None
        self._index_cache = None
        
    def _scan_for_variant(self, chromosome: str, position: int, 
                         reference: str, alternate: str) -> Optional[Dict[str, Any]]:
        """Scan AlphaMissense file for specific variant (memory efficient)"""
        if not self.data_file.exists():
            return None
        
        # Clean chromosome name
        chrom = chromosome if chromosome.startswith('chr') else f'chr{chromosome}'
        
        try:
            with gzip.open(self.data_file, 'rt') as f:
                header_found = False
                
                for line_num, line in enumerate(f):
                    # Skip copyright lines
                    if line.startswith('#') and not line.startswith('#CHROM'):
                        continue
                    
                    # Parse header
                    if line.startswith('#CHROM'):
                        header_found = True
                        continue
                    
                    if not header_found:
                        continue
                    
                    # Parse data line
                    fields = line.strip().split('\t')
                    if len(fields) < 10:
                        continue
                    
                    file_chrom = fields[0]
                    file_pos = int(fields[1])
                    file_ref = fields[2]
                    file_alt = fields[3]
                    
                    # Check for match
                    if (file_chrom == chrom and 
                        file_pos == position and 
                        file_ref == reference and 
                        file_alt == alternate):
                        
                        return {
                            'pathogenicity_score': float(fields[8]),
                            'classification': fields[9],
                            'transcript_id': fields[6],
                            'protein_variant': fields[7],
                            'uniprot_id': fields[5],
                            'source': 'AlphaMissense'
                        }
                    
                    # Early termination if we've passed the position (assuming sorted)
                    if file_chrom == chrom and file_pos > position:
                        break
                    
                    # Progress logging for large files
                    if line_num % 1000000 == 0:
                        logger.debug(f"Scanned {line_num} AlphaMissense lines...")
                        
            return None
            
        except Exception as e:
            logger.debug(f"AlphaMissense scan failed: {e}")
            return None
    
    @lru_cache(maxsize=1000)
    def lookup_variant(self, chromosome: str, position: int, 
                      reference: str, alternate: str) -> Optional[Dict[str, Any]]:
        """
        Look up AlphaMissense prediction for a variant
        
        Args:
            chromosome: Chromosome (with or without 'chr' prefix)
            position: Genomic position
            reference: Reference allele
            alternate: Alternate allele
            
        Returns:
            Dictionary with pathogenicity score and classification, or None
        """
        return self._scan_for_variant(chromosome, position, reference, alternate)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about AlphaMissense data availability"""
        if not self.data_file.exists():
            return {"total_variants": 0, "available": False}
        
        # Basic file stats without loading everything
        stats = {
            "available": True,
            "file_path": str(self.data_file),
            "file_size_mb": round(self.data_file.stat().st_size / (1024*1024), 1)
        }
        
        return stats


# Global instance for efficient reuse
_alphamissense_loader = None

def get_alphamissense_loader(refs_dir: Optional[Path] = None) -> AlphaMissenseLoader:
    """Get global AlphaMissense loader instance"""
    global _alphamissense_loader
    if _alphamissense_loader is None:
        _alphamissense_loader = AlphaMissenseLoader(refs_dir)
    return _alphamissense_loader


def lookup_alphamissense_score(chromosome: str, position: int, 
                              reference: str, alternate: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to lookup AlphaMissense prediction
    
    Args:
        chromosome: Chromosome (with or without 'chr' prefix)
        position: Genomic position  
        reference: Reference allele
        alternate: Alternate allele
        
    Returns:
        Dictionary with pathogenicity score and classification, or None
    """
    loader = get_alphamissense_loader()
    return loader.lookup_variant(chromosome, position, reference, alternate)