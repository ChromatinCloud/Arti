#!/usr/bin/env python3
"""
Update Knowledge Base paths throughout the repository
"""
import json
import os
import re
from pathlib import Path

def load_path_mappings():
    """Load the KB path mapping configuration"""
    mapping_file = Path(__file__).parent.parent / "docs" / "KB_PATH_MAPPING.json"
    with open(mapping_file) as f:
        return json.load(f)

def update_file_paths(file_path, mappings):
    """Update paths in a single file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    changes_made = []
    
    # Update directory path mappings
    for old_path, new_path in mappings["path_mappings"].items():
        if old_path in content:
            content = content.replace(old_path, new_path)
            changes_made.append(f"{old_path} -> {new_path}")
    
    # Update specific file mappings
    for old_file, new_file in mappings["specific_file_mappings"].items():
        if old_file in content:
            content = content.replace(old_file, new_file)
            changes_made.append(f"{old_file} -> {new_file}")
    
    # Update VEP plugin data mappings with context
    plugins_dir_pattern = r'{plugins_dir}/([^"\'`,\s]+)'
    def replace_plugin_path(match):
        plugin_file = match.group(1)
        if plugin_file in mappings["vep_plugin_data_mappings"]:
            new_path = mappings["vep_plugin_data_mappings"][plugin_file]
            changes_made.append(f"{{plugins_dir}}/{plugin_file} -> {new_path}")
            return new_path
        else:
            # Default to new plugin data directory structure
            new_path = f".refs/functional_predictions/plugin_data/{plugin_file}"
            changes_made.append(f"{{plugins_dir}}/{plugin_file} -> {new_path}")
            return new_path
    
    content = re.sub(plugins_dir_pattern, replace_plugin_path, content)
    
    # Write back if changes were made
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return changes_made
    
    return []

def main():
    """Main function to update all KB paths"""
    mappings = load_path_mappings()
    repo_root = Path(__file__).parent.parent
    
    # Files to update
    files_to_update = [
        # Python source files
        "src/annotation_engine/evidence_aggregator.py",
        "src/annotation_engine/vep_runner.py", 
        "src/annotation_engine/plugin_manager.py",
        "src/annotation_engine/tiering.py",
        
        # Shell scripts
        "scripts/setup_comprehensive_kb.sh",
        "scripts/setup_vep.sh",
        "scripts/download_plugin_data.sh",
        
        # Documentation (update examples)
        "docs/KB_DOWNLOAD_BLUEPRINT.md",
        "CLAUDE.md"
    ]
    
    print("🔄 Updating Knowledge Base paths throughout repository...")
    print(f"📁 Repository root: {repo_root}")
    print(f"📋 Files to update: {len(files_to_update)}")
    print()
    
    total_changes = 0
    
    for file_path in files_to_update:
        full_path = repo_root / file_path
        if full_path.exists():
            print(f"📝 Updating: {file_path}")
            changes = update_file_paths(full_path, mappings)
            if changes:
                print(f"   ✅ Made {len(changes)} changes:")
                for change in changes:
                    print(f"      • {change}")
                total_changes += len(changes)
            else:
                print(f"   ℹ️  No changes needed")
        else:
            print(f"   ⚠️  File not found: {file_path}")
        print()
    
    print(f"🎉 Update complete! Total changes made: {total_changes}")
    
    # Generate summary report
    print("\n📊 SUMMARY REPORT:")
    print("="*50)
    print(f"Total files processed: {len(files_to_update)}")
    print(f"Total path updates: {total_changes}")
    print(f"Path mappings applied: {len(mappings['path_mappings'])}")
    print(f"File mappings applied: {len(mappings['specific_file_mappings'])}")
    print(f"VEP plugin mappings: {len(mappings['vep_plugin_data_mappings'])}")
    
    # Recommend next steps
    print("\n🚀 NEXT STEPS:")
    print("1. Review changes with: git diff")
    print("2. Test the annotation pipeline")
    print("3. Update any additional scripts that reference old paths")
    print("4. Create symbolic links or move actual data files")

if __name__ == "__main__":
    main()