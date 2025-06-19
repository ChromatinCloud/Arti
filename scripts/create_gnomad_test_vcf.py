#!/usr/bin/env python3
"""
Create a test VCF with variants that are known to exist in gnomAD v4.1
We'll find some common variants first, then create a VCF
"""

import subprocess
from pathlib import Path

print("Finding common variants in gnomAD v4.1...")

# Let's look for variants in well-studied cancer genes
test_regions = [
    ("7", "140753000-140754000", "BRAF region"),
    ("17", "7571000-7572000", "TP53 region"),
    ("12", "25358000-25359000", "KRAS region")
]

found_variants = []

for chrom, region, desc in test_regions:
    print(f"\nSearching {desc} ({chrom}:{region})...")
    
    url = f"https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/genomes/gnomad.genomes.v4.1.sites.chr{chrom}.vcf.bgz"
    
    cmd = [
        "bcftools", "view", "-H",
        "-r", f"{chrom}:{region}",
        url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split('\n')
            print(f"Found {len(lines)} variants")
            
            # Take first few variants with reasonable AF
            for line in lines[:3]:
                parts = line.split('\t')
                if len(parts) >= 8:
                    var_chrom = parts[0]
                    var_pos = parts[1]
                    var_ref = parts[3]
                    var_alt = parts[4]
                    info = parts[7]
                    
                    # Extract AF
                    af = None
                    for field in info.split(';'):
                        if field.startswith('AF='):
                            af = float(field.split('=')[1])
                            break
                    
                    if af and af > 0.001:  # Common enough variant
                        found_variants.append({
                            'chrom': var_chrom,
                            'pos': var_pos,
                            'ref': var_ref,
                            'alt': var_alt,
                            'af': af
                        })
                        print(f"  Selected: {var_chrom}:{var_pos} {var_ref}>{var_alt} (AF={af:.4f})")
    
    except Exception as e:
        print(f"Error: {e}")

if found_variants:
    # Create test VCF
    vcf_content = """##fileformat=VCFv4.2
##INFO=<ID=TEST,Number=1,Type=String,Description="Test variant from gnomAD">
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
"""
    
    for var in found_variants:
        vcf_content += f"{var['chrom']}\t{var['pos']}\t.\t{var['ref']}\t{var['alt']}\t.\t.\tTEST=gnomAD_AF_{var['af']:.4f}\n"
    
    test_vcf = Path("example_input/gnomad_test.vcf")
    test_vcf.write_text(vcf_content)
    
    print(f"\n✅ Created test VCF: {test_vcf}")
    print(f"Contains {len(found_variants)} variants known to exist in gnomAD v4.1")
    
    # Now run the extraction
    print("\n" + "="*60)
    print("Running gnomAD v4.1 extraction on test variants...")
    print("="*60 + "\n")
    
    subprocess.run([
        "poetry", "run", "python",
        "scripts/gnomad_v4_bcftools.py",
        str(test_vcf),
        "--output", "out/gnomad_v4_test_results.tsv"
    ])
    
else:
    print("\n❌ Could not find suitable test variants")