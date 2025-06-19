import React from 'react';
import { FilterGroup } from '../types/filtering.types';
import { FilterControl } from './FilterControl';
import { useFilteringStore } from '../store/filteringStore';
import { ChevronDownIcon, ChevronRightIcon } from './Icons';

interface FilterPanelProps {
  group: FilterGroup;
}

export const FilterPanel: React.FC<FilterPanelProps> = ({ group }) => {
  const { toggleFilterGroup } = useFilteringStore();

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <button
        onClick={() => toggleFilterGroup(group.id)}
        className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex items-center justify-between transition-colors"
      >
        <h3 className="text-lg font-semibold text-gray-900">{group.name}</h3>
        <div className="text-gray-500">
          {group.expanded ? (
            <ChevronDownIcon className="w-5 h-5" />
          ) : (
            <ChevronRightIcon className="w-5 h-5" />
          )}
        </div>
      </button>
      
      {group.expanded && (
        <div className="divide-y divide-gray-200">
          {group.filters.map(filter => (
            <FilterControl key={filter.id} filter={filter} />
          ))}
        </div>
      )}
    </div>
  );
};