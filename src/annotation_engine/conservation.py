"""
Conservation Score Integration (GERP)

Provides lookup functionality for GERP conservation scores
using BigWig format for fast genomic position queries.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Any, Union
from functools import lru_cache

try:
    import pyBigWig
except ImportError:
    pyBigWig = None

logger = logging.getLogger(__name__)


class GERPLoader:
    """Load and query GERP conservation scores from BigWig files"""
    
    def __init__(self, refs_dir: Optional[Path] = None):
        if refs_dir is None:
            refs_dir = Path(__file__).parent.parent.parent / ".refs"
        
        self.refs_dir = Path(refs_dir)
        self.conservation_dir = self.refs_dir / "conservation"
        self.gerp_file = self.conservation_dir / "gerp_conservation_scores.homo_sapiens.GRCh38.bw"
        
        # BigWig file handle (opened lazily)
        self._bw_handle = None
        self._available = None
        
    def _get_bigwig_handle(self):
        """Get BigWig file handle, opening if necessary"""
        if pyBigWig is None:
            logger.warning("pyBigWig not available - install with: pip install pyBigWig")
            return None
            
        if self._bw_handle is None:
            if not self.gerp_file.exists():
                logger.warning(f"GERP conservation file not found: {self.gerp_file}")
                return None
                
            try:
                self._bw_handle = pyBigWig.open(str(self.gerp_file))
                logger.info(f"Opened GERP conservation file: {self.gerp_file}")
            except Exception as e:
                logger.error(f"Failed to open GERP BigWig file: {e}")
                return None
                
        return self._bw_handle
    
    def is_available(self) -> bool:
        """Check if GERP conservation data is available"""
        if self._available is None:
            bw = self._get_bigwig_handle()
            self._available = bw is not None
        return self._available
    
    @lru_cache(maxsize=10000)
    def lookup_position(self, chromosome: str, position: int) -> Optional[float]:
        """
        Look up GERP conservation score for a genomic position
        
        Args:
            chromosome: Chromosome (with or without 'chr' prefix)
            position: Genomic position (1-based)
            
        Returns:
            GERP conservation score as float, or None if not available
        """
        bw = self._get_bigwig_handle()
        if bw is None:
            return None
        
        # Ensure chromosome has 'chr' prefix for BigWig lookup
        chrom = chromosome if chromosome.startswith('chr') else f'chr{chromosome}'
        
        try:
            # BigWig is 0-based, but we accept 1-based positions
            score = bw.values(chrom, position - 1, position)
            
            if score and len(score) > 0 and score[0] is not None:
                return float(score[0])
            else:
                return None
                
        except Exception as e:
            logger.debug(f"GERP lookup failed for {chrom}:{position}: {e}")
            return None
    
    def lookup_region(self, chromosome: str, start: int, end: int) -> Dict[str, Any]:
        """
        Look up GERP conservation scores for a genomic region
        
        Args:
            chromosome: Chromosome (with or without 'chr' prefix)
            start: Start position (1-based, inclusive)
            end: End position (1-based, inclusive)
            
        Returns:
            Dictionary with summary statistics for the region
        """
        bw = self._get_bigwig_handle()
        if bw is None:
            return {"available": False}
        
        # Ensure chromosome has 'chr' prefix
        chrom = chromosome if chromosome.startswith('chr') else f'chr{chromosome}'
        
        try:
            # Convert to 0-based for BigWig
            scores = bw.values(chrom, start - 1, end)
            
            if scores:
                # Filter out None values
                valid_scores = [s for s in scores if s is not None]
                
                if valid_scores:
                    return {
                        "available": True,
                        "region": f"{chrom}:{start}-{end}",
                        "num_positions": len(valid_scores),
                        "mean_score": sum(valid_scores) / len(valid_scores),
                        "min_score": min(valid_scores),
                        "max_score": max(valid_scores),
                        "scores": valid_scores
                    }
            
            return {"available": True, "num_positions": 0, "scores": []}
            
        except Exception as e:
            logger.debug(f"GERP region lookup failed for {chrom}:{start}-{end}: {e}")
            return {"available": False, "error": str(e)}
    
    def get_chromosomes(self) -> list:
        """Get list of available chromosomes in the BigWig file"""
        bw = self._get_bigwig_handle()
        if bw is None:
            return []
        
        try:
            return list(bw.chroms().keys())
        except Exception as e:
            logger.error(f"Failed to get chromosome list: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the GERP conservation data"""
        if not self.is_available():
            return {"available": False}
        
        bw = self._get_bigwig_handle()
        chromosomes = self.get_chromosomes()
        
        stats = {
            "available": True,
            "file_path": str(self.gerp_file),
            "chromosomes": chromosomes,
            "num_chromosomes": len(chromosomes)
        }
        
        # Add chromosome lengths if available
        try:
            chrom_info = bw.chroms()
            stats["chromosome_lengths"] = dict(chrom_info)
        except Exception:
            pass
            
        return stats
    
    def __del__(self):
        """Clean up BigWig file handle"""
        if self._bw_handle is not None:
            try:
                self._bw_handle.close()
            except Exception:
                pass


