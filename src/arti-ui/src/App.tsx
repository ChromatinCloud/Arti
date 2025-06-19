import React from 'react';
import { CaseHeader } from './components/CaseHeader';
import { VariantList } from './components/VariantList';
import { EvidenceFlowPipeline } from './components/EvidenceFlowPipeline';
import { InterpretationPanel } from './components/InterpretationPanel';
import { useInterpretationStore } from './store/interpretationStore';

function App() {
  const { selectedVariant, viewMode } = useInterpretationStore();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Case Header */}
      <CaseHeader />
      
      {/* Main Content Area */}
      <div className="flex h-[calc(100vh-64px)]">
        {/* Left Panel - Variant List */}
        <div className="w-96 bg-white border-r border-gray-200 overflow-y-auto">
          <VariantList />
        </div>
        
        {/* Center Panel - Evidence Flow */}
        <div className="flex-1 overflow-y-auto">
          {selectedVariant ? (
            <EvidenceFlowPipeline variant={selectedVariant} />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <p className="mt-2 text-sm">Select a variant to view details</p>
              </div>
            </div>
          )}
        </div>
        
        {/* Right Panel - Interpretation Tools */}
        {selectedVariant && (
          <div className="w-96 bg-white border-l border-gray-200 overflow-y-auto">
            <InterpretationPanel />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;