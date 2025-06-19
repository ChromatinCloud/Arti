import React, { useMemo } from 'react';
import { useInterpretationStore } from '../store/interpretationStore';
import { VariantWithFlow } from '../types/variant.types';
import { Check, Clock, AlertCircle, ChevronRight } from 'lucide-react';
import { mockVariants } from '../utils/mockData';

export const VariantList: React.FC = () => {
  const { 
    variants, 
    selectedVariant, 
    selectVariant, 
    filters,
    setFilter,
    setVariants 
  } = useInterpretationStore();
  
  // Use mock data if no variants loaded
  React.useEffect(() => {
    if (variants.length === 0) {
      setVariants(mockVariants);
    }
  }, []);
  
  const filteredVariants = useMemo(() => {
    return variants.filter(variant => {
      // Filter by tier
      if (filters.tiers.length > 0) {
        const variantTier = variant.tierAssignments[0]?.tier;
        if (!filters.tiers.includes(variantTier)) return false;
      }
      
      // Filter by status
      if (filters.status.length > 0 && !filters.status.includes(variant.status)) {
        return false;
      }
      
      // Filter by gene
      if (filters.genes.length > 0 && !filters.genes.includes(variant.gene.symbol)) {
        return false;
      }
      
      // Filter by VAF
      if (variant.vaf < filters.minVaf || variant.vaf > filters.maxVaf) {
        return false;
      }
      
      return true;
    });
  }, [variants, filters]);
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'reviewed':
      case 'approved':
        return <Check className="h-4 w-4 text-green-600" />;
      case 'in_progress':
        return <Clock className="h-4 w-4 text-yellow-600" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-400" />;
    }
  };
  
  const getTierBadge = (tier: string) => {
    const tierClass = tier?.toLowerCase().replace('-', '').replace(' ', '');
    return (
      <span className={`tier-badge tier-${tierClass?.charAt(0) || '4'}`}>
        {tier || 'Untiered'}
      </span>
    );
  };

  return (
    <div className="h-full flex flex-col">
      {/* Filters */}
      <div className="p-4 border-b border-gray-200">
        <div className="space-y-3">
          {/* Search */}
          <input
            type="text"
            placeholder="Search by gene, variant..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          
          {/* Quick Filters */}
          <div className="flex flex-wrap gap-2">
            <button className="px-3 py-1 text-xs border border-gray-300 rounded-full hover:bg-gray-50">
              All Tiers
            </button>
            <button className="px-3 py-1 text-xs border border-red-300 text-red-700 rounded-full hover:bg-red-50">
              Tier I
            </button>
            <button className="px-3 py-1 text-xs border border-orange-300 text-orange-700 rounded-full hover:bg-orange-50">
              Tier II
            </button>
            <button className="px-3 py-1 text-xs border border-gray-300 rounded-full hover:bg-gray-50">
              Unreviewed
            </button>
          </div>
        </div>
      </div>
      
      {/* Stats Bar */}
      <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 text-sm">
        <div className="flex justify-between">
          <span>Showing {filteredVariants.length} of {variants.length} variants</span>
          <span className="text-gray-500">
            {filteredVariants.filter(v => v.status === 'reviewed' || v.status === 'approved').length} reviewed
          </span>
        </div>
      </div>
      
      {/* Variant List */}
      <div className="flex-1 overflow-y-auto">
        {filteredVariants.map((variant) => (
          <div
            key={variant.variantId}
            onClick={() => selectVariant(variant)}
            className={`p-4 border-b border-gray-200 cursor-pointer hover:bg-gray-50 transition-colors ${
              selectedVariant?.variantId === variant.variantId ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <span className="font-semibold text-gray-900">{variant.gene.symbol}</span>
                  <span className="text-sm text-gray-600">{variant.hgvs.protein}</span>
                  {getStatusIcon(variant.status)}
                </div>
                
                <div className="mt-1 text-xs text-gray-500">
                  <span>{variant.chromosome}:{variant.position.toLocaleString()}</span>
                  <span className="mx-2">•</span>
                  <span>VAF: {(variant.vaf * 100).toFixed(1)}%</span>
                  <span className="mx-2">•</span>
                  <span>DP: {variant.depth}x</span>
                </div>
                
                <div className="mt-2 flex items-center space-x-2">
                  {variant.tierAssignments.map((tier, idx) => (
                    <React.Fragment key={tier.guideline}>
                      {idx === 0 && getTierBadge(tier.tier)}
                    </React.Fragment>
                  ))}
                  {variant.annotations.find(a => a.source === 'OncoKB') && (
                    <span className="text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded">
                      OncoKB
                    </span>
                  )}
                  {variant.annotations.find(a => a.source === 'ClinVar') && (
                    <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded">
                      ClinVar
                    </span>
                  )}
                </div>
              </div>
              
              <ChevronRight className="h-4 w-4 text-gray-400 mt-1" />
            </div>
          </div>
        ))}
      </div>
      
      {/* Footer */}
      <div className="p-3 border-t border-gray-200 bg-gray-50">
        <button className="w-full px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded-md">
          Load More Variants
        </button>
      </div>
    </div>
  );
};