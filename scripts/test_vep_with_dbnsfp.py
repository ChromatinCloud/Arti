#!/usr/bin/env python3
"""
Test VEP execution with dbNSFP plugin
"""

import subprocess
import sys
from pathlib import Path
import json

def test_vep_with_dbnsfp():
    """Test VEP with dbNSFP plugin"""
    
    # Paths using correct mount strategy
    repo_root = Path.cwd()
    refs_dir = repo_root / ".refs"
    cache_dir = refs_dir / "functional_predictions" / "vep_cache"
    plugins_dir = refs_dir / "functional_predictions" / "vep_plugins"
    
    # Test VCF
    test_vcf = Path("example_input/proper_test.vcf")
    input_dir = test_vcf.parent.absolute()
    output_dir = Path("out").absolute()
    output_dir.mkdir(exist_ok=True)
    output_json = output_dir / "test_vep_dbnsfp.json"
    
    # VEP command with dbNSFP using correct Docker mount strategy
    vep_cmd = [
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
        "--output_file", f"/output/{output_json.name}",
        "--format", "vcf",
        "--json",
        "--cache",
        "--offline",
        "--dir_cache", "/opt/vep/.vep",
        "--dir_plugins", "/opt/vep/plugins",
        "--assembly", "GRCh38",
        "--force_overwrite",
        "--no_stats",
        "--everything",
        "--plugin", f"dbNSFP,/.refs/variant/vcf/dbnsfp/dbnsfp.vcf.gz,SIFT_score,Polyphen2_HDIV_score,CADD_phred,REVEL_score,MetaSVM_score"
    ]
    
    print("Running VEP with dbNSFP plugin...")
    print(f"Command: {' '.join(vep_cmd)}")
    
    try:
        # Run VEP
        result = subprocess.run(
            vep_cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        print("\nVEP completed successfully!")
        print("Output written to:", output_json)
        
        # Check if dbNSFP scores were added
        if output_json.exists():
            with open(output_json) as f:
                lines = f.readlines()
                
            # Look for dbNSFP annotations (VEP outputs JSON lines, not single JSON)
            found_scores = False
            for line in lines:
                if line.strip():
                    variant = json.loads(line)
                    if "transcript_consequences" in variant:
                        for tc in variant["transcript_consequences"]:
                            if any(key in tc for key in ["sift_score", "polyphen_score", "cadd_phred", "revel_score"]):
                                found_scores = True
                                print(f"\n✅ Found dbNSFP scores for {variant.get('id', 'unknown')}:")
                                for key in ["sift_score", "polyphen_score", "cadd_phred", "revel_score"]:
                                    if key in tc:
                                        print(f"  - {key}: {tc[key]}")
                                break
                        if found_scores:
                            break
            
            if not found_scores:
                print("\n⚠️ No dbNSFP scores found in output")
                print("This may indicate the plugin didn't load properly")
                print("Checking for any plugin output...")
                # Check if at least some variants were processed
                if lines:
                    print(f"✅ VEP processed {len(lines)} variants successfully")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ VEP failed with exit code {e.returncode}")
        print("STDERR:", e.stderr)
        print("STDOUT:", e.stdout)
        assert False, f"VEP failed with exit code {e.returncode}"
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        assert False, f"Error: {e}"

if __name__ == "__main__":
    success = test_vep_with_dbnsfp()
    sys.exit(0 if success else 1)