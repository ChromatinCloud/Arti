#!/usr/bin/env python3
"""
Test version - Process small ClinVar file and query OncoKB API
"""

import pandas as pd
import requests
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
import logging
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# OncoKB API configuration
ONCOKB_API_URL = "https://www.oncokb.org/api/v1/annotate/mutations/byHGVSg"
ONCOKB_API_KEY = "e79469a4-ce6b-4ba9-83aa-df847cc4bba2"
HEADERS = {
    "Authorization": f"Bearer {ONCOKB_API_KEY}",
    "accept": "application/json",
    "Content-Type": "application/json"
}

# Smaller batch size for testing
BATCH_SIZE = 10
RATE_LIMIT_DELAY = 1  # More conservative for testing

def create_hgvsg(row) -> Optional[str]:
    """
    Create HGVS genomic notation from ClinVar row
    """
    try:
        chrom = str(row['Chromosome'])
        start = int(row['Start'])
        stop = int(row['Stop'])
        ref = str(row['ReferenceAlleleVCF'])
        alt = str(row['AlternateAlleleVCF'])
        variant_type = str(row['Type'])
        
        # Skip if missing required fields
        if pd.isna(start) or ref == 'na' or alt == 'na':
            return None
            
        # Create HGVS based on variant type
        if variant_type == 'single nucleotide variant':
            return f"{chrom}:g.{start}{ref}>{alt}"
        elif variant_type == 'Deletion':
            if start == stop:
                return f"{chrom}:g.{start}del"
            else:
                return f"{chrom}:g.{start}_{stop}del"
        elif variant_type == 'Duplication':
            if start == stop:
                return f"{chrom}:g.{start}dup"
            else:
                return f"{chrom}:g.{start}_{stop}dup"
        elif variant_type == 'Insertion':
            return f"{chrom}:g.{start}_{start+1}ins{alt}"
        elif variant_type == 'Indel':
            if len(ref) == 1 and len(alt) > 1:
                return f"{chrom}:g.{start}_{start+1}ins{alt[1:]}"
            elif len(ref) > 1 and len(alt) == 1:
                return f"{chrom}:g.{start+1}_{stop}del"
            else:
                return f"{chrom}:g.{start}_{stop}delins{alt}"
        else:
            logger.warning(f"Unknown variant type: {variant_type}")
            return None
            
    except Exception as e:
        logger.error(f"Error creating HGVS: {e}")
        return None

def query_oncokb_batch(variants: List[Dict[str, str]]) -> List[Dict]:
    """
    Query OncoKB API with a batch of variants
    """
    logger.info(f"Querying OncoKB with {len(variants)} variants...")
    
    try:
        response = requests.post(
            ONCOKB_API_URL,
            headers=HEADERS,
            json=variants,
            timeout=30
        )
        
        if response.status_code == 200:
            results = response.json()
            logger.info(f"Got {len(results)} responses from OncoKB")
            return results
        else:
            logger.error(f"OncoKB API error: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Error querying OncoKB: {e}")
        return []

def main():
    """
    Test with small ClinVar file
    """
    input_file = Path("/tmp/PLP_test.tsv")
    output_file = Path("/tmp/PLP_oncokb_test.tsv")
    
    logger.info(f"Processing test file: {input_file}")
    
    # Read test file
    df = pd.read_csv(input_file, sep='\t')
    logger.info(f"Loaded {len(df)} variants")
    
    # Filter for GRCh38
    df_grch38 = df[df['Assembly'] == 'GRCh38'].copy()
    logger.info(f"Filtered to {len(df_grch38)} GRCh38 variants")
    
    # Create HGVS
    df_grch38['hgvsg'] = df_grch38.apply(create_hgvsg, axis=1)
    df_valid = df_grch38.dropna(subset=['hgvsg']).copy()
    logger.info(f"Created HGVS for {len(df_valid)} variants")
    
    # Take only first 20 for quick test
    df_test = df_valid.head(20).copy()
    
    # Process in small batches
    results = []
    
    for i in range(0, len(df_test), BATCH_SIZE):
        batch_df = df_test.iloc[i:i+BATCH_SIZE]
        
        # Prepare batch
        batch_variants = [
            {
                "hgvsg": row['hgvsg'],
                "referenceGenome": "GRCh38"
            }
            for _, row in batch_df.iterrows()
        ]
        
        # Show what we're querying
        logger.info(f"Batch {i//BATCH_SIZE + 1} variants:")
        for v in batch_variants:
            logger.info(f"  {v['hgvsg']}")
        
        # Query OncoKB
        oncokb_results = query_oncokb_batch(batch_variants)
        
        # Combine results
        for idx, (_, row) in enumerate(batch_df.iterrows()):
            result_row = row.to_dict()
            
            if idx < len(oncokb_results):
                result_row['oncokb_data'] = json.dumps(oncokb_results[idx])
                
                # Log if we got meaningful data
                if oncokb_results[idx]:
                    logger.info(f"Got OncoKB data for: {row['hgvsg']} - {row['GeneSymbol']}")
            else:
                result_row['oncokb_data'] = None
                
            results.append(result_row)
        
        time.sleep(RATE_LIMIT_DELAY)
    
    # Save results
    results_df = pd.DataFrame(results)
    results_df.to_csv(output_file, sep='\t', index=False)
    logger.info(f"Saved {len(results_df)} results to {output_file}")
    
    # Show summary
    with_data = sum(1 for r in results if r.get('oncokb_data') and r['oncokb_data'] != 'null')
    logger.info(f"\nSummary:")
    logger.info(f"  Total variants processed: {len(results)}")
    logger.info(f"  Variants with OncoKB data: {with_data}")
    logger.info(f"  Variants without OncoKB data: {len(results) - with_data}")

if __name__ == "__main__":
    main()