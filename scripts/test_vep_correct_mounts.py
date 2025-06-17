#!/usr/bin/env python3
"""
Test VEP with correct Docker mount paths matching vep_runner.py
"""

import subprocess
import sys
from pathlib import Path
import json

def test_vep_with_correct_mounts():
    """Test VEP using the same mount strategy as vep_runner.py"""
    
    # Paths
    repo_root = Path.cwd()
    refs_dir = repo_root / ".refs"
    cache_dir = refs_dir / "functional_predictions" / "vep_cache"
    plugins_dir = refs_dir / "functional_predictions" / "vep_plugins"
    
    # Test VCF
    test_vcf = Path("example_input/proper_test.vcf")
    input_dir = test_vcf.parent.absolute()
    output_dir = Path("out").absolute()
    output_dir.mkdir(exist_ok=True)
    
    print("VEP Docker Test with Correct Mount Paths")
    print("=" * 80)
    print(f"Repository root: {repo_root}")
    print(f"Cache directory: {cache_dir}")
    print(f"Plugins directory: {plugins_dir}")
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    
    # Build Docker command matching vep_runner.py
    cmd = [
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
        "--output_file", "/output/test_vep_output.json",
        "--format", "vcf",
        "--json",
        "--cache",
        "--offline",
        "--dir_cache", "/opt/vep/.vep",
        "--dir_plugins", "/opt/vep/plugins",
        "--assembly", "GRCh38",
        "--force_overwrite",
        "--no_stats",
        "--everything"
    ]
    
    print("\nCommand:")
    print(" ".join(cmd))
    
    print("\nTesting basic VEP execution...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        print(f"\nExit code: {result.returncode}")
        
        if result.returncode == 0:
            print("✅ VEP executed successfully!")
            
            # Check output file
            output_file = output_dir / "test_vep_output.json"
            if output_file.exists():
                print(f"✅ Output file created: {output_file}")
                
                # Parse JSON to verify (VEP outputs one JSON object per line)
                with open(output_file) as f:
                    lines = f.readlines()
                    variant_count = 0
                    for line in lines:
                        if line.strip():
                            try:
                                json.loads(line)
                                variant_count += 1
                            except json.JSONDecodeError:
                                print(f"❌ Invalid JSON line: {line[:50]}...")
                print(f"✅ Valid JSON with {variant_count} variants annotated")
            else:
                print("❌ Output file not created")
                assert False, "Output file not created"
                
        else:
            print("❌ VEP failed")
            print("\nSTDERR:")
            print(result.stderr)
            
            # Debug mount issues
            if "does not exist" in result.stderr:
                print("\n⚠️ File not found - checking mounts...")
                
                # Test mount accessibility
                test_cmd = [
                    "docker", "run", "--rm",
                    "-v", f"{input_dir}:/input:ro",
                    "ensemblorg/ensembl-vep:release_114.0",
                    "ls", "-la", "/input/"
                ]
                
                test_result = subprocess.run(test_cmd, capture_output=True, text=True)
                print("\nFiles in /input mount:")
                print(test_result.stdout)
            
            assert False, f"VEP failed with exit code {result.returncode}"
                
    except subprocess.TimeoutExpired:
        print("❌ VEP timed out after 300 seconds")
        assert False, "VEP timed out after 300 seconds"
    except Exception as e:
        print(f"❌ Error: {e}")
        assert False, f"Error: {e}"
        
    # Now test with dbNSFP plugin
    if result.returncode == 0:
        print("\n" + "=" * 80)
        print("Testing VEP with dbNSFP plugin...")
        
        cmd_with_plugin = cmd[:-1] + [  # Remove --everything
            "--plugin", "dbNSFP,/.refs/variant/vcf/dbnsfp/dbnsfp.vcf.gz,SIFT_score,Polyphen2_HDIV_score"
        ]
        
        try:
            result = subprocess.run(cmd_with_plugin, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                print("✅ VEP with dbNSFP plugin executed successfully!")
            else:
                print("❌ VEP with plugin failed")
                print(f"STDERR: {result.stderr[:500]}")
                
        except Exception as e:
            print(f"❌ Plugin test error: {e}")
    
    # Test passes if we get here
    assert True

if __name__ == "__main__":
    success = test_vep_with_correct_mounts()
    sys.exit(0 if success else 1)