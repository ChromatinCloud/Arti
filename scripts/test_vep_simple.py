#!/usr/bin/env python3
"""
Simple VEP test using centralized VEP Docker Manager
"""

import subprocess
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from annotation_engine.vep_docker_manager import create_vep_docker_manager, VEPDockerMode

def test_simple_vep():
    """Test VEP using centralized Docker manager"""
    
    print("Testing VEP with centralized Docker manager...")
    
    # Create VEP Docker manager
    try:
        vep_manager = create_vep_docker_manager()
        print(f"✅ VEP Docker Manager initialized")
        
        # Print configuration summary
        config_summary = vep_manager.get_config_summary()
        print("\nConfiguration:")
        for key, value in config_summary.items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"❌ Failed to initialize VEP Docker Manager: {e}")
        assert False, f"VEP Docker Manager initialization failed: {e}"
    
    # Prepare input/output files
    repo_root = Path.cwd()
    input_file = repo_root / "example_input" / "proper_test.vcf"
    output_file = repo_root / "out" / "test_vep_simple_output.json"
    
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        assert False, f"Input file not found: {input_file}"
    
    # Build command using Docker manager
    try:
        cmd = vep_manager.build_docker_command(
            input_file=input_file,
            output_file=output_file,
            vep_args=["--no_check_variants_order"],  # Skip variant order checking
            mode=VEPDockerMode.ANNOTATION
        )
    
        print(f"✅ Command built successfully")
        print(f"\nCommand: {' '.join(cmd)}")
        
    except Exception as e:
        print(f"❌ Failed to build VEP command: {e}")
        assert False, f"Command building failed: {e}"
    
    # Execute VEP using Docker manager
    try:
        print(f"\nExecuting VEP...")
        result = vep_manager.execute_vep(
            input_file=input_file,
            output_file=output_file,
            vep_args=["--no_check_variants_order"],
            mode=VEPDockerMode.ANNOTATION
        )
        
        print("✅ VEP executed successfully!")
        
        # Check if output file was created
        if output_file.exists():
            print(f"✅ Output file created: {output_file}")
            
            # Show output size 
            file_size = output_file.stat().st_size
            print(f"   File size: {file_size} bytes")
            
            # Show first few lines if it's JSON
            try:
                with open(output_file) as f:
                    first_lines = [f.readline().strip() for _ in range(3)]
                print(f"   First lines: {first_lines}")
            except Exception:
                print("   (Could not preview file content)")
        else:
            print(f"❌ Output file not created: {output_file}")
            assert False, "Output file not created"
            
        # Test passes
        assert True
                    
    except subprocess.CalledProcessError as e:
        print(f"❌ VEP failed with exit code {e.returncode}")
        if e.stderr:
            print(f"\nSTDERR: {e.stderr}")
        if e.stdout:
            print(f"\nSTDOUT: {e.stdout[:1000]}")
        assert False, f"VEP failed with exit code {e.returncode}"
        
    except subprocess.TimeoutExpired:
        print("❌ VEP timed out")
        assert False, "VEP timed out"
        
    except Exception as e:
        print(f"❌ Error: {e}")
        assert False, f"Error: {e}"

if __name__ == "__main__":
    test_simple_vep()