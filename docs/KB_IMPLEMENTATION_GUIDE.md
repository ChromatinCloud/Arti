# KB Implementation Guide - Technical Details

**Purpose:** Detailed technical implementation patterns for KB integration  
**Date:** June 16, 2025  
**Focus:** Data structures, query patterns, and performance optimization

## Data Flow Architecture

```
VCF Input → VEP (Functional) → Evidence Aggregator (Clinical) → Tier Engine → Text Generator → JSON Output
     ↓            ↓                      ↓                    ↓              ↓
   Variant    Plugin Scores        KB Queries            Guidelines     Templates
   Objects    (8-10 plugins)      (6-8 direct KBs)     (3 systems)    (8 types)
```

## Core Data Structures

### VariantEvidence Model
```python
from pydantic import BaseModel
from typing import Dict, List, Optional

class FunctionalScores(BaseModel):
    """VEP plugin results"""
    sift: Optional[Dict[str, float]] = None
    polyphen: Optional[Dict[str, float]] = None
    cadd: Optional[float] = None
    revel: Optional[float] = None
    alphamissense: Optional[Dict[str, any]] = None
    spliceai: Optional[Dict[str, float]] = None
    conservation: Optional[Dict[str, float]] = None

class ClinicalEvidence(BaseModel):
    """Direct KB query results"""
    clinvar: Optional[Dict[str, any]] = None
    civic: List[Dict[str, any]] = []
    oncokb: Optional[Dict[str, any]] = None
    hotspots: Optional[Dict[str, any]] = None
    population: Optional[Dict[str, float]] = None

class TierAssignment(BaseModel):
    """Clinical guideline results"""
    amp_tier: str
    amp_rationale: List[str]
    vicc_score: int
    vicc_classification: str
    vicc_evidence: List[str]
    oncokb_level: Optional[str] = None

class VariantEvidence(BaseModel):
    """Complete evidence package for a variant"""
    variant_id: str
    gene: str
    hgvs_c: str
    hgvs_p: str
    functional: FunctionalScores
    clinical: ClinicalEvidence  
    tiers: TierAssignment
    confidence_score: float
```

## KB Query Implementations

### 1. VEP Plugin Results Parser

```python
class VEPResultsParser:
    """Parse VEP JSON output with plugin results"""
    
    def parse_functional_scores(self, vep_transcript: Dict) -> FunctionalScores:
        """Extract functional scores from VEP transcript consequence"""
        
        scores = FunctionalScores()
        
        # dbNSFP scores
        if 'SIFT_score' in vep_transcript:
            scores.sift = {
                'score': float(vep_transcript['SIFT_score']),
                'prediction': vep_transcript.get('SIFT_pred', '')
            }
            
        if 'Polyphen2_HDIV_score' in vep_transcript:
            scores.polyphen = {
                'score': float(vep_transcript['Polyphen2_HDIV_score']),
                'prediction': vep_transcript.get('Polyphen2_HDIV_pred', '')
            }
            
        if 'CADD_phred' in vep_transcript:
            scores.cadd = float(vep_transcript['CADD_phred'])
            
        if 'REVEL_score' in vep_transcript:
            scores.revel = float(vep_transcript['REVEL_score'])
        
        # AlphaMissense
        if 'am_pathogenicity' in vep_transcript:
            scores.alphamissense = {
                'pathogenicity': float(vep_transcript['am_pathogenicity']),
                'class': vep_transcript.get('am_class', ''),
                'likely_pathogenic': float(vep_transcript['am_pathogenicity']) > 0.564
            }
        
        # SpliceAI
        if 'SpliceAI_pred_DS_AG' in vep_transcript:
            scores.spliceai = {
                'ds_ag': float(vep_transcript['SpliceAI_pred_DS_AG']),
                'ds_al': float(vep_transcript['SpliceAI_pred_DS_AL']),
                'ds_dg': float(vep_transcript['SpliceAI_pred_DS_DG']),
                'ds_dl': float(vep_transcript['SpliceAI_pred_DS_DL']),
                'max_score': max([
                    float(vep_transcript['SpliceAI_pred_DS_AG']),
                    float(vep_transcript['SpliceAI_pred_DS_AL']),
                    float(vep_transcript['SpliceAI_pred_DS_DG']),
                    float(vep_transcript['SpliceAI_pred_DS_DL'])
                ])
            }
        
        return scores
```