# Global instance for efficient reuse
_gerp_loader = None

def get_gerp_loader(refs_dir: Optional[Path] = None) -> GERPLoader:
    """Get global GERP loader instance"""
    global _gerp_loader
    if _gerp_loader is None:
        _gerp_loader = GERPLoader(refs_dir)
    return _gerp_loader


class PhyloPLoader:
    """Load and query PhyloP conservation scores from BigWig files"""
    
    def __init__(self, refs_dir: Optional[Path] = None):
        if refs_dir is None:
            refs_dir = Path(__file__).parent.parent.parent / ".refs"
        
        self.refs_dir = Path(refs_dir)
        self.conservation_dir = self.refs_dir / "functional_predictions" / "plugin_data" / "conservation"
        self.phylop_file = self.conservation_dir / "hg38.phyloP100way.bw"
        
        # BigWig file handle (opened lazily)
        self._bw_handle = None
        self._available = None
        
    def _get_bigwig_handle(self):
        """Get BigWig file handle, opening if necessary"""
        if pyBigWig is None:
            logger.warning("pyBigWig not available - install with: pip install pyBigWig")
            return None
            
        if self._bw_handle is None:
            if not self.phylop_file.exists():
                logger.warning(f"PhyloP conservation file not found: {self.phylop_file}")
                return None
                
            try:
                self._bw_handle = pyBigWig.open(str(self.phylop_file))
                logger.info(f"Opened PhyloP conservation file: {self.phylop_file}")
            except Exception as e:
                logger.error(f"Failed to open PhyloP BigWig file: {e}")
                return None
                
        return self._bw_handle
    
    def is_available(self) -> bool:
        """Check if PhyloP conservation data is available"""
        if self._available is None:
            bw = self._get_bigwig_handle()
            self._available = bw is not None
        return self._available
    
    @lru_cache(maxsize=10000)
    def lookup_position(self, chromosome: str, position: int) -> Optional[float]:
        """Look up PhyloP conservation score for a genomic position"""
        bw = self._get_bigwig_handle()
        if bw is None:
            return None
        
        # Ensure chromosome has 'chr' prefix for BigWig lookup
        chrom = chromosome if chromosome.startswith('chr') else f'chr{chromosome}'
        
        try:
            # BigWig is 0-based, but we accept 1-based positions
            score = bw.values(chrom, position - 1, position)
            
            if score and len(score) > 0 and score[0] is not None:
                return float(score[0])
            else:
                return None
                
        except Exception as e:
            logger.debug(f"PhyloP lookup failed for {chrom}:{position}: {e}")
            return None


# Global instances
_phylop_loader = None

def get_phylop_loader(refs_dir: Optional[Path] = None) -> PhyloPLoader:
    """Get global PhyloP loader instance"""
    global _phylop_loader
    if _phylop_loader is None:
        _phylop_loader = PhyloPLoader(refs_dir)
    return _phylop_loader


def lookup_gerp_score(chromosome: str, position: int) -> Optional[float]:
    """
    Convenience function to lookup GERP conservation score
    
    Args:
        chromosome: Chromosome (with or without 'chr' prefix)
        position: Genomic position (1-based)
        
    Returns:
        GERP conservation score as float, or None if not available
    """
    loader = get_gerp_loader()
    return loader.lookup_position(chromosome, position)


def interpret_gerp_score(score: Optional[float]) -> Dict[str, Any]:
    """
    Interpret GERP conservation score according to standard thresholds
    
    Args:
        score: GERP conservation score
        
    Returns:
        Dictionary with interpretation and category
    """
    if score is None:
        return {
            "score": None,
            "category": "unknown",
            "interpretation": "No GERP score available"
        }
    
    # GERP score interpretation (standard thresholds)
    if score >= 2.0:
        category = "highly_conserved"
        interpretation = "Highly conserved, likely functional"
    elif score >= 0.0:
        category = "conserved"
        interpretation = "Moderately conserved"
    else:
        category = "not_conserved"
        interpretation = "Not conserved, likely neutral"
    
    return {
        "score": score,
        "category": category,
        "interpretation": interpretation
    }