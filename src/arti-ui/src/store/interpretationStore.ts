import { create } from 'zustand';
import { Case, VariantWithFlow } from '../types/variant.types';

interface InterpretationState {
  // Case data
  currentCase: Case | null;
  setCurrentCase: (caseData: Case) => void;
  
  // Variants
  variants: VariantWithFlow[];
  setVariants: (variants: VariantWithFlow[]) => void;
  selectedVariant: VariantWithFlow | null;
  selectVariant: (variant: VariantWithFlow | null) => void;
  
  // UI State
  expandedSections: Set<string>;
  toggleSection: (section: string) => void;
  
  // Filters
  filters: {
    tiers: string[];
    status: string[];
    genes: string[];
    minVaf: number;
    maxVaf: number;
  };
  setFilter: (key: string, value: any) => void;
  
  // View preferences
  viewMode: 'pipeline' | 'compact' | 'detailed';
  setViewMode: (mode: 'pipeline' | 'compact' | 'detailed') => void;
  
  // Actions
  updateVariantStatus: (variantId: string, status: string) => void;
  approveTier: (variantId: string, guideline: string) => void;
  selectInterpretation: (variantId: string, interpretationId: string) => void;
}

export const useInterpretationStore = create<InterpretationState>((set) => ({
  // Case data
  currentCase: null,
  setCurrentCase: (caseData) => set({ currentCase: caseData }),
  
  // Variants
  variants: [],
  setVariants: (variants) => set({ variants }),
  selectedVariant: null,
  selectVariant: (variant) => set({ selectedVariant: variant }),
  
  // UI State
  expandedSections: new Set(['annotations', 'rules', 'tier']),
  toggleSection: (section) => set((state) => {
    const newSections = new Set(state.expandedSections);
    if (newSections.has(section)) {
      newSections.delete(section);
    } else {
      newSections.add(section);
    }
    return { expandedSections: newSections };
  }),
  
  // Filters
  filters: {
    tiers: [],
    status: [],
    genes: [],
    minVaf: 0,
    maxVaf: 100,
  },
  setFilter: (key, value) => set((state) => ({
    filters: { ...state.filters, [key]: value }
  })),
  
  // View preferences
  viewMode: 'pipeline',
  setViewMode: (mode) => set({ viewMode: mode }),
  
  // Actions
  updateVariantStatus: (variantId, status) => set((state) => ({
    variants: state.variants.map(v => 
      v.variantId === variantId ? { ...v, status } : v
    ),
    selectedVariant: state.selectedVariant?.variantId === variantId 
      ? { ...state.selectedVariant, status } 
      : state.selectedVariant
  })),
  
  approveTier: (variantId, guideline) => set((state) => ({
    variants: state.variants.map(v => 
      v.variantId === variantId 
        ? { 
            ...v, 
            tierAssignments: v.tierAssignments.map(t => 
              t.guideline === guideline ? { ...t, approved: true } : t
            )
          } 
        : v
    )
  })),
  
  selectInterpretation: (variantId, interpretationId) => set((state) => ({
    variants: state.variants.map(v => 
      v.variantId === variantId 
        ? { ...v, selectedInterpretationId: interpretationId } 
        : v
    )
  })),
}));