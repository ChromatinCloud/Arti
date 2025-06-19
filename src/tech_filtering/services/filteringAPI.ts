import axios from 'axios';
import { FilteringRequest, FilteringResponse } from '../types/filtering.types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export async function applyFiltersAPI(request: FilteringRequest): Promise<FilteringResponse> {
  try {
    const response = await axios.post<FilteringResponse>(
      `${API_BASE_URL}/api/v1/tech-filtering/apply`,
      request,
      {
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 60000 // 60 second timeout for bcftools operations
      }
    );

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message
      };
    }
    return {
      success: false,
      error: 'Unknown error occurred'
    };
  }
}

export async function getVariantCount(vcfPath: string): Promise<number> {
  try {
    const response = await axios.get<{ count: number }>(
      `${API_BASE_URL}/api/v1/tech-filtering/variant-count`,
      {
        params: { vcf_path: vcfPath }
      }
    );
    return response.data.count;
  } catch (error) {
    console.error('Failed to get variant count:', error);
    return 0;
  }
}

export async function downloadFilteredVcf(outputPath: string): Promise<void> {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/v1/tech-filtering/download`,
      {
        params: { file: outputPath },
        responseType: 'blob'
      }
    );

    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'filtered.vcf');
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (error) {
    console.error('Failed to download VCF:', error);
    throw error;
  }
}

export async function sendToArti(
  vcfPath: string, 
  mode: string,
  metadata?: FilteringRequest['metadata']
): Promise<{
  success: boolean;
  jobId?: string;
  caseUid?: string;
  error?: string;
}> {
  try {
    // Use OncoTree code if provided, otherwise fall back to demo cancer types
    let cancerType = metadata?.oncotreeCode;
    if (!cancerType) {
      const cancerTypeMap: Record<string, string> = {
        'tumor-only': 'SKCM',  // Melanoma
        'tumor-normal': 'LUAD'  // Lung adenocarcinoma
      };
      cancerType = cancerTypeMap[mode] || 'SKCM';
    }

    const response = await axios.post(
      `${API_BASE_URL}/api/v1/variants/annotate-file`,
      {
        vcf_path: vcfPath,
        case_uid: metadata?.caseID || `TECH_FILTER_${Date.now()}`,
        patient_uid: metadata?.patientUID,
        cancer_type: cancerType,
        analysis_type: mode.replace('-', '_'), // Convert 'tumor-only' to 'tumor_only'
        tumor_purity: metadata?.tumorPurity,
        specimen_type: metadata?.specimenType
      }
    );

    if (response.data.success) {
      return {
        success: true,
        jobId: response.data.data.job_id,
        caseUid: response.data.data.case_uid
      };
    }

    return {
      success: false,
      error: response.data.error || 'Failed to submit to Arti'
    };
  } catch (error) {
    return {
      success: false,
      error: 'Failed to connect to Arti API'
    };
  }
}