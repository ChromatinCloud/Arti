# TODO – Next High-Value Tasks

## 🎯 Immediate Priorities

### 1. Fix Test Suite (Unblocks Everything)
- [ ] Fix 36 failing VEP-related tests
- [ ] Update test paths for new plugin locations
- [ ] Add tests for AlphaMissense/GERP fallback modules
- [ ] Validate plugin_fallbacks.py integration

### 2. Complete dbNSFP Integration
- [ ] Check if dbNSFP5.1a download completed
- [ ] Update VEP runner to use new dbNSFP if available
- [ ] Enable ClinPred, dbscSNV, VARITY plugins
- [ ] Run full plugin validation

### 3. Input Validation Module
- [ ] Create `src/annotation_engine/input_validator.py`
  - VCF format validation (valid headers, required fields)
  - Multi-sample detection logic
  - Chromosome naming standardization (chr1 vs 1)
  - Sample pairing for tumor-normal
- [ ] Create `src/annotation_engine/patient_context.py`
  - Patient UID validation
  - OncoTree code lookup and validation
  - Case metadata management
  - Sample type inference

### 4. Workflow Router Implementation
- [ ] Create `src/annotation_engine/workflow_router.py`
  - Define tumor-only vs tumor-normal pathways
  - Set KB priority orders per pathway
  - Configure evidence weight multipliers
  - Handle VAF threshold differences
- [ ] Update evidence_aggregator.py to use workflow context
- [ ] Update tiering.py for pathway-specific rules

### 5. Performance Optimization
- [ ] Profile VEP execution with 26 plugins
- [ ] Implement plugin data pre-loading
- [ ] Add progress bars for long operations
- [ ] Cache warming strategy for common genes

## 💡 Quick Wins (< 1 hour each)

1. **Add progress logging to VEP runner**
   - Users need feedback during 77-second runs
   - Simple tqdm integration

2. **Create plugin status command**
   - `annotation-engine --check-plugins`
   - Shows which plugins are ready/missing

3. **Add memory usage tracking**
   - Log peak memory during annotation
   - Identify memory bottlenecks

4. **Document plugin data sources**
   - Create PLUGIN_DATA_SOURCES.md
   - Include download links and versions

## 🔧 Technical Debt

1. **Error Messages**
   - VEP failures need clearer diagnostics
   - Add suggestions for common issues
   - Structured error codes

2. **Configuration**
   - Move hardcoded paths to config.yaml
   - Environment variable support
   - Plugin enable/disable flags

3. **Logging**
   - Structured JSON logging option
   - Separate log levels per module
   - Performance metrics collection

## 🚀 Next Session Starting Points

```bash
# Check test status
poetry run pytest -x  # Stop on first failure

# Validate current setup
poetry run python scripts/validate_knowledge_bases.py

# Check dbNSFP download
ls -lh .refs/functional_predictions/plugin_data/pathogenicity/dbNSFP5.1a*

# Test with all plugins
poetry run annotation-engine --test --verbose
```