### 2. ClinVar Query System

```python
import pysam
from typing import Optional

class ClinVarQuerier:
    """Query ClinVar VCF efficiently"""
    
    def __init__(self, clinvar_vcf_path: str):
        self.vcf_file = pysam.VariantFile(clinvar_vcf_path)
        
    def query_variant(self, chrom: str, pos: int, ref: str, alt: str) -> Optional[Dict]:
        """Query ClinVar for specific variant"""
        
        try:
            # Use tabix for efficient position lookup
            records = self.vcf_file.fetch(chrom, pos-1, pos+1)
            
            for record in records:
                if record.ref == ref and alt in [str(alt_allele) for alt_allele in record.alts]:
                    
                    # Extract clinical significance
                    clnsig = record.info.get('CLNSIG', [''])[0]
                    clnrevstat = record.info.get('CLNREVSTAT', [''])[0]
                    clndn = record.info.get('CLNDN', [''])[0]
                    
                    # VICC scoring
                    vicc_points = 0
                    if any(sig in clnsig for sig in ['Pathogenic', 'Likely_pathogenic']):
                        if 'practice_guideline' in clnrevstat or 'reviewed_by_expert_panel' in clnrevstat:
                            vicc_points = 4  # OS2 - well-established in guidelines
                        else:
                            vicc_points = 2  # OM2 - moderate evidence
                    elif any(sig in clnsig for sig in ['Benign', 'Likely_benign']):
                        vicc_points = -4  # SBS2 - functional studies benign
                    
                    return {
                        'clinical_significance': clnsig,
                        'review_status': clnrevstat,
                        'disease_name': clndn,
                        'vicc_points': vicc_points,
                        'database': 'ClinVar'
                    }
                    
        except Exception as e:
            print(f"ClinVar query error: {e}")
            
        return None
```

### 3. CIViC Query System

```python
import pandas as pd
from typing import List

class CIVICQuerier:
    """Query CIViC evidence database"""
    
    def __init__(self, civic_tsv_path: str):
        self.civic_df = pd.read_csv(civic_tsv_path, sep='\t', low_memory=False)
        
    def query_gene_evidence(self, gene: str, cancer_type: Optional[str] = None) -> List[Dict]:
        """Query CIViC for gene-level therapeutic evidence"""
        
        gene_evidence = self.civic_df[self.civic_df['gene'] == gene]
        
        if cancer_type:
            # Filter by cancer type if provided
            gene_evidence = gene_evidence[
                gene_evidence['disease'].str.contains(cancer_type, case=False, na=False)
            ]
        
        therapeutic_evidence = []
        
        for _, row in gene_evidence.iterrows():
            if row['evidence_type'] == 'Predictive':
                
                # AMP tier mapping
                amp_tier = "III"  # Default VUS
                if row['evidence_level'] in ['A']:
                    amp_tier = "IA"
                elif row['evidence_level'] in ['B']:
                    amp_tier = "IB"  
                elif row['evidence_level'] in ['C']:
                    amp_tier = "IIC"
                elif row['evidence_level'] in ['D']:
                    amp_tier = "IID"
                
                therapeutic_evidence.append({
                    'variant': row['variant'],
                    'drug': row['drugs'],
                    'evidence_level': row['evidence_level'],
                    'clinical_significance': row['clinical_significance'],
                    'disease': row['disease'],
                    'evidence_direction': row['evidence_direction'],
                    'amp_tier_support': amp_tier,
                    'database': 'CIViC'
                })
        
        return therapeutic_evidence
        
    def query_variant_coordinates(self, chrom: str, pos: int, gene: str) -> List[Dict]:
        """Query CIViC by genomic coordinates"""
        
        coord_matches = self.civic_df[
            (self.civic_df['gene'] == gene) &
            (self.civic_df['chromosome'] == chrom) &
            (self.civic_df['start'] <= pos) &
            (self.civic_df['stop'] >= pos)
        ]
        
        return self.query_gene_evidence(gene)  # Return gene-level evidence for now
```

