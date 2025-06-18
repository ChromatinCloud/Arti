# Streamlined API Routes - Phase 3B Sprint 1

**Date**: 2025-06-18  
**API Version**: v1  
**Base URL**: `https://api.annotation-engine.com/api/v1`  

## 🎯 **Realistic Clinical Workflow Focus**

Reduced from 90+ routes to ~30 essential routes that match real clinical usage patterns.

---

## 🔐 **Authentication** (5 routes)
```
POST   /auth/login                    # User authentication
POST   /auth/logout                   # User logout  
POST   /auth/refresh                  # Refresh JWT token
GET    /auth/me                       # Current user info
PUT    /auth/password                 # Change password
```

---

## 🧬 **Variant Processing** (6 routes)
*One comprehensive route per major function - no micro-endpoints*

```
# Core annotation workflow
POST   /variants/annotate             # Submit VCF → get complete annotation bundle
GET    /variants/{variant_id}         # Get complete variant data (VEP + predictions + frequencies + clinical)
POST   /variants/batch                # Batch process multiple VCFs

# Job management  
GET    /jobs/{job_id}                 # Check annotation job status
POST   /jobs/{job_id}/retry           # Retry failed job
DELETE /jobs/{job_id}                 # Cancel job
```

**Single `/variants/{variant_id}` response includes:**
- VEP consequences
- All functional predictions (AlphaMissense, PrimateAI, SpliceAI, REVEL, etc.)
- Population frequencies (gnomAD, ExAC, etc.)
- Conservation scores (GERP, PhyloP, etc.)
- Clinical evidence (ClinVar, OncoKB, CIViC)
- Hotspot annotations

---

## 🏥 **Clinical Workflow** (8 routes)
*Focused on case-level operations*

```
# Case management
GET    /cases                         # List cases (with filtering)
POST   /cases                         # Create new case
GET    /cases/{case_uid}              # Get complete case (variants + interpretations + history)
PUT    /cases/{case_uid}              # Update case
DELETE /cases/{case_uid}              # Archive case

# Clinical decisions
POST   /cases/{case_uid}/interpret    # Create/update variant interpretations
GET    /cases/{case_uid}/report       # Generate clinical report (PDF/JSON)
POST   /cases/{case_uid}/finalize     # Sign-off and finalize case
```

---

## 📊 **Interpretations & History** (5 routes)
*Combined interpretation management*

```
GET    /interpretations/{interp_id}   # Get interpretation with full history timeline
PUT    /interpretations/{interp_id}   # Update interpretation (auto-tracks history)
GET    /interpretations/{interp_id}/compare/{version1}/{version2}  # Compare versions
POST   /interpretations/{interp_id}/approve  # Approve interpretation
POST   /interpretations/{interp_id}/sign     # Digital signature
```

---

## 🩺 **Clinical Evidence** (4 routes)
*Simplified evidence access*

```
GET    /evidence/{variant_id}         # Get all clinical evidence (ClinVar + therapeutic + literature)
GET    /evidence/sources/status       # Check evidence source freshness
PUT    /evidence/sources/refresh      # Trigger evidence refresh
GET    /therapies/search              # Search therapies by variant/gene
```

---

## 🔍 **Search & Discovery** (3 routes)
*Essential search functionality*

```
GET    /search/variants               # Search variants (gene, position, HGVS)
GET    /search/cases                  # Search cases (patient, date, cancer type)
GET    /search/global                 # Global search across all data
```

---

## 📈 **Analytics & Admin** (4 routes)
*Essential monitoring and admin*

```
GET    /analytics/dashboard           # Dashboard overview (cases, tiers, KB status)
GET    /audit/trail                   # Audit trail (with filtering)
POST   /audit/compliance              # Generate compliance reports
GET    /system/health                 # System health check
```

---

## 👥 **User Management** (3 routes)
*Simplified user ops*

```
GET    /users                         # List users
POST   /users                         # Create user  
PUT    /users/{user_id}               # Update user (including permissions)
```

---

## 📋 **Total: ~38 Essential Routes**

### **Route Categories:**
- **Authentication**: 5 routes
- **Variant Processing**: 6 routes  
- **Clinical Workflow**: 8 routes
- **Interpretations**: 5 routes
- **Clinical Evidence**: 4 routes
- **Search**: 3 routes
- **Analytics/Admin**: 4 routes
- **Users**: 3 routes

---

## 🎯 **Key Design Changes**

### **1. Bundle Everything in Single Responses**
Instead of:
```
GET /variants/{id}/predictions
GET /variants/{id}/consequences  
GET /variants/{id}/frequencies
GET /variants/{id}/conservation
```

We have:
```
GET /variants/{id}  # Returns complete annotation bundle
```

### **2. Case-Centric Workflow**
Clinical users think in terms of cases, not individual variants:
```
GET /cases/{case_uid}  # Complete case with all variants + interpretations
```

### **3. Combined Evidence Access**
Instead of separate ClinVar/OncoKB/CIViC endpoints:
```
GET /evidence/{variant_id}  # All clinical evidence in one response
```

### **4. Automatic History Tracking**
No separate history endpoints - history is tracked automatically:
```
PUT /interpretations/{id}  # Updates interpretation + creates history entry
```

---

## 📝 **Example Response Structure**

### **GET /variants/{variant_id}**
```json
{
  "success": true,
  "data": {
    "variant_id": "7:140753336:A>T",
    "gene": "BRAF",
    "hgvs_p": "p.Val600Glu",
    "consequences": ["missense_variant"],
    
    "functional_predictions": {
      "alphamissense": {"score": 0.95, "prediction": "pathogenic"},
      "revel": {"score": 0.89},
      "sift": {"score": 0.01, "prediction": "deleterious"},
      "spliceai": {"donor_loss": 0.02, "acceptor_gain": 0.01}
    },
    
    "population_frequencies": {
      "gnomad_exomes": {"af": 0.000001},
      "gnomad_genomes": {"af": 0.000002}
    },
    
    "conservation": {
      "gerp": 5.8,
      "phylop": 2.1,
      "phastcons": 0.98
    },
    
    "clinical_evidence": {
      "clinvar": {"significance": "Pathogenic", "stars": 4},
      "therapeutic": [
        {"drug": "Vemurafenib", "evidence_level": "FDA_APPROVED"},
        {"drug": "Dabrafenib", "evidence_level": "FDA_APPROVED"}
      ]
    }
  }
}
```

### **GET /cases/{case_uid}**
```json
{
  "success": true,
  "data": {
    "case_uid": "CASE_001",
    "patient_id": "PATIENT_001",
    "cancer_type": "melanoma",
    "analysis_type": "tumor_only",
    "status": "in_progress",
    
    "variants": [
      {
        "variant_id": "7:140753336:A>T",
        "gene": "BRAF",
        "tier": "Tier IA",
        "interpretation_status": "approved"
      }
    ],
    
    "summary": {
      "total_variants": 45,
      "tier_distribution": {"Tier I": 2, "Tier II": 8, "Tier III": 35},
      "actionable_variants": 2
    }
  }
}
```

---

## ✅ **Benefits of Streamlined Approach**

1. **Realistic Usage**: Matches actual clinical workflows
2. **Fewer Round Trips**: Bundle data in meaningful chunks  
3. **Easier Testing**: 38 routes vs 90+ routes
4. **Better Performance**: Fewer API calls, better caching
5. **Simpler Frontend**: Less state management complexity
6. **Faster Development**: Focus on essential features first

---

**This is much more manageable for Sprint 1!** 🚀