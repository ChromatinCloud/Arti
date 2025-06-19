import React from 'react';
import { Annotation } from '../../types/variant.types';
import { useInterpretationStore } from '../../store/interpretationStore';
import { 
  ChevronDown, 
  ChevronRight, 
  FileText, 
  Database,
  Activity,
  Brain,
  Pill,
  AlertTriangle
} from 'lucide-react';

interface AnnotationsCardProps {
  annotations: Annotation[];
}

export const AnnotationsCard: React.FC<AnnotationsCardProps> = ({ annotations }) => {
  const { expandedSections, toggleSection } = useInterpretationStore();
  const isExpanded = expandedSections.has('annotations');

  const getAnnotationIcon = (type: string) => {
    switch (type) {
      case 'therapeutic': return <Pill className="h-4 w-4" />;
      case 'pathogenicity': return <AlertTriangle className="h-4 w-4" />;
      case 'frequency': return <Activity className="h-4 w-4" />;
      case 'functional': return <Brain className="h-4 w-4" />;
      default: return <Database className="h-4 w-4" />;
    }
  };

  const getSourceColor = (source: string) => {
    switch (source) {
      case 'OncoKB': return 'bg-purple-100 text-purple-700';
      case 'ClinVar': return 'bg-green-100 text-green-700';
      case 'COSMIC': return 'bg-orange-100 text-orange-700';
      case 'Functional': return 'bg-blue-100 text-blue-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const renderAnnotationContent = (annotation: Annotation) => {
    switch (annotation.type) {
      case 'therapeutic':
        return (
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium">Level:</span>
              <span className="px-2 py-0.5 bg-purple-600 text-white rounded text-xs font-semibold">
                {annotation.data.level}
              </span>
            </div>
            <div>
              <span className="text-sm font-medium">Drugs:</span>
              <div className="mt-1 flex flex-wrap gap-1">
                {annotation.data.drugs?.map((drug: string) => (
                  <span key={drug} className="px-2 py-1 bg-gray-100 rounded-full text-xs">
                    {drug}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <span className="text-sm font-medium">Cancer Types:</span>
              <div className="mt-1 text-sm text-gray-600">
                {annotation.data.cancerTypes?.join(', ')}
              </div>
            </div>
          </div>
        );

      case 'pathogenicity':
        return (
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium">Clinical Significance:</span>
              <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                annotation.data.clinicalSignificance === 'Pathogenic' 
                  ? 'bg-red-100 text-red-700' 
                  : 'bg-yellow-100 text-yellow-700'
              }`}>
                {annotation.data.clinicalSignificance}
              </span>
            </div>
            <div className="text-sm">
              <span className="font-medium">Review Status:</span> {annotation.data.reviewStatus}
            </div>
            <div className="text-sm">
              <span className="font-medium">Conditions:</span> {annotation.data.conditions?.join(', ')}
            </div>
          </div>
        );

      case 'frequency':
        return (
          <div className="space-y-2">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <span className="text-sm font-medium">Hotspot:</span>
                <span className={`px-2 py-0.5 rounded text-xs ${
                  annotation.data.hotspot ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'
                }`}>
                  {annotation.data.hotspot ? 'Yes' : 'No'}
                </span>
              </div>
              <div className="text-sm">
                <span className="font-medium">Samples:</span> {annotation.data.sampleCount?.toLocaleString()}
              </div>
            </div>
            {annotation.data.cancerTypeDistribution && (
              <div className="space-y-1">
                <span className="text-sm font-medium">Distribution:</span>
                {Object.entries(annotation.data.cancerTypeDistribution).map(([cancer, freq]) => (
                  <div key={cancer} className="flex items-center space-x-2">
                    <div className="w-20 text-xs text-gray-600">{cancer}</div>
                    <div className="flex-1 bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-orange-500 h-2 rounded-full"
                        style={{ width: `${freq * 100}%` }}
                      />
                    </div>
                    <div className="text-xs text-gray-600 w-12 text-right">
                      {(freq * 100).toFixed(0)}%
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );

      case 'functional':
        return (
          <div className="grid grid-cols-2 gap-3 text-sm">
            {annotation.data.alphaMissense && (
              <div>
                <div className="text-xs text-gray-500">AlphaMissense</div>
                <div className="font-medium">{annotation.data.alphaMissense.score.toFixed(3)}</div>
                <div className={`text-xs ${
                  annotation.data.alphaMissense.prediction === 'Pathogenic' 
                    ? 'text-red-600' 
                    : 'text-green-600'
                }`}>
                  {annotation.data.alphaMissense.prediction}
                </div>
              </div>
            )}
            {annotation.data.revel && (
              <div>
                <div className="text-xs text-gray-500">REVEL</div>
                <div className="font-medium">{annotation.data.revel.score.toFixed(3)}</div>
              </div>
            )}
            {annotation.data.cadd && (
              <div>
                <div className="text-xs text-gray-500">CADD</div>
                <div className="font-medium">{annotation.data.cadd.score.toFixed(1)}</div>
              </div>
            )}
            {annotation.data.conservation && (
              <div>
                <div className="text-xs text-gray-500">Conservation</div>
                <div className="text-xs">GERP: {annotation.data.conservation.gerp.toFixed(2)}</div>
                <div className="text-xs">PhyloP: {annotation.data.conservation.phyloP.toFixed(2)}</div>
              </div>
            )}
          </div>
        );

      default:
        return <pre className="text-xs">{JSON.stringify(annotation.data, null, 2)}</pre>;
    }
  };

  return (
    <div className="evidence-card">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => toggleSection('annotations')}
      >
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
            <FileText className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Evidence Collection</h3>
            <p className="text-sm text-gray-500">{annotations.length} annotations from knowledge bases</p>
          </div>
        </div>
        {isExpanded ? <ChevronDown className="h-5 w-5 text-gray-400" /> : <ChevronRight className="h-5 w-5 text-gray-400" />}
      </div>

      {isExpanded && (
        <div className="mt-4 space-y-3">
          {annotations.map((annotation, index) => (
            <div key={index} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center space-x-2">
                  {getAnnotationIcon(annotation.type)}
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getSourceColor(annotation.source)}`}>
                    {annotation.source}
                  </span>
                  <span className="text-xs text-gray-500">v{annotation.version}</span>
                </div>
                <div className="text-sm text-gray-500">
                  Confidence: {(annotation.confidence * 100).toFixed(0)}%
                </div>
              </div>
              
              {renderAnnotationContent(annotation)}
            </div>
          ))}

          {annotations.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <Database className="h-12 w-12 mx-auto mb-2 text-gray-300" />
              <p>No annotations found</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};