### 4. Cancer Hotspots Query

```python
class CancerHotspotsQuerier:
    """Query cancer hotspots database"""
    
    def __init__(self, hotspots_vcf_path: str):
        self.vcf_file = pysam.VariantFile(hotspots_vcf_path)
        
    def query_hotspot(self, chrom: str, pos: int, ref: str, alt: str) -> Optional[Dict]:
        """Check if variant is a known cancer hotspot"""
        
        try:
            records = self.vcf_file.fetch(chrom, pos-1, pos+1)
            
            for record in records:
                if record.ref == ref and alt in [str(alt_allele) for alt_allele in record.alts]:
                    
                    # Extract sample count
                    sample_count = record.info.get('AC', [0])[0]  # Allele count as proxy
                    
                    # VICC scoring based on recurrence
                    vicc_points = 0
                    hotspot_level = "none"
                    
                    if sample_count >= 50:
                        vicc_points = 4  # OS3 - well-established hotspot
                        hotspot_level = "established"
                    elif sample_count >= 10:
                        vicc_points = 2  # OM3 - moderate hotspot evidence
                        hotspot_level = "moderate"
                    elif sample_count >= 3:
                        vicc_points = 1  # OP3 - in hotspot region
                        hotspot_level = "emerging"
                    
                    return {
                        'is_hotspot': True,
                        'sample_count': sample_count,
                        'hotspot_level': hotspot_level,
                        'vicc_points': vicc_points,
                        'database': 'Cancer_Hotspots'
                    }
                    
        except Exception as e:
            print(f"Cancer hotspots query error: {e}")
            
        return None
```

### 5. OncoKB Integration

```python
class OncoKBQuerier:
    """Query OncoKB for gene classifications and therapeutic evidence"""
    
    def __init__(self, oncokb_genes_path: str, api_token: Optional[str] = None):
        self.genes_df = pd.read_csv(oncokb_genes_path, sep='\t')
        self.api_token = api_token
        
    def query_gene_role(self, gene: str) -> Optional[Dict]:
        """Get OncoKB gene classification"""
        
        gene_info = self.genes_df[self.genes_df['Hugo Symbol'] == gene]
        
        if gene_info.empty:
            return None
            
        is_oncogene = gene_info['Is Oncogene'].iloc[0]
        is_tsg = gene_info['Is Tumor Suppressor Gene'].iloc[0]
        
        # VICC scoring
        vicc_points = 0
        gene_role = "unknown"
        
        if is_oncogene:
            vicc_points = 4  # OS1 - activating variant in oncogene
            gene_role = "oncogene"
        elif is_tsg:
            vicc_points = 8  # OVS1 - null variant in tumor suppressor
            gene_role = "tumor_suppressor"
        
        return {
            'gene': gene,
            'is_oncogene': is_oncogene,
            'is_tumor_suppressor': is_tsg,
            'gene_role': gene_role,
            'vicc_points': vicc_points,
            'database': 'OncoKB'
        }
```

## Evidence Aggregation Engine

```python
class EvidenceAggregator:
    """Main evidence aggregation orchestrator"""
    
    def __init__(self):
        self.vep_parser = VEPResultsParser()
        self.clinvar = ClinVarQuerier("path/to/clinvar.vcf.gz")
        self.civic = CIVICQuerier("path/to/civic_variants.tsv")
        self.hotspots = CancerHotspotsQuerier("path/to/hotspots.vcf.gz")
        self.oncokb = OncoKBQuerier("path/to/oncokb_genes.txt")
        
    def aggregate_evidence(self, variant: Dict, vep_result: Dict) -> VariantEvidence:
        """Aggregate all evidence for a single variant"""
        
        # Extract basic variant info
        chrom = variant['chromosome']
        pos = variant['position']
        ref = variant['reference']
        alt = variant['alternate']
        gene = variant['gene_symbol']
        
        # Parse VEP functional scores
        functional_scores = self.vep_parser.parse_functional_scores(vep_result)
        
        # Query clinical databases
        clinical_evidence = ClinicalEvidence()
        
        # ClinVar
        clinical_evidence.clinvar = self.clinvar.query_variant(chrom, pos, ref, alt)
        
        # CIViC
        clinical_evidence.civic = self.civic.query_gene_evidence(gene)
        
        # OncoKB
        clinical_evidence.oncokb = self.oncokb.query_gene_role(gene)
        
        # Cancer Hotspots
        clinical_evidence.hotspots = self.hotspots.query_hotspot(chrom, pos, ref, alt)
        
        # Population frequency (implement gnomAD query)
        clinical_evidence.population = self.query_gnomad(chrom, pos, ref, alt)
        
        # Perform tier assignment
        tiers = self.assign_tiers(functional_scores, clinical_evidence)
        
        # Calculate confidence score
        confidence = self.calculate_confidence(functional_scores, clinical_evidence, tiers)
        
        return VariantEvidence(
            variant_id=f"{chrom}_{pos}_{ref}_{alt}",
            gene=gene,
            hgvs_c=variant.get('hgvs_c', ''),
            hgvs_p=variant.get('hgvs_p', ''),
            functional=functional_scores,
            clinical=clinical_evidence,
            tiers=tiers,
            confidence_score=confidence
        )
```

