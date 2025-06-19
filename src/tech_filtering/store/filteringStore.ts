import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { 
  FilteringState, 
  Filter, 
  FilterGroup, 
  AnalysisMode,
  FilteringRequest,
  FilteringResponse,
  SampleMetadata 
} from '../types/filtering.types';
import { getDefaultFilters } from '../utils/filterDefaults';
import { applyFiltersAPI } from '../services/filteringAPI';

interface FilteringStore extends FilteringState {
  // State
  metadata: SampleMetadata;
  
  // Actions
  setMode: (mode: AnalysisMode) => void;
  setAssay: (assay: string) => void;
  setInputVcf: (vcf: string) => void;
  setMetadata: (metadata: SampleMetadata) => void;
  updateFilter: (filterId: string, value: any) => void;
  toggleFilter: (filterId: string) => void;
  toggleFilterGroup: (groupId: string) => void;
  applyFilters: () => Promise<void>;
  resetFilters: () => void;
  exportVcf: () => void;
  loadPreset: (presetName: string) => void;
}

const initialState: FilteringState = {
  mode: 'tumor-only',
  assay: 'default_assay',
  inputVcf: 'example_input/proper_test.vcf',
  outputVcf: null,
  filters: {},
  filterGroups: [],
  variantCounts: {
    input: 0,
    filtered: 0
  },
  isProcessing: false,
  error: null
};

export const useFilteringStore = create<FilteringStore>()(
  devtools(
    (set, get) => ({
      ...initialState,
      metadata: {},

      setMode: (mode) => {
        const { filters, filterGroups } = getDefaultFilters(mode);
        set({ 
          mode, 
          filters, 
          filterGroups,
          outputVcf: null,
          variantCounts: { input: 0, filtered: 0 }
        });
      },

      setAssay: (assay) => set({ assay }),

      setInputVcf: (inputVcf) => set({ inputVcf }),
      
      setMetadata: (metadata) => set({ metadata }),

      updateFilter: (filterId, value) => {
        const { filters } = get();
        const filter = filters[filterId];
        if (!filter) return;

        set({
          filters: {
            ...filters,
            [filterId]: {
              ...filter,
              value
            }
          }
        });
      },

      toggleFilter: (filterId) => {
        const { filters } = get();
        const filter = filters[filterId];
        if (!filter) return;

        set({
          filters: {
            ...filters,
            [filterId]: {
              ...filter,
              enabled: !filter.enabled
            }
          }
        });
      },

      toggleFilterGroup: (groupId) => {
        const { filterGroups } = get();
        set({
          filterGroups: filterGroups.map(group =>
            group.id === groupId
              ? { ...group, expanded: !group.expanded }
              : group
          )
        });
      },

      applyFilters: async () => {
        const { mode, assay, inputVcf, filters, metadata } = get();
        
        set({ isProcessing: true, error: null });

        try {
          // Prepare filter values for API
          const filterValues: Record<string, any> = {};
          Object.entries(filters).forEach(([id, filter]) => {
            if (filter.enabled) {
              filterValues[id] = filter.value;
            }
          });

          const request: FilteringRequest = {
            mode,
            assay,
            inputVcf,
            filters: filterValues,
            metadata
          };

          const response: FilteringResponse = await applyFiltersAPI(request);

          if (response.success && response.outputVcf) {
            set({
              outputVcf: response.outputVcf,
              variantCounts: response.variantCounts || { input: 0, filtered: 0 },
              isProcessing: false
            });
          } else {
            throw new Error(response.error || 'Filtering failed');
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Unknown error',
            isProcessing: false
          });
        }
      },

      resetFilters: () => {
        const { mode } = get();
        const { filters, filterGroups } = getDefaultFilters(mode);
        set({
          filters,
          filterGroups,
          outputVcf: null,
          variantCounts: { input: 0, filtered: 0 },
          error: null
        });
      },

      exportVcf: () => {
        const { outputVcf } = get();
        if (outputVcf) {
          // Trigger download
          window.location.href = `/api/v1/tech-filtering/download?file=${outputVcf}`;
        }
      },

      loadPreset: (presetName) => {
        // Load preset configuration
        // This would fetch preset overrides and apply them
        console.log(`Loading preset: ${presetName}`);
      }
    }),
    {
      name: 'tech-filtering-store'
    }
  )
);

// Initialize with default filters
const { filters, filterGroups } = getDefaultFilters('tumor-only');
useFilteringStore.setState({ filters, filterGroups });