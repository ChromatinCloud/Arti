import React from 'react';
import { useInterpretationStore } from '../store/interpretationStore';
import { AlertCircle } from 'lucide-react';

export const CaseHeader: React.FC = () => {
  const { currentCase } = useInterpretationStore();
  
  // Mock data for demo
  const mockCase = currentCase || {
    caseUid: 'CASE_001',
    patientUid: 'PT_001',
    cancerType: 'Melanoma',
    oncotreeCode: 'SKCM',
    specimenType: 'FFPE',
    tumorPurity: 0.75,
    analysisType: 'tumor_only' as const,
    status: 'in_progress' as const,
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'in_progress': return 'bg-yellow-100 text-yellow-800';
      case 'review': return 'bg-blue-100 text-blue-800';
      case 'signed_out': return 'bg-green-100 text-green-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-6">
          {/* Patient & Case Info */}
          <div>
            <div className="text-xs text-gray-500">Patient / Case</div>
            <div className="font-medium">
              {mockCase.patientUid} / {mockCase.caseUid}
            </div>
          </div>
          
          {/* Cancer Type */}
          <div>
            <div className="text-xs text-gray-500">Cancer Type</div>
            <div className="font-medium flex items-center space-x-2">
              <span>{mockCase.cancerType}</span>
              <span className="text-xs text-gray-500">({mockCase.oncotreeCode})</span>
            </div>
          </div>
          
          {/* Analysis Type */}
          <div>
            <div className="text-xs text-gray-500">Analysis</div>
            <div className="font-medium">
              {mockCase.analysisType === 'tumor_only' ? 'Tumor Only' : 'Tumor-Normal'}
            </div>
          </div>
          
          {/* Specimen Info */}
          <div>
            <div className="text-xs text-gray-500">Specimen</div>
            <div className="font-medium">
              {mockCase.specimenType} 
              {mockCase.tumorPurity && ` (${Math.round(mockCase.tumorPurity * 100)}%)`}
            </div>
          </div>
          
          {/* Status */}
          <div>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(mockCase.status)}`}>
              {mockCase.status.replace('_', ' ').charAt(0).toUpperCase() + mockCase.status.slice(1).replace('_', ' ')}
            </span>
          </div>
        </div>
        
        {/* Actions */}
        <div className="flex items-center space-x-3">
          <button className="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50">
            Export
          </button>
          <button className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700">
            Generate Report
          </button>
          <button className="px-3 py-1.5 text-sm bg-green-600 text-white rounded-md hover:bg-green-700">
            Sign Out
          </button>
        </div>
      </div>
      
      {/* Warning if missing OncoTree code */}
      {!mockCase.oncotreeCode && (
        <div className="mt-2 flex items-center space-x-2 text-sm text-amber-600">
          <AlertCircle className="h-4 w-4" />
          <span>OncoTree code required for full clinical interpretation functionality</span>
        </div>
      )}
    </header>
  );
};