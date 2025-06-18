# API Routing Specification - Phase 3B Sprint 1

**Date**: 2025-06-18  
**API Version**: v1  
**Base URL**: `https://api.annotation-engine.com/api/v1`  

## 🗂️ **API Organization Structure**

The API is organized into logical modules that map to clinical workflows and database capabilities from Phase 3A.

---

## 🔐 **Authentication & Authorization**

### **Auth Routes**
```
POST   /auth/login                    # User authentication
POST   /auth/logout                   # User logout
POST   /auth/refresh                  # Refresh JWT token
GET    /auth/me                       # Current user info
PUT    /auth/password                 # Change password
```

### **User Management** 
```
GET    /users                         # List users (admin only)
POST   /users                         # Create user (admin only)
GET    /users/{user_id}               # Get user details
PUT    /users/{user_id}               # Update user
DELETE /users/{user_id}               # Deactivate user (admin only)
GET    /users/{user_id}/permissions   # Get user permissions
PUT    /users/{user_id}/permissions   # Update user permissions (admin only)
```

---

## 🧬 **Core Variant Annotation**

### **Variant Processing** 
*Includes VEP annotation, functional predictions (AlphaMissense, PrimateAI, SpliceAI, REVEL, etc.), population frequencies, and computational scoring*
```
POST   /variants/annotate             # Submit VCF for annotation
POST   /variants/batch                # Batch VCF processing
GET    /variants/{variant_id}         # Get variant details
PUT    /variants/{variant_id}         # Update variant information
DELETE /variants/{variant_id}         # Delete variant (admin only)

# VCF Upload and Processing
POST   /variants/upload               # Upload VCF file
GET    /variants/upload/{job_id}      # Check upload status
POST   /variants/{variant_id}/reanalyze # Trigger re-analysis

# Functional Predictions & Annotations
GET    /variants/{variant_id}/predictions    # Get all functional predictions
GET    /variants/{variant_id}/consequences   # Get VEP consequences
GET    /variants/{variant_id}/frequencies    # Get population frequencies
GET    /variants/{variant_id}/conservation   # Get conservation scores
```

### **Annotation Jobs** 
```
GET    /jobs                          # List annotation jobs
GET    /jobs/{job_id}                 # Get job status and results
DELETE /jobs/{job_id}                 # Cancel/delete job
POST   /jobs/{job_id}/retry           # Retry failed job
```

---

## 🏥 **Clinical Case Management**

### **Patients**
```
GET    /patients                      # List patients (with filtering)
POST   /patients                      # Create patient record
GET    /patients/{patient_id}         # Get patient details
PUT    /patients/{patient_id}         # Update patient information
DELETE /patients/{patient_id}         # Archive patient (admin only)
GET    /patients/{patient_id}/cases   # Get patient's cases
```

### **Clinical Cases**
```
GET    /cases                         # List all cases (with filtering)
POST   /cases                         # Create new case
GET    /cases/{case_uid}              # Get case details
PUT    /cases/{case_uid}              # Update case information
DELETE /cases/{case_uid}              # Archive case (admin only)

# Case-specific variant data
GET    /cases/{case_uid}/variants     # Get all variants for case
GET    /cases/{case_uid}/summary      # Get case summary with tier distribution
GET    /cases/{case_uid}/report       # Generate case report (PDF/JSON)
POST   /cases/{case_uid}/finalize     # Finalize case for clinical use
```

---

## 📊 **Variant Interpretations**

### **Interpretation Management**
```
GET    /interpretations               # List interpretations (with filtering)
POST   /interpretations               # Create new interpretation
GET    /interpretations/{interp_id}   # Get interpretation details
PUT    /interpretations/{interp_id}   # Update interpretation
DELETE /interpretations/{interp_id}   # Delete interpretation (admin only)

# Interpretation workflow
POST   /interpretations/{interp_id}/approve    # Approve interpretation
POST   /interpretations/{interp_id}/reject     # Reject interpretation
POST   /interpretations/{interp_id}/sign       # Digitally sign interpretation
GET    /interpretations/{interp_id}/pdf        # Export interpretation as PDF
```

### **Tier Assignments**
```
GET    /interpretations/{interp_id}/tiers      # Get tier assignments
PUT    /interpretations/{interp_id}/tiers      # Update tier assignments
GET    /interpretations/{interp_id}/evidence   # Get supporting evidence
PUT    /interpretations/{interp_id}/evidence   # Update evidence
```

