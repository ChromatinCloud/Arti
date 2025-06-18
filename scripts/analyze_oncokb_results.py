#!/usr/bin/env python3
"""
Post-process OncoKB results to:
1. Log variants with no OncoKB data
2. Convert JSON results to tabular format for variants with data
"""

import pandas as pd
import json
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_oncokb_json(json_str: str) -> List[Dict[str, Any]]:
    """
    Parse OncoKB JSON response and extract relevant fields
    """
    if not json_str or json_str == 'null' or pd.isna(json_str):
        return []
    
    try:
        data = json.loads(json_str)
        
        # Handle empty response
        if not data:
            return []
            
        # Check if this is a meaningful OncoKB annotation
        # Skip if gene doesn't exist or oncogenic is Unknown
        if isinstance(data, dict):
            if not data.get('geneExist', False) or data.get('oncogenic') == 'Unknown':
                return []
            
        # Extract key fields from OncoKB response
        results = []
        
        # OncoKB can return multiple annotations for different alterations
        if isinstance(data, dict):
            data = [data]
            
        for item in data:
            if not isinstance(item, dict):
                continue
                
            # Extract treatment information
            treatments = []
            if 'treatments' in item:
                for treatment in item['treatments']:
                    treatments.append({
                        'level': treatment.get('level', ''),
                        'drugs': ', '.join([d.get('drugName', '') for d in treatment.get('drugs', [])]),
                        'cancerType': treatment.get('cancerType', ''),
                        'fdaApproved': treatment.get('fdaApproved', False)
                    })
            
            # Create record for each treatment or one record if no treatments
            if treatments:
                for treatment in treatments:
                    result = {
                        'gene': item.get('gene', {}).get('hugoSymbol', ''),
                        'alteration': item.get('alteration', ''),
                        'alterationType': item.get('alterationType', ''),
                        'consequence': item.get('consequence', ''),
                        'proteinStart': item.get('proteinStart', ''),
                        'proteinEnd': item.get('proteinEnd', ''),
                        'oncogenic': item.get('oncogenic', ''),
                        'mutationEffect': item.get('mutationEffect', {}).get('knownEffect', ''),
                        'highestSensitiveLevel': item.get('highestSensitiveLevel', ''),
                        'highestResistanceLevel': item.get('highestResistanceLevel', ''),
                        'treatmentLevel': treatment['level'],
                        'treatmentDrugs': treatment['drugs'],
                        'treatmentCancerType': treatment['cancerType'],
                        'treatmentFdaApproved': treatment['fdaApproved']
                    }
                    results.append(result)
            else:
                # No treatments, but still has annotation
                result = {
                    'gene': item.get('gene', {}).get('hugoSymbol', ''),
                    'alteration': item.get('alteration', ''),
                    'alterationType': item.get('alterationType', ''),
                    'consequence': item.get('consequence', ''),
                    'proteinStart': item.get('proteinStart', ''),
                    'proteinEnd': item.get('proteinEnd', ''),
                    'oncogenic': item.get('oncogenic', ''),
                    'mutationEffect': item.get('mutationEffect', {}).get('knownEffect', ''),
                    'highestSensitiveLevel': item.get('highestSensitiveLevel', ''),
                    'highestResistanceLevel': item.get('highestResistanceLevel', ''),
                    'treatmentLevel': '',
                    'treatmentDrugs': '',
                    'treatmentCancerType': '',
                    'treatmentFdaApproved': ''
                }
                if any(result.values()):  # Only add if there's some data
                    results.append(result)
        
        return results
        
    except Exception as e:
        logger.error(f"Error parsing JSON: {e}")
        return []

