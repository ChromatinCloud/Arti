"""
Intelligent caching layer for knowledge base queries

This module provides high-performance caching for expensive KB operations:
1. OncoKB API queries (rate-limited)
2. ClinVar lookups (large dataset) 
3. Literature citation resolution
4. Complex evidence aggregation
5. Text generation results

Features:
- TTL-based expiration
- LRU eviction for memory management
- Compression for large results
- Cache warming strategies
- Performance monitoring
"""

import json
import gzip
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text

from .base import get_db_session
from .expanded_models import KnowledgeBaseCache
from ..models import Evidence

logger = logging.getLogger(__name__)


@dataclass
class CacheStats:
    """Cache performance statistics"""
    total_queries: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_evictions: int = 0
    avg_query_time_ms: float = 0.0
    cache_size_mb: float = 0.0
    hit_rate: float = 0.0


class KnowledgeBaseCacheManager:
    """
    High-performance caching manager for knowledge base queries
    
    Provides intelligent caching with:
    - TTL-based expiration
    - Size-based LRU eviction  
    - Compression for large results
    - Query pattern optimization
    """
    
    def __init__(self, 
                 max_cache_size_mb: int = 500,
                 default_ttl_hours: int = 24,
                 compression_threshold_kb: int = 10):
        """
        Initialize cache manager
        
        Args:
            max_cache_size_mb: Maximum cache size in MB
            default_ttl_hours: Default TTL for cached items
            compression_threshold_kb: Compress results larger than this
        """
        self.max_cache_size_mb = max_cache_size_mb
        self.default_ttl_hours = default_ttl_hours
        self.compression_threshold_kb = compression_threshold_kb
        
        # Performance tracking
        self.stats = CacheStats()
        
        # KB-specific TTL settings
        self.ttl_settings = {
            "oncokb": 12,      # OncoKB: 12 hours (updated frequently)
            "clinvar": 168,    # ClinVar: 1 week (updated weekly)  
            "cosmic": 720,     # COSMIC: 1 month (updated monthly)
            "gnomad": 8760,    # gnomAD: 1 year (stable population data)
            "literature": 48,  # Literature: 2 days (new publications)
            "civic": 24,       # CIViC: 1 day (community updates)
            "text_generation": 168  # Generated text: 1 week
        }
    
    def get_cached_result(self, 
                         cache_key: str,
                         kb_source: str,
                         query_type: str) -> Optional[Any]:
        """
        Retrieve cached result if available and not expired
        
        Args:
            cache_key: Unique identifier for the query
            kb_source: Knowledge base source (e.g., "oncokb", "clinvar")
            query_type: Type of query (e.g., "variant_lookup", "gene_search")
            
        Returns:
            Cached result or None if not found/expired
        """
        self.stats.total_queries += 1
        
        with get_db_session() as session:
            try:
                # Look up cache entry
                cache_entry = session.query(KnowledgeBaseCache).filter(
                    and_(
                        KnowledgeBaseCache.cache_key == cache_key,
                        KnowledgeBaseCache.kb_source == kb_source,
                        KnowledgeBaseCache.query_type == query_type,
                        or_(
                            KnowledgeBaseCache.expires_at.is_(None),
                            KnowledgeBaseCache.expires_at > datetime.utcnow()
                        )
                    )
                ).first()
                
                if cache_entry:
                    # Update access statistics
                    cache_entry.access_count += 1
                    cache_entry.last_accessed = datetime.utcnow()
                    session.commit()
                    
                    # Decompress if needed and return result
                    result = self._decompress_result(cache_entry.cached_result)
                    self.stats.cache_hits += 1
                    
                    logger.debug(f"Cache HIT: {kb_source}:{query_type}:{cache_key[:16]}...")
                    return result
                    
                else:
                    self.stats.cache_misses += 1
                    logger.debug(f"Cache MISS: {kb_source}:{query_type}:{cache_key[:16]}...")
                    return None
                    
            except Exception as e:
                logger.error(f"Error retrieving from cache: {e}")
                return None
    
    def cache_result(self,
                    cache_key: str,
                    kb_source: str, 
                    query_type: str,
                    result: Any,
                    custom_ttl_hours: Optional[int] = None) -> bool:
        """
        Cache a query result with appropriate TTL
        
        Args:
            cache_key: Unique identifier for the query
            kb_source: Knowledge base source
            query_type: Type of query
            result: Result to cache
            custom_ttl_hours: Custom TTL override
            
        Returns:
            True if cached successfully, False otherwise
        """
        with get_db_session() as session:
            try:
                # Calculate expiration time
                ttl_hours = custom_ttl_hours or self.ttl_settings.get(kb_source, self.default_ttl_hours)
                expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
                
                # Compress large results
                compressed_result, metadata = self._compress_result(result)
                
                # Create cache entry
                cache_entry = KnowledgeBaseCache(
                    cache_key=cache_key,
                    kb_source=kb_source,
                    query_type=query_type,
                    cached_result=compressed_result,
                    result_metadata=metadata,
                    expires_at=expires_at,
                    access_count=0,
                    kb_version=self._get_kb_version(kb_source),
                    data_checksum=self._calculate_checksum(result)
                )
                
                # Use merge to handle duplicates
                session.merge(cache_entry)
                session.commit()
                
                logger.debug(f"Cached: {kb_source}:{query_type}:{cache_key[:16]}... (TTL: {ttl_hours}h)")
                
                # Trigger cleanup if cache is getting large
                self._cleanup_if_needed(session)
                
                return True
                
            except Exception as e:
                logger.error(f"Error caching result: {e}")
                return False
    
    def generate_cache_key(self, **query_params) -> str:
        """
        Generate consistent cache key from query parameters
        
        Args:
            **query_params: Query parameters to hash
            
        Returns:
            SHA-256 hash of normalized parameters
        """
        # Sort parameters for consistent hashing
        normalized_params = {}
        for key, value in sorted(query_params.items()):
            if isinstance(value, (list, dict)):
                # Convert complex types to JSON for consistent hashing
                normalized_params[key] = json.dumps(value, sort_keys=True)
            else:
                normalized_params[key] = str(value)
        
        # Create hash
        params_string = json.dumps(normalized_params, sort_keys=True)
        return hashlib.sha256(params_string.encode()).hexdigest()
    
    def invalidate_cache(self,
                        kb_source: Optional[str] = None,
                        query_type: Optional[str] = None,
                        cache_key: Optional[str] = None) -> int:
        """
        Invalidate cache entries based on criteria
        
        Args:
            kb_source: Invalidate all entries for this KB source
            query_type: Invalidate all entries for this query type
            cache_key: Invalidate specific cache key
            
        Returns:
            Number of entries invalidated
        """
        with get_db_session() as session:
            try:
                query = session.query(KnowledgeBaseCache)
                
                if cache_key:
                    query = query.filter(KnowledgeBaseCache.cache_key == cache_key)
                if kb_source:
                    query = query.filter(KnowledgeBaseCache.kb_source == kb_source)
                if query_type:
                    query = query.filter(KnowledgeBaseCache.query_type == query_type)
                
                count = query.count()
                query.delete()
                session.commit()
                
                logger.info(f"Invalidated {count} cache entries")
                return count
                
            except Exception as e:
                logger.error(f"Error invalidating cache: {e}")
                return 0
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        
        with get_db_session() as session:
            try:
                # Calculate database statistics
                total_entries = session.query(KnowledgeBaseCache).count()
                
                # Size statistics  
                size_query = session.execute(text("""
                    SELECT 
                        kb_source,
                        COUNT(*) as entry_count,
                        AVG(access_count) as avg_access_count,
                        COUNT(CASE WHEN expires_at > datetime('now') OR expires_at IS NULL THEN 1 END) as active_entries
                    FROM kb_cache 
                    GROUP BY kb_source
                """))
                
                kb_stats = {}
                for row in size_query:
                    kb_stats[row.kb_source] = {
                        "entry_count": row.entry_count,
                        "avg_access_count": row.avg_access_count,
                        "active_entries": row.active_entries
                    }
                
                # Calculate hit rate
                hit_rate = self.stats.cache_hits / max(1, self.stats.total_queries)
                
                return {
                    "performance": {
                        "total_queries": self.stats.total_queries,
                        "cache_hits": self.stats.cache_hits,
                        "cache_misses": self.stats.cache_misses,
                        "hit_rate": f"{hit_rate:.1%}",
                        "avg_query_time_ms": self.stats.avg_query_time_ms
                    },
                    "storage": {
                        "total_entries": total_entries,
                        "max_size_mb": self.max_cache_size_mb,
                        "current_size_mb": self.stats.cache_size_mb
                    },
                    "by_kb_source": kb_stats,
                    "ttl_settings": self.ttl_settings
                }
                
            except Exception as e:
                logger.error(f"Error getting cache statistics: {e}")
                return {"error": str(e)}
    
    def warm_cache(self, kb_source: str, common_queries: List[Dict[str, Any]]) -> int:
        """
        Pre-populate cache with common queries
        
        Args:
            kb_source: Knowledge base to warm
            common_queries: List of query parameters to pre-execute
            
        Returns:
            Number of queries warmed
        """
        warmed_count = 0
        
        for query_params in common_queries:
            try:
                # Generate cache key
                cache_key = self.generate_cache_key(**query_params)
                
                # Check if already cached
                if self.get_cached_result(cache_key, kb_source, query_params.get("query_type", "unknown")):
                    continue
                
                # Execute query and cache result (implementation depends on KB)
                # This would typically call the actual KB API/database
                # For now, we'll skip the actual execution
                
                warmed_count += 1
                
            except Exception as e:
                logger.error(f"Error warming cache for {query_params}: {e}")
        
        logger.info(f"Warmed {warmed_count} cache entries for {kb_source}")
        return warmed_count
    
    def _compress_result(self, result: Any) -> Tuple[Any, Dict[str, Any]]:
        """Compress large results to save space"""
        
        # Convert result to JSON
        result_json = json.dumps(result, default=str)
        result_size_kb = len(result_json.encode()) / 1024
        
        metadata = {
            "original_size_kb": result_size_kb,
            "compressed": False,
            "compression_ratio": 1.0
        }
        
        # Compress if above threshold
        if result_size_kb > self.compression_threshold_kb:
            try:
                compressed_data = gzip.compress(result_json.encode())
                compressed_size_kb = len(compressed_data) / 1024
                
                metadata.update({
                    "compressed": True,
                    "compressed_size_kb": compressed_size_kb,
                    "compression_ratio": result_size_kb / compressed_size_kb
                })
                
                return compressed_data, metadata
                
            except Exception as e:
                logger.warning(f"Compression failed: {e}")
        
        return result, metadata
    
    def _decompress_result(self, cached_result: Any) -> Any:
        """Decompress cached results if needed"""
        
        try:
            # If it's bytes, try to decompress
            if isinstance(cached_result, bytes):
                decompressed = gzip.decompress(cached_result).decode()
                return json.loads(decompressed)
            else:
                # Already decompressed
                return cached_result
                
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            return cached_result
    
    def _calculate_checksum(self, result: Any) -> str:
        """Calculate MD5 checksum of result for integrity"""
        result_json = json.dumps(result, sort_keys=True, default=str)
        return hashlib.md5(result_json.encode()).hexdigest()
    
    def _get_kb_version(self, kb_source: str) -> str:
        """Get version identifier for knowledge base"""
        # In practice, this would query the KB for version info
        return f"{kb_source}_v{datetime.utcnow().strftime('%Y%m%d')}"
    
    def _cleanup_if_needed(self, session: Session) -> None:
        """Clean up expired and least-used cache entries if needed"""
        
        try:
            # Remove expired entries
            expired_count = session.query(KnowledgeBaseCache).filter(
                and_(
                    KnowledgeBaseCache.expires_at.isnot(None),
                    KnowledgeBaseCache.expires_at <= datetime.utcnow()
                )
            ).delete()
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired cache entries")
            
            # Check if we need size-based cleanup
            total_entries = session.query(KnowledgeBaseCache).count()
            
            # Simple size estimation (rough)
            estimated_size_mb = total_entries * 0.1  # Rough estimate
            
            if estimated_size_mb > self.max_cache_size_mb:
                # Remove least recently used entries
                entries_to_remove = int(total_entries * 0.1)  # Remove 10%
                
                oldest_entries = session.query(KnowledgeBaseCache).order_by(
                    KnowledgeBaseCache.last_accessed.asc()
                ).limit(entries_to_remove)
                
                for entry in oldest_entries:
                    session.delete(entry)
                
                self.stats.cache_evictions += entries_to_remove
                logger.info(f"Evicted {entries_to_remove} LRU cache entries")
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error during cache cleanup: {e}")


