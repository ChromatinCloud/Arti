#!/usr/bin/env python3
"""
Process ClinVar Conflicting (C) variants through OncoKB API with proper token
"""

import pandas as pd
import requests
import json
import time
from pathlib import Path
from datetime import datetime
import logging
from typing import List, Dict, Any, Optional
from tqdm import tqdm
import os

# Set up logging
log_file = f"/tmp/clinvar_oncokb_C_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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

# Read token from secrets file
token_file = Path(".refs/clinical_evidence/oncokb/secrets2")
if token_file.exists():
    with open(token_file, 'r') as f:
        ONCOKB_API_TOKEN = f.read().strip()
    logger.info("Successfully loaded OncoKB API token from secrets file")
else:
    logger.error("OncoKB API token file not found!")
    ONCOKB_API_TOKEN = "demo"

HEADERS = {
    "Authorization": f"Bearer {ONCOKB_API_TOKEN}",
    "Content-Type": "application/json"
}

def query_oncokb_batch(hgvs_list: List[str], max_retries: int = 3) -> Optional[List[Dict[str, Any]]]:
    """Query OncoKB API with a batch of HGVS notations"""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                ONCOKB_API_URL,
                headers=HEADERS,
                json=hgvs_list,
                timeout=300
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"OncoKB API error: {response.status_code} - {response.text}")
                if response.status_code == 429:  # Rate limit
                    time.sleep(60 * (attempt + 1))
                elif response.status_code >= 500:  # Server error
                    time.sleep(30 * (attempt + 1))
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Request failed (attempt {attempt + 1}): {e}")
            time.sleep(10 * (attempt + 1))
    
    return None

def process_file(file_path: str, batch_size: int = 2000):
    """Process a single ClinVar TSV file"""
    logger.info(f"Processing {file_path}...")
    
    # Load the TSV file
    df = pd.read_csv(file_path, sep='\t', low_memory=False)
    logger.info(f"Loaded {len(df)} variants from {Path(file_path).name}")
    
    # Filter for GRCh38 variants only
    if 'Assembly' in df.columns:
        df_grch38 = df[df['Assembly'] == 'GRCh38'].copy()
        logger.info(f"Filtered to {len(df_grch38)} GRCh38 variants")
    else:
        df_grch38 = df
        logger.warning("No Assembly column found, processing all variants")
    
    # Create HGVS notations
    hgvs_notations = []
    for _, row in df_grch38.iterrows():
        # Skip variants without proper chromosome info
        if pd.isna(row.get('Chromosome')) or pd.isna(row.get('Start')):
            continue
            
        # Format: chr:start_ref>alt
        chrom = str(row['Chromosome'])
        if not chrom.startswith('chr'):
            chrom = f"chr{chrom}"
        
        # Determine variant type and format accordingly
        if row.get('Type') == 'single nucleotide variant':
            hgvs = f"{chrom}:g.{row['Start']}{row.get('ReferenceAlleleVCF', 'N')}>{row.get('AlternateAlleleVCF', 'N')}"
        elif row.get('Type') == 'Deletion':
            if pd.notna(row.get('Stop')):
                if row['Start'] == row['Stop']:
                    hgvs = f"{chrom}:g.{row['Start']}del"
                else:
                    hgvs = f"{chrom}:g.{row['Start']}_{row['Stop']}del"
            else:
                hgvs = f"{chrom}:g.{row['Start']}del"
        elif row.get('Type') == 'Insertion':
            hgvs = f"{chrom}:g.{row['Start']}_{int(row['Start'])+1}ins{row.get('AlternateAlleleVCF', '')}"
        else:
            # Skip complex variants for now
            continue
            
        hgvs_notations.append(hgvs)
    
    logger.info(f"Created HGVS for {len(hgvs_notations)} variants")
    
    # Process in batches
    results = []
    output_file = f"{Path(file_path).stem}_oncokb.json"
    
    # Process existing results if any
    if Path(output_file).exists():
        with open(output_file, 'r') as f:
            results = json.load(f)
        logger.info(f"Loaded {len(results)} existing results")
    
    # Determine starting point
    processed_count = len(results)
    remaining_hgvs = hgvs_notations[processed_count:]
    
    # Query OncoKB in batches
    with tqdm(total=len(remaining_hgvs), initial=processed_count, desc=f"Querying OncoKB for {Path(file_path).stem}") as pbar:
        for i in range(0, len(remaining_hgvs), batch_size):
            batch = remaining_hgvs[i:i+batch_size]
            
            oncokb_results = query_oncokb_batch(batch)
            
            if oncokb_results:
                results.extend(oncokb_results)
                logger.info(f"Successfully queried {len(batch)} variants, got {len(oncokb_results)} responses")
                
                # Save progress
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                
                pbar.update(len(batch))
            else:
                logger.error(f"Failed to process batch {i//batch_size + 1}")
                # Continue with next batch
                pbar.update(len(batch))
            
            # Rate limiting
            time.sleep(1)
    
    logger.info(f"Completed processing {Path(file_path).name}")
    logger.info(f"Total results: {len(results)}")

def main():
    """Process C.tsv file"""
    logger.info("Starting OncoKB processor for Conflicting (C) variants")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 50)
    
    # Path to C.tsv
    c_file = Path(".refs/clinical_evidence/clinvar/clinvar_by_significance/C.tsv")
    
    if not c_file.exists():
        logger.error(f"File not found: {c_file}")
        return 1
    
    # Use batch size of 2000 for non-pathogenic variants
    batch_size = 2000
    
    logger.info(f"Processing {c_file.name} with batch size {batch_size}")
    logger.info(f"File size: {c_file.stat().st_size / (1024**2):.1f} MB")
    
    # Process the file
    process_file(str(c_file), batch_size=batch_size)
    
    logger.info(f"Completed processing {c_file.name}")
    return 0

if __name__ == "__main__":
    main()