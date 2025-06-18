# TODO – Next High-Value Tasks

> Last Updated: 2025-01-18

## 🎉 Recently Completed (2025-01-18)
- ✅ **ALL TESTS PASSING**: Fixed 39 failing tests → 0 failures!
- ✅ **CGC/VICC Implementation**: Complete oncogenicity classifier with all 17 criteria
- ✅ **Inter-guideline Evidence**: OncoKB "Oncogenic" → CGC/VICC OS1 mapping
- ✅ **GA4GH Integration**: Comprehensive implementation of VRS, VICC Meta-KB, Phenopackets, VA standard
- ✅ **Clinical Context Extractor**: Cross-guideline mapping and canned text generation
- ✅ **Dependency Injection**: Clean DI pattern throughout test infrastructure
- ✅ **dbNSFP Integration**: Completed (per system status)
- ✅ **Test Suite Refactoring**: All VEP-related tests now properly mocked
- ✅ **Documentation**: Created comprehensive logs for KB mapping and GA4GH implementation

## 🎯 Current Sprint Focus (Phase 2B)

### 1. Input Validation & Patient Context (High Priority)
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

### 2. Workflow Router Implementation
- [ ] Create `src/annotation_engine/workflow_router.py`
  - Define tumor-only vs tumor-normal pathways
  - Set KB priority orders per pathway
  - Configure evidence weight multipliers
  - Handle VAF threshold differences
- [ ] Update evidence_aggregator.py to use workflow context
- [ ] Update tiering.py for pathway-specific rules

### 3. Performance & Production Readiness
- [ ] Add memory usage tracking
  - Log peak memory during annotation
  - Identify memory bottlenecks
- [ ] Document plugin data sources
  - Create PLUGIN_DATA_SOURCES.md
  - Include download links and versions
- [ ] Production deployment configuration
  - Docker optimization for GA4GH modules
  - API endpoint setup for service-info

### 4. Integration Testing with GA4GH
- [ ] End-to-end test: VCF → VRS → VICC → Phenopacket
- [ ] Validate VRS IDs against known variants
- [ ] Test VICC concordance analysis
- [ ] Verify Phenopacket schema compliance

## 💡 Quick Wins (< 30 minutes each)

1. **Update CLI for GA4GH formats**
   - Add `--output-format phenopacket`
   - Add `--vrs-normalize` flag
   - Add `--export-va` option

2. **Create GA4GH usage examples**
   - Example commands in README
   - Sample phenopacket output
   - VRS ID generation demo

3. **Add concordance metrics to output**
   - Show when multiple DBs agree
   - Display confidence based on concordance
   - Flag discordant interpretations

## 🔧 Technical Debt

1. **Configuration Management**
   - Move GA4GH endpoints to config
   - Add VICC API key support
   - Configurable VRS normalization

2. **Error Handling**
   - Better VICC query failure messages
   - VRS normalization error recovery
   - Phenopacket validation errors

3. **Caching Strategy**
   - Cache VRS IDs for variants
   - Cache VICC query results
   - Implement TTL for external queries

## 🚀 Next Steps Priority Order

1. **Input validation** - Critical for production use
2. **Workflow router** - Enables tumor-normal support
3. **CLI updates** - Expose GA4GH functionality
4. **Integration tests** - Validate full pipeline
5. **Performance optimization** - For production scale

## 📊 Current System Status

- **Test Suite**: ✅ All tests passing (0 failures)
- **CGC/VICC**: ✅ Fully implemented with cross-DB concordance
- **GA4GH**: ✅ Comprehensive integration complete
- **VEP Plugins**: ✅ 26 plugins configured and validated
- **Knowledge Bases**: ✅ OncoKB, CIViC, ClinVar, COSMIC integrated
- **Documentation**: ✅ Extensive logs and implementation guides

## 🎯 Phase 3 Preview (After Current Sprint)

1. **Web API Development**
   - RESTful endpoints for all functionality
   - GA4GH service-info endpoint
   - Batch processing API

2. **Database Backend**
   - PostgreSQL schema for results
   - Variant interpretation history
   - Audit trail for clinical use

3. **Clinical Report Generation**
   - Automated report templates
   - Canned text integration
   - PDF export with interpretations

4. **Real-time KB Updates**
   - Automated OncoKB sync
   - CIViC webhook integration
   - Version tracking for interpretations