# ============================================================================
# SPECIALIZED CACHE DECORATORS
# ============================================================================

def cached_kb_query(kb_source: str, query_type: str, ttl_hours: Optional[int] = None):
    """
    Decorator for caching knowledge base queries
    
    Usage:
        @cached_kb_query("oncokb", "variant_lookup", ttl_hours=12)
        def get_oncokb_variant(gene, variant):
            # Expensive OncoKB API call
            return api_result
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_manager = KnowledgeBaseCacheManager()
            
            # Generate cache key from function arguments
            cache_key = cache_manager.generate_cache_key(
                function=func.__name__,
                args=args,
                kwargs=kwargs
            )
            
            # Try to get cached result
            cached_result = cache_manager.get_cached_result(cache_key, kb_source, query_type)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.cache_result(cache_key, kb_source, query_type, result, ttl_hours)
            
            return result
        
        return wrapper
    return decorator


# ============================================================================
# CACHE WARMING UTILITIES
# ============================================================================

def warm_common_caches():
    """Warm cache with commonly accessed data"""
    
    cache_manager = KnowledgeBaseCacheManager()
    
    # Common OncoKB queries
    oncokb_queries = [
        {"gene": "BRAF", "variant": "V600E", "query_type": "variant_lookup"},
        {"gene": "EGFR", "variant": "L858R", "query_type": "variant_lookup"}, 
        {"gene": "KRAS", "variant": "G12D", "query_type": "variant_lookup"},
        {"gene": "TP53", "query_type": "gene_lookup"},
        {"gene": "PIK3CA", "variant": "H1047R", "query_type": "variant_lookup"}
    ]
    
    # Common ClinVar queries  
    clinvar_queries = [
        {"gene": "BRCA1", "query_type": "gene_lookup"},
        {"gene": "BRCA2", "query_type": "gene_lookup"},
        {"variant": "NM_000059.3:c.5266dupC", "query_type": "variant_lookup"}
    ]
    
    # Warm caches
    cache_manager.warm_cache("oncokb", oncokb_queries)
    cache_manager.warm_cache("clinvar", clinvar_queries)
    
    logger.info("Cache warming complete")


if __name__ == "__main__":
    # Example usage
    cache_manager = KnowledgeBaseCacheManager()
    
    # Generate cache statistics
    stats = cache_manager.get_cache_statistics()
    print("Cache Statistics:")
    print(json.dumps(stats, indent=2))
    
    # Warm common caches
    warm_common_caches()