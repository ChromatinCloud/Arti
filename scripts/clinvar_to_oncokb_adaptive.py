#!/usr/bin/env python3
"""
Process ClinVar files and query OncoKB API for each variant with adaptive batch sizes
Creates OncoKB annotation files for each ClinVar significance category
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

# Rate limiting
RATE_LIMIT_DELAY = 0.5  # seconds between batches

def get_batch_size(filename: str) -> int:
    """
    Determine batch size based on file type
    P/LP/PLP files get smaller batches due to higher complexity
    """
    filename_lower = filename.lower()
    if any(x in filename_lower for x in ['plp', 'lp.tsv', 'p.tsv']):
        return 500  # Smaller batches for pathogenic variants
    else:
        return 2000  # Standard batch size for others

def create_hgvsg(row) -> Optional[str]:
    """Create HGVS genomic notation from variant data"""
    try:
        chrom = str(row['Chromosome']).replace('chr', '')
        start = int(row['Start'])
        stop = int(row['Stop'])
        ref = str(row['ReferenceAllele']).upper()
        alt = str(row['AlternateAllele']).upper()
        variant_type = str(row['Type'])
        
        # Handle different variant types
        if variant_type == 'single nucleotide variant':
            return f"{chrom}:g.{start}{ref}>{alt}"
        elif variant_type == 'Deletion':
            if stop == start:
                return f"{chrom}:g.{start}del"
            else:
                return f"{chrom}:g.{start}_{stop}del"
        elif variant_type == 'Duplication':
            if stop == start:
                return f"{chrom}:g.{start}dup"
            else:
                return f"{chrom}:g.{start}_{stop}dup"
        elif variant_type == 'Insertion':
            return f"{chrom}:g.{start}_{stop}ins{alt}"
        elif variant_type == 'Indel':
            return f"{chrom}:g.{start}_{stop}delins{alt}"
        elif variant_type == 'Microsatellite':
            if len(ref) > len(alt):
                return f"{chrom}:g.{start}_{stop}del"
            elif len(ref) < len(alt):
                return f"{chrom}:g.{start}_{stop}ins{alt[len(ref):]}"
            else:
                return f"{chrom}:g.{start}_{stop}delins{alt}"
        elif variant_type == 'Inversion':
            return f"{chrom}:g.{start}_{stop}inv"
        else:
            logger.warning(f"Unknown variant type: {variant_type}")
            return None
            
    except Exception as e:
        logger.warning(f"Error creating HGVS for variant: {e}")
        return None

def query_oncokb_batch(variants: List[Dict]) -> List[Dict]:
    """Query OncoKB API with a batch of variants"""
    max_retries = 3
    base_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                ONCOKB_API_URL,
                headers=HEADERS,
                json=variants,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully queried {len(variants)} variants, got {len(result)} responses")
                return result
            else:
                error_msg = f"OncoKB API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                
                if response.status_code in [500, 502, 503, 504]:
                    # Server errors - retry with exponential backoff
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
                        continue
                
                # Client errors or final attempt - return empty results
                return [{}] * len(variants)
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                continue
            else:
                return [{}] * len(variants)
    
    return [{}] * len(variants)

def process_clinvar_file(input_file: Path, output_file: Path):
    """Process a single ClinVar file and create OncoKB annotations"""
    logger.info(f"Processing {input_file}...")
    
    # Determine batch size based on filename
    batch_size = get_batch_size(input_file.name)
    logger.info(f"Using batch size {batch_size} for {input_file.name}")
    
    # Read input file
    try:
        df = pd.read_csv(input_file, sep='\t', low_memory=False)
        logger.info(f"Loaded {len(df)} variants from {input_file.name}")
    except Exception as e:
        logger.error(f"Error reading {input_file}: {e}")
        return
    
    # Filter for GRCh38 variants only
    df_grch38 = df[df['Assembly'] == 'GRCh38'].copy()
    logger.info(f"Filtered to {len(df_grch38)} GRCh38 variants")
    
    # Create HGVS notation
    df_grch38['hgvsg'] = df_grch38.apply(create_hgvsg, axis=1)
    
    # Remove variants without valid HGVS
    df_valid = df_grch38.dropna(subset=['hgvsg']).copy()
    logger.info(f"Created HGVS for {len(df_valid)} variants")
    
    # Prepare results list
    results = []
    
    # Process in batches
    total_batches = (len(df_valid) + batch_size - 1) // batch_size
    
    with tqdm(total=total_batches, desc=f"Querying OncoKB for {input_file.name}") as pbar:
        for i in range(0, len(df_valid), batch_size):
            batch_df = df_valid.iloc[i:i+batch_size]
            
            # Prepare batch for API
            batch_variants = [
                {
                    "hgvsg": row['hgvsg'],
                    "referenceGenome": "GRCh38"
                }
                for _, row in batch_df.iterrows()
            ]
            
            # Query OncoKB
            oncokb_results = query_oncokb_batch(batch_variants)
            
            # Combine results with original data
            for idx, (_, row) in enumerate(batch_df.iterrows()):
                result_row = row.to_dict()
                
                if idx < len(oncokb_results):
                    result_row['oncokb_data'] = json.dumps(oncokb_results[idx])
                else:
                    result_row['oncokb_data'] = None
                    
                results.append(result_row)
            
            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)
            pbar.update(1)
    
    # Create output dataframe
    results_df = pd.DataFrame(results)
    
    # Save to file
    results_df.to_csv(output_file, sep='\t', index=False)
    logger.info(f"Saved {len(results_df)} results to {output_file}")

def main():
    """Main function for command line usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process ClinVar file with OncoKB API')
    parser.add_argument('input_file', help='Input ClinVar TSV file')
    parser.add_argument('output_file', help='Output file with OncoKB annotations')
    
    args = parser.parse_args()
    
    input_file = Path(args.input_file)
    output_file = Path(args.output_file)
    
    if not input_file.exists():
        logger.error(f"Input file does not exist: {input_file}")
        return
    
    process_clinvar_file(input_file, output_file)

if __name__ == "__main__":
    main()