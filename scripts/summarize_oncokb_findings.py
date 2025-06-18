#!/usr/bin/env python3
"""
Summarize OncoKB findings from the PLP subset analysis
"""

import pandas as pd
from pathlib import Path

def main():
    # Read the annotations
    annotations_file = Path("/tmp/plp_oncokb_annotations.tsv")
    df = pd.read_csv(annotations_file, sep='\t')
    
    print("OncoKB Annotation Summary for Pathogenic/Likely Pathogenic ClinVar Variants")
    print("="*80)
    print(f"\nTotal annotations: {len(df)}")
    print(f"Unique variants: {df['hgvsg'].nunique()}")
    
    # Gene information - use ClinVar gene_symbol where OncoKB gene is missing
    df['gene_final'] = df['gene'].fillna(df['gene_symbol'])
    
    print(f"\nTop 20 genes with OncoKB annotations:")
    gene_counts = df['gene_final'].value_counts().head(20)
    for gene, count in gene_counts.items():
        print(f"  {gene}: {count} annotations")
    
    print("\nOncogenic Classifications:")
    for onco, count in df['oncogenic'].value_counts().items():
        print(f"  {onco}: {count}")
    
    # Treatment annotations
    df_treatment = df[df['treatmentLevel'].notna()]
    print(f"\nVariants with treatment annotations: {len(df_treatment)}")
    
    print("\nTreatment Levels:")
    for level, count in df_treatment['treatmentLevel'].value_counts().items():
        print(f"  {level}: {count}")
    
    print("\nFDA-Approved treatments:")
    fda_approved = df_treatment[df_treatment['treatmentFdaApproved'] == True]
    print(f"  Total: {len(fda_approved)} annotations")
    
    print("\nExample treatment annotations:")
    examples = df_treatment[['gene_symbol', 'hgvsg', 'oncogenic', 'treatmentLevel', 'treatmentDrugs', 'treatmentCancerType']].head(10)
    for idx, row in examples.iterrows():
        print(f"\n  Gene: {row['gene_symbol']}")
        print(f"  Variant: {row['hgvsg']}")
        print(f"  Oncogenic: {row['oncogenic']}")
        print(f"  Treatment: {row['treatmentDrugs']} (Level: {row['treatmentLevel']})")
        print(f"  Cancer Type: {row['treatmentCancerType']}")
    
    # Cancer types
    cancer_types = df_treatment['treatmentCancerType'].value_counts()
    print(f"\nTop cancer types with treatments:")
    for cancer, count in cancer_types.head(10).items():
        if pd.notna(cancer):
            print(f"  {cancer}: {count}")
    
    # Resistance annotations
    resistance = df[df['highestResistanceLevel'].notna()]
    print(f"\nVariants with resistance annotations: {len(resistance)}")
    
    # Save a focused summary
    summary_df = df[df['oncogenic'].isin(['Oncogenic', 'Likely Oncogenic'])][
        ['gene_symbol', 'hgvsg', 'oncogenic', 'treatmentLevel', 'treatmentDrugs', 'highestSensitiveLevel', 'highestResistanceLevel']
    ].drop_duplicates()
    
    summary_file = Path("/tmp/oncokb_clinvar_plp_summary.tsv")
    summary_df.to_csv(summary_file, sep='\t', index=False)
    print(f"\nSummary saved to: {summary_file}")

if __name__ == "__main__":
    main()