---

## 📚 **History & Audit Tracking**

### **Interpretation History** (leverages Phase 3A history_tracking.py)
```
GET    /interpretations/{interp_id}/history    # Get interpretation timeline
GET    /interpretations/{interp_id}/versions   # List all versions
GET    /interpretations/{interp_id}/versions/{version}  # Get specific version
GET    /interpretations/{interp_id}/compare/{v1}/{v2}   # Compare versions
POST   /interpretations/{interp_id}/revert/{version}    # Revert to version
```

### **Audit Trail** (leverages Phase 3A audit_trail.py)
```
GET    /audit/events                  # Get audit events (with filtering)
GET    /audit/events/{event_uuid}     # Get specific audit event
GET    /audit/users/{user_id}         # Get user activity audit
GET    /audit/cases/{case_uid}        # Get case-specific audit trail
GET    /audit/compliance/{framework}  # Get compliance report (HIPAA/CLIA/CAP)
POST   /audit/reports                 # Generate compliance reports
```

---

## 🩺 **Clinical Evidence Integration**

### **Evidence Sources Management** (leverages Phase 3A expanded_models.py)
```
GET    /evidence/sources/status       # Get all evidence source status and versions
GET    /evidence/sources/{source}/status    # Get specific source status
PUT    /evidence/sources/{source}/refresh   # Trigger source refresh
GET    /evidence/sources/versions     # Get historical source versions
```

### **Clinical Significance Data**
```
GET    /evidence/clinical/variants/{variant_id}    # Get clinical significance annotations
GET    /evidence/clinical/search                   # Search clinical variants
GET    /evidence/clinical/conflicts/{variant_id}   # Get interpretation conflicts
```

### **Therapeutic Evidence**
```
GET    /evidence/therapeutic/genes/{gene}          # Get therapeutic gene information
GET    /evidence/therapeutic/variants/{variant_id} # Get therapeutic annotations
GET    /evidence/therapeutic/treatments/{variant_id} # Get treatment annotations
GET    /evidence/therapeutic/levels/{variant_id}   # Get evidence levels
```

### **Literature & Citations**
```
GET    /literature/citations          # Search literature citations
GET    /literature/pmid/{pmid}        # Get citation by PMID
GET    /literature/sources            # Get citation sources with reliability
POST   /literature/citations          # Add new citation
```

### **Therapy Information**
```
GET    /therapies                     # List therapies (with filtering)
GET    /therapies/{therapy_id}        # Get therapy details
GET    /therapies/search              # Search therapies by name/target
GET    /therapies/{therapy_id}/interactions  # Get drug interactions
```

---

## ⚡ **Caching & Performance** (leverages Phase 3A caching_layer.py)

### **Cache Management**
```
GET    /cache/stats                   # Get cache performance statistics
GET    /cache/{kb_source}/stats       # Get KB-specific cache stats
DELETE /cache/{kb_source}             # Clear KB cache (admin only)
DELETE /cache/expired                 # Clear expired cache entries
POST   /cache/warm                    # Warm cache with common queries
```

### **System Performance**
```
GET    /system/health                 # Health check endpoint
GET    /system/metrics                # System performance metrics
GET    /system/version                # API and software versions
```

---

## 📄 **Reporting & Export**

### **Report Generation**
```
GET    /reports/cases/{case_uid}      # Generate case report
GET    /reports/variants/{variant_id} # Generate variant report
POST   /reports/custom                # Generate custom report
GET    /reports/{report_id}           # Get generated report
GET    /reports/{report_id}/download  # Download report file
```

### **Data Export**
```
POST   /export/variants               # Export variant data (CSV/JSON)
POST   /export/cases                  # Export case data
POST   /export/audit                  # Export audit trail
GET    /export/{export_id}            # Get export job status
GET    /export/{export_id}/download   # Download export file
```

---

## 🔍 **Search & Discovery**

### **Global Search**
```
GET    /search                        # Global search across all entities
GET    /search/variants               # Search variants by gene/position/HGVS
GET    /search/cases                  # Search cases by patient/date/cancer_type
GET    /search/interpretations        # Search interpretations by tier/gene
```

### **Advanced Filtering**
```
GET    /filter/variants               # Advanced variant filtering
GET    /filter/cases                  # Advanced case filtering
POST   /filter/save                   # Save filter configuration
GET    /filter/saved                  # Get saved filters
```

---

## 📊 **Analytics & Statistics**

