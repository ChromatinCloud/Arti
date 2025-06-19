#!/usr/bin/env python3
"""
Demo: Extract gnomAD v4.1 AFs for common variants
"""

import subprocess
import tempfile
from pathlib import Path

# Create a demo VCF with variants likely to be in gnomAD
# These are common SNPs from clinically relevant genes
demo_vcf_content = """##fileformat=VCFv4.2
##contig=<ID=1>
##contig=<ID=7>
##contig=<ID=17>
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
1	115256530	.	T	C	.	.	.
7	140453136	.	A	T	.	.	.
17	7579472	.	G	C	.	.	.
"""

# Write demo VCF
demo_vcf = Path("example_input/demo_gnomad.vcf")
demo_vcf.write_text(demo_vcf_content)

print("Created demo VCF with common variants")
print("\nQuerying gnomAD v4.1 for these variants...")

# Query each variant
for line in demo_vcf_content.split('\n'):
    if line and not line.startswith('#'):
        parts = line.split('\t')
        if len(parts) >= 5:
            chrom, pos, _, ref, alt = parts[:5]
            
            url = f"https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/vcf/genomes/gnomad.genomes.v4.1.sites.chr{chrom}.vcf.bgz"
            
            # Query exact position
            cmd = [
                "bcftools", "view", "-H",
                "-r", f"{chrom}:{pos}",
                url
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and result.stdout:
                    print(f"\n✅ Found data for {chrom}:{pos} {ref}>{alt}")
                    
                    # Parse the result
                    for var_line in result.stdout.strip().split('\n'):
                        if var_line:
                            var_parts = var_line.split('\t')
                            if len(var_parts) >= 8:
                                var_pos = var_parts[1]
                                var_ref = var_parts[3]
                                var_alt = var_parts[4]
                                info = var_parts[7]
                                
                                # Extract AF values
                                af_fields = {}
                                for field in info.split(';'):
                                    if '=' in field:
                                        key, value = field.split('=', 1)
                                        if key.startswith('AF'):
                                            af_fields[key] = value
                                
                                if var_pos == pos and var_ref == ref and var_alt == alt:
                                    print(f"   Exact match found!")
                                    for af_key, af_val in sorted(af_fields.items()):
                                        print(f"   {af_key}: {af_val}")
                else:
                    print(f"\n❌ No data for {chrom}:{pos} {ref}>{alt}")
                    
            except Exception as e:
                print(f"\n❌ Error querying {chrom}:{pos}: {e}")

print("\n\nNow running the full extraction script on demo VCF...")
subprocess.run([
    "poetry", "run", "python", 
    "scripts/gnomad_v4_working.py",
    "example_input/demo_gnomad.vcf",
    "--output", "out/demo_gnomad_v4.tsv",
    "--report"
])