#!/usr/bin/env python3
"""
Simple test script for VCF utilities without complex dependencies
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_vcf_detection():
    """Test VCF file type detection"""
    
    try:
        from vcf_utils import detect_vcf_file_type
        
        # Test files in example_input
        example_dir = Path(__file__).parent.parent.parent / "example_input"
        
        print("Testing VCF file type detection:")
        print("=" * 50)
        
        for vcf_file in example_dir.glob("*.vcf*"):
            print(f"File: {vcf_file.name}")
            
            try:
                file_info = detect_vcf_file_type(vcf_file)
                print(f"  Type: {file_info['file_type']}")
                print(f"  Is VCF: {file_info['is_vcf']}")
                print(f"  Is gzipped: {file_info['is_gzipped']}")
                print(f"  Is indexed: {file_info['is_indexed']}")
                print(f"  Can process: {file_info['can_process']}")
                
            except Exception as e:
                print(f"  Error: {e}")
            
            print()
            
    except ImportError as e:
        print(f"Import error: {e}")
        return False
        
    return True

def test_vcf_handler():
    """Test VCF file handler with plain text files"""
    
    try:
        from vcf_utils import VCFFileHandler
        
        # Test with plain text VCF
        example_dir = Path(__file__).parent.parent.parent / "example_input"
        test_vcf = example_dir / "proper_test.vcf"
        
        if not test_vcf.exists():
            print(f"Test file not found: {test_vcf}")
            return False
        
        print(f"Testing VCF handler with: {test_vcf.name}")
        print("=" * 50)
        
        handler = VCFFileHandler(test_vcf)
        print(f"Is gzipped: {handler.is_gzipped}")
        print(f"Is indexed: {handler.is_indexed}")
        
        # Get file stats without expensive operations
        stats = {
            "file_path": str(handler.vcf_path),
            "file_size": handler.vcf_path.stat().st_size,
            "is_gzipped": handler.is_gzipped,
            "is_indexed": handler.is_indexed
        }
        
        print(f"File stats: {stats}")
        
        # Try to iterate first few variants
        print("First 3 variants:")
        variant_count = 0
        for variant in handler.iterate_variants():
            print(f"  {variant['chromosome']}:{variant['position']} {variant['reference']}>{variant['alternate']}")
            variant_count += 1
            if variant_count >= 3:
                break
        
        return True
        
    except Exception as e:
        print(f"VCF handler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("VCF Utilities Test Script")
    print("=" * 60)
    
    # Test detection
    detection_ok = test_vcf_detection()
    print()
    
    # Test handler
    handler_ok = test_vcf_handler()
    print()
    
    if detection_ok and handler_ok:
        print("✅ All VCF utilities tests passed!")
    else:
        print("❌ Some VCF utilities tests failed!")
        sys.exit(1)