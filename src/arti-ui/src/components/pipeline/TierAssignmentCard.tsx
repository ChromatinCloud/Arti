import React from 'react';
import { TierAssignment } from '../../types/variant.types';
import { useInterpretationStore } from '../../store/interpretationStore';
import { 
  ChevronDown, 
  ChevronRight, 
  Award,
  Shield,
  FileText,
  CheckCircle
} from 'lucide-react';

interface TierAssignmentCardProps {
  assignments: TierAssignment[];
}

export const TierAssignmentCard: React.FC<TierAssignmentCardProps> = ({ assignments }) => {
  const { expandedSections, toggleSection } = useInterpretationStore();
  const isExpanded = expandedSections.has('tiers');

  const getGuidelineIcon = (guideline: string) => {
    switch (guideline) {
      case 'OncoKB': return <Shield className="h-4 w-4" />;
      case 'CGC_VICC': return <FileText className="h-4 w-4" />;
      case 'AMP_ASCO': return <Award className="h-4 w-4" />;
      default: return <Award className="h-4 w-4" />;
    }
  };

  const getTierColor = (tier: string) => {
    const tierLevel = tier?.toLowerCase().replace('-', '').replace(' ', '');
    if (tierLevel?.includes('1') || tierLevel?.includes('i')) return 'border-red-500 bg-red-50 text-red-900';
    if (tierLevel?.includes('2') || tierLevel?.includes('ii')) return 'border-orange-500 bg-orange-50 text-orange-900';
    if (tierLevel?.includes('3') || tierLevel?.includes('iii')) return 'border-yellow-500 bg-yellow-50 text-yellow-900';
    if (tierLevel?.includes('4') || tierLevel?.includes('iv')) return 'border-gray-500 bg-gray-50 text-gray-900';
    return 'border-gray-300 bg-gray-50 text-gray-700';
  };

  const getConsensus = () => {
    if (assignments.length === 0) return null;
    
    const tiers = assignments.map(a => a.tier);
    const allSame = tiers.every(t => t === tiers[0]);
    
    if (allSame) {
      return { status: 'unanimous', tier: tiers[0] };
    }
    
    // Check if all are high tier (I/1)
    const allHighTier = tiers.every(t => 
      t?.toLowerCase().includes('1') || t?.toLowerCase().includes('i')
    );
    
    if (allHighTier) {
      return { status: 'concordant', tier: 'Tier I' };
    }
    
    return { status: 'discordant', tier: null };
  };

  const consensus = getConsensus();

  return (
    <div className="evidence-card">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => toggleSection('tiers')}
      >
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-yellow-100 rounded-full flex items-center justify-center">
            <Award className="h-5 w-5 text-yellow-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Tier Assignment</h3>
            <p className="text-sm text-gray-500">
              {assignments.length} guideline{assignments.length !== 1 ? 's' : ''} evaluated
            </p>
          </div>
        </div>
        {isExpanded ? <ChevronDown className="h-5 w-5 text-gray-400" /> : <ChevronRight className="h-5 w-5 text-gray-400" />}
      </div>

      {isExpanded && (
        <div className="mt-4 space-y-4">
          {/* Consensus View */}
          {consensus && (
            <div className={`rounded-lg p-4 border-2 ${
              consensus.status === 'unanimous' ? 'border-green-300 bg-green-50' :
              consensus.status === 'concordant' ? 'border-blue-300 bg-blue-50' :
              'border-amber-300 bg-amber-50'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <CheckCircle className={`h-5 w-5 ${
                    consensus.status === 'unanimous' ? 'text-green-600' :
                    consensus.status === 'concordant' ? 'text-blue-600' :
                    'text-amber-600'
                  }`} />
                  <span className="font-medium text-gray-900">
                    {consensus.status === 'unanimous' ? 'Unanimous Agreement' :
                     consensus.status === 'concordant' ? 'Concordant High Tier' :
                     'Discordant Tiers'}
                  </span>
                </div>
                {consensus.tier && (
                  <span className={`px-3 py-1 rounded-full text-sm font-semibold border-2 ${getTierColor(consensus.tier)}`}>
                    {consensus.tier}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Individual Assignments */}
          <div className="space-y-3">
            {assignments.map((assignment) => (
              <div key={assignment.guideline} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    {getGuidelineIcon(assignment.guideline)}
                    <span className="font-medium text-gray-900">{assignment.guideline}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className={`px-3 py-1 rounded-full text-sm font-semibold border ${getTierColor(assignment.tier)}`}>
                      {assignment.tier}
                    </span>
                    <span className="text-sm text-gray-500">
                      {(assignment.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                <div className="text-sm text-gray-700">
                  {assignment.justification}
                </div>

                {assignment.rules.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <div className="text-xs text-gray-500 mb-1">Rules Applied:</div>
                    <div className="flex flex-wrap gap-1">
                      {assignment.rules.map((ruleId) => (
                        <span key={ruleId} className="px-2 py-0.5 bg-gray-100 rounded text-xs text-gray-600">
                          {ruleId}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Tier Distribution Visualization */}
          {assignments.length > 1 && (
            <div className="bg-gray-50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-gray-900 mb-3">Tier Distribution</h4>
              <div className="flex items-center justify-around">
                {['I', 'II', 'III', 'IV'].map((tier) => {
                  const count = assignments.filter(a => 
                    a.tier?.includes(tier) || a.tier?.includes(tier.toLowerCase())
                  ).length;
                  const percentage = (count / assignments.length) * 100;
                  
                  return (
                    <div key={tier} className="text-center">
                      <div className={`w-16 h-16 rounded-full flex items-center justify-center text-lg font-bold border-2 ${
                        count > 0 ? getTierColor(`Tier ${tier}`) : 'border-gray-200 bg-gray-100 text-gray-400'
                      }`}>
                        {count}
                      </div>
                      <div className="text-xs mt-1 text-gray-600">Tier {tier}</div>
                      {count > 0 && (
                        <div className="text-xs text-gray-500">{percentage.toFixed(0)}%</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {assignments.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <Award className="h-12 w-12 mx-auto mb-2 text-gray-300" />
              <p>No tier assignments</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};