import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Container,
  Paper,
  Typography,
  LinearProgress,
  Chip,
  Alert,
  Button,
  Grid,
  Card,
  CardContent,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Tooltip,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Tabs,
  Tab,
} from '@mui/material'
import {
  ArrowBack,
  Download,
  Refresh,
  Visibility,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  Timeline,
  ViewList,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { jobsAPI, variantsAPI } from '../services/api'
import { format } from 'date-fns'
import VariantFlowDiagram from '../components/VariantFlowDiagram'

interface Variant {
  variant_id: number
  chromosome: string
  position: number
  reference: string
  alternate: string
  gene: string
  consequence: string
  amp_tier: string
  vicc_tier?: string
  confidence_score: number
  canned_text?: string
  interpretation?: string
}

interface FlowData {
  annotations: Array<{
    source: string
    type: string
    value: any
    confidence?: number
  }>
  rules: Array<{
    id: string
    name: string
    triggered: boolean
    score: number
    evidence: string[]
  }>
  triggered_rules: string[]
  tier_rationale: string[]
}

interface JobUpdate {
  type: 'progress' | 'variant_update' | 'connected'
  job_id: string
  status?: string
  progress?: number
  message?: string
  current_step?: string
  variant?: Variant
  flow_data?: FlowData
  timestamp: string
}

const JobDetail: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const [variants, setVariants] = useState<Variant[]>([])
  const [variantFlows, setVariantFlows] = useState<Map<number, FlowData>>(new Map())
  const [isConnected, setIsConnected] = useState(false)
  const [currentProgress, setCurrentProgress] = useState(0)
  const [currentMessage, setCurrentMessage] = useState('')
  const [currentStep, setCurrentStep] = useState('')
  const [viewMode, setViewMode] = useState<'table' | 'flow'>('flow')
  const [selectedVariant, setSelectedVariant] = useState<number | null>(null)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [detailDialogStage, setDetailDialogStage] = useState<string>('')
  const [detailDialogData, setDetailDialogData] = useState<any>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Fetch job details
  const { data: job, isLoading, error, refetch } = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => jobsAPI.getById(jobId!),
    enabled: !!jobId,
    refetchInterval: (data) => {
      // Stop polling if job is completed or failed
      if (data?.status === 'completed' || data?.status === 'failed') {
        return false
      }
      return 5000 // Poll every 5 seconds while running
    },
  })

  // WebSocket connection for real-time updates
  useEffect(() => {
    if (!jobId || !job || (job.status !== 'running' && job.status !== 'pending')) {
      return
    }

    const connectWebSocket = () => {
      const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.hostname}:8000/ws/jobs/${jobId}`
      
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const update: JobUpdate = JSON.parse(event.data)
          handleUpdate(update)
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        wsRef.current = null

        // Reconnect after 3 seconds if job is still running
        if (job?.status === 'running') {
          reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000)
        }
      }
    }

    connectWebSocket()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [jobId, job?.status])

  const handleUpdate = (update: JobUpdate) => {
    switch (update.type) {
      case 'progress':
        setCurrentProgress(update.progress || 0)
        setCurrentMessage(update.message || '')
        setCurrentStep(update.current_step || '')
        break
      
      case 'variant_update':
        if (update.variant) {
          setVariants(prev => [...prev, update.variant!])
          
          // Store flow data if available
          if (update.flow_data && update.variant.variant_id) {
            setVariantFlows(prev => {
              const newMap = new Map(prev)
              newMap.set(update.variant!.variant_id, update.flow_data!)
              return newMap
            })
          }
          
          // Auto-select first variant in flow view
          if (variants.length === 0 && viewMode === 'flow') {
            setSelectedVariant(update.variant.variant_id)
          }
        }
        break
      
      case 'connected':
        console.log('Connected to job progress stream')
        break
    }
  }

  const handleStageClick = (stage: string, data: any) => {
    setDetailDialogStage(stage)
    setDetailDialogData(data)
    setDetailDialogOpen(true)
  }

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'Tier I': return 'error'
      case 'Tier II': return 'warning'
      case 'Tier III': return 'info'
      case 'Tier IV': return 'default'
      default: return 'default'
    }
  }

  const getConfidenceIcon = (score: number) => {
    if (score >= 0.8) return <CheckCircle color="success" fontSize="small" />
    if (score >= 0.5) return <Warning color="warning" fontSize="small" />
    return <ErrorIcon color="error" fontSize="small" />
  }

  if (isLoading) {
    return (
      <Container>
        <Box sx={{ mt: 4 }}>
          <LinearProgress />
          <Typography variant="body2" sx={{ mt: 2 }}>Loading job details...</Typography>
        </Box>
      </Container>
    )
  }

  if (error || !job) {
    return (
      <Container>
        <Alert severity="error" sx={{ mt: 4 }}>
          Failed to load job details
        </Alert>
      </Container>
    )
  }

  return (
    <Container maxWidth="xl">
      <Box sx={{ mt: 4, mb: 4 }}>
        {/* Header */}
        <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
          <IconButton onClick={() => navigate('/dashboard')}>
            <ArrowBack />
          </IconButton>
          <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
            {job.name}
          </Typography>
          <Chip
            label={job.status.toUpperCase()}
            color={job.status === 'completed' ? 'success' : job.status === 'failed' ? 'error' : 'default'}
          />
          {isConnected && (
            <Chip
              label="Live Updates"
              color="success"
              size="small"
              variant="outlined"
            />
          )}
        </Box>

        {/* Job Info */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle2" color="text.secondary">Case UID</Typography>
              <Typography>{job.case_uid || 'N/A'}</Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle2" color="text.secondary">Cancer Type</Typography>
              <Typography>{job.cancer_type || 'N/A'}</Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle2" color="text.secondary">Created</Typography>
              <Typography>{format(new Date(job.created_at), 'PPpp')}</Typography>
            </Grid>
          </Grid>

          {/* Progress */}
          {job.status === 'running' && (
            <Box sx={{ mt: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <Typography variant="body2" sx={{ flexGrow: 1 }}>
                  {currentMessage || 'Processing...'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {currentProgress}%
                </Typography>
              </Box>
              <LinearProgress variant="determinate" value={currentProgress} />
              {currentStep && (
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                  Step: {currentStep}
                </Typography>
              )}
            </Box>
          )}

          {/* Summary Stats */}
          {job.result_summary && (
            <Box sx={{ mt: 3 }}>
              <Divider sx={{ mb: 2 }} />
              <Grid container spacing={2}>
                <Grid item xs={6} sm={3}>
                  <Typography variant="subtitle2" color="text.secondary">Total Variants</Typography>
                  <Typography variant="h6">{job.result_summary.total_variants}</Typography>
                </Grid>
                <Grid item xs={6} sm={3}>
                  <Typography variant="subtitle2" color="text.secondary">High Confidence</Typography>
                  <Typography variant="h6">{job.result_summary.high_confidence_variants}</Typography>
                </Grid>
                {Object.entries(job.result_summary.tier_counts || {}).map(([tier, count]) => (
                  <Grid item xs={6} sm={3} key={tier}>
                    <Typography variant="subtitle2" color="text.secondary">{tier}</Typography>
                    <Typography variant="h6">{count as number}</Typography>
                  </Grid>
                ))}
              </Grid>
            </Box>
          )}
        </Paper>

        {/* Real-time Variants View */}
        {variants.length > 0 && (
          <Paper sx={{ mb: 3 }}>
            <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Typography variant="h6">
                Annotated Variants ({variants.length})
              </Typography>
              <Tabs value={viewMode} onChange={(e, v) => setViewMode(v)}>
                <Tab icon={<Timeline />} label="Flow View" value="flow" />
                <Tab icon={<ViewList />} label="Table View" value="table" />
              </Tabs>
            </Box>

            {/* Flow View */}
            {viewMode === 'flow' && (
              <Box sx={{ display: 'flex', height: 600 }}>
                {/* Variant List */}
                <Box sx={{ width: 300, borderRight: 1, borderColor: 'divider', overflowY: 'auto' }}>
                  <List>
                    {variants.map((variant) => {
                      const flowData = variantFlows.get(variant.variant_id)
                      const isImportant = variant.amp_tier === 'Tier I' || variant.amp_tier === 'Tier II'
                      
                      return (
                        <ListItem
                          key={variant.variant_id}
                          button
                          selected={selectedVariant === variant.variant_id}
                          onClick={() => setSelectedVariant(variant.variant_id)}
                          sx={{
                            borderLeft: isImportant ? 4 : 0,
                            borderColor: isImportant ? getTierColor(variant.amp_tier) + '.main' : 'transparent',
                          }}
                        >
                          <ListItemIcon>
                            {getConfidenceIcon(variant.confidence_score)}
                          </ListItemIcon>
                          <ListItemText
                            primary={`${variant.gene || variant.chromosome}:${variant.position}`}
                            secondary={
                              <Box>
                                <Chip
                                  label={variant.amp_tier}
                                  size="small"
                                  color={getTierColor(variant.amp_tier)}
                                  sx={{ mr: 1 }}
                                />
                                {flowData && (
                                  <Typography variant="caption" color="text.secondary">
                                    {flowData.triggered_rules.length} rules triggered
                                  </Typography>
                                )}
                              </Box>
                            }
                          />
                        </ListItem>
                      )
                    })}
                  </List>
                </Box>

                {/* Flow Diagram */}
                <Box sx={{ flex: 1, overflowX: 'auto', p: 2 }}>
                  {selectedVariant && variantFlows.has(selectedVariant) && (
                    <VariantFlowDiagram
                      data={{
                        variant: variants.find(v => v.variant_id === selectedVariant)!,
                        annotations: variantFlows.get(selectedVariant)!.annotations,
                        rules: variantFlows.get(selectedVariant)!.rules,
                        tier: {
                          amp: variants.find(v => v.variant_id === selectedVariant)!.amp_tier,
                          vicc: variants.find(v => v.variant_id === selectedVariant)!.vicc_tier || 'Unknown',
                          confidence: variants.find(v => v.variant_id === selectedVariant)!.confidence_score,
                        },
                        interpretation: {
                          summary: variants.find(v => v.variant_id === selectedVariant)!.interpretation || '',
                          clinical_significance: variants.find(v => v.variant_id === selectedVariant)!.amp_tier,
                          recommendations: variantFlows.get(selectedVariant)!.tier_rationale || [],
                        },
                      }}
                      isActive={true}
                      onStageClick={handleStageClick}
                    />
                  )}
                  {(!selectedVariant || !variantFlows.has(selectedVariant)) && (
                    <Typography color="text.secondary" align="center" sx={{ mt: 4 }}>
                      Select a variant to view its annotation flow
                    </Typography>
                  )}
                </Box>
              </Box>
            )}

            {/* Table View */}
            {viewMode === 'table' && (
              <TableContainer sx={{ maxHeight: 600 }}>
                <Table stickyHeader size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Position</TableCell>
                      <TableCell>Change</TableCell>
                      <TableCell>Gene</TableCell>
                      <TableCell>Consequence</TableCell>
                      <TableCell>Tier</TableCell>
                      <TableCell align="center">Confidence</TableCell>
                      <TableCell>Interpretation</TableCell>
                      <TableCell align="center">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {variants.map((variant, index) => (
                      <TableRow key={variant.variant_id || index} hover>
                        <TableCell>
                          {variant.chromosome}:{variant.position}
                        </TableCell>
                        <TableCell>
                          {variant.reference}>{variant.alternate}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">
                            {variant.gene || '-'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="caption">
                            {variant.consequence || '-'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', gap: 0.5 }}>
                            <Chip
                              label={variant.amp_tier}
                              size="small"
                              color={getTierColor(variant.amp_tier)}
                            />
                            {variant.vicc_tier && (
                              <Chip
                                label={variant.vicc_tier}
                                size="small"
                                variant="outlined"
                              />
                            )}
                          </Box>
                        </TableCell>
                        <TableCell align="center">
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, justifyContent: 'center' }}>
                            {getConfidenceIcon(variant.confidence_score)}
                            <Typography variant="caption">
                              {(variant.confidence_score * 100).toFixed(0)}%
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Tooltip title={variant.interpretation || 'No interpretation'}>
                            <Typography
                              variant="caption"
                              sx={{
                                display: '-webkit-box',
                                WebkitLineClamp: 2,
                                WebkitBoxOrient: 'vertical',
                                overflow: 'hidden',
                                maxWidth: 300,
                              }}
                            >
                              {variant.interpretation || '-'}
                            </Typography>
                          </Tooltip>
                        </TableCell>
                        <TableCell align="center">
                          <Tooltip title="View details">
                            <IconButton
                              size="small"
                              onClick={() => navigate(`/variants/${variant.variant_id}`)}
                            >
                              <Visibility fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Paper>
        )}

        {/* Actions */}
        {job.status === 'completed' && (
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="contained"
              startIcon={<Download />}
              onClick={() => window.open(`/api/reports/download/${jobId}/report.pdf`)}
            >
              Download Report
            </Button>
            <Button
              variant="outlined"
              onClick={() => navigate(`/jobs/${jobId}/variants`)}
            >
              View All Variants
            </Button>
          </Box>
        )}

        {/* Detail Dialog */}
        <Dialog
          open={detailDialogOpen}
          onClose={() => setDetailDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>
            {detailDialogStage.charAt(0).toUpperCase() + detailDialogStage.slice(1)} Details
          </DialogTitle>
          <DialogContent dividers>
            {detailDialogStage === 'annotations' && detailDialogData && (
              <List>
                {detailDialogData.map((ann: any, idx: number) => (
                  <ListItem key={idx}>
                    <ListItemIcon>
                      <Chip
                        label={ann.source}
                        size="small"
                        color={ann.type === 'clinical' ? 'primary' : 'default'}
                      />
                    </ListItemIcon>
                    <ListItemText
                      primary={ann.value}
                      secondary={`Type: ${ann.type} | Confidence: ${(ann.confidence * 100).toFixed(0)}%`}
                    />
                  </ListItem>
                ))}
              </List>
            )}
            
            {detailDialogStage === 'rules' && detailDialogData && (
              <List>
                {detailDialogData.map((rule: any, idx: number) => (
                  <ListItem key={idx}>
                    <ListItemIcon>
                      {rule.triggered ? (
                        <CheckCircle color="success" />
                      ) : (
                        <Error color="disabled" />
                      )}
                    </ListItemIcon>
                    <ListItemText
                      primary={rule.name}
                      secondary={
                        <>
                          Score: {rule.score} | ID: {rule.id}
                          {rule.evidence && rule.evidence.length > 0 && (
                            <Box component="ul" sx={{ mt: 1, pl: 2 }}>
                              {rule.evidence.map((ev: string, i: number) => (
                                <li key={i}>{ev}</li>
                              ))}
                            </Box>
                          )}
                        </>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            )}
            
            {detailDialogStage === 'tier' && detailDialogData && (
              <Box>
                <Typography variant="h6" gutterBottom>
                  {detailDialogData.amp}
                </Typography>
                <Typography variant="subtitle1" gutterBottom>
                  {detailDialogData.vicc}
                </Typography>
                <Typography variant="body1" paragraph>
                  Confidence Score: {(detailDialogData.confidence * 100).toFixed(0)}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={detailDialogData.confidence * 100}
                  sx={{ mb: 2 }}
                />
              </Box>
            )}
            
            {detailDialogStage === 'interpretation' && detailDialogData && (
              <Box>
                <Typography variant="body1" paragraph>
                  {detailDialogData.summary}
                </Typography>
                <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>
                  Clinical Significance: {detailDialogData.clinical_significance}
                </Typography>
                {detailDialogData.recommendations && detailDialogData.recommendations.length > 0 && (
                  <>
                    <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>
                      Recommendations:
                    </Typography>
                    <List>
                      {detailDialogData.recommendations.map((rec: string, idx: number) => (
                        <ListItem key={idx}>
                          <ListItemText primary={rec} />
                        </ListItem>
                      ))}
                    </List>
                  </>
                )}
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDetailDialogOpen(false)}>Close</Button>
          </DialogActions>
        </Dialog>
      </Box>
    </Container>
  )
}

export default JobDetail