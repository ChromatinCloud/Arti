"""
Error handling module for validation and CLI operations

Provides comprehensive error handling following clinical application standards
with user-friendly error messages and debugging information.
"""

import sys
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class ValidationError(Exception):
    """
    Custom exception for validation errors
    
    Provides structured error information for consistent handling
    across the application.
    """
    
    def __init__(self, error_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format"""
        return {
            'error_type': self.error_type,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


class CLIErrorHandler:
    """
    CLI error handler with user-friendly error reporting
    
    Provides consistent error formatting and helpful suggestions
    for command-line users.
    """
    
    def __init__(self):
        self.error_codes = {
            'file_not_found': {
                'icon': '📄',
                'category': 'File Error',
                'suggestions': [
                    'Check if the file path is correct',
                    'Ensure the file exists and is readable',
                    'Use absolute path if relative path fails'
                ]
            },
            'empty_file': {
                'icon': '📭',
                'category': 'File Error',
                'suggestions': [
                    'Check if the file contains data',
                    'Verify file was transferred completely',
                    'Try a different input file'
                ]
            },
            'invalid_vcf_format': {
                'icon': '🧬',
                'category': 'VCF Format Error',
                'suggestions': [
                    'Validate VCF format with vcf-validator',
                    'Check for missing header lines',
                    'Ensure proper column structure',
                    'Use bcftools to fix format issues'
                ]
            },
            'schema_validation': {
                'icon': '⚠️',
                'category': 'Input Validation Error',
                'suggestions': [
                    'Check command line arguments',
                    'Verify required parameters are provided',
                    'Use --help for usage information'
                ]
            },
            'file_read_error': {
                'icon': '🔐',
                'category': 'File Access Error',
                'suggestions': [
                    'Check file permissions',
                    'Ensure file is not corrupted',
                    'Try decompressing file manually if .gz'
                ]
            },
            'parsing_error': {
                'icon': '🔧',
                'category': 'File Parsing Error',
                'suggestions': [
                    'Check file format is correct',
                    'Look for special characters or encoding issues',
                    'Try opening file in text editor to inspect'
                ]
            }
        }
    
    def handle_validation_error(self, error: ValidationError, verbose: int = 0) -> None:
        """Handle validation error with user-friendly output"""
        
        error_info = self.error_codes.get(error.error_type, {
            'icon': '❌',
            'category': 'Validation Error',
            'suggestions': ['Check input and try again']
        })
        
        # Print error header
        print(f"\n{error_info['icon']} {error_info['category']}")
        print("=" * 50)
        
        # Print main error message
        print(f"🔍 {error.message}")
        
        # Print details if available and verbose
        if error.details and verbose > 0:
            print(f"\n📋 Details:")
            for key, value in error.details.items():
                if key == 'errors' and isinstance(value, list):
                    print(f"   {key}: {len(value)} validation errors")
                    if verbose > 1:
                        for i, err in enumerate(value[:3]):  # Show first 3
                            print(f"      {i+1}. Line {err.get('line', '?')}: {err.get('error', 'Unknown error')}")
                        if len(value) > 3:
                            print(f"      ... and {len(value) - 3} more")
                elif isinstance(value, (str, int, float, bool)):
                    print(f"   {key}: {value}")
        
        # Print helpful suggestions
        print(f"\n💡 Suggestions:")
        for suggestion in error_info['suggestions']:
            print(f"   • {suggestion}")
        
        # Print debug information if very verbose
        if verbose > 2:
            print(f"\n🐛 Debug Information:")
            print(f"   Error Type: {error.error_type}")
            print(f"   Timestamp: {error.timestamp}")
            if error.details:
                print(f"   Raw Details: {error.details}")
    
    def handle_unexpected_error(self, error: Exception, verbose: int = 0) -> None:
        """Handle unexpected errors with debugging information"""
        
        print(f"\n💥 Unexpected Error")
        print("=" * 50)
        print(f"🔍 An unexpected error occurred: {str(error)}")
        
        if verbose > 0:
            print(f"\n📋 Error Details:")
            print(f"   Type: {type(error).__name__}")
            print(f"   Message: {str(error)}")
        
        if verbose > 1:
            print(f"\n🔧 Stack Trace:")
            traceback.print_exc()
        
        print(f"\n💡 Suggestions:")
        print(f"   • Try running with --verbose for more information")
        print(f"   • Check input files and parameters")
        print(f"   • Report this issue if problem persists")
    
    def print_file_validation_summary(self, file_path: Path, errors: list, warnings: list) -> None:
        """Print file validation summary"""
        
        print(f"\n📄 File Validation: {file_path.name}")
        print("-" * 40)
        
        if not errors and not warnings:
            print("✅ File validation passed")
            return
        
        if errors:
            print(f"❌ Errors: {len(errors)}")
            for error in errors[:3]:  # Show first 3
                line = error.get('line', '?')
                msg = error.get('error', 'Unknown error')
                print(f"   Line {line}: {msg}")
            if len(errors) > 3:
                print(f"   ... and {len(errors) - 3} more errors")
        
        if warnings:
            print(f"⚠️  Warnings: {len(warnings)}")
            for warning in warnings[:2]:  # Show first 2
                line = warning.get('line', '?')
                msg = warning.get('warning', 'Unknown warning')
                print(f"   Line {line}: {msg}")
            if len(warnings) > 2:
                print(f"   ... and {len(warnings) - 2} more warnings")
    
    def create_error_report(self, error: ValidationError, output_dir: Optional[Path] = None) -> Optional[Path]:
        """Create detailed error report file"""
        
        if not output_dir:
            return None
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create error report filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = output_dir / f"error_report_{timestamp}.json"
            
            # Create detailed error report
            import json
            error_report = {
                'timestamp': error.timestamp.isoformat(),
                'error_type': error.error_type,
                'message': error.message,
                'details': error.details,
                'system_info': {
                    'platform': sys.platform,
                    'python_version': sys.version,
                    'working_directory': str(Path.cwd())
                }
            }
            
            # Write report file
            with open(report_file, 'w') as f:
                json.dump(error_report, f, indent=2, default=str)
            
            return report_file
            
        except Exception as e:
            print(f"⚠️  Could not create error report: {e}")
            return None


class ProgressReporter:
    """Simple progress reporter for long-running operations"""
    
    def __init__(self, total_steps: int, description: str = "Processing"):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.start_time = datetime.now()
    
    def update(self, step: int, message: Optional[str] = None) -> None:
        """Update progress"""
        self.current_step = step
        percentage = (step / self.total_steps) * 100
        
        # Create progress bar
        bar_length = 30
        filled_length = int(bar_length * step // self.total_steps)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        # Calculate elapsed time
        elapsed = datetime.now() - self.start_time
        elapsed_str = str(elapsed).split('.')[0]  # Remove microseconds
        
        # Print progress line
        status_msg = f" - {message}" if message else ""
        print(f"\r🔄 {self.description}: |{bar}| {percentage:.1f}% ({step}/{self.total_steps}) [{elapsed_str}]{status_msg}", end='', flush=True)
        
        if step >= self.total_steps:
            print()  # New line when complete
    
    def finish(self, message: str = "Complete") -> None:
        """Mark progress as finished"""
        self.update(self.total_steps, message)


class ValidationWarning:
    """
    Warning class for non-critical validation issues
    """
    
    def __init__(self, warning_type: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.warning_type = warning_type
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert warning to dictionary format"""
        return {
            'warning_type': self.warning_type,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }