import React, { useState } from 'react';
import { Interpretation } from '../../types/variant.types';
import { useInterpretationStore } from '../../store/interpretationStore';
import { 
  ChevronDown, 
  ChevronRight, 
  BookOpen,
  Copy,
  Edit3,
  Check,
  FileText,
  Sparkles,
  Plus,
  Filter,
  SortDesc,
  Calendar,
  Stethoscope,
  X
} from 'lucide-react';

interface InterpretationCardProps {
  interpretations: Interpretation[];
}

export const InterpretationCard: React.FC<InterpretationCardProps> = ({ interpretations }) => {
  const { expandedSections, toggleSection, currentCase } = useInterpretationStore();
  const isExpanded = expandedSections.has('interpretation');
  const [selectedInterpretation, setSelectedInterpretation] = useState<string | null>(
    interpretations.length > 0 ? interpretations[0].id : null
  );
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showCustomForm, setShowCustomForm] = useState(false);
  const [customInterpretation, setCustomInterpretation] = useState('');
  const [sortBy, setSortBy] = useState<'recent' | 'confidence' | 'disease'>('recent');
  const [filterByDisease, setFilterByDisease] = useState(false);

  const handleCopy = (content: string, id: string) => {
    navigator.clipboard.writeText(content);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleSaveCustom = () => {
    if (customInterpretation.trim()) {
      // In real app, would save to backend
      console.log('Saving custom interpretation:', customInterpretation);
      setShowCustomForm(false);
      setCustomInterpretation('');
    }
  };

  // Filter interpretations by disease if enabled
  const filteredInterpretations = filterByDisease 
    ? interpretations.filter(interp => 
        interp.diseaseContext?.includes(currentCase?.cancerType || '') ||
        interp.content.toLowerCase().includes(currentCase?.cancerType?.toLowerCase() || ''))
    : interpretations;

  // Sort interpretations
  const sortedInterpretations = [...filteredInterpretations].sort((a, b) => {
    switch (sortBy) {
      case 'recent':
        return new Date(b.lastModified || 0).getTime() - new Date(a.lastModified || 0).getTime();
      case 'confidence':
        return b.confidence - a.confidence;
      case 'disease':
        // Sort by disease relevance (if has disease context matching current case)
        const aRelevant = a.diseaseContext?.includes(currentCase?.cancerType || '') ? 1 : 0;
        const bRelevant = b.diseaseContext?.includes(currentCase?.cancerType || '') ? 1 : 0;
        return bRelevant - aRelevant;
      default:
        return 0;
    }
  });

  const selected = sortedInterpretations.find(i => i.id === selectedInterpretation);

  return (
    <div className="evidence-card">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => toggleSection('interpretation')}
      >
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
            <BookOpen className="h-5 w-5 text-indigo-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Clinical Interpretation</h3>
            <p className="text-sm text-gray-500">
              {interpretations.length} template{interpretations.length !== 1 ? 's' : ''} available
            </p>
          </div>
        </div>
        {isExpanded ? <ChevronDown className="h-5 w-5 text-gray-400" /> : <ChevronRight className="h-5 w-5 text-gray-400" />}
      </div>

      {isExpanded && (
        <div className="mt-4 space-y-4">
          {/* Controls */}
          <div className="flex items-center justify-between space-x-2">
            <div className="flex items-center space-x-2">
              {/* Sort Dropdown */}
              <div className="relative">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="pl-8 pr-3 py-1.5 text-xs border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="recent">Most Recent</option>
                  <option value="confidence">Highest Confidence</option>
                  <option value="disease">Disease Relevance</option>
                </select>
                <SortDesc className="absolute left-2 top-1/2 transform -translate-y-1/2 h-3 w-3 text-gray-400" />
              </div>

              {/* Disease Filter Toggle */}
              <button
                onClick={() => setFilterByDisease(!filterByDisease)}
                className={`flex items-center space-x-1 px-2 py-1.5 text-xs rounded-md border transition-colors ${
                  filterByDisease 
                    ? 'bg-blue-50 border-blue-300 text-blue-700' 
                    : 'bg-white border-gray-300 text-gray-600 hover:bg-gray-50'
                }`}
              >
                <Stethoscope className="h-3 w-3" />
                <span>{currentCase?.cancerType || 'Disease'}</span>
              </button>
            </div>

            {/* Add Custom Button */}
            <button
              onClick={() => setShowCustomForm(true)}
              className="flex items-center space-x-1 px-3 py-1.5 text-xs bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            >
              <Plus className="h-3 w-3" />
              <span>Custom</span>
            </button>
          </div>

          {/* Custom Interpretation Form */}
          {showCustomForm && (
            <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-gray-900">Custom Interpretation</h4>
                <button
                  onClick={() => setShowCustomForm(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <textarea
                value={customInterpretation}
                onChange={(e) => setCustomInterpretation(e.target.value)}
                placeholder="Enter your clinical interpretation..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={6}
              />
              <div className="flex justify-end space-x-2 mt-3">
                <button
                  onClick={() => setShowCustomForm(false)}
                  className="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveCustom}
                  className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
                >
                  Save Interpretation
                </button>
              </div>
            </div>
          )}

          {sortedInterpretations.length > 0 ? (
            <>
              {/* Template Selection */}
              {sortedInterpretations.length > 1 && (
                <div className="space-y-2">
                  <div className="text-xs text-gray-500">
                    {filteredInterpretations.length !== interpretations.length && (
                      <span>Showing {filteredInterpretations.length} of {interpretations.length} interpretations</span>
                    )}
                  </div>
                  <div className="flex space-x-2 p-1 bg-gray-100 rounded-lg">
                    {sortedInterpretations.slice(0, 3).map((interp) => (
                      <button
                        key={interp.id}
                        onClick={() => setSelectedInterpretation(interp.id)}
                        className={`flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                          selectedInterpretation === interp.id
                            ? 'bg-white text-gray-900 shadow-sm'
                            : 'text-gray-600 hover:text-gray-900'
                        }`}
                      >
                        <div className="truncate">{interp.templateName}</div>
                        <div className="text-xs text-gray-500">
                          {(interp.confidence * 100).toFixed(0)}%
                        </div>
                      </button>
                    ))}
                    {sortedInterpretations.length > 3 && (
                      <div className="flex items-center px-2 text-xs text-gray-500">
                        +{sortedInterpretations.length - 3} more
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Selected Interpretation */}
              {selected && (
                <div className="space-y-4">
                  {/* Header */}
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="font-medium text-gray-900">{selected.templateName}</h4>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className="text-sm text-gray-500">
                          Confidence: {(selected.confidence * 100).toFixed(0)}%
                        </span>
                        <span className="text-gray-300">•</span>
                        <span className="text-sm text-gray-500">
                          Template ID: {selected.templateId}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleCopy(selected.content, selected.id)}
                        className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                        title="Copy to clipboard"
                      >
                        {copiedId === selected.id ? (
                          <Check className="h-4 w-4 text-green-600" />
                        ) : (
                          <Copy className="h-4 w-4" />
                        )}
                      </button>
                      <button
                        className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                        title="Edit interpretation"
                      >
                        <Edit3 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="prose prose-sm max-w-none">
                    <div className="bg-gray-50 rounded-lg p-4 text-gray-700 whitespace-pre-wrap">
                      {selected.content}
                    </div>
                  </div>

                  {/* Evidence Tags */}
                  {selected.evidence.length > 0 && (
                    <div>
                      <div className="text-xs font-medium text-gray-700 mb-2">Key Evidence:</div>
                      <div className="flex flex-wrap gap-2">
                        {selected.evidence.map((ev, idx) => (
                          <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs">
                            {ev}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Citations */}
                  {selected.citations.length > 0 && (
                    <div>
                      <div className="text-xs font-medium text-gray-700 mb-2">References:</div>
                      <div className="space-y-1">
                        {selected.citations.map((citation) => (
                          <div key={citation.id} className="flex items-center space-x-2 text-sm">
                            <FileText className="h-3 w-3 text-gray-400" />
                            <span className="text-gray-600">{citation.text}</span>
                            {citation.pmid && (
                              <a
                                href={`https://pubmed.ncbi.nlm.nih.gov/${citation.pmid}/`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:underline text-xs"
                              >
                                PMID: {citation.pmid}
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-8">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-100 rounded-full mb-4">
                <Sparkles className="h-8 w-8 text-gray-400" />
              </div>
              <p className="text-gray-500 mb-4">
                {interpretations.length === 0 
                  ? 'No interpretation templates available'
                  : `No interpretations match current filters`
                }
              </p>
              <div className="space-x-2">
                {interpretations.length === 0 && (
                  <button className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 text-sm font-medium">
                    Generate Interpretation
                  </button>
                )}
                <button 
                  onClick={() => setShowCustomForm(true)}
                  className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 text-sm font-medium"
                >
                  Write Custom
                </button>
                {filterByDisease && (
                  <button 
                    onClick={() => setFilterByDisease(false)}
                    className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 text-sm font-medium"
                  >
                    Show All
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};