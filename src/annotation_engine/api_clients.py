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
import requests
import json


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

# gnomAD Client
# Verified gnomAD API URL: https://gnomad.broadinstitute.org/api (often redirects from /graphql)
# Sticking to /graphql as per documentation examples.
GNOMAD_API_URL = "https://gnomad.broadinstitute.org/graphql"

def get_gnomad_allele_frequency(variant_id: str, reference_genome: str, dataset_id: str = None) -> dict | None:
    """
    Fetches allele frequency information for a given variant from the gnomAD API.

    Args:
        variant_id (str): The variant ID in the format "chrom-pos-ref-alt" (e.g., "7-140753336-A-T").
        reference_genome (str): The reference genome build ("GRCh38" or "GRCh37").
        dataset_id (str, optional): The gnomAD dataset ID (e.g., "gnomad_r4", "gnomad_r3", "gnomad_r2_1").
                                     Defaults to "gnomad_r4" for GRCh38 and "gnomad_r2_1" for GRCh37.

    Returns:
        dict | None: A dictionary containing allele frequency information
                     (e.g., {"exome_af": 0.001, "exome_ac": 10, "exome_an": 10000,
                              "genome_af": 0.0005, "genome_ac": 5, "genome_an": 9000})
                     or None if the variant is not found, an error occurs, or no frequency data is available.
    """
    if reference_genome not in ["GRCh38", "GRCh37"]:
        # Consider logging this error instead of just printing, or raise ValueError
        print(f"Error: Invalid reference_genome '{reference_genome}'. Must be 'GRCh38' or 'GRCh37'.")
        return None

    if dataset_id is None:
        if reference_genome == "GRCh38":
            dataset_id = "gnomad_r4"
        elif reference_genome == "GRCh37":
            dataset_id = "gnomad_r2_1"

    # Basic validation for dataset compatibility (can be expanded)
    if reference_genome == "GRCh38" and dataset_id not in ["gnomad_r3", "gnomad_r4"]:
        if dataset_id == "gnomad_r2_1": # Common case of wanting GRCh37 data with GRCh38 coordinates (needs liftover, not handled here)
            print(f"Warning: {dataset_id} is a GRCh37 dataset. Results may be incorrect for GRCh38 variant {variant_id} without liftover.")
        # else:
            # print(f"Warning: Dataset {dataset_id} may not be standard for GRCh38.")
            pass # Allow to proceed
    elif reference_genome == "GRCh37" and dataset_id not in ["gnomad_r2_1", "exac"]: # exac is also GRCh37
        print(f"Warning: Dataset {dataset_id} may not be standard for GRCh37.")
        # Allow to proceed

    query_fields = """
        exome { af ac an }
        genome { af ac an }
    """

    # Construct the GraphQL query based on dataset specifics
    # gnomAD v3/v4 (GRCh38) use 'variant_id' and dataset names like 'gnomad_r3', 'gnomad_r4'
    if dataset_id in ["gnomad_r3", "gnomad_r4"]:
        query = f"""
        query GetVariantAlleleFrequency {{
          variant(variant_id: "{variant_id}", dataset: {dataset_id}) {{
            {query_fields}
          }}
        }}
        """
    # gnomAD v2 (GRCh37) uses 'variantId' and dataset name 'gnomad_r2_1'
    elif dataset_id == "gnomad_r2_1":
        query = f"""
        query GetVariantAlleleFrequency {{
          variant(variantId: "{variant_id}", dataset: {dataset_id}) {{ # Note: variantId
            {query_fields}
          }}
        }}
        """
    else:
        # Fallback for other/custom datasets: try with 'variant_id' and provided dataset_id
        # This is a guess and might require users to know the exact dataset name for the API.
        print(f"Warning: Using a generic query structure for dataset '{dataset_id}'. This might fail if the API expects a different format.")
        query = f"""
        query GetVariantAlleleFrequency {{
          variant(variant_id: "{variant_id}", dataset: {dataset_id}) {{
            {query_fields}
          }}
        }}
        """

    try:
        # Using a timeout is crucial for network requests.
        response = requests.post(GNOMAD_API_URL, json={'query': query}, timeout=15)
        response.raise_for_status()  # Raises HTTPError for 4XX/5XX responses
        data = response.json()

        if "errors" in data and data["errors"]:
            error_messages = [error.get("message", "Unknown GraphQL error") for error in data["errors"]]
            # Log or print more detailed errors if in debug mode or needed
            # print(f"GraphQL API errors for variant {variant_id}, dataset {dataset_id}: {error_messages}")
            # Check for specific error messages if needed, e.g., variant not found
            if any("variant not found" in msg.lower() for msg in error_messages):
                return None # Variant specifically not found
            return None # Other GraphQL error

        variant_data = data.get("data", {}).get("variant")

        if not variant_data:
            # This means the 'variant' key was null or missing in the response data,
            # which usually implies the variant wasn't found in the specified dataset.
            return None

        results = {}
        # Process exome data if present and not null
        if variant_data.get("exome") is not None:
            results["exome_af"] = variant_data["exome"].get("af")
            results["exome_ac"] = variant_data["exome"].get("ac")
            results["exome_an"] = variant_data["exome"].get("an")

        # Process genome data if present and not null
        if variant_data.get("genome") is not None:
            results["genome_af"] = variant_data["genome"].get("af")
            results["genome_ac"] = variant_data["genome"].get("ac")
            results["genome_an"] = variant_data["genome"].get("an")

        # If, after processing, no actual data points were extracted, return None.
        # This handles cases where 'exome' or 'genome' keys exist but are empty or lack af/ac/an.
        if not any(value is not None for value in results.values()):
            return None

        return results

    except requests.exceptions.HTTPError as e:
        # Handle HTTP errors (e.g., 500, 403)
        # print(f"HTTP error for variant {variant_id}, dataset {dataset_id}: {e}")
        return None
    except requests.exceptions.ConnectionError as e:
        # Handle errors like DNS failure, refused connection
        # print(f"Connection error for variant {variant_id}, dataset {dataset_id}: {e}")
        return None
    except requests.exceptions.Timeout as e:
        # Handle request timeout
        # print(f"Timeout error for variant {variant_id}, dataset {dataset_id}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        # Catch any other error raised by the requests library
        # print(f"Request error for variant {variant_id}, dataset {dataset_id}: {e}")
        return None
    except json.JSONDecodeError:
        # Handle cases where the response is not valid JSON
        # print(f"JSON parsing error for variant {variant_id}, dataset {dataset_id}. Response: {response.text[:200]}...")
        return None
    except Exception as e:
        # Catch any other unexpected errors during execution of the function
        # print(f"An unexpected error of type {type(e).__name__} occurred for {variant_id}, {dataset_id}: {e}")
        return None

