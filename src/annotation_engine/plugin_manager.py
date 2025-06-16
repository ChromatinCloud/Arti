"""
Plugin manager for VEP plugins and external tools.

This module handles interaction with VEP plugins (like dbNSFP, AlphaMissense)
and manages plugin data files and configurations.
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel


class PluginError(Exception):
    """Base exception for plugin-related errors."""
    pass


class VEPPluginConfig(BaseModel):
    """Configuration for a VEP plugin."""
    name: str
    enabled: bool = True
    data_file: Optional[str] = None
    params: Dict[str, Any] = {}


class VEPPluginManager:
    """Manager for VEP plugins and their data files."""
    
    def __init__(self, vep_executable: str = "scripts/vep", plugins_dir: Optional[str] = None):
        self.vep_executable = vep_executable
        self.plugins_dir = plugins_dir or self._find_plugins_dir()
        self.available_plugins = self._discover_plugins()
    
    def _find_plugins_dir(self) -> str:
        """Find VEP plugins directory."""
        # Check common locations
        candidates = [
            ".refs/functional_predictions/vep_plugins",
            ".refs/vep_setup/ensembl-vep/Plugins",
            os.path.expanduser("~/.vep/Plugins")
        ]
        
        for candidate in candidates:
            if os.path.isdir(candidate):
                return candidate
        
        raise PluginError("VEP plugins directory not found")
    
    def _discover_plugins(self) -> List[str]:
        """Discover available VEP plugins."""
        if not os.path.isdir(self.plugins_dir):
            return []
        
        plugins = []
        for file in os.listdir(self.plugins_dir):
            if file.endswith('.pm'):
                plugin_name = file[:-3]  # Remove .pm extension
                plugins.append(plugin_name)
        
        return sorted(plugins)
    
    def list_available_plugins(self) -> List[str]:
        """Get list of available VEP plugins."""
        return self.available_plugins
    
    def check_plugin_data(self, plugin_name: str) -> Dict[str, Any]:
        """
        Check if plugin data files are available.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dict with plugin status and data file paths
        """
        status = {
            "plugin": plugin_name,
            "available": plugin_name in self.available_plugins,
            "data_files": [],
            "configured": False
        }
        
        # Plugin-specific data file checks
        if plugin_name == "dbNSFP":
            # Look for dbNSFP data files
            candidates = [
                ".refs/functional_predictions/plugin_data/pathogenicity/dbNSFP5.1.gz",
                ".refs/functional_predictions/plugin_data/pathogenicity/dbNSFP4.6a_variant.txt.gz",
                f"{os.path.expanduser('~')}/.vep/dbNSFP.gz"
            ]
            
            for candidate in candidates:
                if os.path.isfile(candidate):
                    status["data_files"].append(candidate)
                    status["configured"] = True
        
        elif plugin_name == "AlphaMissense":
            # Look for AlphaMissense data files
            candidates = [
                ".refs/functional_predictions/plugin_data/protein_impact/AlphaMissense_hg38.tsv.gz",
                f"{os.path.expanduser('~')}/.vep/AlphaMissense_hg38.tsv.gz"
            ]
            
            for candidate in candidates:
                if os.path.isfile(candidate):
                    status["data_files"].append(candidate)
                    status["configured"] = True
        
        elif plugin_name == "SpliceAI":
            # Look for SpliceAI data files
            candidates = [
                ".refs/functional_predictions/plugin_data/splicing/spliceai_scores.masked.snv.hg38.vcf.gz",
                f"{os.path.expanduser('~')}/.vep/spliceai_scores.raw.snv.hg38.vcf.gz"
            ]
            
            for candidate in candidates:
                if os.path.isfile(candidate):
                    status["data_files"].append(candidate)
                    status["configured"] = True
        
        return status
    
    def build_plugin_args(self, plugins: List[VEPPluginConfig]) -> List[str]:
        """
        Build VEP command line arguments for plugins.
        
        Args:
            plugins: List of plugin configurations
            
        Returns:
            List of VEP arguments for plugins
        """
        args = []
        
        for plugin in plugins:
            if not plugin.enabled:
                continue
            
            if plugin.name not in self.available_plugins:
                raise PluginError(f"Plugin {plugin.name} not available")
            
            # Build plugin argument
            plugin_arg = f"--plugin {plugin.name}"
            
            # Add data file if specified
            if plugin.data_file and os.path.isfile(plugin.data_file):
                plugin_arg += f",{plugin.data_file}"
            
            # Add parameters
            for key, value in plugin.params.items():
                plugin_arg += f",{key}={value}"
            
            args.append(plugin_arg)
        
        return args
    
    def get_default_plugins(self) -> List[VEPPluginConfig]:
        """Get default plugin configuration for annotation engine."""
        plugins = []
        
        # dbNSFP for functional predictions
        dbnsfp_status = self.check_plugin_data("dbNSFP")
        if dbnsfp_status["configured"]:
            plugins.append(VEPPluginConfig(
                name="dbNSFP",
                data_file=dbnsfp_status["data_files"][0],
                params={
                    "SIFT_score": True,
                    "Polyphen2_HDIV_score": True,
                    "CADD_phred": True,
                    "REVEL_score": True
                }
            ))
        
        # AlphaMissense for missense predictions
        alphamissense_status = self.check_plugin_data("AlphaMissense")
        if alphamissense_status["configured"]:
            plugins.append(VEPPluginConfig(
                name="AlphaMissense",
                data_file=alphamissense_status["data_files"][0]
            ))
        
        # SpliceAI for splice predictions
        spliceai_status = self.check_plugin_data("SpliceAI")
        if spliceai_status["configured"]:
            plugins.append(VEPPluginConfig(
                name="SpliceAI",
                data_file=spliceai_status["data_files"][0],
                params={
                    "cutoff": "0.5"
                }
            ))
        
        return plugins
    
    def validate_setup(self) -> Dict[str, Any]:
        """Validate VEP plugin setup."""
        report = {
            "vep_executable": os.path.isfile(self.vep_executable),
            "plugins_dir": os.path.isdir(self.plugins_dir),
            "available_plugins": len(self.available_plugins),
            "plugin_details": {}
        }
        
        # Check important plugins
        important_plugins = ["dbNSFP", "AlphaMissense", "SpliceAI", "LoF"]
        
        for plugin in important_plugins:
            status = self.check_plugin_data(plugin)
            report["plugin_details"][plugin] = status
        
        return report


# Global instance
plugin_manager = VEPPluginManager()


def get_vep_plugin_args() -> List[str]:
    """Get VEP plugin arguments for the annotation engine."""
    default_plugins = plugin_manager.get_default_plugins()
    return plugin_manager.build_plugin_args(default_plugins)


def validate_vep_plugins() -> bool:
    """Validate that essential VEP plugins are available."""
    report = plugin_manager.validate_setup()
    
    # Check if VEP is available
    if not report["vep_executable"]:
        raise PluginError("VEP executable not found")
    
    # Check if plugins directory exists
    if not report["plugins_dir"]:
        raise PluginError("VEP plugins directory not found")
    
    # Warn about missing important plugins
    missing_plugins = []
    for plugin, details in report["plugin_details"].items():
        if not details["available"]:
            missing_plugins.append(plugin)
    
    if missing_plugins:
        print(f"Warning: Missing VEP plugins: {', '.join(missing_plugins)}")
    
    return len(missing_plugins) == 0