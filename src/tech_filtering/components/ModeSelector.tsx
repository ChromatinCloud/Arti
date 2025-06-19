import React from 'react';
import { useFilteringStore } from '../store/filteringStore';
import { AnalysisMode } from '../types/filtering.types';

export const ModeSelector: React.FC = () => {
  const { mode, assay, setMode, setAssay } = useFilteringStore();

  const modes: { value: AnalysisMode; label: string; description: string }[] = [
    {
      value: 'tumor-only',
      label: 'Tumor Only',
      description: 'Single tumor sample analysis'
    },
    {
      value: 'tumor-normal',
      label: 'Tumor-Normal',
      description: 'Paired tumor and normal samples'
    }
  ];

  return (
    <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-200">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Analysis Mode
          </label>
          <div className="space-y-2">
            {modes.map(m => (
              <label
                key={m.value}
                className={`flex items-start p-3 border rounded-lg cursor-pointer transition-all ${
                  mode === m.value
                    ? 'border-primary bg-primary bg-opacity-5'
                    : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <input
                  type="radio"
                  name="mode"
                  value={m.value}
                  checked={mode === m.value}
                  onChange={(e) => setMode(e.target.value as AnalysisMode)}
                  className="mt-0.5 text-primary focus:ring-primary"
                />
                <div className="ml-3">
                  <div className="font-medium">{m.label}</div>
                  <div className="text-sm text-gray-600">{m.description}</div>
                </div>
              </label>
            ))}
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Assay Type
          </label>
          <select
            value={assay}
            onChange={(e) => setAssay(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary"
          >
            <option value="default_assay">Default Clinical Panel</option>
            {/* Add more assays as needed */}
          </select>
        </div>
      </div>
    </div>
  );
};