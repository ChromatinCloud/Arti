import React, { useState, useEffect } from 'react';
import { useFilteringStore } from '../store/filteringStore';
import { MetadataBanner } from './MetadataBanner';
import { ModeSelector } from './ModeSelector';
import { FilterPanel } from './FilterPanel';
import { VariantCounter } from './VariantCounter';
import { ArtiHandoff } from './ArtiHandoff';
import { getVariantCount } from '../services/filteringAPI';
import { SampleMetadata } from '../types/filtering.types';

export const TechFilteringPage: React.FC = () => {
  const { 
    mode, 
    inputVcf, 
    filterGroups, 
    isProcessing, 
    error,
    outputVcf,
    metadata,
    applyFilters, 
    resetFilters,
    exportVcf,
    setInputVcf,
    setMetadata
  } = useFilteringStore();
  
  const [showArtiHandoff, setShowArtiHandoff] = useState(false);
  
  // Get metadata from URL params or parent app
  useEffect(() => {
    // Check URL parameters (if passed from parent app)
    const urlParams = new URLSearchParams(window.location.search);
    const newMetadata: SampleMetadata = {
      patientUID: urlParams.get('patientUID') || undefined,
      caseID: urlParams.get('caseID') || undefined,
      oncotreeCode: urlParams.get('oncotreeCode') || undefined,
      tumorPurity: urlParams.get('tumorPurity') ? parseFloat(urlParams.get('tumorPurity')!) : undefined,
      specimenType: urlParams.get('specimenType') || undefined
    };
    
    // Check if parent window passed data via postMessage
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === 'SAMPLE_METADATA') {
        setMetadata(event.data.metadata);
      }
    };
    
    window.addEventListener('message', handleMessage);
    
    // Set metadata from URL if available
    if (Object.values(newMetadata).some(v => v !== undefined)) {
      setMetadata(newMetadata);
    }
    
    return () => window.removeEventListener('message', handleMessage);
  }, [setMetadata]);

  // Get initial variant count
  useEffect(() => {
    const fetchInitialCount = async () => {
      const count = await getVariantCount(inputVcf);
      useFilteringStore.setState({
        variantCounts: { input: count, filtered: 0 }
      });
    };
    fetchInitialCount();
  }, [inputVcf]);

  // Show Arti handoff when filtering completes
  useEffect(() => {
    if (outputVcf) {
      setShowArtiHandoff(true);
    }
  }, [outputVcf]);

  const handleApplyFilters = async () => {
    await applyFilters();
  };

  return (
    <div className={`min-h-screen ${mode === 'tumor-only' ? 'bg-red-50' : 'bg-blue-50'}`}>
      {/* Metadata Banner */}
      <MetadataBanner metadata={metadata} />
      
      {/* Header */}
      <header className={`${mode === 'tumor-only' ? 'bg-red-600' : 'bg-blue-600'} text-white`}>
        <div className="max-w-7xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold">Technical Variant Filtering</h1>
          <p className="mt-2 text-lg opacity-90">
            Pre-process variants before clinical interpretation in Arti
          </p>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Mode and Input Selection */}
        <div className="mb-6 space-y-4">
          <ModeSelector />
          
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Input VCF File
            </label>
            <div className="flex space-x-3">
              <input
                type="text"
                value={inputVcf}
                onChange={(e) => setInputVcf(e.target.value)}
                className="flex-1 p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
                placeholder="Path to VCF file"
              />
              <button className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors">
                Browse
              </button>
            </div>
          </div>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Filters Column */}
          <div className="lg:col-span-2 space-y-4">
            {filterGroups.map(group => (
              <FilterPanel key={group.id} group={group} />
            ))}
          </div>

          {/* Summary Column */}
          <div className="space-y-4">
            <VariantCounter />
            
            {/* Action Buttons */}
            <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 space-y-3">
              <button
                onClick={handleApplyFilters}
                disabled={isProcessing}
                className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
                  isProcessing
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : mode === 'tumor-only'
                    ? 'bg-red-600 text-white hover:bg-red-700'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                {isProcessing ? 'Processing...' : 'Apply Filters'}
              </button>
              
              <button
                onClick={resetFilters}
                disabled={isProcessing}
                className="w-full py-3 px-4 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Reset Filters
              </button>
              
              {outputVcf && (
                <button
                  onClick={exportVcf}
                  className="w-full py-3 px-4 bg-gray-100 text-gray-700 rounded-lg font-medium hover:bg-gray-200 transition-colors"
                >
                  Export Filtered VCF
                </button>
              )}
            </div>

            {/* Error Display */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h4 className="text-red-800 font-medium mb-1">Error</h4>
                <p className="text-red-700 text-sm">{error}</p>
              </div>
            )}

            {/* Preset Selector */}
            <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filter Presets
              </label>
              <select className="w-full p-2 border border-gray-300 rounded-lg">
                <option value="">Custom Settings</option>
                <option value="high_sensitivity">High Sensitivity</option>
                <option value="high_specificity">High Specificity</option>
                <option value="hotspot_mode">Hotspot Mode</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Arti Handoff Modal */}
      <ArtiHandoff 
        isOpen={showArtiHandoff} 
        onClose={() => setShowArtiHandoff(false)} 
      />
    </div>
  );
};