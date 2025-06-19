import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box,
  Container,
  Paper,
  Typography,
  Grid,
  Chip,
  Button,
  Alert,
  LinearProgress,
  Divider,
  Card,
  CardContent,
  IconButton,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableRow,
} from '@mui/material'
import {
  ArrowBack,
  OpenInNew,
  ContentCopy,
  CheckCircle,
  Warning,
  Error as ErrorIcon,
} from '@mui/icons-material'
import { useQuery } from '@tanstack/react-query'
import { variantsAPI } from '../services/api'

interface TabPanelProps {
  children?: React.ReactNode
  index: number
  value: number
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`variant-tabpanel-${index}`}
      aria-labelledby={`variant-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  )
}

const VariantDetail: React.FC = () => {
  const { variantId } = useParams<{ variantId: string }>()
  const navigate = useNavigate()
  const [tabValue, setTabValue] = React.useState(0)

  const { data: variant, isLoading, error } = useQuery({
    queryKey: ['variant', variantId],
    queryFn: () => variantsAPI.getById(variantId!),
    enabled: !!variantId,
  })

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
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
    if (score >= 0.8) return <CheckCircle color="success" />
    if (score >= 0.5) return <Warning color="warning" />
    return <ErrorIcon color="error" />
  }

  if (isLoading) {
    return (
      <Container>
        <Box sx={{ mt: 4 }}>
          <LinearProgress />
          <Typography variant="body2" sx={{ mt: 2 }}>Loading variant details...</Typography>
        </Box>
      </Container>
    )
  }

  if (error || !variant) {
    return (
      <Container>
        <Alert severity="error" sx={{ mt: 4 }}>
          Failed to load variant details
        </Alert>
      </Container>
    )
  }

  const annotations = variant.annotations || {}
  const cannedText = annotations.canned_text || {}

  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4, mb: 4 }}>
        {/* Header */}
        <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
          <IconButton onClick={() => navigate(-1)}>
            <ArrowBack />
          </IconButton>
          <Typography variant="h4" component="h1" sx={{ flexGrow: 1 }}>
            {variant.gene_symbol || 'Unknown Gene'} - {variant.hgvs_p || variant.hgvs_c || 'Variant'}
          </Typography>
        </Box>

        {/* Summary Card */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="subtitle2" color="text.secondary">Genomic Position</Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="h6">
                  {variant.chromosome}:{variant.position} {variant.reference}>{variant.alternate}
                </Typography>
                <IconButton size="small" onClick={() => handleCopy(`${variant.chromosome}:${variant.position}`)}>
                  <ContentCopy fontSize="small" />
                </IconButton>
              </Box>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="subtitle2" color="text.secondary">Classification</Typography>
              <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                <Chip
                  label={variant.amp_tier}
                  color={getTierColor(variant.amp_tier)}
                  size="small"
                />
                <Chip
                  label={variant.vicc_tier}
                  variant="outlined"
                  size="small"
                />
              </Box>
            </Grid>
            <Grid item xs={12} md={3}>
              <Typography variant="subtitle2" color="text.secondary">Confidence Score</Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                {getConfidenceIcon(variant.confidence_score)}
                <Typography variant="h6">
                  {(variant.confidence_score * 100).toFixed(0)}%
                </Typography>
              </Box>
            </Grid>
          </Grid>

          <Divider sx={{ my: 2 }} />

          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle2" color="text.secondary">Gene</Typography>
              <Typography>{variant.gene_symbol || '-'}</Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle2" color="text.secondary">Transcript</Typography>
              <Typography>{variant.transcript_id || '-'}</Typography>
            </Grid>
            <Grid item xs={12} md={4}>
              <Typography variant="subtitle2" color="text.secondary">Consequence</Typography>
              <Typography>{variant.consequence || '-'}</Typography>
            </Grid>
          </Grid>
        </Paper>

        {/* Clinical Interpretation */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Clinical Interpretation
          </Typography>
          <Typography variant="body1" paragraph>
            {annotations.clinical_interpretation || 'No clinical interpretation available.'}
          </Typography>
          
          {cannedText.summary && (
            <>
              <Typography variant="subtitle1" sx={{ mt: 2, mb: 1 }} fontWeight="medium">
                Summary
              </Typography>
              <Typography variant="body2" paragraph>
                {cannedText.summary}
              </Typography>
            </>
          )}
          
          {cannedText.evidence && (
            <>
              <Typography variant="subtitle1" sx={{ mt: 2, mb: 1 }} fontWeight="medium">
                Evidence
              </Typography>
              <Typography variant="body2" paragraph>
                {cannedText.evidence}
              </Typography>
            </>
          )}
          
          {cannedText.recommendation && (
            <>
              <Typography variant="subtitle1" sx={{ mt: 2, mb: 1 }} fontWeight="medium">
                Recommendation
              </Typography>
              <Typography variant="body2">
                {cannedText.recommendation}
              </Typography>
            </>
          )}
        </Paper>

        {/* Detailed Information Tabs */}
        <Paper sx={{ mb: 3 }}>
          <Tabs
            value={tabValue}
            onChange={(e, newValue) => setTabValue(newValue)}
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab label="Population Frequencies" />
            <Tab label="External Evidence" />
            <Tab label="Functional Predictions" />
            <Tab label="Raw Annotations" />
          </Tabs>

          <Box sx={{ p: 3 }}>
            <TabPanel value={tabValue} index={0}>
              <Table size="small">
                <TableBody>
                  <TableRow>
                    <TableCell>gnomAD AF</TableCell>
                    <TableCell>{variant.gnomad_af?.toExponential(3) || 'Not found'}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>gnomAD AF PopMax</TableCell>
                    <TableCell>{variant.gnomad_af_popmax?.toExponential(3) || 'Not found'}</TableCell>
                  </TableRow>
                  {annotations.population_frequencies && Object.entries(annotations.population_frequencies).map(([pop, freq]) => (
                    <TableRow key={pop}>
                      <TableCell>{pop}</TableCell>
                      <TableCell>{freq as number}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TabPanel>

            <TabPanel value={tabValue} index={1}>
              <Grid container spacing={3}>
                {variant.oncokb_evidence && (
                  <Grid item xs={12} md={4}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1" gutterBottom>
                          OncoKB
                        </Typography>
                        <Typography variant="body2">
                          {JSON.stringify(variant.oncokb_evidence, null, 2)}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                )}
                {variant.civic_evidence && (
                  <Grid item xs={12} md={4}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1" gutterBottom>
                          CIViC
                        </Typography>
                        <Typography variant="body2">
                          {JSON.stringify(variant.civic_evidence, null, 2)}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                )}
                {variant.cosmic_evidence && (
                  <Grid item xs={12} md={4}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1" gutterBottom>
                          COSMIC
                        </Typography>
                        <Typography variant="body2">
                          {JSON.stringify(variant.cosmic_evidence, null, 2)}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                )}
              </Grid>
              {!variant.oncokb_evidence && !variant.civic_evidence && !variant.cosmic_evidence && (
                <Typography color="text.secondary">No external evidence available</Typography>
              )}
            </TabPanel>

            <TabPanel value={tabValue} index={2}>
              {annotations.functional_predictions ? (
                <Table size="small">
                  <TableBody>
                    {Object.entries(annotations.functional_predictions).map(([tool, prediction]) => (
                      <TableRow key={tool}>
                        <TableCell>{tool}</TableCell>
                        <TableCell>{JSON.stringify(prediction)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <Typography color="text.secondary">No functional predictions available</Typography>
              )}
            </TabPanel>

            <TabPanel value={tabValue} index={3}>
              <pre style={{ overflow: 'auto', fontSize: '0.875rem' }}>
                {JSON.stringify(annotations, null, 2)}
              </pre>
            </TabPanel>
          </Box>
        </Paper>

        {/* External Links */}
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="outlined"
            size="small"
            startIcon={<OpenInNew />}
            href={`https://www.ncbi.nlm.nih.gov/clinvar/?term=${variant.chromosome}[CHR]+AND+${variant.position}[CHRPOS]`}
            target="_blank"
          >
            ClinVar
          </Button>
          <Button
            variant="outlined"
            size="small"
            startIcon={<OpenInNew />}
            href={`https://gnomad.broadinstitute.org/variant/${variant.chromosome}-${variant.position}-${variant.reference}-${variant.alternate}`}
            target="_blank"
          >
            gnomAD
          </Button>
          {variant.gene_symbol && (
            <Button
              variant="outlined"
              size="small"
              startIcon={<OpenInNew />}
              href={`https://www.oncokb.org/gene/${variant.gene_symbol}`}
              target="_blank"
            >
              OncoKB
            </Button>
          )}
        </Box>
      </Box>
    </Container>
  )
}

export default VariantDetail