# Example Usage (can be removed or kept for direct testing of this file)
if __name__ == '__main__':
    print("Running example queries for get_gnomad_allele_frequency (within api_clients.py)...")

    # Example 1: GRCh38 variant, gnomAD r4 (e.g., a known pathogenic variant in BRCA1)
    # Using a variant ID that is more likely to be present and have data.
    # Example: A variant in BRCA1. Coordinates for GRCh38.
    variant1_grch38 = "17-43045702-G-A"
    print(f"\nTesting GRCh38 (gnomAD r4) for {variant1_grch38}:")
    freq1 = get_gnomad_allele_frequency(variant1_grch38, "GRCh38", "gnomad_r4")
    if freq1:
        print(f"  Frequencies: {freq1}")
    else:
        print(f"  No data or error reported.")

    # Example 2: GRCh38 variant, gnomAD r3
    print(f"\nTesting GRCh38 (gnomAD r3) for {variant1_grch38}:")
    freq2 = get_gnomad_allele_frequency(variant1_grch38, "GRCh38", "gnomad_r3")
    if freq2:
        print(f"  Frequencies: {freq2}")
    else:
        print(f"  No data or error reported.")

    # Example 3: GRCh37 variant, gnomAD r2.1
    # Example: A common SNP in CFTR gene (GRCh37 coordinates)
    variant1_grch37 = "7-117199644-A-G"
    print(f"\nTesting GRCh37 (gnomAD r2.1) for {variant1_grch37}:")
    freq3 = get_gnomad_allele_frequency(variant1_grch37, "GRCh37", "gnomad_r2_1")
    if freq3:
        print(f"  Frequencies: {freq3}")
    else:
        print(f"  No data or error reported.")

    # Example 4: Variant likely not in gnomAD (or very rare)
    variant_rare_or_fake = "1-1000000-A-T" # A made-up variant
    print(f"\nTesting non-existent/rare variant {variant_rare_or_fake} (GRCh38, gnomAD r4 default):")
    freq4 = get_gnomad_allele_frequency(variant_rare_or_fake, "GRCh38")
    if freq4:
        print(f"  Frequencies: {freq4}")
    else:
        print(f"  No data or error reported (expected for rare/non-existent variant).")

    # Example 5: Using default dataset_id for GRCh38 (should be gnomad_r4)
    print(f"\nTesting GRCh38 (default dataset) for {variant1_grch38}:")
    freq5 = get_gnomad_allele_frequency(variant1_grch38, "GRCh38")
    if freq5:
        print(f"  Frequencies (default gnomad_r4): {freq5}")
    else:
        print(f"  No data or error reported.")

    # Example 6: Using default dataset_id for GRCh37 (should be gnomad_r2_1)
    print(f"\nTesting GRCh37 (default dataset) for {variant1_grch37}:")
    freq6 = get_gnomad_allele_frequency(variant1_grch37, "GRCh37")
    if freq6:
        print(f"  Frequencies (default gnomad_r2_1): {freq6}")
    else:
        print(f"  No data or error reported.")

    # Example 7: Invalid reference genome
    print(f"\nTesting invalid reference genome 'GRCh39':")
    freq7 = get_gnomad_allele_frequency(variant1_grch38, "GRCh39")
    if freq7 is None:
        print(f"  Correctly returned None for invalid reference genome.")
    else:
        print(f"  Test failed: Did not return None for invalid reference. Got: {freq7}")

    # Example 8: Invalid dataset_id but valid genome (should try generic query)
    print(f"\nTesting unsupported dataset 'gnomad_custom_v1' for GRCh38 (using generic query):")
    freq8 = get_gnomad_allele_frequency(variant1_grch38, "GRCh38", "gnomad_custom_v1")
    if freq8 is None:
        print(f"  No data or error reported (expected for unknown dataset).")
    else: # This might pass if gnomAD API defaults or handles unknown dataset names gracefully
        print(f"  Frequencies: {freq8}")
        print(f"  Note: This dataset was expected to fail or return no data. Check API behavior for '{variant1_grch38}' with dataset 'gnomad_custom_v1'.")

    print("\nExample queries for get_gnomad_allele_frequency finished.")