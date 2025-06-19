import React from 'react';
import { VariantWithFlow } from '../types/variant.types';
import { VariantCard } from './pipeline/VariantCard';
import { AnnotationsCard } from './pipeline/AnnotationsCard';
import { RulesCard } from './pipeline/RulesCard';
import { TierAssignmentCard } from './pipeline/TierAssignmentCard';
import { InterpretationCard } from './pipeline/InterpretationCard';
import { FlowConnector } from './pipeline/FlowConnector';
import { useInterpretationStore } from '../store/interpretationStore';

interface EvidenceFlowPipelineProps {
  variant: VariantWithFlow;
}

export const EvidenceFlowPipeline: React.FC<EvidenceFlowPipelineProps> = ({ variant }) => {
  const { viewMode } = useInterpretationStore();

  if (viewMode === 'compact') {
    return (
      <div className="p-6">
        <CompactFlowView variant={variant} />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">
          {variant.gene.symbol} {variant.hgvs.protein}
        </h2>
        <div className="flex items-center space-x-2">
          <span className="tier-badge tier-1">
            {variant.tierAssignments[0]?.tier || 'Untiered'}
          </span>
        </div>
      </div>

      {/* Pipeline Flow */}
      <div className="space-y-4">
        <VariantCard variant={variant} />
        <FlowConnector />
        
        <AnnotationsCard annotations={variant.annotations} />
        <FlowConnector />
        
        <RulesCard rules={variant.rulesEvaluated} />
        <FlowConnector />
        
        <TierAssignmentCard assignments={variant.tierAssignments} />
        <FlowConnector />
        
        <InterpretationCard interpretations={variant.interpretations} />
      </div>
    </div>
  );
};

const CompactFlowView: React.FC<{ variant: VariantWithFlow }> = ({ variant }) => {
  const steps = [
    { label: 'Variant', status: 'complete' },
    { label: `${variant.annotations.length} Annotations`, status: 'complete' },
    { label: `${variant.rulesEvaluated.filter(r => r.fired).length} Rules Fired`, status: 'complete' },
    { label: variant.tierAssignments[0]?.tier || 'Untiered', status: 'complete' },
    { label: 'Interpretation', status: variant.interpretations.length > 0 ? 'complete' : 'active' }
  ];

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <React.Fragment key={step.label}>
            <div className="flex flex-col items-center">
              <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                step.status === 'complete' ? 'bg-green-500' : 'bg-blue-500'
              } text-white font-semibold text-sm`}>
                {index + 1}
              </div>
              <span className="mt-2 text-xs text-gray-600">{step.label}</span>
            </div>
            {index < steps.length - 1 && (
              <div className="flex-1 h-0.5 bg-gray-300 mx-2" />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};