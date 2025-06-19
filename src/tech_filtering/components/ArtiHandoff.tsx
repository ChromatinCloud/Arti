import React, { useState } from 'react';
import { useFilteringStore } from '../store/filteringStore';
import { sendToArti } from '../services/filteringAPI';
import { CheckCircleIcon, XCircleIcon } from './Icons';

interface ArtiHandoffProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ArtiHandoff: React.FC<ArtiHandoffProps> = ({ isOpen, onClose }) => {
  const { outputVcf, variantCounts, mode, metadata } = useFilteringStore();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  const handleSendToArti = async () => {
    if (!outputVcf) return;

    setIsSubmitting(true);
    setSubmitResult(null);

    try {
      const result = await sendToArti(outputVcf, mode, metadata);
      
      if (result.success) {
        setSubmitResult({
          success: true,
          message: `Successfully submitted to Arti! Job ID: ${result.jobId}`
        });
        
        // Redirect to Arti after 2 seconds
        setTimeout(() => {
          window.location.href = `/arti/cases/${result.caseUid}`;
        }, 2000);
      } else {
        setSubmitResult({
          success: false,
          message: result.error || 'Failed to submit to Arti'
        });
      }
    } catch (error) {
      setSubmitResult({
        success: false,
        message: 'Error connecting to Arti'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Technical Filtering Complete!
        </h2>
        
        <div className="mb-6">
          <p className="text-gray-700 mb-2">
            Successfully filtered your variants:
          </p>
          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="text-lg font-medium text-gray-900">
              {variantCounts.filtered.toLocaleString()} variants
            </div>
            <div className="text-sm text-gray-600">
              ready for clinical interpretation
            </div>
          </div>
        </div>

        {submitResult && (
          <div className={`mb-4 p-4 rounded-lg flex items-start space-x-3 ${
            submitResult.success ? 'bg-green-50' : 'bg-red-50'
          }`}>
            {submitResult.success ? (
              <CheckCircleIcon className="w-5 h-5 text-green-600 mt-0.5" />
            ) : (
              <XCircleIcon className="w-5 h-5 text-red-600 mt-0.5" />
            )}
            <div className={submitResult.success ? 'text-green-800' : 'text-red-800'}>
              {submitResult.message}
            </div>
          </div>
        )}

        <div className="flex space-x-3">
          <button
            onClick={handleSendToArti}
            disabled={isSubmitting || submitResult?.success}
            className={`flex-1 py-2 px-4 rounded-lg font-medium transition-colors ${
              isSubmitting || submitResult?.success
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-primary text-white hover:bg-primary-dark'
            }`}
          >
            {isSubmitting ? 'Submitting...' : 'Go to Arti?'}
          </button>
          
          <button
            onClick={onClose}
            className="flex-1 py-2 px-4 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};