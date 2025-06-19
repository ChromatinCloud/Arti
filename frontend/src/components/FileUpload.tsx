import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Typography,
  LinearProgress,
  Alert,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material'
import { CloudUpload as UploadIcon } from '@mui/icons-material'
import { useDropzone } from 'react-dropzone'
import { jobsAPI } from '../services/api'

interface FileUploadProps {
  open: boolean
  onClose: () => void
  onSuccess: (jobId: string) => void
}

const CANCER_TYPES = [
  'melanoma',
  'lung_adenocarcinoma',
  'lung_squamous',
  'breast',
  'colorectal',
  'prostate',
  'pancreatic',
  'ovarian',
  'glioblastoma',
  'leukemia_aml',
  'leukemia_cll',
  'lymphoma',
  'other',
]

const FileUpload: React.FC<FileUploadProps> = ({ open, onClose, onSuccess }) => {
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [cancerType, setCancerType] = useState('')
  const [caseUid, setCaseUid] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        const vcfFile = acceptedFiles[0]
        if (vcfFile.name.endsWith('.vcf') || vcfFile.name.endsWith('.vcf.gz')) {
          setFile(vcfFile)
          setName(vcfFile.name.replace(/\.(vcf|vcf\.gz)$/, ''))
          setError('')
        } else {
          setError('Please upload a VCF file')
        }
      }
    },
    accept: {
      'text/plain': ['.vcf'],
      'application/gzip': ['.gz'],
    },
    maxFiles: 1,
  })

  const handleSubmit = async () => {
    if (!file || !name) {
      setError('Please provide a file and name')
      return
    }

    setUploading(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('name', name)
      if (description) formData.append('description', description)
      if (cancerType) formData.append('cancer_type', cancerType)
      if (caseUid) formData.append('case_uid', caseUid)

      const response = await jobsAPI.create(formData)
      onSuccess(response.data.job_id)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed')
      setUploading(false)
    }
  }

  const handleClose = () => {
    if (!uploading) {
      setFile(null)
      setName('')
      setDescription('')
      setCancerType('')
      setCaseUid('')
      setError('')
      onClose()
    }
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Upload VCF for Annotation</DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box
          {...getRootProps()}
          sx={{
            border: '2px dashed #ccc',
            borderRadius: 2,
            p: 3,
            textAlign: 'center',
            cursor: 'pointer',
            bgcolor: isDragActive ? 'action.hover' : 'background.paper',
            mb: 2,
          }}
        >
          <input {...getInputProps()} />
          <UploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 1 }} />
          {file ? (
            <Typography>{file.name}</Typography>
          ) : (
            <Typography color="text.secondary">
              {isDragActive
                ? 'Drop the VCF file here...'
                : 'Drag & drop a VCF file here, or click to select'}
            </Typography>
          )}
        </Box>

        <TextField
          fullWidth
          label="Job Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          margin="normal"
          required
          disabled={uploading}
        />

        <TextField
          fullWidth
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          margin="normal"
          multiline
          rows={2}
          disabled={uploading}
        />

        <FormControl fullWidth margin="normal">
          <InputLabel>Cancer Type</InputLabel>
          <Select
            value={cancerType}
            onChange={(e) => setCancerType(e.target.value)}
            disabled={uploading}
          >
            <MenuItem value="">
              <em>None</em>
            </MenuItem>
            {CANCER_TYPES.map((type) => (
              <MenuItem key={type} value={type}>
                {type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, ' ')}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <TextField
          fullWidth
          label="Case UID"
          value={caseUid}
          onChange={(e) => setCaseUid(e.target.value)}
          margin="normal"
          disabled={uploading}
          helperText="Optional: Patient or sample identifier"
        />

        {uploading && (
          <Box sx={{ mt: 2 }}>
            <LinearProgress />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Uploading file and creating job...
            </Typography>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={uploading}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={!file || !name || uploading}
        >
          Start Analysis
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default FileUpload