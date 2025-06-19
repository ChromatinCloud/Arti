#!/usr/bin/env python3
"""
Process ClinVar PLP (Pathogenic/Likely Pathogenic) file through OncoKB API
Based on the working clinvar_to_oncokb.py format
"""

import pandas as pd
import requests
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
import logging
from tqdm import tqdm
from datetime import datetime

# Configure logging
log_file = f"/tmp/clinvar_oncokb_PLP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# OncoKB API configuration
ONCOKB_API_URL = "https://www.oncokb.org/api/v1/annotate/mutations/byHGVSg"
ONCOKB_API_KEY = "e79469a4-ce6b-4ba9-83aa-df847cc4bba2"  # Using the working token
HEADERS = {
    "Authorization": f"Bearer {ONCOKB_API_KEY}",
    "accept": "application/json",
    "Content-Type": "application/json"
}

# Batch size for API calls - smaller for pathogenic variants
BATCH_SIZE = 500
RATE_LIMIT_DELAY = 0.5  # seconds between batches

# Track warnings to avoid spam
logged_warnings = set()

def create_hgvsg(row) -> Optional[str]:
    """
    Create HGVS genomic notation from ClinVar row
    Based on variant type (column 2)
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
            # SNV: chr:g.posref>alt
            return f"{chrom}:g.{start}{ref}>{alt}"
            
        elif variant_type == 'Deletion':
            # Deletion: chr:g.start_stopdel
            if start == stop:
                return f"{chrom}:g.{start}del"
            else:
                return f"{chrom}:g.{start}_{stop}del"
                
        elif variant_type == 'Duplication':
            # Duplication: chr:g.start_stopdup
            if start == stop:
                return f"{chrom}:g.{start}dup"
            else:
                return f"{chrom}:g.{start}_{stop}dup"
                
        elif variant_type == 'Insertion':
            # Insertion: chr:g.pos_pos+1ins[seq]
            return f"{chrom}:g.{start}_{start+1}ins{alt}"
            
        elif variant_type == 'Indel':
            # Complex indel: chr:g.start_stopdelins[alt]
            if len(ref) == 1 and len(alt) > 1:
                # Simple insertion
                return f"{chrom}:g.{start}_{start+1}ins{alt[1:]}"
            elif len(ref) > 1 and len(alt) == 1:
                # Simple deletion
                return f"{chrom}:g.{start+1}_{stop}del"
            else:
                # Complex indel
                return f"{chrom}:g.{start}_{stop}delins{alt}"
                
        elif variant_type == 'Microsatellite':
            # Microsatellites are repeat expansions/contractions
            # Treat as indels for HGVS notation
            if len(ref) > len(alt):
                # Contraction - deletion
                return f"{chrom}:g.{start}_{stop}del"
            elif len(ref) < len(alt):
                # Expansion - insertion
                return f"{chrom}:g.{start}_{stop}ins{alt[len(ref):]}"
            else:
                # Same length - substitution
                return f"{chrom}:g.{start}_{stop}delins{alt}"
                
        elif variant_type == 'Inversion':
            # Inversions: chr:g.start_stopinv
            return f"{chrom}:g.{start}_{stop}inv"
                
        else:
            # Unknown variant type - log first time only
            if variant_type not in logged_warnings:
                logger.warning(f"Unknown variant type: {variant_type}")
                logged_warnings.add(variant_type)
            return None
            
    except Exception as e:
        logger.error(f"Error creating HGVS: {e} for row: {row}")
        return None

def query_oncokb_batch(variants: List[Dict[str, str]], max_retries: int = 3) -> List[Dict]:
    """
    Query OncoKB API with a batch of variants with retry logic
    """
    for attempt in range(max_retries):
        try:
            response = requests.post(
                ONCOKB_API_URL,
                headers=HEADERS,
                json=variants,
                timeout=60  # Increased timeout for larger batches
            )
            
            if response.status_code == 200:
                results = response.json()
                logger.info(f"Successfully queried {len(variants)} variants, got {len(results)} responses")
                return results
            elif response.status_code == 429:  # Rate limit
                wait_time = (attempt + 1) * 5  # Exponential backoff
                logger.warning(f"Rate limited, waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"OncoKB API error: {response.status_code} - {response.text[:200]}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return []
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1}, retrying...")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return []
        except Exception as e:
            logger.error(f"Error querying OncoKB: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return []
    
    return []

def process_clinvar_file(input_file: Path, output_file: Path):
    """
    Process a single ClinVar file and create corresponding OncoKB file
    """
    logger.info(f"Processing {input_file.name}...")
    
    # Read ClinVar file
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
    total_batches = (len(df_valid) + BATCH_SIZE - 1) // BATCH_SIZE
    
    with tqdm(total=total_batches, desc=f"Querying OncoKB for {input_file.name}") as pbar:
        for i in range(0, len(df_valid), BATCH_SIZE):
            batch_df = df_valid.iloc[i:i+BATCH_SIZE]
            
            # Prepare batch for API - THIS IS THE KEY FORMAT
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
    """
    Process PLP.tsv file
    """
    logger.info("Starting OncoKB processor for Pathogenic/Likely Pathogenic (PLP) variants")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Using batch size: {BATCH_SIZE}")
    logger.info("=" * 50)
    
    # Paths
    clinvar_file = Path(".refs/clinical_evidence/clinvar/clinvar_by_significance/PLP.tsv")
    output_file = Path(".refs/clinical_evidence/oncokb/oncokb_by_significance/PLP.tsv")
    
    # Create output directory if needed
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    if not clinvar_file.exists():
        logger.error(f"File not found: {clinvar_file}")
        return 1
    
    # Check if already processed
    if output_file.exists():
        logger.info(f"Output file already exists: {output_file}")
        logger.info("Delete it to reprocess")
        return 0
    
    logger.info(f"Input file: {clinvar_file}")
    logger.info(f"File size: {clinvar_file.stat().st_size / (1024**2):.1f} MB")
    
    # Process the file
    process_clinvar_file(clinvar_file, output_file)
    
    logger.info(f"Completed processing {clinvar_file.name}")
    return 0

if __name__ == "__main__":
    main()