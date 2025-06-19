import React, { useState, useCallback } from 'react';
import { Upload, AlertCircle, CheckCircle, Info } from 'lucide-react';
import { useFilteringStore } from '../store/filteringStore';

interface VCFUploaderProps {
  mode: 'tumor-only' | 'tumor-normal';
}

export const VCFUploader: React.FC<VCFUploaderProps> = ({ mode }) => {
  const [dragActive, setDragActive] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);
  
  const { setInputVcf } = useFilteringStore();

  const validateFile = (file: File): Promise<{ valid: boolean; error?: string; warnings?: string[] }> => {
    return new Promise((resolve) => {
      // Basic file validation
      if (!file.name.endsWith('.vcf') && !file.name.endsWith('.vcf.gz')) {
        resolve({ valid: false, error: 'File must be a VCF file (.vcf or .vcf.gz)' });
        return;
      }

      if (file.size === 0) {
        resolve({ valid: false, error: 'File is empty' });
        return;
      }

      if (file.size > 5 * 1024 * 1024 * 1024) { // 5GB limit
        resolve({ valid: false, error: 'File size exceeds 5GB limit' });
        return;
      }

      // Read first few lines to validate VCF format
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result as string;
        const lines = content.split('\n').slice(0, 100); // Read first 100 lines
        
        // Check for VCF format header
        if (!lines[0].startsWith('##fileformat=VCF')) {
          resolve({ valid: false, error: 'Invalid VCF format: missing ##fileformat header' });
          return;
        }

        // Count samples
        const headerLine = lines.find(line => line.startsWith('#CHROM'));
        if (!headerLine) {
          resolve({ valid: false, error: 'Invalid VCF format: missing #CHROM header' });
          return;
        }

        const samples = headerLine.split('\t').slice(9); // Samples start after FORMAT column
        const sampleCount = samples.length;

        // Mode-specific validation
        if (mode === 'tumor-only' && sampleCount > 1) {
          resolve({ 
            valid: false, 
            error: `Tumor-only mode requires single-sample VCF. Found ${sampleCount} samples: ${samples.join(', ')}` 
          });
          return;
        }

        const warnings: string[] = [];

        // Check for tumor-normal specific fields in multi-sample VCF
        if (mode === 'tumor-normal' && sampleCount > 2) {
          warnings.push(`VCF contains ${sampleCount} samples. Only the first two will be used as tumor and normal.`);
        }

        // Try to identify tumor/normal samples
        if (mode === 'tumor-normal' && sampleCount >= 2) {
          const hasTumorNormalNames = samples.some(s => 
            s.toLowerCase().includes('tumor') || s.toLowerCase().includes('normal')
          );
          if (!hasTumorNormalNames) {
            warnings.push(
              `Could not identify tumor/normal samples from names (${samples.join(', ')}). ` +
              'Will assume first sample is tumor, second is normal.'
            );
          }
        }

        resolve({ valid: true, warnings });
      };

      // Read first 1MB of file
      const blob = file.slice(0, 1024 * 1024);
      reader.readAsText(blob);
    });
  };

  const handleFiles = useCallback(async (files: FileList) => {
    setUploadError(null);
    setValidationWarnings([]);

    // Convert FileList to Array
    const fileArray = Array.from(files);

    // Mode-specific file count validation
    if (mode === 'tumor-only' && fileArray.length > 1) {
      setUploadError('Tumor-only mode accepts only one VCF file');
      return;
    }

    if (mode === 'tumor-normal' && fileArray.length > 2) {
      setUploadError('Tumor-normal mode accepts maximum 2 VCF files (tumor and normal)');
      return;
    }

    // Validate each file
    const allWarnings: string[] = [];
    for (const file of fileArray) {
      const validation = await validateFile(file);
      if (!validation.valid) {
        setUploadError(validation.error || 'Invalid file');
        return;
      }
      if (validation.warnings) {
        allWarnings.push(...validation.warnings);
      }
    }

    // Store files and warnings
    setUploadedFiles(fileArray);
    setValidationWarnings(allWarnings);

    // Update store with file paths (in real app, would upload and get server paths)
    const filePaths = fileArray.map(f => f.name).join(',');
    setInputVcf(filePaths);
  }, [mode, setInputVcf]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  }, [handleFiles]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  }, [handleFiles]);

  return (
    <div className="w-full">
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-8 text-center transition-all
          ${dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
          ${uploadError ? 'border-red-500 bg-red-50' : ''}
          ${uploadedFiles.length > 0 && !uploadError ? 'border-green-500 bg-green-50' : ''}
        `}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <input
          type="file"
          id="vcf-upload"
          className="hidden"
          accept=".vcf,.vcf.gz"
          multiple={mode === 'tumor-normal'}
          onChange={handleFileInput}
        />
        
        <label htmlFor="vcf-upload" className="cursor-pointer">
          {uploadedFiles.length === 0 && !uploadError && (
            <>
              <Upload className="mx-auto h-12 w-12 text-gray-400" />
              <p className="mt-2 text-sm text-gray-600">
                Drop VCF file{mode === 'tumor-normal' ? '(s)' : ''} here or click to browse
              </p>
              <p className="mt-1 text-xs text-gray-500">
                {mode === 'tumor-only' 
                  ? 'Single-sample VCF required' 
                  : 'Multi-sample VCF or 2 separate files accepted'}
              </p>
            </>
          )}

          {uploadError && (
            <>
              <AlertCircle className="mx-auto h-12 w-12 text-red-500" />
              <p className="mt-2 text-sm font-semibold text-red-700">{uploadError}</p>
              <p className="mt-1 text-xs text-gray-600">Click to try again</p>
            </>
          )}

          {uploadedFiles.length > 0 && !uploadError && (
            <>
              <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
              <p className="mt-2 text-sm font-semibold text-green-700">
                {uploadedFiles.length === 1 
                  ? `Uploaded: ${uploadedFiles[0].name}`
                  : `Uploaded ${uploadedFiles.length} files`}
              </p>
              {uploadedFiles.length > 1 && (
                <ul className="mt-1 text-xs text-gray-600">
                  {uploadedFiles.map((f, i) => (
                    <li key={i}>{f.name}</li>
                  ))}
                </ul>
              )}
            </>
          )}
        </label>
      </div>

      {validationWarnings.length > 0 && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <div className="flex">
            <Info className="h-5 w-5 text-yellow-600 flex-shrink-0" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">Validation Warnings</h3>
              <ul className="mt-1 text-xs text-yellow-700 list-disc list-inside">
                {validationWarnings.map((warning, i) => (
                  <li key={i}>{warning}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {mode === 'tumor-normal' && uploadedFiles.length === 1 && (
        <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-md">
          <div className="flex">
            <Info className="h-5 w-5 text-blue-600 flex-shrink-0" />
            <div className="ml-3 text-xs">
              <p className="text-blue-800">
                Multi-sample VCF detected. If samples are not clearly labeled as tumor/normal, 
                you can specify sample names in the metadata section below.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};