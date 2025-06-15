# Critical Guideline Corrections Needed

## Summary of Issues Found

The codebase has a fundamental misunderstanding about the clinical guidelines being implemented. The documentation incorrectly references:

1. **ACMG/AMP 2015** guidelines for **germline** pathogenicity assessment
2. Evidence criteria codes (BA1, BS1, PM2, PS1, etc.) which are specific to germline variants

However, according to the user and CLAUDE.md, this application should implement:

1. **AMP/ASCO/CAP 2017** guidelines for **somatic** variant interpretation
2. **VICC 2022** guidelines for **somatic** oncogenicity assessment  
3. **OncoKB** therapeutic tiers for **somatic** actionability

All three frameworks are for SOMATIC variants in cancer, NOT germline variants.

## Key Differences

### ACMG/AMP 2015 (Germline) - INCORRECT for this project
- Assesses hereditary disease risk
- Uses 28 evidence criteria (PVS1, PS1-4, PM1-6, PP1-5, BA1, BS1-4, BP1-7)
- Classifies as: Pathogenic, Likely Pathogenic, VUS, Likely Benign, Benign
- For inherited variants in constitutional DNA

### AMP/ASCO/CAP 2017 (Somatic) - CORRECT for this project
- Assesses cancer driver potential
- Uses Tiers I-IV based on clinical actionability
- Tier I: FDA-approved therapy for this cancer type
- Tier II: FDA-approved for different cancer or investigational
- Tier III: Clinical significance unclear
- Tier IV: Benign or likely benign
- For acquired variants in tumor DNA

## Implementation Impact

The current documentation describes implementing ACMG/AMP 2015 criteria, but the code should actually implement:

1. **CancerVar's 12 CBP (Cancer-specific evidence-Based Prioritization) criteria** for AMP 2017
2. **VICC 2022 oncogenicity scoring**
3. **OncoKB therapeutic levels**

## Files Needing Major Revision

1. **docs/ANNOTATION_BLUEPRINT.md** - Section III.B entirely describes wrong guidelines
2. **docs/CLINICAL_GUIDELINES_MAPPING.md** - Maps all 42 KBs to wrong ACMG criteria
3. **README.md** - References wrong ACMG criteria throughout
4. **docs/CONFIGURATION_MANAGEMENT.md** - Likely has similar issues

## Correct References

- CLAUDE.md correctly states "AMP 2017 and VICC 2022"
- TODO.md correctly mentions "12 CancerVar CBP weights"
- cli.py now correctly states "somatic variants following AMP ACMG 2017"

## Next Steps

1. Remove all ACMG/AMP 2015 germline criteria references
2. Replace with AMP/ASCO/CAP 2017 somatic tier definitions
3. Update knowledge base mappings to reflect somatic interpretation
4. Ensure tiering.py implements CancerVar CBP scoring, not ACMG criteria