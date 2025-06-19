import React from 'react';
import { ArrowDown } from 'lucide-react';

export const FlowConnector: React.FC = () => {
  return (
    <div className="flex items-center justify-center py-2">
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute inset-x-1/2 top-0 bottom-0 w-0.5 bg-gradient-to-b from-gray-300 via-gray-400 to-gray-300" />
        
        {/* Arrow icon */}
        <div className="relative bg-white p-1 rounded-full">
          <ArrowDown className="h-5 w-5 text-gray-400" />
        </div>
      </div>
    </div>
  );
};