## Performance Optimization Patterns

### 1. Efficient File Access
```python
# Use tabix for large VCF files
import pysam

class OptimizedVCFQuerier:
    def __init__(self, vcf_path: str):
        self.vcf = pysam.VariantFile(vcf_path)
        
    def batch_query(self, variants: List[Dict]) -> Dict:
        """Batch query multiple variants efficiently"""
        results = {}
        
        # Group variants by chromosome for efficient iteration
        by_chrom = {}
        for var in variants:
            chrom = var['chromosome']
            if chrom not in by_chrom:
                by_chrom[chrom] = []
            by_chrom[chrom].append(var)
        
        # Query each chromosome once
        for chrom, chrom_variants in by_chrom.items():
            min_pos = min(v['position'] for v in chrom_variants)
            max_pos = max(v['position'] for v in chrom_variants)
            
            # Fetch region once
            records = list(self.vcf.fetch(chrom, min_pos-1, max_pos+1))
            
            # Match variants to records
            for var in chrom_variants:
                var_key = f"{var['chromosome']}_{var['position']}_{var['reference']}_{var['alternate']}"
                results[var_key] = self.match_variant(var, records)
                
        return results
```

### 2. Caching Strategy
```python
from functools import lru_cache
import pickle
from pathlib import Path

class CachedEvidenceAggregator:
    """Evidence aggregator with intelligent caching"""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        
    @lru_cache(maxsize=1000)
    def get_gene_evidence(self, gene: str) -> Dict:
        """Cache gene-level evidence that doesn't change per variant"""
        
        cache_file = self.cache_dir / f"gene_{gene}.pkl"
        
        if cache_file.exists():
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        
        # Query fresh data
        evidence = {
            'oncokb': self.oncokb.query_gene_role(gene),
            'civic': self.civic.query_gene_evidence(gene),
            # Other gene-level queries
        }
        
        # Cache for future use
        with open(cache_file, 'wb') as f:
            pickle.dump(evidence, f)
            
        return evidence
```

## Testing Strategy

### Unit Tests for Each KB
```python
import pytest

class TestClinVarQuerier:
    
    def test_pathogenic_variant_query(self):
        querier = ClinVarQuerier("test_clinvar.vcf.gz")
        result = querier.query_variant("17", 43094692, "G", "A")  # BRCA1 pathogenic
        
        assert result is not None
        assert "Pathogenic" in result['clinical_significance']
        assert result['vicc_points'] > 0
        
    def test_benign_variant_query(self):
        querier = ClinVarQuerier("test_clinvar.vcf.gz")
        result = querier.query_variant("17", 43000000, "G", "A")  # Benign variant
        
        assert result is not None
        assert "Benign" in result['clinical_significance']
        assert result['vicc_points'] < 0
        
    def test_absent_variant_query(self):
        querier = ClinVarQuerier("test_clinvar.vcf.gz")
        result = querier.query_variant("1", 1, "G", "A")  # Non-existent
        
        assert result is None
```

This implementation guide provides the concrete technical patterns needed to build our annotation workflow with optimal performance and maintainability.