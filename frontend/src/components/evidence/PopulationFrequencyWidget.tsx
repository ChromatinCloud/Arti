import React from 'react'
import {
  Box,
  Typography,
  Paper,
  Grid,
  Chip,
  LinearProgress,
  Tooltip,
} from '@mui/material'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts'

interface PopulationData {
  gnomad_af?: number
  gnomad_af_popmax?: number
  gnomad_af_afr?: number
  gnomad_af_amr?: number
  gnomad_af_eas?: number
  gnomad_af_nfe?: number
  gnomad_af_sas?: number
  gnomad_homozygotes?: number
  all_of_us_af?: number
  exac_af?: number
  onekg_af?: number
}

interface PopulationFrequencyWidgetProps {
  data: PopulationData
  expanded?: boolean
}

const PopulationFrequencyWidget: React.FC<PopulationFrequencyWidgetProps> = ({ data, expanded = false }) => {
  const getFrequencyColor = (af: number) => {
    if (af === 0) return '#4caf50' // Novel
    if (af < 0.0001) return '#8bc34a' // Ultra-rare
    if (af < 0.001) return '#ff9800' // Very rare
    if (af < 0.01) return '#ff5722' // Rare
    return '#f44336' // Common
  }

  const getFrequencyLabel = (af: number) => {
    if (af === 0) return 'Novel'
    if (af < 0.0001) return 'Ultra-rare'
    if (af < 0.001) return 'Very rare'
    if (af < 0.01) return 'Rare'
    return 'Common'
  }

  const formatAF = (af: number | undefined) => {
    if (af === undefined || af === null) return 'Not found'
    if (af === 0) return '0 (Novel)'
    return af.toExponential(2)
  }

  // Prepare population distribution data
  const populationData = [
    { name: 'AFR', value: data.gnomad_af_afr || 0, label: 'African' },
    { name: 'AMR', value: data.gnomad_af_amr || 0, label: 'American' },
    { name: 'EAS', value: data.gnomad_af_eas || 0, label: 'East Asian' },
    { name: 'NFE', value: data.gnomad_af_nfe || 0, label: 'European' },
    { name: 'SAS', value: data.gnomad_af_sas || 0, label: 'South Asian' },
  ].filter(d => d.value > 0)

  const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7c7c', '#8dd1e1']

  if (!expanded) {
    // Compact view
    return (
      <Box>
        <Grid container spacing={1}>
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="body2" color="text.secondary">
                gnomAD:
              </Typography>
              <Chip
                label={formatAF(data.gnomad_af)}
                size="small"
                sx={{
                  bgcolor: data.gnomad_af ? getFrequencyColor(data.gnomad_af) : 'grey.300',
                  color: 'white',
                }}
              />
              {data.gnomad_af && (
                <Chip
                  label={getFrequencyLabel(data.gnomad_af)}
                  size="small"
                  variant="outlined"
                />
              )}
            </Box>
          </Grid>
          {data.gnomad_af_popmax !== undefined && (
            <Grid item xs={12}>
              <Typography variant="caption" color="text.secondary">
                PopMax: {formatAF(data.gnomad_af_popmax)}
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
        Population Frequencies
      </Typography>

      {/* Main frequency display */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          Global Allele Frequency
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h4">
            {data.gnomad_af !== undefined ? formatAF(data.gnomad_af) : 'Not found'}
          </Typography>
          {data.gnomad_af !== undefined && data.gnomad_af > 0 && (
            <Chip
              label={getFrequencyLabel(data.gnomad_af)}
              color={data.gnomad_af < 0.01 ? 'success' : 'error'}
            />
          )}
        </Box>
        {data.gnomad_homozygotes !== undefined && (
          <Typography variant="caption" color="text.secondary">
            {data.gnomad_homozygotes} homozygotes observed
          </Typography>
        )}
      </Box>

      {/* Population distribution */}
      {populationData.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" color="text.secondary" gutterBottom>
            Population Distribution
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={populationData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={(entry) => `${entry.name}: ${entry.value.toExponential(1)}`}
                  >
                    {populationData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                </PieChart>
              </ResponsiveContainer>
            </Grid>
            <Grid item xs={12} md={6}>
              {populationData.map((pop, idx) => (
                <Box key={pop.name} sx={{ mb: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Typography variant="body2">{pop.label}</Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {formatAF(pop.value)}
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={Math.min(pop.value * 10000, 100)}
                    sx={{ height: 6, bgcolor: 'grey.200' }}
                  />
                </Box>
              ))}
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Other databases */}
      <Box>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          Other Databases
        </Typography>
        <Grid container spacing={1}>
          {data.all_of_us_af !== undefined && (
            <Grid item xs={12} sm={6}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2">All of Us:</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {formatAF(data.all_of_us_af)}
                </Typography>
              </Box>
            </Grid>
          )}
          {data.exac_af !== undefined && (
            <Grid item xs={12} sm={6}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2">ExAC:</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {formatAF(data.exac_af)}
                </Typography>
              </Box>
            </Grid>
          )}
          {data.onekg_af !== undefined && (
            <Grid item xs={12} sm={6}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="body2">1000 Genomes:</Typography>
                <Typography variant="body2" fontWeight="bold">
                  {formatAF(data.onekg_af)}
                </Typography>
              </Box>
            </Grid>
          )}
        </Grid>
      </Box>

      {/* Clinical interpretation hint */}
      {data.gnomad_af !== undefined && data.gnomad_af < 0.01 && (
        <Box sx={{ mt: 2, p: 1, bgcolor: 'success.light', borderRadius: 1 }}>
          <Typography variant="caption" color="success.dark">
            ✓ Rare variant (AF {'<'} 1%) supports pathogenicity
          </Typography>
        </Box>
      )}
    </Paper>
  )
}

export default PopulationFrequencyWidget