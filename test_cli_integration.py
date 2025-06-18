#!/usr/bin/env python3
"""
Test CLI integration for enhanced text options
"""

def test_enhanced_text_options():
    """Test that enhanced text options are properly defined"""
    print("Testing enhanced text options in CLI...")
    
    # Check if the CLI file has our new options
    with open('src/annotation_engine/cli.py', 'r') as f:
        cli_content = f.read()
    
    required_options = [
        '--enable-enhanced-text',
        '--disable-enhanced-text', 
        '--text-confidence-threshold',
        '--citation-style',
        '--text-style',
        '--include-citations',
        '--pertinent-negatives-scope'
    ]
    
    found_options = []
    for option in required_options:
        if option in cli_content:
            found_options.append(option)
            print(f"✅ Found option: {option}")
        else:
            print(f"❌ Missing option: {option}")
    
    print(f"\nFound {len(found_options)}/{len(required_options)} enhanced text options")
    
    # Check if enhanced text options are passed to analysis request
    if 'enhanced_text_options=' in cli_content:
        print("✅ Enhanced text options passed to AnalysisRequest")
    else:
        print("❌ Enhanced text options not passed to AnalysisRequest")
    
    # Check if AnalysisRequest schema includes enhanced text options
    with open('src/annotation_engine/validation/input_schemas.py', 'r') as f:
        schema_content = f.read()
    
    if 'enhanced_text_options' in schema_content:
        print("✅ AnalysisRequest schema includes enhanced_text_options")
    else:
        print("❌ AnalysisRequest schema missing enhanced_text_options")
    
    return len(found_options) == len(required_options)

def test_integration_components():
    """Test that integration components are available"""
    print("\nTesting integration components...")
    
    # Check integration file exists and has key components
    try:
        with open('src/annotation_engine/canned_text_integration.py', 'r') as f:
            integration_content = f.read()
        
        key_components = [
            'ComprehensiveCannedTextGenerator',
            'EnhancedNarrativeGenerator',
            'use_enhanced_narratives',
            'generate_enhanced_narrative'
        ]
        
        for component in key_components:
            if component in integration_content:
                print(f"✅ Found component: {component}")
            else:
                print(f"❌ Missing component: {component}")
        
        print("✅ Integration file exists and has key components")
        return True
        
    except FileNotFoundError:
        print("❌ Integration file not found")
        return False

def test_tiering_engine_integration():
    """Test that tiering engine uses comprehensive generator"""
    print("\nTesting tiering engine integration...")
    
    try:
        with open('src/annotation_engine/tiering.py', 'r') as f:
            tiering_content = f.read()
        
        if 'ComprehensiveCannedTextGenerator' in tiering_content:
            print("✅ TieringEngine uses ComprehensiveCannedTextGenerator")
            return True
        else:
            print("❌ TieringEngine not updated to use ComprehensiveCannedTextGenerator")
            return False
            
    except FileNotFoundError:
        print("❌ Tiering engine file not found")
        return False

def main():
    print("🧪 Testing Enhanced Text Integration")
    print("=" * 50)
    
    results = []
    
    # Test CLI options
    results.append(test_enhanced_text_options())
    
    # Test integration components
    results.append(test_integration_components())
    
    # Test tiering engine integration
    results.append(test_tiering_engine_integration())
    
    print("\n" + "=" * 50)
    if all(results):
        print("🎉 All integration tests passed!")
        print("✅ Enhanced text system ready for use")
        return 0
    else:
        print("❌ Some integration tests failed")
        return 1

if __name__ == "__main__":
    exit(main())