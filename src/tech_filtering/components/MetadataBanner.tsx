import React, { useState } from 'react';
import { useFilteringStore } from '../store/filteringStore';

interface MetadataBannerProps {
  metadata: {
    patientUID?: string;
    caseID?: string;
    oncotreeCode?: string;
    tumorPurity?: number;
    specimenType?: string;
  };
  showSampleNameInputs?: boolean;
  onSampleNamesChange?: (tumor: string, normal: string) => void;
}

export const MetadataBanner: React.FC<MetadataBannerProps> = ({ 
  metadata, 
  showSampleNameInputs = false,
  onSampleNamesChange 
}) => {
  const { mode } = useFilteringStore();
  const [tumorSample, setTumorSample] = useState('');
  const [normalSample, setNormalSample] = useState('');
  
  // OncoTree code to display name mapping (subset of common codes)
  const oncotreeDisplayNames: Record<string, string> = {
    'SKCM': 'Melanoma',
    'LUAD': 'Lung Adenocarcinoma',
    'BRCA': 'Breast Cancer',
    'COAD': 'Colon Adenocarcinoma',
    'PRAD': 'Prostate Adenocarcinoma',
    'GBM': 'Glioblastoma',
    'OV': 'Ovarian Cancer',
    'PAAD': 'Pancreatic Adenocarcinoma',
    'RCC': 'Renal Cell Carcinoma',
    'HCC': 'Hepatocellular Carcinoma'
  };
  
  const getOncotreeDisplay = (code?: string) => {
    if (!code) return 'Not Specified';
    return oncotreeDisplayNames[code] || code;
  };
  
  const getPurityDisplay = (purity?: number) => {
    if (purity === undefined || purity === null) return 'Not Specified';
    return `${(purity * 100).toFixed(0)}%`;
  };
  
  const getSpecimenDisplay = (type?: string) => {
    if (!type) return 'Not Specified';
    const displayMap: Record<string, string> = {
      'FFPE': 'FFPE',
      'FreshFrozen': 'Fresh Frozen',
      'Blood': 'Blood',
      'Other': 'Other'
    };
    return displayMap[type] || type;
  };

  return (
    <div className={`${mode === 'tumor-only' ? 'bg-red-600' : 'bg-blue-600'} text-white`}>
      <div className="max-w-7xl mx-auto px-4 py-3">
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 text-sm">
          {/* Patient & Case Info */}
          <div className="space-y-1">
            <div className="opacity-75 text-xs uppercase tracking-wider">Patient / Case</div>
            <div className="font-medium">
              {metadata.patientUID || 'No Patient ID'} / {metadata.caseID || 'No Case ID'}
            </div>
          </div>
          
          {/* Cancer Type */}
          <div className="space-y-1">
            <div className="opacity-75 text-xs uppercase tracking-wider">Cancer Type</div>
            <div className="font-medium flex items-center space-x-2">
              <span>{getOncotreeDisplay(metadata.oncotreeCode)}</span>
              {!metadata.oncotreeCode && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800">
                  Required
                </span>
              )}
            </div>
          </div>
          
          {/* Tumor Purity */}
          <div className="space-y-1">
            <div className="opacity-75 text-xs uppercase tracking-wider">Tumor Purity</div>
            <div className="font-medium">
              {getPurityDisplay(metadata.tumorPurity)}
            </div>
          </div>
          
          {/* Specimen Type */}
          <div className="space-y-1">
            <div className="opacity-75 text-xs uppercase tracking-wider">Specimen Type</div>
            <div className="font-medium">
              {getSpecimenDisplay(metadata.specimenType)}
            </div>
          </div>
          
          {/* Genome Build */}
          <div className="space-y-1">
            <div className="opacity-75 text-xs uppercase tracking-wider">Reference</div>
            <div className="font-medium">GRCh38</div>
          </div>
        </div>
        
        {/* Sample name inputs for multi-sample VCFs */}
        {showSampleNameInputs && mode === 'tumor-normal' && (
          <div className="mt-3 pt-3 border-t border-white/20">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs opacity-75 mb-1">Tumor Sample Name</label>
                <input
                  type="text"
                  value={tumorSample}
                  onChange={(e) => {
                    setTumorSample(e.target.value);
                    if (onSampleNamesChange) {
                      onSampleNamesChange(e.target.value, normalSample);
                    }
                  }}
                  placeholder="e.g., TUMOR, Patient1_T"
                  className="w-full px-2 py-1 text-sm bg-white/10 border border-white/20 rounded focus:bg-white/20 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs opacity-75 mb-1">Normal Sample Name</label>
                <input
                  type="text"
                  value={normalSample}
                  onChange={(e) => {
                    setNormalSample(e.target.value);
                    if (onSampleNamesChange) {
                      onSampleNamesChange(tumorSample, e.target.value);
                    }
                  }}
                  placeholder="e.g., NORMAL, Patient1_N"
                  className="w-full px-2 py-1 text-sm bg-white/10 border border-white/20 rounded focus:bg-white/20 focus:outline-none"
                />
              </div>
            </div>
            <p className="text-xs opacity-75 mt-2">
              Specify sample names if your multi-sample VCF uses non-standard naming
            </p>
          </div>
        )}
        
        {/* Warning if missing critical data */}
        {(!metadata.oncotreeCode || !metadata.caseID) && (
          <div className="mt-3 pt-3 border-t border-white/20">
            <div className="flex items-center space-x-2 text-sm">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span>
                {!metadata.caseID && !metadata.oncotreeCode 
                  ? 'Case ID and OncoTree code are required for clinical interpretation'
                  : !metadata.caseID 
                  ? 'Case ID is required'
                  : 'OncoTree code is required for full clinical interpretation functionality'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};