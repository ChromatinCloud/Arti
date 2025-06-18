# Tier Assignment Implementation: Reality Check

## Current State vs. Original Vision

### What Was Promised (Original Design)
- **YAML-driven rules** for easy guideline updates without code changes
- **Configuration files** defining tier assignment logic
- **Modular rules engine** reading from YAML files
- **12 CBP criteria** from CancerVar implemented as configurable rules

### What Was Actually Built
- **All rules hardcoded in Python** classes and methods
- **Only 2 YAML files** with basic thresholds (TMB, MSI, HRD)
- **No rule engine** - just direct Python implementation
- **Strategy Pattern** for evidence scoring (good design, but not configurable)

### Configuration Files That Exist
```
config/
├── thresholds.yaml     # 4 lines: TMB, MSI, HRD thresholds
└── tumor_drivers.yaml  # Simple gene-to-tumor mappings
```

## Industry Comparison

### How Other Tools Actually Work

| Tool | Configuration Approach | Reality |
|------|----------------------|---------|
| **PCGR** | Started with TOML, abandoned it | Now uses CLI parameters only |
| **OncoKB** | No config files | API-based, internal Java rules |
| **CancerVar** | Uses .ini files | Most logic still in Python |
| **CGI** | No user config | REST API with hidden logic |
| **cBioPortal** | Java properties | Just displays pre-calculated tiers |

**Key Finding**: Nobody uses YAML rule engines for tier assignment!

## Why The Industry Moved Away From Config-Based Rules

1. **Regulatory Liability**: Clinical tier assignment has legal implications
2. **Complexity**: Guidelines are nuanced and context-dependent
3. **Validation**: Hard to verify YAML rules meet clinical standards
4. **Performance**: Rule engines slow for large variant sets
5. **User Reality**: Clinicians prefer GUIs over editing YAML

## Current Implementation Analysis

### What Works Well
- Clean Python implementation with good patterns
- Dependency injection for testing
- Evidence aggregation from multiple sources
- Working tier assignment (though hardcoded)

### What's Missing
1. **CGC/VICC 2022 Oncogenicity Classification**
   - Mentioned in docs but not implemented
   - Critical for modern variant interpretation

2. **Sequential Two-Layer Approach**
   - Industry best practice: Oncogenicity → Clinical Actionability
   - Current implementation mixes biological and clinical evidence

3. **Transparent Evidence Trail**
   - Need complete audit trail for clinical use
   - Current JSON output lacks detailed evidence tracking

## Recommended Path Forward

### Option 1: Embrace Current Approach (Minimal Change)
- Keep hardcoded Python rules
- Add missing CGC/VICC 2022 implementation
- Improve evidence tracking in output
- Document that this follows PCGR pattern (abandoned config files)

### Option 2: Implement Two-Layer Architecture (Best Practice)
- Layer 1: CGC/VICC oncogenicity (new implementation)
- Layer 2: AMP/ASCO/CAP actionability (refactor existing)
- Keep rules in Python (industry standard)
- Add comprehensive JSON output with full evidence trail

### Option 3: Hybrid Approach (Pragmatic)
- Keep core rules in Python
- Add YAML for thresholds and mappings only
- Implement CGC/VICC as new module
- Focus on output transparency over input configurability

## The Reality of Clinical Variant Interpretation

The field has learned that:
- **APIs > Config Files** for tier assignment
- **Validated Code > Flexible Rules** for clinical safety
- **Transparency in Output > Flexibility in Input**
- **Sequential Classification > Merged Frameworks**

## Conclusion

The original vision of YAML-based rules was forward-thinking but impractical. The current Python-based implementation aligns with industry standards. The main gap is missing CGC/VICC oncogenicity classification and the lack of a clear two-layer architecture.

**Recommendation**: Implement Option 2 (Two-Layer Architecture) while keeping rules in Python code. This provides the best balance of clinical validity, maintainability, and industry alignment.