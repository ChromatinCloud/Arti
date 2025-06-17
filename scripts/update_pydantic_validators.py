#!/usr/bin/env python3
"""
Update Pydantic v1 validators to v2 field_validators
"""

import re
from pathlib import Path

def update_validators(file_path):
    """Update all @validator decorators to @field_validator with @classmethod"""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match @validator lines and the following function definition
    pattern = r'(@validator\([^)]+\)\s*\n\s*def\s+\w+\(cls,)'
    
    def replacement(match):
        validator_line = match.group(0)
        # Replace @validator with @field_validator and add @classmethod
        new_validator = validator_line.replace('@validator', '@field_validator')
        # Add @classmethod decorator if not present
        if '@classmethod' not in new_validator:
            lines = new_validator.split('\n')
            lines.insert(1, '    @classmethod')
            new_validator = '\n'.join(lines)
        # Update function signature
        new_validator = new_validator.replace('(cls,', '(cls, v):')
        return new_validator.rstrip(')')
    
    # Replace all occurrences
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    # Handle specific patterns that need manual adjustment
    updates = [
        # Fix function signatures that don't follow standard pattern
        (r'(@field_validator[^)]+\)\s*\n\s*@classmethod\s*\n\s*def\s+\w+\(cls,\s*v\):\s*\n\s*def\s+\w+\(cls,)', 
         lambda m: m.group(0).split('def')[-2] + 'def'),
        
        # Ensure all field_validator functions have @classmethod and correct signature
        (r'(@field_validator[^)]+\)\s*\n\s*def\s+(\w+)\(cls,([^)]*)\):',
         r'\1\n    @classmethod\n    def \2(cls, v):'),
    ]
    
    for pattern, replacement in updates:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Manual fixes for specific cases
    content = content.replace('always=True', 'mode="before"')  # Update mode syntax
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Updated validators in {file_path}")

if __name__ == "__main__":
    file_path = Path("src/annotation_engine/validation/input_schemas.py")
    update_validators(file_path)
    print("Validator update complete!")