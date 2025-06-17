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
    
    # Paths
    test_vcf = Path("example_input/proper_test.vcf")
    output_json = Path("out/test_vep_dbnsfp.json")
    refs_dir = Path(".refs")
    
    # VEP command with dbNSFP using Docker
    vep_cmd = [
        "docker", "run", "--rm",
        "-v", f"{Path.cwd()}:/data",
        "-v", f"{Path.cwd()}/.refs:/opt/vep/.vep",
        "ensemblorg/ensembl-vep:release_114.0",
        "vep",
        "--format", "vcf",
        "--json",
        "--cache",
        "--dir_cache", "/opt/vep/.vep/functional_predictions/vep_cache",
        "--dir_plugins", "/opt/vep/.vep/functional_predictions/vep_plugins",
        "--plugin", f"dbNSFP,/opt/vep/.vep/variant/vcf/dbnsfp/dbnsfp.vcf.gz,SIFT_score,Polyphen2_HDIV_score,CADD_phred,REVEL_score,MetaSVM_score",
        "--fasta", "/opt/vep/.vep/misc/fasta/assembly/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz",
        "--assembly", "GRCh38",
        "--use_given_ref",
        "--force_overwrite",
        "--offline",
        "--input_file", f"/data/{test_vcf}",
        "--output_file", f"/data/{output_json}",
        "--no_stats"
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
                data = json.load(f)
                
            # Look for dbNSFP annotations
            found_scores = False
            for variant in data:
                if "transcript_consequences" in variant:
                    for tc in variant["transcript_consequences"]:
                        if any(key in tc for key in ["sift_score", "polyphen_score", "cadd_phred", "revel_score"]):
                            found_scores = True
                            print(f"\n✅ Found dbNSFP scores for {variant['id']}:")
                            for key in ["sift_score", "polyphen_score", "cadd_phred", "revel_score"]:
                                if key in tc:
                                    print(f"  - {key}: {tc[key]}")
                            break
                    if found_scores:
                        break
            
            if not found_scores:
                print("\n⚠️ No dbNSFP scores found in output")
                print("This may indicate the plugin didn't load properly")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ VEP failed with exit code {e.returncode}")
        print("STDERR:", e.stderr)
        print("STDOUT:", e.stdout)
        return False
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = test_vep_with_dbnsfp()
    sys.exit(0 if success else 1)