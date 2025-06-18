#!/usr/bin/env python3
"""
Monitor OncoKB processing progress
"""

import time
import subprocess
from pathlib import Path
from datetime import datetime

def get_progress():
    """Get current processing progress"""
    oncokb_dir = Path("/Users/lauferva/Desktop/Arti/.refs/clinical_evidence/oncokb/oncokb_by_significance/")
    clinvar_dir = Path("/Users/lauferva/Desktop/Arti/.refs/clinical_evidence/clinvar/clinvar_by_significance/")
    
    # Count completed files
    completed = len(list(oncokb_dir.glob("*.tsv")))
    total = len(list(clinvar_dir.glob("*.tsv")))
    
    # Get current file being processed from log
    try:
        log_files = list(Path("/tmp").glob("clinvar_oncokb_processing_*.log"))
        if log_files:
            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            
            # Get last few lines
            result = subprocess.run(
                f"tail -100 {latest_log} | grep 'Processing\\|Successfully queried' | tail -5",
                shell=True,
                capture_output=True,
                text=True
            )
            current_status = result.stdout.strip()
        else:
            current_status = "No log file found"
    except:
        current_status = "Unable to read log"
    
    # Check if process is running
    result = subprocess.run(
        "ps aux | grep process_all_clinvar_oncokb | grep -v grep",
        shell=True,
        capture_output=True,
        text=True
    )
    is_running = bool(result.stdout.strip())
    
    return {
        'completed': completed,
        'total': total,
        'current_status': current_status,
        'is_running': is_running
    }

def main():
    print("OncoKB Processing Monitor")
    print("=" * 50)
    print("Press Ctrl+C to stop monitoring\n")
    
    while True:
        progress = get_progress()
        
        print(f"\r{datetime.now().strftime('%H:%M:%S')} | ", end="")
        print(f"Files: {progress['completed']}/{progress['total']} ", end="")
        print(f"({progress['completed']/progress['total']*100:.1f}%) | ", end="")
        
        if progress['is_running']:
            print("Status: RUNNING", end="")
        else:
            print("Status: STOPPED", end="")
        
        print(" " * 20, end="")  # Clear line
        
        if progress['completed'] == progress['total']:
            print("\n\nProcessing complete!")
            break
        
        time.sleep(10)  # Update every 10 seconds

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")