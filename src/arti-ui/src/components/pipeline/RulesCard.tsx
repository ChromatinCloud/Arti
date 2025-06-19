import React from 'react';
import { RuleEvaluation } from '../../types/variant.types';
import { useInterpretationStore } from '../../store/interpretationStore';
import { 
  ChevronDown, 
  ChevronRight, 
  GitBranch,
  CheckCircle,
  XCircle,
  AlertCircle,
  Code
} from 'lucide-react';

interface RulesCardProps {
  rules: RuleEvaluation[];
}

export const RulesCard: React.FC<RulesCardProps> = ({ rules }) => {
  const { expandedSections, toggleSection } = useInterpretationStore();
  const isExpanded = expandedSections.has('rules');

  const firedRules = rules.filter(r => r.fired);
  const notFiredRules = rules.filter(r => !r.fired);

  const getGuidelineColor = (guideline: string) => {
    switch (guideline) {
      case 'OncoKB': return 'bg-purple-100 text-purple-700';
      case 'CGC_VICC': return 'bg-blue-100 text-blue-700';
      case 'AMP_ASCO': return 'bg-green-100 text-green-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high': return 'text-red-600';
      case 'medium': return 'text-yellow-600';
      case 'low': return 'text-green-600';
      default: return 'text-gray-600';
    }
  };

  const renderEvidence = (evidence: any[]) => {
    return evidence.map((ev, idx) => (
      <div key={idx} className="flex items-center space-x-2 text-xs">
        <span className={`h-2 w-2 rounded-full ${ev.supporting ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className="text-gray-600">{ev.type}:</span>
        <span className="font-medium">{ev.value}</span>
        <span className="text-gray-500">({ev.source})</span>
      </div>
    ));
  };

  return (
    <div className="evidence-card">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => toggleSection('rules')}
      >
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
            <GitBranch className="h-5 w-5 text-green-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Classification Rules</h3>
            <p className="text-sm text-gray-500">
              {firedRules.length} of {rules.length} rules fired
            </p>
          </div>
        </div>
        {isExpanded ? <ChevronDown className="h-5 w-5 text-gray-400" /> : <ChevronRight className="h-5 w-5 text-gray-400" />}
      </div>

      {isExpanded && (
        <div className="mt-4 space-y-4">
          {/* Summary Stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-green-50 rounded-lg p-3">
              <div className="flex items-center space-x-2">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <span className="text-sm font-medium text-green-900">Fired</span>
              </div>
              <div className="text-2xl font-bold text-green-900 mt-1">{firedRules.length}</div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="flex items-center space-x-2">
                <XCircle className="h-4 w-4 text-gray-600" />
                <span className="text-sm font-medium text-gray-900">Not Fired</span>
              </div>
              <div className="text-2xl font-bold text-gray-900 mt-1">{notFiredRules.length}</div>
            </div>
            <div className="bg-blue-50 rounded-lg p-3">
              <div className="flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 text-blue-600" />
                <span className="text-sm font-medium text-blue-900">High Impact</span>
              </div>
              <div className="text-2xl font-bold text-blue-900 mt-1">
                {firedRules.filter(r => r.impact === 'high').length}
              </div>
            </div>
          </div>

          {/* Fired Rules */}
          {firedRules.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-2 flex items-center">
                <CheckCircle className="h-4 w-4 text-green-600 mr-1" />
                Rules That Fired
              </h4>
              <div className="space-y-2">
                {firedRules.map((rule) => (
                  <div key={rule.ruleId} className="border border-green-200 rounded-lg p-3 bg-green-50">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-gray-900">{rule.ruleName}</span>
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getGuidelineColor(rule.guideline)}`}>
                            {rule.guideline}
                          </span>
                          <span className={`text-xs font-medium ${getImpactColor(rule.impact)}`}>
                            {rule.impact} impact
                          </span>
                        </div>
                        <div className="text-sm text-gray-600 mt-1">
                          Outcome: <span className="font-medium text-gray-900">{rule.outcome}</span>
                        </div>
                      </div>
                      <div className="text-sm text-gray-500">
                        {(rule.confidence * 100).toFixed(0)}%
                      </div>
                    </div>

                    {/* Evidence */}
                    <div className="bg-white rounded p-2 mb-2">
                      <div className="text-xs font-medium text-gray-700 mb-1">Evidence:</div>
                      <div className="space-y-1">
                        {renderEvidence(rule.evidence)}
                      </div>
                    </div>

                    {/* Logic */}
                    <div className="bg-gray-800 text-gray-100 rounded p-2 font-mono text-xs overflow-x-auto">
                      <Code className="h-3 w-3 inline mr-1" />
                      {rule.logic}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Not Fired Rules (Collapsed by default) */}
          {notFiredRules.length > 0 && (
            <details className="group">
              <summary className="cursor-pointer text-sm font-semibold text-gray-600 hover:text-gray-900">
                Show {notFiredRules.length} rules that didn't fire
              </summary>
              <div className="mt-2 space-y-2">
                {notFiredRules.map((rule) => (
                  <div key={rule.ruleId} className="border border-gray-200 rounded-lg p-3 bg-gray-50 opacity-60">
                    <div className="flex items-center space-x-2">
                      <XCircle className="h-4 w-4 text-gray-400" />
                      <span className="text-sm text-gray-700">{rule.ruleName}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs ${getGuidelineColor(rule.guideline)}`}>
                        {rule.guideline}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </details>
          )}

          {rules.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <GitBranch className="h-12 w-12 mx-auto mb-2 text-gray-300" />
              <p>No rules evaluated</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};