def process_oncokb_file(input_file: Path, no_data_log: Path, tabular_output: Path):
    """
    Process a single OncoKB results file
    """
    logger.info(f"Processing {input_file.name}...")
    
    # Read the file
    try:
        df = pd.read_csv(input_file, sep='\t', low_memory=False)
        logger.info(f"Loaded {len(df)} variants from {input_file.name}")
    except Exception as e:
        logger.error(f"Error reading {input_file}: {e}")
        return
    
    # Separate variants with and without OncoKB data
    variants_with_data = []
    variants_without_data = []
    
    for _, row in df.iterrows():
        oncokb_data = row.get('oncokb_data', '')
        parsed_data = parse_oncokb_json(oncokb_data)
        
        if parsed_data:
            # Add parsed data to results
            for data_item in parsed_data:
                combined_row = {
                    # Original ClinVar data
                    'clinvar_allele_id': row.get('AlleleID', ''),
                    'gene_symbol': row.get('GeneSymbol', ''),
                    'hgvsg': row.get('hgvsg', ''),
                    'clinical_significance': row.get('ClinicalSignificance', ''),
                    'variant_type': row.get('Type', ''),
                    # OncoKB data
                    **data_item
                }
                variants_with_data.append(combined_row)
        else:
            # No OncoKB data - log it
            variants_without_data.append({
                'hgvsg': row.get('hgvsg', ''),
                'gene': row.get('GeneSymbol', ''),
                'type': row.get('Type', ''),
                'significance': row.get('ClinicalSignificance', '')
            })
    
    # Write variants without data to log
    if variants_without_data:
        with open(no_data_log, 'a') as f:
            f.write(f"\n\n=== {input_file.name} - Variants without OncoKB data ===\n")
            f.write(f"Total: {len(variants_without_data)} variants\n\n")
            
            for variant in variants_without_data[:100]:  # Log first 100 as example
                f.write(f"{variant['hgvsg']} | {variant['gene']} | {variant['type']}\n")
                
            if len(variants_without_data) > 100:
                f.write(f"\n... and {len(variants_without_data) - 100} more variants\n")
    
    # Save tabular data
    if variants_with_data:
        result_df = pd.DataFrame(variants_with_data)
        
        # Append to existing file or create new
        if tabular_output.exists():
            existing_df = pd.read_csv(tabular_output, sep='\t')
            result_df = pd.concat([existing_df, result_df], ignore_index=True)
            
        result_df.to_csv(tabular_output, sep='\t', index=False)
        logger.info(f"Added {len(variants_with_data)} OncoKB annotations to tabular output")
    
    logger.info(f"Summary for {input_file.name}:")
    logger.info(f"  - Variants with OncoKB data: {len(set(row['hgvsg'] for row in variants_with_data))}")
    logger.info(f"  - Variants without OncoKB data: {len(variants_without_data)}")

def main():
    """
    Process all OncoKB result files
    """
    oncokb_dir = Path("/Users/lauferva/Desktop/Arti/.refs/clinical_evidence/oncokb/oncokb_by_significance/")
    output_dir = Path("/Users/lauferva/Desktop/Arti/out/oncokb_analysis/")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Output files
    no_data_log = output_dir / f"variants_without_oncokb_data_{datetime.now().strftime('%Y%m%d')}.log"
    tabular_output = output_dir / f"oncokb_annotations_tabular_{datetime.now().strftime('%Y%m%d')}.tsv"
    
    # Initialize log file
    with open(no_data_log, 'w') as f:
        f.write(f"OncoKB Analysis Log - {datetime.now()}\n")
        f.write("="*80 + "\n")
        f.write("Variants without OncoKB annotations\n")
        f.write("Format: HGVSg | Gene | Type\n")
    
    # Process each OncoKB file
    for oncokb_file in sorted(oncokb_dir.glob("*.tsv")):
        process_oncokb_file(oncokb_file, no_data_log, tabular_output)
    
    # Final summary
    if tabular_output.exists():
        final_df = pd.read_csv(tabular_output, sep='\t')
        logger.info(f"\nFinal summary:")
        logger.info(f"Total OncoKB annotations: {len(final_df)}")
        logger.info(f"Unique variants with annotations: {final_df['hgvsg'].nunique()}")
        logger.info(f"Genes covered: {final_df['gene'].nunique()}")
        
        # Oncogenic distribution
        if 'oncogenic' in final_df.columns:
            logger.info("\nOncogenic classifications:")
            for onco, count in final_df['oncogenic'].value_counts().items():
                logger.info(f"  {onco}: {count}")

if __name__ == "__main__":
    main()