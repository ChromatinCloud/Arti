#!/usr/bin/env python3
"""
Validate knowledge base files and report status

Checks presence, format, and accessibility of all required knowledge base files.
"""

import sys
import gzip
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class KnowledgeBaseValidator:
    """Validate knowledge base files and structure"""
    
    def __init__(self, refs_dir: Optional[Path] = None):
        if refs_dir is None:
            refs_dir = Path(__file__).parent.parent / ".refs"
        self.refs_dir = Path(refs_dir)
        self.results = {"valid": [], "missing": [], "errors": []}
        
    def validate_all(self) -> Dict[str, List[str]]:
        """Run all validation checks"""
        print("Knowledge Base Validation Report")
        print("=" * 80)
        
        # Clinical evidence
        self._validate_clinical_evidence()
        
        # Population frequencies
        self._validate_population_frequencies()
        
        # Functional predictions
        self._validate_functional_predictions()
        
        # Cancer signatures
        self._validate_cancer_signatures()
        
        # VEP setup
        self._validate_vep_setup()
        
        # Print summary
        self._print_summary()
        
        return self.results
    
    def _validate_clinical_evidence(self):
        """Validate clinical evidence databases"""
        print("\n[Clinical Evidence]")
        
        checks = [
            ("ClinVar VCF", "clinical_evidence/clinvar/clinvar.vcf.gz", self._check_vcf_gz),
            ("ClinVar TSV", "clinical_evidence/clinvar/variant_summary.txt.gz", self._check_tsv_gz),
            ("CIViC Variants", "clinical_evidence/civic/civic_variants.tsv", self._check_tsv),
            ("OncoKB Gene List", "clinical_evidence/oncokb/cancer_gene_list.json", self._check_json),
            ("CGC Census", "cancer_signatures/cosmic/cancer_gene_census.tsv.gz", self._check_tsv_gz),
        ]
        
        self._run_checks(checks)
    
    def _validate_population_frequencies(self):
        """Validate population frequency databases"""
        print("\n[Population Frequencies]")
        
        checks = [
            ("gnomAD Genomes", "population_frequencies/gnomad/gnomad.genomes.v3.1.2.sites.vcf.bgz", self._check_vcf_gz),
            ("gnomAD Exomes", "population_frequencies/gnomad/gnomad.exomes.r2.1.1.sites.liftover_grch38.vcf.bgz", self._check_vcf_gz),
            ("gnomAD Coverage", "population_frequencies/gnomad/gnomad.exomes.coverage.summary.tsv.gz", self._check_exists),
            ("dbSNP", "population_frequencies/dbsnp/dbsnp156.vcf.gz", self._check_vcf_gz),
        ]
        
        self._run_checks(checks)
    
    def _validate_functional_predictions(self):
        """Validate functional prediction data"""
        print("\n[Functional Predictions]")
        
        checks = [
            ("AlphaMissense", "functional_predictions/plugin_data/protein_impact/AlphaMissense_hg38.tsv.gz", self._check_alphamissense),
            ("dbNSFP", "functional_predictions/plugin_data/pathogenicity/dbNSFP5.1.gz", self._check_exists),
            ("REVEL", "functional_predictions/plugin_data/pathogenicity/revel_all_chromosomes.tsv.gz", self._check_exists),
            ("BayesDel", "functional_predictions/plugin_data/pathogenicity/BayesDel_addAF_V1.2.tsv.gz", self._check_exists),
            ("PrimateAI", "functional_predictions/plugin_data/protein_impact/PrimateAI_scores_v0.2.tsv.gz", self._check_exists),
            ("EVE", "functional_predictions/plugin_data/protein_impact/eve_merged.vcf.gz", self._check_exists),
            ("VARITY", "functional_predictions/plugin_data/protein_impact/VARITY_R_LOO_v1.0.tsv.gz", self._check_exists),
            ("SpliceAI", "functional_predictions/plugin_data/splicing/spliceai_scores.masked.snv.hg38.vcf.gz", self._check_vcf_gz),
            ("dbscSNV", "functional_predictions/plugin_data/splicing/dbscSNV1.1_GRCh38.txt.gz", self._check_tsv_gz),
            ("Conservation", "functional_predictions/plugin_data/conservation/conservation_scores.wig.gz", self._check_exists),
            ("LoFtool", "functional_predictions/plugin_data/gene_constraint/LoFtool_scores.txt", self._check_exists),
        ]
        
        self._run_checks(checks)
    
    def _validate_cancer_signatures(self):
        """Validate cancer-specific databases"""
        print("\n[Cancer Signatures]")
        
        checks = [
            ("MSK Hotspots", "cancer_signatures/hotspots/cancerhotspots.org.snv.txt", self._check_tsv),
            ("MSK 3D Hotspots", "cancer_signatures/hotspots/cancerhotspots.org.maf.3d.txt", self._check_tsv),
            ("COSMIC Hotspots", "cancer_signatures/hotspots/cosmic_hotspots.vcf.gz", self._check_vcf_gz),
            ("OncoVI SNV Hotspots", "cancer_signatures/hotspots/oncovi_single_residue_hotspots.tsv", self._check_tsv),
            ("OncoVI INDEL Hotspots", "cancer_signatures/hotspots/oncovi_indel_hotspots.tsv", self._check_tsv),
            ("COSMIC CGC", "cancer_signatures/cosmic/cancer_gene_census.tsv", self._check_tsv),
            ("TCGA Mutations", "cancer_signatures/tcga/tcga_somatic_mutations.vcf.gz", self._check_vcf_gz),
        ]
        
        self._run_checks(checks)
    
    def _validate_vep_setup(self):
        """Validate VEP installation"""
        print("\n[VEP Setup]")
        
        checks = [
            ("VEP Cache", "functional_predictions/vep_cache/homo_sapiens/114_GRCh38", self._check_dir),
            ("VEP Plugins", "functional_predictions/vep_plugins", self._check_plugin_dir),
            ("Reference FASTA", "functional_predictions/vep_cache/homo_sapiens/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz", self._check_exists),
        ]
        
        self._run_checks(checks)
    
    def _run_checks(self, checks: List[Tuple[str, str, callable]]):
        """Run a list of validation checks"""
        for name, path, check_func in checks:
            full_path = self.refs_dir / path if not path.startswith("/") else Path(path)
            status, message = check_func(full_path)
            
            if status == "valid":
                self.results["valid"].append(f"{name}: {message}")
                print(f"  ✓ {name}: {message}")
            elif status == "missing":
                self.results["missing"].append(f"{name}: {full_path}")
                print(f"  ✗ {name}: MISSING")
            else:
                self.results["errors"].append(f"{name}: {message}")
                print(f"  ⚠ {name}: ERROR - {message}")
    
    def _check_exists(self, path: Path) -> Tuple[str, str]:
        """Check if file exists"""
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            return "valid", f"{size_mb:.1f} MB"
        return "missing", str(path)
    
    def _check_dir(self, path: Path) -> Tuple[str, str]:
        """Check if directory exists and has content"""
        if path.exists() and path.is_dir():
            count = len(list(path.iterdir()))
            return "valid", f"{count} items"
        return "missing", str(path)
    
    def _check_plugin_dir(self, path: Path) -> Tuple[str, str]:
        """Check plugin directory"""
        if path.exists() and path.is_dir():
            pm_files = list(path.glob("*.pm"))
            return "valid", f"{len(pm_files)} plugins"
        return "missing", str(path)
    
    def _check_vcf_gz(self, path: Path) -> Tuple[str, str]:
        """Validate gzipped VCF file"""
        if not path.exists():
            return "missing", str(path)
        
        try:
            with gzip.open(path, 'rt') as f:
                first_line = f.readline()
                if first_line.startswith("##fileformat=VCF"):
                    size_mb = path.stat().st_size / (1024 * 1024)
                    return "valid", f"VCF format, {size_mb:.1f} MB"
                else:
                    return "error", "Not a valid VCF file"
        except Exception as e:
            return "error", str(e)
    
    def _check_tsv(self, path: Path) -> Tuple[str, str]:
        """Validate TSV file"""
        if not path.exists():
            return "missing", str(path)
        
        try:
            df = pd.read_csv(path, sep='\t', nrows=5)
            rows = len(pd.read_csv(path, sep='\t'))
            return "valid", f"{rows} rows, {len(df.columns)} columns"
        except Exception as e:
            return "error", str(e)
    
    def _check_tsv_gz(self, path: Path) -> Tuple[str, str]:
        """Validate gzipped TSV file"""
        if not path.exists():
            return "missing", str(path)
        
        try:
            df = pd.read_csv(path, sep='\t', compression='gzip', nrows=5)
            size_mb = path.stat().st_size / (1024 * 1024)
            return "valid", f"TSV format, {len(df.columns)} columns, {size_mb:.1f} MB"
        except Exception as e:
            return "error", str(e)
    
    def _check_json(self, path: Path) -> Tuple[str, str]:
        """Validate JSON file"""
        if not path.exists():
            return "missing", str(path)
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            if isinstance(data, list):
                return "valid", f"{len(data)} items"
            elif isinstance(data, dict):
                return "valid", f"{len(data)} keys"
            else:
                return "valid", "Valid JSON"
        except Exception as e:
            return "error", str(e)
    
    def _check_alphamissense(self, path: Path) -> Tuple[str, str]:
        """Check AlphaMissense file with custom format"""
        if not path.exists():
            return "missing", str(path)
        
        try:
            # AlphaMissense has header lines starting with #
            with gzip.open(path, 'rt') as f:
                # Skip copyright lines
                for line in f:
                    if line.startswith('#CHROM'):
                        break
                # Read one data line to verify format
                data_line = f.readline()
                if data_line and len(data_line.split('\t')) >= 10:
                    size_mb = path.stat().st_size / (1024 * 1024)
                    return "valid", f"AlphaMissense format, {size_mb:.1f} MB"
                else:
                    return "error", "Invalid AlphaMissense format"
        except Exception as e:
            return "error", str(e)
    
    def _print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 80)
        print("SUMMARY:")
        print(f"  Valid files: {len(self.results['valid'])}")
        print(f"  Missing files: {len(self.results['missing'])}")
        print(f"  Errors: {len(self.results['errors'])}")
        
        if self.results['missing']:
            print("\nMissing files:")
            for item in self.results['missing']:
                print(f"  - {item}")
        
        if self.results['errors']:
            print("\nErrors:")
            for item in self.results['errors']:
                print(f"  - {item}")
        
        total_files = len(self.results['valid']) + len(self.results['missing']) + len(self.results['errors'])
        percent_complete = (len(self.results['valid']) / total_files) * 100 if total_files > 0 else 0
        print(f"\nKnowledge base completeness: {percent_complete:.1f}%")


def main():
    """Run knowledge base validation"""
    validator = KnowledgeBaseValidator()
    results = validator.validate_all()
    
    # Exit with error code if missing files
    if results['missing'] or results['errors']:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()