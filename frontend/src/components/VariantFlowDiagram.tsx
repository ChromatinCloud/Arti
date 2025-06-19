import React, { useEffect, useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  Chip,
  Card,
  CardContent,
  Fade,
  Zoom,
  IconButton,
  Tooltip,
  Collapse,
  Button,
} from '@mui/material'
import {
  ArrowForward,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  ExpandMore,
  ExpandLess,
  Biotech,
  Rule,
  Category,
  Description,
} from '@mui/icons-material'

interface Annotation {
  source: string
  type: string
  value: any
  confidence?: number
}

interface Rule {
  id: string
  name: string
  triggered: boolean
  score: number
  evidence: string[]
}

interface VariantFlow {
  variant: {
    chromosome: string
    position: number
    reference: string
    alternate: string
    gene?: string
  }
  annotations: Annotation[]
  rules: Rule[]
  tier: {
    amp: string
    vicc: string
    confidence: number
  }
  interpretation: {
    summary: string
    clinical_significance: string
    recommendations: string[]
  }
}

interface VariantFlowDiagramProps {
  data: VariantFlow
  isActive?: boolean
  onStageClick?: (stage: string, data: any) => void
}

const VariantFlowDiagram: React.FC<VariantFlowDiagramProps> = ({
  data,
  isActive = false,
  onStageClick,
}) => {
  const [stage, setStage] = useState(0)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})

  // Animate through stages when active
  useEffect(() => {
    if (isActive) {
      const timer = setInterval(() => {
        setStage((prev) => {
          if (prev < 4) return prev + 1
          clearInterval(timer)
          return prev
        })
      }, 800)
      return () => clearInterval(timer)
    }
  }, [isActive])

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }))
  }

  const getAnnotationIcon = (type: string) => {
    switch (type) {
      case 'pathogenicity':
        return <Warning fontSize="small" color="warning" />
      case 'population':
        return <Biotech fontSize="small" color="info" />
      case 'functional':
        return <CheckCircle fontSize="small" color="success" />
      default:
        return <Biotech fontSize="small" />
    }
  }

  const getTierColor = (tier: string): any => {
    switch (tier) {
      case 'Tier I':
        return 'error'
      case 'Tier II':
        return 'warning'
      case 'Tier III':
        return 'info'
      case 'Tier IV':
        return 'default'
      default:
        return 'default'
    }
  }

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, overflowX: 'auto', pb: 2 }}>
        {/* Stage 1: Variant */}
        <Zoom in={stage >= 0} timeout={600}>
          <Card
            sx={{
              minWidth: 200,
              cursor: 'pointer',
              border: stage === 0 && isActive ? '2px solid' : '1px solid',
              borderColor: stage === 0 && isActive ? 'primary.main' : 'divider',
              transition: 'all 0.3s',
            }}
            onClick={() => onStageClick?.('variant', data.variant)}
          >
            <CardContent>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                Variant
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {data.variant.chromosome}:{data.variant.position}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {data.variant.reference}>{data.variant.alternate}
              </Typography>
              {data.variant.gene && (
                <Chip
                  label={data.variant.gene}
                  size="small"
                  sx={{ mt: 1 }}
                  color="primary"
                  variant="outlined"
                />
              )}
            </CardContent>
          </Card>
        </Zoom>

        {/* Arrow 1 */}
        <Fade in={stage >= 1} timeout={300}>
          <ArrowForward color="action" />
        </Fade>

        {/* Stage 2: Annotations */}
        <Zoom in={stage >= 1} timeout={600}>
          <Card
            sx={{
              minWidth: 250,
              maxWidth: 300,
              cursor: 'pointer',
              border: stage === 1 && isActive ? '2px solid' : '1px solid',
              borderColor: stage === 1 && isActive ? 'primary.main' : 'divider',
              transition: 'all 0.3s',
            }}
            onClick={() => onStageClick?.('annotations', data.annotations)}
          >
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Annotations ({data.annotations.length})
                </Typography>
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation()
                    toggleSection('annotations')
                  }}
                >
                  {expandedSections.annotations ? <ExpandLess /> : <ExpandMore />}
                </IconButton>
              </Box>
              <Collapse in={expandedSections.annotations} timeout="auto" unmountOnExit>
                <Box sx={{ mt: 1, maxHeight: 150, overflowY: 'auto' }}>
                  {data.annotations.slice(0, 5).map((ann, idx) => (
                    <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      {getAnnotationIcon(ann.type)}
                      <Typography variant="caption">
                        {ann.source}: {ann.value}
                      </Typography>
                    </Box>
                  ))}
                  {data.annotations.length > 5 && (
                    <Typography variant="caption" color="text.secondary">
                      +{data.annotations.length - 5} more...
                    </Typography>
                  )}
                </Box>
              </Collapse>
              {!expandedSections.annotations && (
                <Box sx={{ mt: 1 }}>
                  {data.annotations.slice(0, 3).map((ann, idx) => (
                    <Chip
                      key={idx}
                      label={ann.source}
                      size="small"
                      sx={{ mr: 0.5, mb: 0.5 }}
                      variant="outlined"
                    />
                  ))}
                </Box>
              )}
            </CardContent>
          </Card>
        </Zoom>

        {/* Arrow 2 */}
        <Fade in={stage >= 2} timeout={300}>
          <ArrowForward color="action" />
        </Fade>

        {/* Stage 3: Rules */}
        <Zoom in={stage >= 2} timeout={600}>
          <Card
            sx={{
              minWidth: 250,
              maxWidth: 300,
              cursor: 'pointer',
              border: stage === 2 && isActive ? '2px solid' : '1px solid',
              borderColor: stage === 2 && isActive ? 'primary.main' : 'divider',
              transition: 'all 0.3s',
            }}
            onClick={() => onStageClick?.('rules', data.rules)}
          >
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Rules Triggered
                </Typography>
                <Rule fontSize="small" color="action" />
              </Box>
              <Box sx={{ mt: 1 }}>
                {data.rules
                  .filter((r) => r.triggered)
                  .slice(0, 3)
                  .map((rule, idx) => (
                    <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      <CheckCircle fontSize="small" color="success" />
                      <Typography variant="caption">{rule.name}</Typography>
                      <Chip label={`+${rule.score}`} size="small" color="success" />
                    </Box>
                  ))}
                <Typography variant="body2" fontWeight="bold" sx={{ mt: 1 }}>
                  Total Score: {data.rules.reduce((sum, r) => sum + (r.triggered ? r.score : 0), 0)}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Zoom>

        {/* Arrow 3 */}
        <Fade in={stage >= 3} timeout={300}>
          <ArrowForward color="action" />
        </Fade>

        {/* Stage 4: Tier/Level */}
        <Zoom in={stage >= 3} timeout={600}>
          <Card
            sx={{
              minWidth: 200,
              cursor: 'pointer',
              border: stage === 3 && isActive ? '2px solid' : '1px solid',
              borderColor: stage === 3 && isActive ? 'primary.main' : 'divider',
              transition: 'all 0.3s',
            }}
            onClick={() => onStageClick?.('tier', data.tier)}
          >
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Classification
                </Typography>
                <Category fontSize="small" color="action" />
              </Box>
              <Box sx={{ mt: 1 }}>
                <Chip
                  label={data.tier.amp}
                  color={getTierColor(data.tier.amp)}
                  size="medium"
                  sx={{ mb: 1, width: '100%' }}
                />
                <Chip
                  label={data.tier.vicc}
                  variant="outlined"
                  size="small"
                  sx={{ mb: 1, width: '100%' }}
                />
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    Confidence:
                  </Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {(data.tier.confidence * 100).toFixed(0)}%
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Zoom>

        {/* Arrow 4 */}
        <Fade in={stage >= 4} timeout={300}>
          <ArrowForward color="action" />
        </Fade>

        {/* Stage 5: Interpretation */}
        <Zoom in={stage >= 4} timeout={600}>
          <Card
            sx={{
              minWidth: 300,
              maxWidth: 400,
              cursor: 'pointer',
              border: stage === 4 && isActive ? '2px solid' : '1px solid',
              borderColor: stage === 4 && isActive ? 'primary.main' : 'divider',
              transition: 'all 0.3s',
            }}
            onClick={() => onStageClick?.('interpretation', data.interpretation)}
          >
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="subtitle2" color="text.secondary">
                  Clinical Interpretation
                </Typography>
                <Description fontSize="small" color="action" />
              </Box>
              <Typography variant="body2" sx={{ mt: 1, mb: 1 }}>
                {data.interpretation.summary}
              </Typography>
              <Chip
                label={data.interpretation.clinical_significance}
                size="small"
                color={
                  data.interpretation.clinical_significance.includes('Pathogenic')
                    ? 'error'
                    : 'default'
                }
              />
              {data.interpretation.recommendations.length > 0 && (
                <Box sx={{ mt: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    Recommendations:
                  </Typography>
                  <ul style={{ margin: 0, paddingLeft: 20 }}>
                    {data.interpretation.recommendations.slice(0, 2).map((rec, idx) => (
                      <li key={idx}>
                        <Typography variant="caption">{rec}</Typography>
                      </li>
                    ))}
                  </ul>
                </Box>
              )}
            </CardContent>
          </Card>
        </Zoom>
      </Box>

      {/* Legend */}
      {isActive && stage === 4 && (
        <Fade in timeout={1000}>
          <Box sx={{ mt: 2, display: 'flex', gap: 2, justifyContent: 'center' }}>
            <Typography variant="caption" color="text.secondary">
              Click any card to view details
            </Typography>
          </Box>
        </Fade>
      )}
    </Box>
  )
}

export default VariantFlowDiagram