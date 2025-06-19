#!/usr/bin/env python3
"""
Test access to gnomAD v4.1 public data
"""

import subprocess
import sys

# Test positions that are likely to have data
test_queries = [
    ("1", 10000, 20000),    # Early chr1
    ("7", 140000000, 141000000),  # BRAF region
    ("17", 7600000, 7700000),     # TP53 region
]

print("Testing gnomAD v4.1 access...\n")

for chrom, start, end in test_queries:
    url = f"https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/genomes/gnomad.genomes.v4.1.sites.chr{chrom}.vcf.bgz"
    region = f"{chrom}:{start}-{end}"
    
    print(f"Querying {region}...")
    
    cmd = ["tabix", url, region]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            variant_count = len([l for l in lines if l])
            print(f"✅ Success! Found {variant_count} variants")
            
            if variant_count > 0:
                # Show first variant
                first_var = lines[0].split('\t')
                if len(first_var) >= 8:
                    print(f"   Example: {first_var[0]}:{first_var[1]} {first_var[3]}>{first_var[4]}")
                    # Try to extract AF from INFO field
                    info = first_var[7]
                    for field in info.split(';'):
                        if field.startswith('AF='):
                            print(f"   AF: {field}")
                            break
        else:
            print(f"❌ Failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout - URL may be inaccessible")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print()

print("\nTesting specific variant lookup...")
# Test looking up the exact variants from our VCF
test_variants = [
    ("3", 178952085),
    ("7", 140753336),
    ("12", 25245350),
    ("17", 7674220)
]

for chrom, pos in test_variants:
    url = f"https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/genomes/gnomad.genomes.v4.1.sites.chr{chrom}.vcf.bgz"
    region = f"{chrom}:{pos}-{pos}"
    
    cmd = ["tabix", url, region]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and result.stdout.strip():
            print(f"✅ Found variant at {chrom}:{pos}")
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split('\t')
                if len(parts) >= 5 and parts[1] == str(pos):
                    print(f"   {parts[3]}>{parts[4]}")
        else:
            print(f"❌ No data for {chrom}:{pos}")
            
    except Exception as e:
        print(f"❌ Error querying {chrom}:{pos}: {e}")