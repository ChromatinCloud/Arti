# VEP Plugin vs. Standalone KB Analysis

**Date:** June 16, 2025  
**Purpose:** Determine optimal approach for using our knowledge bases in the annotation workflow

## Executive Summary

**Recommendation:** Use hybrid approach - VEP plugins for complex functional predictions, direct KB access for clinical evidence and simple lookups.

## Our Knowledge Bases vs. VEP Plugins

### Knowledge Bases That ARE VEP Plugins

#### High-Evidence Functional Predictors
| KB/Plugin | Current Location | VEP Plugin | Size | Usage Pattern | Recommendation |
|-----------|------------------|------------|------|---------------|----------------|
| **AlphaMissense** | `functional_predictions/protein_impact/` | ✅ Yes | 1.1GB | Position lookup | **Use VEP Plugin** |
| **dbNSFP** | Missing/Empty | ✅ Yes | ~15GB | Multi-column lookup | **Use VEP Plugin** |
| **REVEL** | `functional_predictions/pathogenicity/` | ✅ Yes | ~1GB | Position lookup | **Use VEP Plugin** |
| **PrimateAI** | `functional_predictions/protein_impact/` | ✅ Yes | 868MB | Position lookup | **Use VEP Plugin** |
| **SpliceAI** | `functional_predictions/splicing/` | ✅ Yes | Large | Splice logic | **Use VEP Plugin** |

#### Moderate-Evidence Predictors  
| KB/Plugin | Current Location | VEP Plugin | Complexity | Recommendation |
|-----------|------------------|------------|------------|----------------|
| **BayesDel** | `functional_predictions/pathogenicity/` | ✅ Yes | Low | **Use VEP Plugin** |
| **ClinPred** | `functional_predictions/pathogenicity/` | ✅ Yes | Low | **Use VEP Plugin** |
| **FATHMM** | Missing | ✅ Yes | Medium | **Use VEP Plugin** |
| **Conservation** | `functional_predictions/conservation/` | ✅ Yes | Medium (BigWig) | **Use VEP Plugin** |
| **LoFtool** | `functional_predictions/gene_constraint/` | ✅ Yes | Low | **Use VEP Plugin** |

### Knowledge Bases That ARE NOT VEP Plugins

#### Clinical Evidence (High Priority for Direct Access)
| KB | Current Location | Size | Usage Pattern | Recommendation |
|----|------------------|------|---------------|----------------|
| **ClinVar** | `clinical_evidence/clinvar/` | 350MB | Position + clinical significance | **Direct Access** |
| **CIViC** | `clinical_evidence/civic/` | 15MB | Gene + variant evidence | **Direct Access** |
| **OncoKB** | `clinical_evidence/oncokb/` | 1MB | Gene lists + actionability | **Direct Access** |
| **Cancer Hotspots** | `cancer_signatures/hotspots/` | 5MB | Position-based hotspots | **Direct Access** |

#### Population & Context Data
| KB | Current Location | Usage Pattern | Recommendation |
|----|------------------|---------------|----------------|
| **gnomAD** | `population_frequencies/gnomad/` | Population filtering | **Direct Access** |
| **COSMIC CGC** | `cancer_signatures/cosmic/` | Gene classification | **Direct Access** |
| **OncoVI Hotspots** | `cancer_signatures/hotspots/` | Position-based evidence | **Direct Access** |

## Analysis by Workflow Component

### 1. VEP Annotation Phase
**Approach:** Use VEP with functional prediction plugins
**Plugins to Enable:**
- dbNSFP (comprehensive functional scores)
- AlphaMissense (missense pathogenicity)
- SpliceAI (splice impact)
- REVEL (ensemble scores)
- Conservation (GERP/PhyloP)

**Rationale:**
- VEP handles complex tabix indexing and BigWig parsing
- Standardized output format
- Efficient batch processing
- Complex consequence-dependent logic

### 2. Evidence Aggregation Phase  
**Approach:** Direct KB access after VEP
**Knowledge Bases to Query Directly:**
- ClinVar → Clinical significance
- CIViC → Therapeutic evidence  
- OncoKB → Actionability levels
- Cancer Hotspots → Recurrence evidence
- gnomAD → Population frequencies

**Rationale:**
- Clinical evidence requires custom logic not available in VEP plugins
- Need flexibility for AMP/VICC scoring algorithms
- Easier to implement custom filtering and weighting
- Better control over evidence aggregation workflow

### 3. Tier Assignment Phase
**Approach:** Direct access to processed evidence
**Data Sources:**
- VEP plugin results (functional scores)
- Aggregated clinical evidence
- Population frequency data
- Hotspot evidence

## Implementation Strategy

### Phase 1: Hybrid Approach Implementation

#### VEP Configuration
```bash
vep \
  --plugin dbNSFP,/path/to/dbNSFP5.1.gz,SIFT_score,Polyphen2_HDIV_score,CADD_phred,REVEL_score \
  --plugin AlphaMissense,/path/to/AlphaMissense_hg38.tsv.gz \
  --plugin SpliceAI,/path/to/spliceai_hg38.vcf.gz \
  --plugin Conservation,/path/to/gerp_scores.wig \
  --plugin REVEL,/path/to/revel_scores.tsv.gz
```

#### Evidence Aggregator Updates
- Parse VEP JSON for functional scores
- Query clinical KBs directly with custom logic
- Combine evidence types for tier assignment

### Storage Optimization

#### Keep Full Files (VEP Plugins)
- dbNSFP: ~15GB (comprehensive)
- AlphaMissense: 1.1GB (all missense)
- SpliceAI: Large (all splice sites)
- REVEL: ~1GB (all missense)

#### Potential for Slicing (Direct Access KBs)
- ClinVar: Keep pathogenic/likely pathogenic only (~20% reduction)
- gnomAD: Could filter to rare variants (AF < 1%) for somatic analysis
- Cancer Hotspots: Keep as-is (already curated)

## Benefits of Hybrid Approach

### VEP Plugin Advantages
1. **Efficiency:** Tabix indexing for large files
2. **Standardization:** Consistent output format
3. **Maintenance:** Plugin updates handle format changes
4. **Performance:** Optimized for batch processing
5. **Complex Logic:** Handles splice regions, consequences

### Direct KB Access Advantages  
1. **Flexibility:** Custom evidence weighting
2. **Clinical Logic:** AMP/VICC scoring algorithms
3. **Integration:** Better workflow control
4. **Debugging:** Easier to trace evidence sources
5. **Customization:** Institution-specific filtering

## Resource Requirements

### Disk Space (Estimated)
- **VEP Plugins:** ~20GB (dbNSFP + others)
- **Direct KBs:** ~2GB (clinical evidence)
- **VEP Cache:** ~15GB (offline annotation)
- **Total:** ~37GB

### Processing Time
- **VEP Phase:** 30-60 minutes for whole genome
- **Evidence Aggregation:** 5-10 minutes
- **Tier Assignment:** 1-2 minutes

## Next Steps

1. **Download Missing Plugin Data:** Complete dbNSFP, REVEL, full SpliceAI
2. **Implement VEP Runner:** Use selected plugins only
3. **Update Evidence Aggregator:** Parse VEP JSON + query KBs directly
4. **Test Hybrid Workflow:** Validate with example VCFs
5. **Optimize Performance:** Profile and tune as needed

This hybrid approach maximizes the strengths of both VEP plugins (for functional prediction) and direct KB access (for clinical evidence), while maintaining flexibility for our specific annotation workflow requirements.