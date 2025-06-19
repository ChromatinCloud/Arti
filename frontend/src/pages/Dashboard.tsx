import React from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Button,
  Paper,
  LinearProgress,
} from '@mui/material'
import {
  CloudUpload as UploadIcon,
  Assessment as AssessmentIcon,
  Science as ScienceIcon,
  CheckCircle as CheckIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { jobsAPI } from '../services/api'
import FileUpload from '../components/FileUpload'

const Dashboard: React.FC = () => {
  const navigate = useNavigate()
  const [uploadOpen, setUploadOpen] = React.useState(false)

  // Fetch recent jobs
  const { data: jobsData } = useQuery({
    queryKey: ['recentJobs'],
    queryFn: () => jobsAPI.list({ per_page: 5 }),
    refetchInterval: 5000
  })

  const stats = {
    totalJobs: jobsData?.data.total || 0,
    runningJobs: jobsData?.data.jobs.filter((j: any) => j.status === 'running').length || 0,
    completedJobs: jobsData?.data.jobs.filter((j: any) => j.status === 'completed').length || 0,
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      <Grid container spacing={3}>
        {/* Quick Actions */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <UploadIcon color="primary" sx={{ mr: 2 }} />
                <Typography variant="h6">New Analysis</Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" mb={2}>
                Upload a VCF file to start variant annotation
              </Typography>
              <Button
                variant="contained"
                fullWidth
                startIcon={<UploadIcon />}
                onClick={() => setUploadOpen(true)}
              >
                Upload VCF
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Statistics */}
        <Grid item xs={12} md={8}>
          <Grid container spacing={2}>
            <Grid item xs={4}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="h3" color="primary">
                  {stats.totalJobs}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Jobs
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={4}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="h3" color="warning.main">
                  {stats.runningJobs}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Running
                </Typography>
              </Paper>
            </Grid>
            <Grid item xs={4}>
              <Paper sx={{ p: 2, textAlign: 'center' }}>
                <Typography variant="h3" color="success.main">
                  {stats.completedJobs}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Completed
                </Typography>
              </Paper>
            </Grid>
          </Grid>
        </Grid>

        {/* Recent Jobs */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Jobs
              </Typography>
              {jobsData?.data.jobs.map((job: any) => (
                <Paper
                  key={job.id}
                  sx={{ p: 2, mb: 2, cursor: 'pointer' }}
                  onClick={() => navigate(`/jobs/${job.job_id}`)}
                >
                  <Box display="flex" alignItems="center" justifyContent="space-between">
                    <Box>
                      <Typography variant="subtitle1">{job.name}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        Created: {new Date(job.created_at).toLocaleString()}
                      </Typography>
                    </Box>
                    <Box display="flex" alignItems="center">
                      {job.status === 'running' && (
                        <>
                          <ScienceIcon color="primary" sx={{ mr: 1 }} />
                          <LinearProgress
                            variant="determinate"
                            value={job.progress}
                            sx={{ width: 100, mr: 2 }}
                          />
                        </>
                      )}
                      {job.status === 'completed' && (
                        <CheckIcon color="success" />
                      )}
                      <Typography
                        variant="body2"
                        color={
                          job.status === 'completed'
                            ? 'success.main'
                            : job.status === 'running'
                            ? 'primary'
                            : 'text.secondary'
                        }
                      >
                        {job.status}
                      </Typography>
                    </Box>
                  </Box>
                </Paper>
              ))}
              {jobsData?.data.jobs.length === 0 && (
                <Typography variant="body2" color="text.secondary">
                  No jobs yet. Upload a VCF to get started!
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Features */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <AssessmentIcon color="secondary" sx={{ mr: 2 }} />
                <Typography variant="h6">Analysis Features</Typography>
              </Box>
              <Typography variant="body2" paragraph>
                • VEP annotation with 26 specialized plugins
              </Typography>
              <Typography variant="body2" paragraph>
                • AMP/ASCO/CAP 2017 and VICC 2022 tier assignment
              </Typography>
              <Typography variant="body2" paragraph>
                • OncoKB, CIViC, and COSMIC evidence integration
              </Typography>
              <Typography variant="body2" paragraph>
                • Population frequency from gnomAD v4
              </Typography>
              <Typography variant="body2">
                • Clinical interpretation with GA4GH standards
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* File Upload Dialog */}
      <FileUpload
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        onSuccess={(jobId) => {
          setUploadOpen(false)
          navigate(`/jobs/${jobId}`)
        }}
      />
    </Box>
  )
}

export default Dashboard