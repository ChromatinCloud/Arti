import React, { useState } from 'react';
import { useInterpretationStore } from '../store/interpretationStore';
import { 
  FileText, 
  Save, 
  Send, 
  History,
  MessageSquare,
  Settings,
  ChevronDown,
  User,
  Calendar,
  Tag
} from 'lucide-react';

export const InterpretationPanel: React.FC = () => {
  const { selectedVariant } = useInterpretationStore();
  const [activeTab, setActiveTab] = useState<'actions' | 'history' | 'notes' | 'templates'>('actions');
  const [note, setNote] = useState('');

  if (!selectedVariant) {
    return (
      <div className="h-full flex items-center justify-center text-gray-500 p-6">
        <div className="text-center">
          <FileText className="h-12 w-12 mx-auto mb-2 text-gray-300" />
          <p>Select a variant to begin interpretation</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4">
        <h3 className="font-semibold text-gray-900">Interpretation Tools</h3>
        <p className="text-sm text-gray-500 mt-1">
          {selectedVariant.gene.symbol} {selectedVariant.hgvs.protein}
        </p>
      </div>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="flex">
          {[
            { id: 'actions', label: 'Actions' },
            { id: 'templates', label: 'Templates' },
            { id: 'history', label: 'History' },
            { id: 'notes', label: 'Notes' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex-1 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'actions' && (
          <div className="p-4 space-y-4">
            {/* Quick Actions */}
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-3">Quick Actions</h4>
              <div className="space-y-2">
                <button className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium flex items-center justify-center">
                  <Save className="h-4 w-4 mr-2" />
                  Save Interpretation
                </button>
                <button className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm font-medium flex items-center justify-center">
                  <Send className="h-4 w-4 mr-2" />
                  Submit for Review
                </button>
                <button className="w-full px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 text-sm font-medium flex items-center justify-center">
                  <FileText className="h-4 w-4 mr-2" />
                  Generate Report
                </button>
              </div>
            </div>

            {/* Status Update */}
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-3">Update Status</h4>
              <select className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="reviewed">Reviewed</option>
                <option value="approved">Approved</option>
              </select>
            </div>

            {/* Assign To */}
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-3">Assign To</h4>
              <div className="flex items-center space-x-2">
                <User className="h-4 w-4 text-gray-400" />
                <select className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option>Dr. Smith</option>
                  <option>Dr. Johnson</option>
                  <option>Dr. Williams</option>
                </select>
              </div>
            </div>

            {/* Tags */}
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-3">Tags</h4>
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded-full text-xs">
                  Actionable
                </span>
                <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs">
                  FDA Approved
                </span>
                <button className="px-2 py-1 border border-gray-300 text-gray-600 rounded-full text-xs hover:bg-gray-50">
                  + Add Tag
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="p-4">
            <div className="space-y-3">
              {[
                { 
                  user: 'Dr. Smith', 
                  action: 'Updated tier to I-A', 
                  time: '2 hours ago',
                  details: 'Based on OncoKB Level 1 evidence'
                },
                { 
                  user: 'System', 
                  action: 'Automated annotation complete', 
                  time: '3 hours ago',
                  details: '4 knowledge bases queried'
                },
                { 
                  user: 'Dr. Johnson', 
                  action: 'Added clinical note', 
                  time: 'Yesterday',
                  details: 'Patient has prior response to BRAF inhibitors'
                }
              ].map((entry, idx) => (
                <div key={idx} className="border-l-2 border-gray-200 pl-4 pb-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-medium text-sm text-gray-900">{entry.user}</div>
                      <div className="text-sm text-gray-600">{entry.action}</div>
                      {entry.details && (
                        <div className="text-xs text-gray-500 mt-1">{entry.details}</div>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 flex items-center">
                      <Calendar className="h-3 w-3 mr-1" />
                      {entry.time}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'templates' && (
          <div className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-gray-900">Available Templates</h4>
              <select className="text-xs border border-gray-300 rounded px-2 py-1">
                <option>All Diseases</option>
                <option>Melanoma</option>
                <option>Colorectal</option>
                <option>Pan-Cancer</option>
              </select>
            </div>
            
            <div className="space-y-2">
              {selectedVariant?.interpretations.map((interp) => (
                <div key={interp.id} className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="font-medium text-sm text-gray-900">{interp.templateName}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        Confidence: {(interp.confidence * 100).toFixed(0)}% • 
                        {interp.diseaseContext?.join(', ')}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        Modified: {new Date(interp.lastModified || '').toLocaleDateString()}
                      </div>
                    </div>
                    <div className="flex items-center space-x-1 ml-2">
                      <button className="p-1 text-gray-400 hover:text-gray-600">
                        <Copy className="h-3 w-3" />
                      </button>
                      <button className="p-1 text-gray-400 hover:text-gray-600">
                        <Edit3 className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
              
              <button className="w-full p-3 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-gray-400 hover:text-gray-600 text-sm">
                + Create New Template
              </button>
            </div>
          </div>
        )}

        {activeTab === 'notes' && (
          <div className="p-4 space-y-4">
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-3">Add Note</h4>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Enter clinical notes or observations..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                rows={4}
              />
              <button className="mt-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium">
                Add Note
              </button>
            </div>

            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-3">Previous Notes</h4>
              <div className="space-y-3">
                {[
                  {
                    user: 'Dr. Johnson',
                    time: '1 day ago',
                    note: 'Consider combination therapy given tumor burden'
                  },
                  {
                    user: 'Dr. Smith',
                    time: '3 days ago',
                    note: 'Patient eligible for clinical trial NCT04585815'
                  }
                ].map((note, idx) => (
                  <div key={idx} className="bg-gray-50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-900">{note.user}</span>
                      <span className="text-xs text-gray-500">{note.time}</span>
                    </div>
                    <p className="text-sm text-gray-700">{note.note}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="bg-white border-t border-gray-200 p-4">
        <button className="w-full px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 text-sm font-medium flex items-center justify-center">
          <Settings className="h-4 w-4 mr-2" />
          Interpretation Settings
        </button>
      </div>
    </div>
  );
};