import React from 'react';
import { VariantWithFlow } from '../../types/variant.types';
import { useInterpretationStore } from '../../store/interpretationStore';
import { ChevronDown, ChevronRight, Dna } from 'lucide-react';

interface VariantCardProps {
  variant: VariantWithFlow;
}

export const VariantCard: React.FC<VariantCardProps> = ({ variant }) => {
  const { expandedSections, toggleSection } = useInterpretationStore();
  const isExpanded = expandedSections.has('variant');

  return (
    <div className="evidence-card">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => toggleSection('variant')}
      >
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center">
            <Dna className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Variant Details</h3>
            <p className="text-sm text-gray-500">Genomic and molecular information</p>
          </div>
        </div>
        {isExpanded ? <ChevronDown className="h-5 w-5 text-gray-400" /> : <ChevronRight className="h-5 w-5 text-gray-400" />}
      </div>

      {isExpanded && (
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <DataField label="Gene" value={variant.gene.symbol} />
            <DataField label="Position" value={`${variant.chromosome}:${variant.position.toLocaleString()}`} />
            <DataField label="Change" value={`${variant.reference}>${variant.alternate}`} />
            <DataField label="Transcript" value={variant.gene.transcriptId} />
            <DataField label="HGVS.c" value={variant.hgvs.coding} />
            <DataField label="HGVS.p" value={variant.hgvs.protein} highlight />
            <DataField label="VAF" value={`${(variant.vaf * 100).toFixed(1)}%`} highlight />
            <DataField label="Depth" value={`${variant.depth}x`} />
            <DataField label="Consequence" value={variant.consequence.join(', ')} />
            <DataField label="Quality" value={variant.quality.toString()} />
          </div>

          {/* VAF Visualization */}
          <div className="mt-4">
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-600">Variant Allele Frequency</span>
              <span className="font-medium">{(variant.vaf * 100).toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full"
                style={{ width: `${variant.vaf * 100}%` }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const DataField: React.FC<{ label: string; value: string; highlight?: boolean }> = ({ 
  label, 
  value, 
  highlight = false 
}) => (
  <div>
    <dt className="text-xs text-gray-500">{label}</dt>
    <dd className={`text-sm ${highlight ? 'font-semibold text-gray-900' : 'text-gray-700'}`}>
      {value}
    </dd>
  </div>
);