import React from 'react'
import {
  Box,
  Typography,
  Paper,
  Grid,
  Chip,
  LinearProgress,
  Tooltip,
  IconButton,
  Divider,
} from '@mui/material'
import { Info, Warning, CheckCircle, Error } from '@mui/icons-material'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

interface PredictionData {
  revel_score?: number
  cadd_phred?: number
  polyphen_score?: number
  polyphen_pred?: string
  sift_score?: number
  sift_pred?: string
  metalr_score?: number
  metalr_pred?: string
  metasvm_score?: number
  metasvm_pred?: string
  alphamissense_score?: number
  alphamissense_pred?: string
  spliceai_scores?: {
    acceptor_gain?: number
    acceptor_loss?: number
    donor_gain?: number
    donor_loss?: number
  }
}

interface FunctionalPredictionWidgetProps {
  data: PredictionData
  expanded?: boolean
}

const FunctionalPredictionWidget: React.FC<FunctionalPredictionWidgetProps> = ({ data, expanded = false }) => {
  const getPredictionColor = (score: number, inverted: boolean = false) => {
    if (inverted) {
      if (score < 0.3) return '#f44336' // Deleterious
      if (score < 0.7) return '#ff9800' // Possibly deleterious
      return '#4caf50' // Benign
    } else {
      if (score > 0.7) return '#f44336' // Deleterious
      if (score > 0.3) return '#ff9800' // Possibly deleterious
      return '#4caf50' // Benign
    }
  }

  const getPredictionLabel = (pred: string | undefined) => {
    if (!pred) return 'Unknown'
    const normalized = pred.toLowerCase()
    if (normalized.includes('deleterious') || normalized.includes('damaging')) return 'Deleterious'
    if (normalized.includes('tolerated') || normalized.includes('benign')) return 'Benign'
    return pred
  }

  // Prepare data for bar chart
  const predictionScores = [
    { name: 'REVEL', score: data.revel_score, threshold: 0.5 },
    { name: 'CADD', score: data.cadd_phred ? data.cadd_phred / 40 : undefined, threshold: 0.5 },
    { name: 'PolyPhen', score: data.polyphen_score, threshold: 0.5 },
    { name: 'SIFT', score: data.sift_score, threshold: 0.05, inverted: true },
    { name: 'AlphaMissense', score: data.alphamissense_score, threshold: 0.5 },
  ].filter(d => d.score !== undefined)

  const consensusScore = predictionScores.length > 0
    ? predictionScores.reduce((sum, p) => sum + (p.inverted ? 1 - p.score! : p.score!), 0) / predictionScores.length
    : undefined

  if (!expanded) {
    // Compact view
    return (
      <Box>
        <Grid container spacing={1}>
          {data.revel_score !== undefined && (
            <Grid item xs={12}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  REVEL:
                </Typography>
                <Chip
                  label={data.revel_score.toFixed(3)}
                  size="small"
                  color={data.revel_score > 0.5 ? 'error' : 'success'}
                />
                {data.revel_score > 0.7 && (
                  <Warning fontSize="small" color="error" />
                )}
              </Box>
            </Grid>
          )}
          {consensusScore !== undefined && (
            <Grid item xs={12}>
              <Typography variant="caption" color="text.secondary">
                Consensus: {(consensusScore * 100).toFixed(0)}% pathogenic
              </Typography>
            </Grid>
          )}
        </Grid>
      </Box>
    )
  }

  // Expanded view
  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>
        Functional Predictions
      </Typography>

      {/* Consensus score */}
      {consensusScore !== undefined && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Consensus Pathogenicity Score
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Box sx={{ flex: 1 }}>
              <LinearProgress
                variant="determinate"
                value={consensusScore * 100}
                sx={{
                  height: 20,
                  borderRadius: 10,
                  bgcolor: 'grey.200',
                  '& .MuiLinearProgress-bar': {
                    bgcolor: getPredictionColor(consensusScore),
                  },
                }}
              />
            </Box>
            <Typography variant="h6" sx={{ minWidth: 60 }}>
              {(consensusScore * 100).toFixed(0)}%
            </Typography>
          </Box>
          <Typography variant="caption" color="text.secondary">
            Based on {predictionScores.length} prediction tools
          </Typography>
        </Box>
      )}

      {/* Individual predictions chart */}
      {predictionScores.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Individual Predictions
          </Typography>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={predictionScores}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis domain={[0, 1]} />
              <RechartsTooltip />
              <Bar dataKey="score">
                {predictionScores.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={getPredictionColor(entry.score!, entry.inverted)}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Box>
      )}

      {/* Detailed predictions */}
      <Box>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          Detailed Scores
        </Typography>
        <Grid container spacing={2}>
          {data.revel_score !== undefined && (
            <Grid item xs={12} sm={6}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="body2">REVEL</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Threshold: 0.5
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" fontWeight="bold">
                    {data.revel_score.toFixed(3)}
                  </Typography>
                  {data.revel_score > 0.5 ? (
                    <Error fontSize="small" color="error" />
                  ) : (
                    <CheckCircle fontSize="small" color="success" />
                  )}
                </Box>
              </Box>
            </Grid>
          )}

          {data.cadd_phred !== undefined && (
            <Grid item xs={12} sm={6}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="body2">CADD</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Phred score
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" fontWeight="bold">
                    {data.cadd_phred.toFixed(1)}
                  </Typography>
                  {data.cadd_phred > 20 ? (
                    <Error fontSize="small" color="error" />
                  ) : (
                    <CheckCircle fontSize="small" color="success" />
                  )}
                </Box>
              </Box>
            </Grid>
          )}

          {data.polyphen_score !== undefined && (
            <Grid item xs={12} sm={6}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="body2">PolyPhen-2</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {data.polyphen_pred || 'HumDiv'}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" fontWeight="bold">
                    {data.polyphen_score.toFixed(3)}
                  </Typography>
                  <Chip
                    label={getPredictionLabel(data.polyphen_pred)}
                    size="small"
                    color={data.polyphen_pred?.includes('damaging') ? 'error' : 'success'}
                  />
                </Box>
              </Box>
            </Grid>
          )}

          {data.sift_score !== undefined && (
            <Grid item xs={12} sm={6}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="body2">SIFT</Typography>
                  <Typography variant="caption" color="text.secondary">
                    Lower = more deleterious
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" fontWeight="bold">
                    {data.sift_score.toFixed(3)}
                  </Typography>
                  <Chip
                    label={getPredictionLabel(data.sift_pred)}
                    size="small"
                    color={data.sift_pred?.includes('deleterious') ? 'error' : 'success'}
                  />
                </Box>
              </Box>
            </Grid>
          )}

          {data.alphamissense_score !== undefined && (
            <Grid item xs={12} sm={6}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="body2">AlphaMissense</Typography>
                  <Typography variant="caption" color="text.secondary">
                    AI-based prediction
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" fontWeight="bold">
                    {data.alphamissense_score.toFixed(3)}
                  </Typography>
                  <Chip
                    label={getPredictionLabel(data.alphamissense_pred)}
                    size="small"
                    color={data.alphamissense_score > 0.5 ? 'error' : 'success'}
                  />
                </Box>
              </Box>
            </Grid>
          )}
        </Grid>
      </Box>

      {/* Splicing predictions */}
      {data.spliceai_scores && Object.values(data.spliceai_scores).some(v => v && v > 0) && (
        <>
          <Divider sx={{ my: 2 }} />
          <Box>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Splicing Predictions (SpliceAI)
            </Typography>
            <Grid container spacing={1}>
              {Object.entries(data.spliceai_scores).map(([key, value]) => {
                if (!value || value === 0) return null
                return (
                  <Grid item xs={12} sm={6} key={key}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                      <Typography variant="body2">
                        {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:
                      </Typography>
                      <Chip
                        label={value.toFixed(3)}
                        size="small"
                        color={value > 0.5 ? 'error' : value > 0.2 ? 'warning' : 'default'}
                      />
                    </Box>
                  </Grid>
                )
              })}
            </Grid>
          </Box>
        </>
      )}

      {/* Clinical interpretation hint */}
      {consensusScore !== undefined && consensusScore > 0.7 && (
        <Box sx={{ mt: 2, p: 1, bgcolor: 'error.light', borderRadius: 1 }}>
          <Typography variant="caption" color="error.dark">
            ⚠ Multiple tools predict deleterious effect
          </Typography>
        </Box>
      )}
    </Paper>
  )
}

export default FunctionalPredictionWidget