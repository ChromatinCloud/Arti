import React from 'react';
import { useFilteringStore } from '../store/filteringStore';
import { ArrowRightIcon } from './Icons';

export const VariantCounter: React.FC = () => {
  const { variantCounts } = useFilteringStore();
  const { input, filtered } = variantCounts;
  
  const reductionPercent = input > 0 
    ? ((1 - filtered / input) * 100).toFixed(1)
    : 0;

  return (
    <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-200">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Variant Filtering Summary</h3>
      
      <div className="flex items-center justify-between">
        <div className="text-center">
          <div className="text-3xl font-bold text-gray-900">
            {input.toLocaleString()}
          </div>
          <div className="text-sm text-gray-600">Input Variants</div>
        </div>
        
        <ArrowRightIcon className="w-8 h-8 text-gray-400" />
        
        <div className="text-center">
          <div className="text-3xl font-bold text-primary">
            {filtered.toLocaleString()}
          </div>
          <div className="text-sm text-gray-600">Filtered Variants</div>
        </div>
      </div>
      
      {input > 0 && (
        <div className="mt-4 text-center">
          <div className="text-sm text-gray-600">
            {reductionPercent}% reduction
          </div>
          <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-primary h-2 rounded-full transition-all duration-500"
              style={{ width: `${(filtered / input) * 100}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
};