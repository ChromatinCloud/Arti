"""
API clients for external knowledge bases that provide web services.

This module handles real-time API calls to services like CIViC and OncoKB
when API keys are available or for public endpoints.
"""

import asyncio
import os
from typing import Dict, List, Optional, Any
import httpx
from pydantic import BaseModel


class APIError(Exception):
    """Base exception for API-related errors."""
    pass


class CivicAPIClient:
    """Client for CIViC API (https://civicdb.org/api/)."""
    
    def __init__(self):
        self.base_url = "https://civicdb.org/api"
        self.timeout = 30.0
    
    async def get_variant_evidence(self, gene: str, variant: str) -> List[Dict[str, Any]]:
        """
        Query CIViC API for evidence about a specific variant.
        
        Args:
            gene: Gene symbol (e.g., "TP53")
            variant: Variant description (e.g., "R175H")
            
        Returns:
            List of evidence items from CIViC
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Search for variants by gene and variant name
                url = f"{self.base_url}/variants"
                params = {
                    "gene": gene,
                    "name": variant,
                    "count": 50
                }
                
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                return data.get("records", [])
                
            except httpx.HTTPError as e:
                raise APIError(f"CIViC API error: {e}")
    
    async def get_gene_evidence(self, gene: str) -> List[Dict[str, Any]]:
        """Get all evidence for a gene from CIViC."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                url = f"{self.base_url}/genes/{gene}/variants"
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
                return data.get("records", [])
                
            except httpx.HTTPError as e:
                raise APIError(f"CIViC API error: {e}")


class OncoKBAPIClient:
    """Client for OncoKB API (https://www.oncokb.org/api/)."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ONCOKB_API_KEY")
        self.base_url = "https://www.oncokb.org/api/v1"
        self.timeout = 30.0
        
        if not self.api_key:
            raise APIError("OncoKB API key required. Set ONCOKB_API_KEY environment variable.")
    
    @property
    def headers(self) -> Dict[str, str]:
        """Request headers with API key."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def annotate_variants(self, variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Annotate multiple variants using OncoKB API.
        
        Args:
            variants: List of variant dicts with keys: gene, variant, tumor_type
            
        Returns:
            List of OncoKB annotation results
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                url = f"{self.base_url}/annotate/mutations/byProteinChange"
                
                # Format variants for OncoKB API
                oncokb_variants = []
                for v in variants:
                    oncokb_variants.append({
                        "gene": v.get("gene"),
                        "alteration": v.get("variant"),
                        "tumorType": v.get("tumor_type", ""),
                        "consequence": v.get("consequence", ""),
                        "proteinStart": v.get("protein_start"),
                        "proteinEnd": v.get("protein_end")
                    })
                
                response = await client.post(
                    url, 
                    json=oncokb_variants,
                    headers=self.headers
                )
                response.raise_for_status()
                
                return response.json()
                
            except httpx.HTTPError as e:
                raise APIError(f"OncoKB API error: {e}")
    
    async def get_cancer_genes(self) -> List[Dict[str, Any]]:
        """Get list of cancer genes from OncoKB."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                url = f"{self.base_url}/utils/allCuratedGenes"
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                return response.json()
                
            except httpx.HTTPError as e:
                raise APIError(f"OncoKB API error: {e}")


class APIManager:
    """Central manager for all API clients."""
    
    def __init__(self):
        self.civic = CivicAPIClient()
        self.oncokb = None  # Initialize only if API key available
        
        # Try to initialize OncoKB client
        try:
            self.oncokb = OncoKBAPIClient()
        except APIError:
            # OncoKB API key not available, will fall back to downloaded files
            pass
    
    async def get_civic_evidence(self, gene: str, variant: str) -> List[Dict[str, Any]]:
        """Get evidence from CIViC API."""
        return await self.civic.get_variant_evidence(gene, variant)
    
    async def get_oncokb_annotations(self, variants: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """Get annotations from OncoKB API if available."""
        if self.oncokb:
            return await self.oncokb.annotate_variants(variants)
        return None
    
    def has_oncokb_api(self) -> bool:
        """Check if OncoKB API is available."""
        return self.oncokb is not None


# Global instance
api_manager = APIManager()


async def query_apis_for_variant(gene: str, variant: str, tumor_type: str = "") -> Dict[str, Any]:
    """
    Query all available APIs for a single variant.
    
    Args:
        gene: Gene symbol
        variant: Variant description
        tumor_type: Cancer type (optional)
        
    Returns:
        Combined evidence from all APIs
    """
    evidence = {
        "civic": [],
        "oncokb": None,
        "api_errors": []
    }
    
    # Query CIViC
    try:
        evidence["civic"] = await api_manager.get_civic_evidence(gene, variant)
    except APIError as e:
        evidence["api_errors"].append(f"CIViC: {e}")
    
    # Query OncoKB if available
    if api_manager.has_oncokb_api():
        try:
            oncokb_result = await api_manager.get_oncokb_annotations([{
                "gene": gene,
                "variant": variant,
                "tumor_type": tumor_type
            }])
            evidence["oncokb"] = oncokb_result[0] if oncokb_result else None
        except APIError as e:
            evidence["api_errors"].append(f"OncoKB: {e}")
    
    return evidence