### **Dashboard Data**
```
GET    /analytics/overview            # Dashboard overview statistics
GET    /analytics/tiers               # Tier distribution analytics
GET    /analytics/genes               # Most frequently annotated genes
GET    /analytics/kb_coverage         # Knowledge base coverage metrics
GET    /analytics/user_activity       # User activity statistics
```

### **Quality Metrics**
```
GET    /quality/completeness          # Annotation completeness metrics
GET    /quality/confidence            # Confidence score distributions
GET    /quality/agreement             # Inter-annotator agreement
```

---

## 🛠️ **Administrative Functions**

### **System Administration**
```
GET    /admin/users/active            # Get active user sessions
POST   /admin/maintenance/start       # Start maintenance mode
POST   /admin/maintenance/stop        # Stop maintenance mode
GET    /admin/logs                    # Get system logs
GET    /admin/database/stats          # Database performance statistics
```

### **Configuration Management**
```
GET    /config/settings               # Get system configuration
PUT    /config/settings               # Update system configuration
GET    /config/thresholds             # Get tier thresholds
PUT    /config/thresholds             # Update tier thresholds
```

---

## 📋 **API Design Principles**

### **URL Structure**
- **Resource-based**: URLs represent resources, not actions
- **Hierarchical**: Nested resources follow logical relationships
- **Consistent**: Similar patterns across all endpoints
- **Versioned**: API version in URL path (`/api/v1/`)

### **HTTP Methods**
- **GET**: Retrieve data (safe, idempotent)
- **POST**: Create new resources or complex operations
- **PUT**: Update existing resources (idempotent)
- **DELETE**: Remove resources
- **PATCH**: Partial updates (future enhancement)

### **Response Format**
```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "timestamp": "2025-06-18T10:30:00Z",
    "version": "1.0.0",
    "request_id": "req_123456"
  }
}
```

### **Error Handling**
```json
{
  "success": false,
  "error": {
    "code": "VARIANT_NOT_FOUND",
    "message": "Variant with ID '123' not found",
    "details": { ... }
  },
  "meta": {
    "timestamp": "2025-06-18T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

---

## 🔒 **Security Considerations**

### **Authentication**
- **JWT tokens** with role-based access control
- **Token expiration** and refresh mechanisms
- **Multi-factor authentication** for admin users

### **Authorization Levels**
- **Public**: System health, API documentation
- **User**: Read access to own cases and interpretations
- **Clinician**: Full clinical workflow access
- **Admin**: User management, system configuration
- **Super Admin**: All operations including data deletion

### **Data Protection**
- **HTTPS only** for all communications
- **Request rate limiting** by user and IP
- **Input validation** and SQL injection prevention
- **Audit logging** for all data access

---

## 📈 **Performance Requirements**

### **Response Time Targets**
- **Simple queries**: < 100ms
- **Complex queries**: < 500ms
- **File uploads**: < 30 seconds
- **Report generation**: < 5 minutes

### **Scalability**
- **Concurrent users**: 100+ simultaneous
- **Database connections**: Connection pooling
- **Caching**: Redis for frequently accessed data
- **Background jobs**: Celery for long-running tasks

---

---

## 🎯 **Updated API Organization Summary**

### **📊 Complete Clinical Workflow Coverage**
- **Patient/Case Management**: Full CRUD operations
- **Variant Processing**: VCF upload → annotation → interpretation (includes VEP, AlphaMissense, PrimateAI, SpliceAI, REVEL, conservation scores, population frequencies)
- **History Tracking**: Leverages our Phase 3A history system
- **Audit Trail**: Complete regulatory compliance

### **🩺 Clinical Evidence Integration** 
- **Clinical Significance**: Access to clinical variant databases and annotations
- **Therapeutic Evidence**: Treatment annotations and evidence levels  
- **Literature**: Citation management with reliability tiers
- **Therapies**: Drug information and interactions

### **⚡ Performance & Monitoring**
- **Caching APIs**: Manage our intelligent caching layer
- **System Health**: Performance metrics and monitoring
- **Analytics**: Dashboard data and quality metrics

### **🔒 Enterprise Security**
- **Role-based access**: User/Clinician/Admin/Super Admin levels
- **Comprehensive audit**: Every API call logged for compliance
- **Data protection**: HTTPS, rate limiting, input validation

**Total: 85+ endpoints across 12 logical modules**

---

**Next Step: Let's implement the FastAPI backend with these routes!** 🚀