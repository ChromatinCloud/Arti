#!/usr/bin/env python3
"""
Debug VEP dbNSFP plugin issues
"""

import subprocess
import sys
from pathlib import Path
import json

def debug_vep_dbnsfp():
    """Debug VEP dbNSFP plugin step by step"""
    
    repo_root = Path.cwd()
    refs_dir = repo_root / ".refs"
    cache_dir = refs_dir / "functional_predictions" / "vep_cache"
    plugins_dir = refs_dir / "functional_predictions" / "vep_plugins"
    
    # Test VCF
    test_vcf = Path("example_input/proper_test.vcf")
    input_dir = test_vcf.parent.absolute()
    output_dir = Path("out").absolute()
    output_dir.mkdir(exist_ok=True)
    
    print("Debugging VEP dbNSFP plugin...")
    print(f"dbNSFP VCF path: {refs_dir}/variant/vcf/dbnsfp/dbnsfp.vcf.gz")
    print(f"File exists: {(refs_dir / 'variant/vcf/dbnsfp/dbnsfp.vcf.gz').exists()}")
    print(f"Index exists: {(refs_dir / 'variant/vcf/dbnsfp/dbnsfp.vcf.gz.tbi').exists()}")
    
    # Step 1: Test VEP without plugins first
    print("\n1. Testing VEP without plugins...")
    basic_cmd = [
        "docker", "run", "--rm",
        "-v", f"{cache_dir}:/opt/vep/.vep:ro",
        "-v", f"{plugins_dir}:/opt/vep/plugins:ro",
        "-v", f"{refs_dir}:/.refs:ro",
        "-v", f"{input_dir}:/input:ro",
        "-v", f"{output_dir}:/output",
        "-w", "/input",
        "ensemblorg/ensembl-vep:release_114.0",
        "vep",
        "--input_file", f"/input/{test_vcf.name}",
        "--output_file", "/output/test_basic.json",
        "--format", "vcf",
        "--json",
        "--cache",
        "--offline",
        "--dir_cache", "/opt/vep/.vep",
        "--assembly", "GRCh38",
        "--force_overwrite",
        "--no_stats"
    ]
    
    try:
        result = subprocess.run(basic_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print("✅ Basic VEP works")
        else:
            print(f"❌ Basic VEP failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Basic VEP error: {e}")
        return False
    
    # Step 2: Test with simpler dbNSFP plugin call
    print("\n2. Testing VEP with dbNSFP plugin (simple)...")
    simple_plugin_cmd = [
        "docker", "run", "--rm",
        "-v", f"{cache_dir}:/opt/vep/.vep:ro",
        "-v", f"{plugins_dir}:/opt/vep/plugins:ro",
        "-v", f"{refs_dir}:/.refs:ro",
        "-v", f"{input_dir}:/input:ro",
        "-v", f"{output_dir}:/output",
        "-w", "/input",
        "ensemblorg/ensembl-vep:release_114.0",
        "vep",
        "--input_file", f"/input/{test_vcf.name}",
        "--output_file", "/output/test_simple_plugin.json",
        "--format", "vcf",
        "--json",
        "--cache",
        "--offline",
        "--dir_cache", "/opt/vep/.vep",
        "--dir_plugins", "/opt/vep/plugins",
        "--assembly", "GRCh38",
        "--force_overwrite",
        "--no_stats",
        "--plugin", "dbNSFP,/.refs/variant/vcf/dbnsfp/dbnsfp.vcf.gz"
    ]
    
    try:
        result = subprocess.run(simple_plugin_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print("✅ VEP with simple dbNSFP plugin works")
            
            # Check output
            output_file = output_dir / "test_simple_plugin.json"
            if output_file.exists():
                with open(output_file) as f:
                    lines = f.readlines()
                
                print(f"✅ Output file created with {len(lines)} variants")
                
                # Look for dbNSFP data in any form
                found_dbnsfp = False
                for line in lines:
                    if line.strip():
                        variant = json.loads(line)
                        # Check all possible locations for dbNSFP data
                        variant_str = json.dumps(variant)
                        if "dbnsfp" in variant_str.lower() or "sift" in variant_str.lower():
                            found_dbnsfp = True
                            print("✅ Found dbNSFP-related data!")
                            # Print first 200 chars to see structure
                            print(f"Data preview: {variant_str[:200]}...")
                            break
                
                if not found_dbnsfp:
                    print("⚠️ No dbNSFP data found in simple plugin test")
                    # Print structure of one variant to debug
                    if lines:
                        variant = json.loads(lines[0])
                        print("Variant structure:")
                        for key in variant.keys():
                            print(f"  - {key}")
                            if key == "transcript_consequences" and variant[key]:
                                print("    First transcript consequence keys:")
                                for tc_key in variant[key][0].keys():
                                    print(f"      - {tc_key}")
                
        else:
            print(f"❌ VEP with simple plugin failed")
            print(f"STDERR: {result.stderr[:500]}")
            print(f"STDOUT: {result.stdout[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Plugin test error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = debug_vep_dbnsfp()
    sys.exit(0 if success else 1)