# TODO – Next High-Value Tasks

> Last Updated: 2025-06-18

## 🎉 Recently Completed (2025-06-18)
- ✅ **COMPREHENSIVE CANNED TEXT SYSTEM**: All 8 text types implemented with 6,632 lines of code
  - General Gene Info, Gene Dx Interpretation, General Variant Info, Variant Dx Interpretation
  - Incidental/Secondary Findings, Chromosomal Alteration Interpretation, Pertinent Negatives, Biomarkers
  - Sophisticated template system with confidence scoring and evidence synthesis
- ✅ **ENHANCED PERTINENT NEGATIVES**: Beyond gene mutations to include:
  - Chromosomal alterations (+7/-10 in GBM, 1p/19q codeletion)
  - Methylation status (MGMT, TERT promoter, MLH1 promoter)
  - Specific variants (EGFRvIII, TERT promoter mutations)
  - Amplifications/deletions, fusion events, expression markers, molecular signatures
  - Cancer-specific catalogs for GBM, colorectal, lung adenocarcinoma, breast cancer
- ✅ **DETERMINISTIC NARRATIVE GENERATOR**: Professional narrative weaving
  - 5-tier source reliability system (FDA/Guidelines > Expert > Community > Computational)
  - Reliable citation management with automatic numbering and comprehensive references
  - Evidence clustering and synthesis by conclusion with proper transitions
  - Quality assurance with confidence scoring and graceful degradation
- ✅ **GA4GH CLINICAL CONTEXT EXTENSION**: Enhanced existing extractor
  - Therapy class mapping and cancer type hierarchies
  - Cross-guideline evidence mapping (OncoKB → CGC/VICC)
  - Ontology term extraction and clinical scenario building
- ✅ **COMPREHENSIVE TESTING**: Complete validation and examples
  - Unit tests for all text generators and narrative components
  - Integration tests with real-world examples (BRAF V600E, TP53, BRCA1, etc.)
  - Edge case handling and error recovery testing
- ✅ **IMPLEMENTATION DOCUMENTATION**: Complete technical documentation
  - Detailed implementation log (canned_text_implementation_complete_20250618.log)
  - Comprehensive examples and usage demonstrations
  - Integration guides and API documentation

## 🎯 Current Sprint Focus (Phase 2C - Production Integration)

### 1. Canned Text System Integration (High Priority)
- [ ] Integrate comprehensive canned text generator with tiering engine
  - Update existing CannedTextGenerator interface implementation
  - Replace basic text generation with enhanced narrative system
  - Ensure backward compatibility with existing workflows
- [ ] Add canned text configuration options to CLI
  - `--enable-enhanced-text` flag for new system
  - `--text-confidence-threshold` for quality control
  - `--citation-style` for reference formatting options
- [ ] Performance optimization for text generation
  - Template caching for repeated evidence patterns
  - Parallel text generation for multiple variants
  - Memory optimization for large evidence sets

### 2. Input Validation & Patient Context (Medium Priority)
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

### 3. Workflow Router Implementation
- [ ] Create `src/annotation_engine/workflow_router.py`
  - Define tumor-only vs tumor-normal pathways
  - Set KB priority orders per pathway
  - Configure evidence weight multipliers
  - Handle VAF threshold differences
- [ ] Update evidence_aggregator.py to use workflow context
- [ ] Update tiering.py for pathway-specific rules

### 4. Performance & Production Readiness
- [ ] Add memory usage tracking
  - Log peak memory during annotation
  - Identify memory bottlenecks
- [ ] Document plugin data sources
  - Create PLUGIN_DATA_SOURCES.md
  - Include download links and versions
- [ ] Production deployment configuration
  - Docker optimization for GA4GH modules
  - API endpoint setup for service-info

### 5. Integration Testing with Canned Text System
- [ ] End-to-end test: VCF → Evidence → Canned Text → Report
- [ ] Validate citation accuracy and completeness
- [ ] Test narrative quality across different evidence combinations
- [ ] Verify confidence scoring and graceful degradation
- [ ] Test cancer-specific pertinent negatives generation

### 6. Integration Testing with GA4GH
- [ ] End-to-end test: VCF → VRS → VICC → Phenopacket
- [ ] Validate VRS IDs against known variants
- [ ] Test VICC concordance analysis
- [ ] Verify Phenopacket schema compliance

## 💡 Quick Wins (< 30 minutes each)

1. **Update CLI for enhanced canned text**
   - Add `--text-style` option (clinical, research, brief)
   - Add `--include-citations` flag for reference control
   - Add `--pertinent-negatives-scope` for negative finding types

2. **Create canned text usage examples**
   - Example commands with enhanced text generation
   - Sample outputs for each text type
   - Citation formatting demonstrations

3. **Add text quality metrics to output**
   - Show confidence scores for generated text
   - Display evidence completeness indicators
   - Flag low-confidence or incomplete narratives

4. **Update CLI for GA4GH formats**
   - Add `--output-format phenopacket`
   - Add `--vrs-normalize` flag
   - Add `--export-va` option

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
   - Cache generated text templates and narratives
   - Implement TTL for external queries

4. **Text Generation Optimization**
   - Template compilation and caching
   - Evidence clustering optimization
   - Citation registry performance
   - Memory usage optimization for large evidence sets

## 🚀 Next Steps Priority Order

1. **Canned text integration** - Complete system integration
2. **Input validation** - Critical for production use
3. **Workflow router** - Enables tumor-normal support
4. **CLI updates** - Expose enhanced text and GA4GH functionality
5. **Integration tests** - Validate full pipeline including text generation
6. **Performance optimization** - For production scale

## 📊 Current System Status

- **Test Suite**: ✅ All tests passing (0 failures)
- **CGC/VICC**: ✅ Fully implemented with cross-DB concordance
- **GA4GH**: ✅ Comprehensive integration complete
- **VEP Plugins**: ✅ 26 plugins configured and validated
- **Knowledge Bases**: ✅ OncoKB, CIViC, ClinVar, COSMIC integrated
- **Documentation**: ✅ Extensive logs and implementation guides
- **Canned Text System**: ✅ All 8 text types with enhanced narratives and citations

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
   - Automated report templates with enhanced canned text
   - PDF export with professional narratives and citations
   - Customizable report formats and styling

4. **Real-time KB Updates**
   - Automated OncoKB sync
   - CIViC webhook integration
   - Version tracking for interpretations