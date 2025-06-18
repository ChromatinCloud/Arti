#!/usr/bin/env python3
"""
Generate synthetic VCF files for testing annotation-engine
Creates realistic tumor-normal pairs with:
- Mix of ClinVar significance levels (P/LP, VUS, B/LB)
- Range of OncoKB evidence levels
- Various variant types (SNV, indel, CNV, SV)
- Germline variants + somatic mutations with realistic signatures
"""

import random
import datetime
from pathlib import Path
from typing import List, Dict, Tuple
import argparse

# Seed for reproducibility
random.seed(42)

class VCFGenerator:
    def __init__(self):
        # Common cancer genes from COSMIC Cancer Gene Census
        self.cancer_genes = [
            "TP53", "PIK3CA", "KRAS", "BRAF", "EGFR", "BRCA1", "BRCA2", 
            "APC", "PTEN", "CDKN2A", "RB1", "VHL", "MLH1", "MSH2", "MSH6",
            "ATM", "CHEK2", "PALB2", "CDH1", "STK11", "NF1", "NF2", "TSC1",
            "TSC2", "FHIT", "WWOX", "PTCH1", "SMAD4", "DCC", "FBXW7"
        ]
        
        # Chromosomes with relative frequencies (autosomes + X)
        self.chromosomes = {
            "1": 8.0, "2": 7.5, "3": 6.8, "4": 6.2, "5": 5.8, "6": 5.5,
            "7": 5.2, "8": 4.8, "9": 4.5, "10": 4.2, "11": 4.0, "12": 3.8,
            "13": 3.5, "14": 3.3, "15": 3.0, "16": 2.8, "17": 2.5, "18": 2.3,
            "19": 2.0, "20": 1.8, "21": 1.5, "22": 1.3, "X": 2.0
        }
        
        # Variant type distributions
        self.variant_types = {
            "snv": 0.70,      # Single nucleotide variants
            "small_indel": 0.20,  # <50bp insertions/deletions
            "cnv": 0.08,      # Copy number variants
            "sv": 0.02        # Structural variants
        }
        
        # ClinVar significance levels
        self.clinvar_significance = {
            "Pathogenic": 0.15,
            "Likely_pathogenic": 0.10,
            "Uncertain_significance": 0.50,
            "Likely_benign": 0.15,
            "Benign": 0.10
        }
        
        # OncoKB evidence levels
        self.oncokb_levels = {
            "LEVEL_1": 0.05,    # FDA-approved biomarkers
            "LEVEL_2": 0.10,    # Standard care biomarkers
            "LEVEL_3A": 0.15,   # Compelling clinical evidence
            "LEVEL_3B": 0.20,   # Standard care or investigational
            "LEVEL_4": 0.30,    # Compelling biological evidence
            "LEVEL_R1": 0.05,   # Standard care resistance
            "LEVEL_R2": 0.15    # Investigational resistance
        }
        
        # Tumor mutational signatures (simplified)
        self.mutation_signatures = {
            "smoking": {"C>A": 0.4, "C>G": 0.2, "C>T": 0.2, "other": 0.2},
            "uv": {"C>T": 0.6, "CC>TT": 0.2, "other": 0.2},
            "aging": {"C>T": 0.5, "T>C": 0.2, "other": 0.3},
            "msi": {"indel": 0.4, "C>T": 0.3, "other": 0.3},
            "brca": {"indel": 0.3, "C>G": 0.3, "other": 0.4}
        }

    def generate_vcf_header(self, sample_name: str, tumor_type: str = None) -> List[str]:
        """Generate VCF header with metadata"""
        header = [
            "##fileformat=VCFv4.2",
            f"##fileDate={datetime.date.today().strftime('%Y%m%d')}",
            "##source=annotation-engine-test-generator",
            "##reference=GRCh38",
            "##contig=<ID=1,length=248956422>",
            "##contig=<ID=2,length=242193529>",
            "##contig=<ID=3,length=198295559>",
            "##contig=<ID=4,length=190214555>",
            "##contig=<ID=5,length=181538259>",
            "##contig=<ID=6,length=170805979>",
            "##contig=<ID=7,length=159345973>",
            "##contig=<ID=8,length=145138636>",
            "##contig=<ID=9,length=138394717>",
            "##contig=<ID=10,length=133797422>",
            "##contig=<ID=11,length=135086622>",
            "##contig=<ID=12,length=133275309>",
            "##contig=<ID=13,length=114364328>",
            "##contig=<ID=14,length=107043718>",
            "##contig=<ID=15,length=101991189>",
            "##contig=<ID=16,length=90338345>",
            "##contig=<ID=17,length=83257441>",
            "##contig=<ID=18,length=80373285>",
            "##contig=<ID=19,length=58617616>",
            "##contig=<ID=20,length=64444167>",
            "##contig=<ID=21,length=46709983>",
            "##contig=<ID=22,length=50818468>",
            "##contig=<ID=X,length=156040895>",
            "##INFO=<ID=AC,Number=A,Type=Integer,Description=\"Allele count in genotypes\">",
            "##INFO=<ID=AF,Number=A,Type=Float,Description=\"Allele Frequency\">",
            "##INFO=<ID=AN,Number=1,Type=Integer,Description=\"Total number of alleles in called genotypes\">",
            "##INFO=<ID=GENE,Number=1,Type=String,Description=\"Gene symbol\">",
            "##INFO=<ID=VARIANT_CLASS,Number=1,Type=String,Description=\"Sequence Ontology variant class\">",
            "##INFO=<ID=CLINVAR_SIG,Number=1,Type=String,Description=\"ClinVar clinical significance\">",
            "##INFO=<ID=ONCOKB_LEVEL,Number=1,Type=String,Description=\"OncoKB evidence level\">",
            "##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">",
            "##FORMAT=<ID=AD,Number=R,Type=Integer,Description=\"Allelic depths for ref and alt alleles\">",
            "##FORMAT=<ID=DP,Number=1,Type=Integer,Description=\"Approximate read depth\">",
            "##FORMAT=<ID=VAF,Number=A,Type=Float,Description=\"Variant allele frequency\">",
        ]
        
        if tumor_type:
            header.append(f"##tumor_type={tumor_type}")
            header.append(f"##mutation_signature={self.get_signature_for_tumor_type(tumor_type)}")
        
        # Column header
        if sample_name.endswith("_tumor_normal"):
            header.append("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tNORMAL\tTUMOR")
        else:
            header.append(f"#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\t{sample_name}")
        
        return header

    def get_signature_for_tumor_type(self, tumor_type: str) -> str:
        """Map tumor types to mutation signatures"""
        signature_map = {
            "lung": "smoking",
            "melanoma": "uv", 
            "breast": "brca",
            "colorectal": "msi",
            "prostate": "aging",
            "pancreatic": "brca",
            "ovarian": "brca"
        }
        return signature_map.get(tumor_type.lower(), "aging")

    def select_chromosome(self) -> str:
        """Select chromosome based on frequency weights"""
        chroms = list(self.chromosomes.keys())
        weights = list(self.chromosomes.values())
        return random.choices(chroms, weights=weights)[0]

    def generate_position(self, chrom: str) -> int:
        """Generate realistic genomic position"""
        # Avoid centromeres and telomeres
        chrom_lengths = {
            "1": 248956422, "2": 242193529, "3": 198295559, "4": 190214555,
            "5": 181538259, "6": 170805979, "7": 159345973, "8": 145138636,
            "9": 138394717, "10": 133797422, "11": 135086622, "12": 133275309,
            "13": 114364328, "14": 107043718, "15": 101991189, "16": 90338345,
            "17": 83257441, "18": 80373285, "19": 58617616, "20": 64444167,
            "21": 46709983, "22": 50818468, "X": 156040895
        }
        
        max_pos = chrom_lengths.get(chrom, 100000000)
        # Avoid first and last 10% of chromosome
        start = max_pos // 10
        end = max_pos - (max_pos // 10)
        return random.randint(start, end)

    def generate_snv(self, signature: str = "aging") -> Tuple[str, str]:
        """Generate SNV based on mutational signature"""
        sig = self.mutation_signatures.get(signature, self.mutation_signatures["aging"])
        
        # Common SNV patterns
        snv_patterns = {
            "C>A": [("C", "A"), ("G", "T")],  # Complementary pairs
            "C>G": [("C", "G"), ("G", "C")],
            "C>T": [("C", "T"), ("G", "A")],
            "T>C": [("T", "C"), ("A", "G")],
            "T>A": [("T", "A"), ("A", "T")],
            "T>G": [("T", "G"), ("A", "C")]
        }
        
        # Select mutation type based on signature
        rand = random.random()
        cumulative = 0
        
        for mut_type, prob in sig.items():
            cumulative += prob
            if rand <= cumulative:
                if mut_type in snv_patterns:
                    return random.choice(snv_patterns[mut_type])
                else:
                    # Default SNV
                    bases = ["A", "C", "G", "T"]
                    ref = random.choice(bases)
                    alt = random.choice([b for b in bases if b != ref])
                    return ref, alt
        
        # Fallback
        bases = ["A", "C", "G", "T"]
        ref = random.choice(bases)
        alt = random.choice([b for b in bases if b != ref])
        return ref, alt

    def generate_indel(self, signature: str = "aging") -> Tuple[str, str]:
        """Generate insertion or deletion"""
        # Indel size distribution (most are 1-3 bp)
        size_weights = [0.4, 0.3, 0.2, 0.1]  # 1bp, 2bp, 3bp, 4-10bp
        size = random.choices([1, 2, 3, random.randint(4, 10)], weights=size_weights)[0]
        
        bases = ["A", "C", "G", "T"]
        
        if random.random() < 0.6:  # Deletion
            ref = "".join(random.choices(bases, k=size+1))
            alt = ref[0]  # Keep first base
            return ref, alt
        else:  # Insertion
            ref = random.choice(bases)
            insertion = "".join(random.choices(bases, k=size))
            alt = ref + insertion
            return ref, alt

    def generate_cnv(self) -> Tuple[str, str, str]:
        """Generate copy number variant"""
        cnv_types = ["DEL", "DUP", "AMP"]  # Deletion, Duplication, Amplification
        cnv_type = random.choice(cnv_types)
        
        # CNV size (100bp to 100kb)
        size = random.choice([
            random.randint(100, 1000),      # Small CNVs
            random.randint(1000, 10000),    # Medium CNVs  
            random.randint(10000, 100000)   # Large CNVs
        ])
        
        ref = "N"  # Symbolic allele
        alt = f"<{cnv_type}>"
        info_extra = f"SVTYPE={cnv_type};SVLEN={size if cnv_type != 'DEL' else -size}"
        
        return ref, alt, info_extra

    def generate_variant_info(self) -> Dict[str, str]:
        """Generate realistic variant annotations"""
        # Select ClinVar significance
        clinvar_sig = random.choices(
            list(self.clinvar_significance.keys()),
            weights=list(self.clinvar_significance.values())
        )[0]
        
        # Select OncoKB level (only for cancer-relevant variants)
        oncokb_level = ""
        if random.random() < 0.3:  # 30% have OncoKB annotations
            oncokb_level = random.choices(
                list(self.oncokb_levels.keys()),
                weights=list(self.oncokb_levels.values())
            )[0]
        
        # Select gene
        if random.random() < 0.4:  # 40% in known cancer genes
            gene = random.choice(self.cancer_genes)
        else:
            # Generate random gene name
            gene = f"GENE{random.randint(1000, 9999)}"
        
        return {
            "gene": gene,
            "clinvar_sig": clinvar_sig,
            "oncokb_level": oncokb_level
        }

    def generate_genotype_data(self, is_tumor: bool = False, vaf: float = None) -> Tuple[str, str]:
        """Generate realistic genotype and format data"""
        if is_tumor:
            # Tumor sample - can have various VAFs
            if vaf is None:
                vaf = random.choice([0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
            
            # Generate read depths
            total_depth = random.randint(50, 200)
            alt_reads = int(total_depth * vaf)
            ref_reads = total_depth - alt_reads
            
            # Determine genotype based on VAF
            if vaf < 0.15:
                gt = "0/1"  # Heterozygous (low VAF = subclonal)
            elif vaf < 0.7:
                gt = "0/1"  # Heterozygous
            else:
                gt = "1/1"  # Homozygous
                
            format_data = f"{gt}:{ref_reads},{alt_reads}:{total_depth}:{vaf:.3f}"
            
        else:
            # Normal sample
            total_depth = random.randint(30, 150)
            
            if random.random() < 0.95:  # 95% are reference
                gt = "0/0"
                ref_reads = total_depth
                alt_reads = 0
                vaf = 0.0
            else:  # 5% are germline heterozygous
                gt = "0/1"
                vaf = random.uniform(0.45, 0.55)  # Germline ~50%
                alt_reads = int(total_depth * vaf)
                ref_reads = total_depth - alt_reads
            
            format_data = f"{gt}:{ref_reads},{alt_reads}:{total_depth}:{vaf:.3f}"
        
        return gt, format_data

    def generate_variant(self, signature: str = "aging", is_somatic: bool = False) -> Dict:
        """Generate a single variant"""
        chrom = self.select_chromosome()
        pos = self.generate_position(chrom)
        
        # Select variant type
        var_type = random.choices(
            list(self.variant_types.keys()),
            weights=list(self.variant_types.values())
        )[0]
        
        # Generate variant based on type
        if var_type == "snv":
            ref, alt = self.generate_snv(signature)
            info_extra = "VARIANT_CLASS=SNV"
        elif var_type == "small_indel":
            ref, alt = self.generate_indel(signature)
            info_extra = "VARIANT_CLASS=indel"
        elif var_type == "cnv":
            ref, alt, cnv_info = self.generate_cnv()
            info_extra = f"VARIANT_CLASS=copy_number_variant;{cnv_info}"
        else:  # sv
            # Simplified SV representation
            ref = "N"
            alt = "<BND>"
            info_extra = "VARIANT_CLASS=structural_variant;SVTYPE=BND"
        
        # Generate annotations
        annotations = self.generate_variant_info()
        
        # Build INFO field
        info_parts = [
            f"GENE={annotations['gene']}",
            info_extra,
            f"CLINVAR_SIG={annotations['clinvar_sig']}"
        ]
        
        if annotations['oncokb_level']:
            info_parts.append(f"ONCOKB_LEVEL={annotations['oncokb_level']}")
        
        # Add allele frequency info
        af = random.uniform(0.001, 0.1) if not is_somatic else random.uniform(0.05, 0.8)
        info_parts.extend([f"AC=1", f"AF={af:.4f}", f"AN=2"])
        
        return {
            "chrom": chrom,
            "pos": pos,
            "id": ".",
            "ref": ref,
            "alt": alt,
            "qual": random.randint(20, 60),
            "filter": "PASS",
            "info": ";".join(info_parts),
            "format": "GT:AD:DP:VAF",
            "is_somatic": is_somatic,
            "vaf": af if is_somatic else None
        }

    def generate_vcf(self, 
                     output_file: str, 
                     sample_name: str,
                     num_variants: int,
                     tumor_type: str = None,
                     tumor_normal_pair: bool = False,
                     somatic_fraction: float = 0.3) -> None:
        """Generate complete VCF file"""
        
        # Determine mutation signature
        signature = "aging"
        if tumor_type:
            signature = self.get_signature_for_tumor_type(tumor_type)
        
        # Generate header
        header = self.generate_vcf_header(sample_name, tumor_type)
        
        # Generate variants
        variants = []
        num_somatic = int(num_variants * somatic_fraction) if tumor_normal_pair else 0
        num_germline = num_variants - num_somatic
        
        # Generate germline variants
        for _ in range(num_germline):
            variant = self.generate_variant(signature, is_somatic=False)
            variants.append(variant)
        
        # Generate somatic variants (only for tumor-normal pairs)
        for _ in range(num_somatic):
            variant = self.generate_variant(signature, is_somatic=True)
            variants.append(variant)
        
        # Sort variants by position
        variants.sort(key=lambda x: (x["chrom"], x["pos"]))
        
        # Write VCF file
        with open(output_file, 'w') as f:
            # Write header
            for line in header:
                f.write(line + "\n")
            
            # Write variants
            for variant in variants:
                if tumor_normal_pair:
                    # Generate normal and tumor genotypes
                    if variant["is_somatic"]:
                        # Somatic: normal=ref, tumor=alt
                        normal_gt, normal_fmt = self.generate_genotype_data(is_tumor=False)
                        tumor_gt, tumor_fmt = self.generate_genotype_data(is_tumor=True, vaf=variant["vaf"])
                    else:
                        # Germline: both have variant (with drift)
                        base_vaf = random.uniform(0.45, 0.55)
                        normal_gt, normal_fmt = self.generate_genotype_data(is_tumor=False)
                        # Add some VAF drift in tumor for germline variants
                        tumor_vaf = base_vaf + random.uniform(-0.1, 0.1)
                        tumor_vaf = max(0.1, min(0.9, tumor_vaf))
                        tumor_gt, tumor_fmt = self.generate_genotype_data(is_tumor=True, vaf=tumor_vaf)
                    
                    sample_data = f"{normal_fmt}\t{tumor_fmt}"
                else:
                    # Single sample
                    gt, fmt_data = self.generate_genotype_data(is_tumor=tumor_type is not None)
                    sample_data = fmt_data
                
                # Write variant line
                line = f"{variant['chrom']}\t{variant['pos']}\t{variant['id']}\t{variant['ref']}\t{variant['alt']}\t{variant['qual']}\t{variant['filter']}\t{variant['info']}\t{variant['format']}\t{sample_data}"
                f.write(line + "\n")

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic VCF files for testing")
    parser.add_argument("--output-dir", "-o", default="./test_vcfs", help="Output directory")
    parser.add_argument("--sizes", nargs="+", type=int, default=[10, 100, 1000, 10000], 
                       help="Variant counts to generate")
    parser.add_argument("--tumor-types", nargs="+", default=["lung", "breast", "melanoma", "colorectal"],
                       help="Tumor types to generate")
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    generator = VCFGenerator()
    
    # Generate various test VCFs
    for size in args.sizes:
        # Generate tumor-only samples
        for tumor_type in args.tumor_types:
            filename = f"{tumor_type}_tumor_only_{size}vars.vcf"
            filepath = output_dir / filename
            print(f"Generating {filepath}")
            generator.generate_vcf(
                str(filepath),
                sample_name=f"{tumor_type}_tumor",
                num_variants=size,
                tumor_type=tumor_type,
                tumor_normal_pair=False
            )
        
        # Generate tumor-normal pairs
        for tumor_type in args.tumor_types:
            filename = f"{tumor_type}_tumor_normal_{size}vars.vcf"
            filepath = output_dir / filename
            print(f"Generating {filepath}")
            generator.generate_vcf(
                str(filepath),
                sample_name=f"{tumor_type}_tumor_normal",
                num_variants=size,
                tumor_type=tumor_type,
                tumor_normal_pair=True,
                somatic_fraction=0.3  # 30% somatic mutations
            )
        
        # Generate germline-only sample
        filename = f"germline_only_{size}vars.vcf"
        filepath = output_dir / filename
        print(f"Generating {filepath}")
        generator.generate_vcf(
            str(filepath),
            sample_name="germline_sample",
            num_variants=size,
            tumor_type=None,
            tumor_normal_pair=False
        )
    
    print(f"\nGenerated test VCFs in {output_dir}")
    print("Files include:")
    print("- Tumor-only samples for different cancer types")
    print("- Tumor-normal matched pairs")
    print("- Germline-only samples") 
    print("- Range of variant counts (10 to 10,000)")
    print("- Mixed ClinVar significance levels")
    print("- OncoKB evidence levels")
    print("- Realistic mutation signatures per tumor type")

if __name__ == "__main__":
    main()