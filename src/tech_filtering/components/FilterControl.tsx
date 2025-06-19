import React from 'react';
import { Filter } from '../types/filtering.types';
import { useFilteringStore } from '../store/filteringStore';

interface FilterControlProps {
  filter: Filter;
}

export const FilterControl: React.FC<FilterControlProps> = ({ filter }) => {
  const { updateFilter, toggleFilter } = useFilteringStore();

  const renderControl = () => {
    switch (filter.type) {
      case 'checkbox':
        return (
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id={filter.id}
              checked={filter.value}
              onChange={(e) => updateFilter(filter.id, e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
            />
            <span className="text-sm">{filter.description}</span>
          </div>
        );

      case 'slider':
        const displayValue = filter.unit === '%' 
          ? (filter.value * 100).toFixed(1) 
          : filter.value;
          
        return (
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm">{filter.description}</span>
              <span className="text-sm font-medium">
                {displayValue} {filter.unit || ''}
              </span>
            </div>
            <input
              type="range"
              min={filter.min}
              max={filter.max}
              step={filter.step || 1}
              value={filter.value}
              onChange={(e) => updateFilter(filter.id, parseFloat(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer slider"
            />
            <div className="flex justify-between text-xs text-gray-500">
              <span>{filter.min}</span>
              <span>{filter.max}</span>
            </div>
          </div>
        );

      case 'range':
        return (
          <div className="space-y-2">
            <span className="text-sm">{filter.description}</span>
            <div className="flex items-center space-x-2">
              <input
                type="number"
                min={filter.min}
                max={filter.max}
                step={filter.step || 0.01}
                value={filter.value[0]}
                onChange={(e) => updateFilter(filter.id, [parseFloat(e.target.value), filter.value[1]])}
                className="w-20 px-2 py-1 border rounded"
              />
              <span>-</span>
              <input
                type="number"
                min={filter.min}
                max={filter.max}
                step={filter.step || 0.01}
                value={filter.value[1]}
                onChange={(e) => updateFilter(filter.id, [filter.value[0], parseFloat(e.target.value)])}
                className="w-20 px-2 py-1 border rounded"
              />
            </div>
          </div>
        );

      case 'multiselect':
        return (
          <div className="space-y-2">
            <span className="text-sm">{filter.description}</span>
            <div className="grid grid-cols-2 gap-2">
              {filter.options.map(option => (
                <label key={option} className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    checked={filter.value.includes(option)}
                    onChange={(e) => {
                      const newValue = e.target.checked
                        ? [...filter.value, option]
                        : filter.value.filter(v => v !== option);
                      updateFilter(filter.id, newValue);
                    }}
                    className="w-4 h-4 rounded border-gray-300"
                  />
                  <span className="text-sm">{option}</span>
                </label>
              ))}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="p-4 border-b last:border-b-0">
      <div className="flex items-start space-x-3">
        <input
          type="checkbox"
          checked={filter.enabled}
          onChange={() => toggleFilter(filter.id)}
          className="mt-1 w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
        />
        <div className="flex-1">
          <h4 className="font-medium text-gray-900">{filter.name}</h4>
          {renderControl()}
        </div>
      </div>
    </div>
  );
};