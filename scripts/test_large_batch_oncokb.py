#!/usr/bin/env python3
"""
Test OncoKB API with 1000-variant batches
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from clinvar_to_oncokb import process_clinvar_file
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)

def main():
    # Create a test file with 2500 variants to test multiple 1000-variant batches
    print("Creating test file with 2500 variants...")
    
    plp_file = Path("/Users/lauferva/Desktop/Arti/.refs/clinical_evidence/clinvar/clinvar_by_significance/PLP.tsv")
    test_file = Path("/tmp/PLP_batch_test.tsv")
    output_file = Path("/tmp/PLP_batch_test_oncokb.tsv")
    
    # Read header + 2500 variants
    with open(plp_file, 'r') as f_in, open(test_file, 'w') as f_out:
        for i, line in enumerate(f_in):
            if i <= 2500:  # header + 2500 variants
                f_out.write(line)
            else:
                break
    
    print(f"Test file created: {test_file}")
    
    # Process with 1000-variant batches
    print("\nProcessing with 1000-variant batches...")
    process_clinvar_file(test_file, output_file)
    
    # Check results
    if output_file.exists():
        df = pd.read_csv(output_file, sep='\t')
        print(f"\nResults:")
        print(f"  Total variants processed: {len(df)}")
        
        # Count variants with OncoKB data
        with_data = 0
        for _, row in df.iterrows():
            if row.get('oncokb_data') and row['oncokb_data'] != 'null':
                import json
                try:
                    data = json.loads(row['oncokb_data'])
                    if data.get('geneExist') or data.get('oncogenic') != 'Unknown':
                        with_data += 1
                except:
                    pass
        
        print(f"  Variants with OncoKB annotations: {with_data}")
        print(f"  Success rate: {(with_data/len(df))*100:.1f}%")

if __name__ == "__main__":
    main()