# Annotation Visualization Specification

> Context-aware visual representations for different annotation types

## Overview

Each annotation type should have a purpose-built visualization that best conveys its clinical significance. This document specifies visualization components for different annotation categories.

## 1. Protein Truncation Visualizations

### 1.1 Gene/Protein Domain View
```jsx
<TruncationVisualizer variant={variant}>
  {/* Linear protein representation */}
  <ProteinTrack length={1267} units="aa">
    <Domain name="RAS" start={1} end={189} color="#FF6B6B" />
    <Domain name="C1" start={234} end={280} color="#4ECDC4" />
    <Domain name="Kinase" start={457} end={717} color="#45B7D1" />
    <Domain name="WW" start={990} end={1020} color="#96CEB4" />
    
    <TruncationMarker position={600} type="nonsense">
      <Tooltip>
        p.Arg600* (c.1798C>T)
        Results in loss of 667 amino acids
        Kinase domain disrupted
      </Tooltip>
    </TruncationMarker>
  </ProteinTrack>
  
  {/* Exon view below */}
  <ExonTrack>
    <Exon number={1} start={1} end={120} />
    <Exon number={2} start={121} end={245} />
    <Exon number={15} start={1750} end={1850} highlighted={true}>
      <VariantPosition pos={1798} />
    </Exon>
    {/* ... more exons */}
  </ExonTrack>
  
  <LostDomains>
    <Alert severity="high">
      Lost functional domains: Kinase (partial), WW domain (complete)
    </Alert>
  </LostDomains>
</TruncationVisualizer>
```

### 1.2 NMD Prediction Visualization
```jsx
<NMDPredictor variant={variant}>
  <ExonMap>
    {exons.map(exon => (
      <ExonBlock 
        key={exon.number}
        highlighted={exon.number === variantExon}
        nmdBoundary={exon.isLastExon - 50}
      />
    ))}
  </ExonMap>
  
  <NMDStatus>
    {variant.position < lastExonBoundary - 50 ? (
      <Badge color="red">NMD Likely</Badge>
    ) : (
      <Badge color="yellow">NMD Escape Possible</Badge>
    )}
  </NMDStatus>
</NMDPredictor>
```

## 2. Hotspot & Clustering Visualizations

### 2.1 3D Protein Structure Hotspot View
```jsx
<HotspotStructureViewer pdbId="5P21" variant={variant}>
  <Molstar3D>
    <ProteinStructure />
    <HotspotRegion residues={[12, 13, 61]} color="red" radius={5} />
    <VariantPosition residue={12} label="G12D" pulse={true} />
    <ProximityAlert distance="3.2Å" to="GTP binding site" />
  </Molstar3D>
  
  <HotspotStats>
    <Stat label="Variants in 5Å radius" value={847} />
    <Stat label="Most common" value="G12D (45%)" />
    <Stat label="Functional impact" value="GTP binding disrupted" />
  </HotspotStats>
</HotspotStructureViewer>
```

### 2.2 Linear Hotspot Density Map
```jsx
<HotspotDensityMap gene="KRAS">
  <HeatmapTrack>
    {positions.map(pos => (
      <HeatmapCell
        position={pos}
        intensity={getVariantCount(pos)}
        onClick={() => showVariants(pos)}
      />
    ))}
  </HeatmapTrack>
  
  <AnnotationTrack>
    <Hotspot position={12} label="Codon 12" count={2341} />
    <Hotspot position={13} label="Codon 13" count={892} />
    <Hotspot position={61} label="Codon 61" count={651} />
  </AnnotationTrack>
  
  <CurrentVariant position={variant.position} />
</HotspotDensityMap>
```

## 3. Splicing Impact Visualizations

### 3.1 Splice Site Diagram
```jsx
<SpliceVisualizer variant={variant}>
  <SpliceJunction>
    <Exon number={7} sequence="...AGGTAGGT" />
    <IntronBoundary>
      <DonorSite score={0.98} />
      <ConsensusSequence expected="GT" observed="AT" />
    </IntronBoundary>
    <Intron length="2341bp" />
    <IntronBoundary>
      <AcceptorSite score={0.87} />
    </IntronBoundary>
    <Exon number={8} sequence="CAGGATCC..." />
  </SpliceJunction>
  
  <SpliceAIPrediction>
    <PredictionBar 
      acceptorGain={0.02}
      acceptorLoss={0.89}
      donorGain={0.01}
      donorLoss={0.95}
    />
    <Interpretation>
      High confidence splice disruption (Δ score: -0.95)
    </Interpretation>
  </SpliceAIPrediction>
  
  <ConsequencePreview>
    <WildType>Exon 7 → Exon 8 (normal)</WildType>
    <Mutant>Exon 7 → Exon 9 (exon 8 skipped)</Mutant>
    <FrameShift>Results in frameshift after aa 234</FrameShift>
  </ConsequencePreview>
</SpliceVisualizer>
```

### 3.2 RNA Secondary Structure Impact
```jsx
<RNAStructureViewer>
  <StructureDiagram>
    <WildTypeStructure />
    <Arrow />
    <MutantStructure highlightChange={true} />
  </StructureDiagram>
  
  <StructureMetrics>
    <Metric name="ΔG change" value="+12.3 kcal/mol" />
    <Metric name="Structure disrupted" value="Stem-loop 3" />
  </StructureMetrics>
</RNAStructureViewer>
```

## 4. Population Frequency Visualizations

### 4.1 Ancestry-Specific Frequency Plot
```jsx
<PopulationFrequencyPlot variant={variant}>
  <WorldMap>
    <PopulationDot
      location="Africa"
      size={scaleByFreq(0.0003)}
      label="AFR: 0.03%"
    />
    <PopulationDot
      location="Europe"
      size={scaleByFreq(0.00001)}
      label="EUR: 0.001%"
    />
    {/* More populations */}
  </WorldMap>
  
  <FrequencyBarChart>
    <Bar population="African" value={0.0003} />
    <Bar population="European" value={0.00001} />
    <Bar population="East Asian" value={0} />
    <Bar population="South Asian" value={0.00002} />
    <Bar population="Latino" value={0.00001} />
  </FrequencyBarChart>
  
  <ClinicalContext>
    {variant.maxPopAF > 0.0001 ? (
      <Alert>Consider founder effect in {maxPop} population</Alert>
    ) : (
      <Badge color="green">Rare across all populations</Badge>
    )}
  </ClinicalContext>
</PopulationFrequencyPlot>
```

## 5. Pathway Impact Visualizations

### 5.1 Interactive Pathway Diagram
```jsx
<PathwayImpactViewer variant={variant} pathway="MAPK">
  <PathwayDiagram>
    <Node id="EGFR" status="normal" />
    <Edge from="EGFR" to="RAS" />
    <Node id="RAS" status="activated" highlight={true}>
      <VariantLabel>KRAS G12D</VariantLabel>
    </Node>
    <Edge from="RAS" to="RAF" status="hyperactive" />
    <Node id="RAF" status="hyperactive" />
    <Edge from="RAF" to="MEK" status="hyperactive" />
    <Node id="MEK" status="hyperactive" />
    <Edge from="MEK" to="ERK" status="hyperactive" />
    <Node id="ERK" status="hyperactive" />
    
    <DrugTargets>
      <Target node="MEK" drugs={["Trametinib", "Cobimetinib"]} />
      <Target node="RAF" drugs={["Vemurafenib", "Dabrafenib"]} />
    </DrugTargets>
  </PathwayDiagram>
  
  <PathwayStats>
    <Stat label="Downstream effects" value="147 genes" />
    <Stat label="Drug targets available" value="4" />
  </PathwayStats>
</PathwayImpactViewer>
```

## 6. Conservation Visualizations

### 6.1 Multi-Species Alignment View
```jsx
<ConservationViewer variant={variant}>
  <AlignmentTrack>
    <Species name="Human" sequence="VGAGKSAL" highlight={5} />
    <Species name="Mouse" sequence="VGAGKSAL" />
    <Species name="Dog" sequence="VGAGKSAL" />
    <Species name="Chicken" sequence="VGAGKSAL" />
    <Species name="Zebrafish" sequence="VGAGKSAL" />
    <Species name="Fly" sequence="VGAGKSTL" diff={6} />
    <Species name="Yeast" sequence="IGSGKSTL" diff={[1,2,6]} />
  </AlignmentTrack>
  
  <ConservationScore>
    <PhyloP score={7.234} max={10} />
    <GERP score={5.89} max={6} />
    <Interpretation>
      Highly conserved across 98 vertebrate species
    </Interpretation>
  </ConservationScore>
</ConservationViewer>
```

## 7. Functional Score Visualizations

### 7.1 Multi-Predictor Radar Chart
```jsx
<FunctionalScoreRadar variant={variant}>
  <RadarChart>
    <Axis label="AlphaMissense" value={0.98} max={1} />
    <Axis label="REVEL" value={0.95} max={1} />
    <Axis label="CADD" value={29.4} max={40} />
    <Axis label="PolyPhen-2" value={1.0} max={1} />
    <Axis label="SIFT" value={0.0} max={1} inverted={true} />
    <Axis label="Conservation" value={0.89} max={1} />
  </RadarChart>
  
  <ConsensusScore>
    <ProgressBar value={0.94} label="94% Pathogenic" color="red" />
  </ConsensusScore>
</FunctionalScoreRadar>
```

### 7.2 Score Distribution Context
```jsx
<ScoreDistribution score={variant.revelScore}>
  <Histogram>
    <Bin range="0-0.1" count={50234} />
    <Bin range="0.1-0.2" count={23421} />
    {/* ... more bins */}
    <Bin range="0.9-1.0" count={3421} highlight={true}>
      <VariantMarker />
    </Bin>
  </Histogram>
  
  <Percentile>
    Your variant: 98.7th percentile for pathogenicity
  </Percentile>
</ScoreDistribution>
```

## 8. Clinical Trial & Drug Visualizations

### 8.1 Drug Response Network
```jsx
<DrugResponseNetwork variant={variant}>
  <CentralNode label={variant.name} />
  
  <DrugNodes>
    <Drug name="Vemurafenib" status="FDA Approved" distance={1}>
      <ResponseRate>ORR: 48%</ResponseRate>
      <SurvivalData>mPFS: 6.9 months</SurvivalData>
    </Drug>
    
    <Drug name="Dabrafenib + Trametinib" status="FDA Approved" distance={1}>
      <ResponseRate>ORR: 69%</ResponseRate>
      <SurvivalData>mPFS: 11.0 months</SurvivalData>
    </Drug>
    
    <Drug name="PLX8394" status="Phase II" distance={2}>
      <TrialInfo>NCT02428712</TrialInfo>
    </Drug>
  </DrugNodes>
  
  <ResistanceMechanisms>
    <Mechanism name="NRAS mutations" frequency="20%" />
    <Mechanism name="MEK1 mutations" frequency="7%" />
  </ResistanceMechanisms>
</DrugResponseNetwork>
```

## 9. Chromosomal Alteration Visualizations

### 9.1 Karyotype View
```jsx
<KaryotypeVisualizer alteration="t(9;22)(q34;q11)">
  <ChromosomePair>
    <Chromosome number={9}>
      <Band name="q34" highlight={true} />
      <BreakPoint position="133,289,000" />
    </Chromosome>
    
    <Chromosome number={22}>
      <Band name="q11" highlight={true} />
      <BreakPoint position="23,523,000" />
    </Chromosome>
  </ChromosomePair>
  
  <FusionResult>
    <FusionGene>BCR-ABL1</FusionGene>
    <FusionProtein>p210</FusionProtein>
    <Consequence>Constitutive tyrosine kinase activity</Consequence>
  </FusionResult>
</KaryotypeVisualizer>
```

### 9.2 Circos Plot for Complex Rearrangements
```jsx
<CircosPlot alterations={complexAlterations}>
  <Chromosome chr={1} />
  <Chromosome chr={2} />
  {/* ... all chromosomes */}
  
  <Translocation from="chr9:133289000" to="chr22:23523000" />
  <Deletion chr={13} start="32889611" end="32973805" />
  <Amplification chr={7} start="140434000" end="140624000" copies={8} />
  
  <Legend>
    <Item color="red" label="Deletion" />
    <Item color="blue" label="Translocation" />
    <Item color="green" label="Amplification" />
  </Legend>
</CircosPlot>
```

## 10. Expression & Methylation Visualizations

### 10.1 Expression Heatmap
```jsx
<ExpressionHeatmap gene={variant.gene}>
  <TissueExpression>
    <Tissue name="Melanoma" value={8.2} percentile={95} />
    <Tissue name="Normal Skin" value={2.1} percentile={20} />
    <Tissue name="Brain" value={0.5} percentile={5} />
    {/* More tissues */}
  </TissueExpression>
  
  <ComparisonBar>
    <NormalRange min={1} max={3} />
    <TumorExpression value={8.2} />
  </ComparisonBar>
</ExpressionHeatmap>
```

### 10.2 Methylation Pattern
```jsx
<MethylationViewer gene={variant.gene}>
  <CpGIsland start={-500} end={+1500}>
    <MethylationTrack>
      {cpgSites.map(site => (
        <CpGSite
          position={site.pos}
          methylation={site.methyl}
          color={methylationColor(site.methyl)}
        />
      ))}
    </MethylationTrack>
  </CpGIsland>
  
  <PromoterStatus>
    {avgMethylation > 0.7 ? (
      <Badge color="red">Hypermethylated - Gene Silenced</Badge>
    ) : (
      <Badge color="green">Normal Methylation</Badge>
    )}
  </PromoterStatus>
</MethylationViewer>
```

## 11. Interactive Features for All Visualizations

### 11.1 Universal Controls
```jsx
<VisualizationControls>
  <ZoomControl min={0.5} max={3} />
  <PanControl />
  <DownloadButton formats={['PNG', 'SVG', 'PDF']} />
  <ShareButton />
  <FullscreenToggle />
  <AnnotationToggle layers={['domains', 'variants', 'conservation']} />
</VisualizationControls>
```

### 11.2 Context-Sensitive Information
```jsx
<InfoPanel>
  <DataSources>
    <Source name="PDB" version="2024.01" />
    <Source name="UniProt" version="2024_01" />
    <Source name="gnomAD" version="v4.0" />
  </DataSources>
  
  <LastUpdated>2025-01-19</LastUpdated>
  
  <LearnMore>
    <Link to="/help/visualizations">Understanding this view</Link>
    <Link to="/methods">Calculation methods</Link>
  </LearnMore>
</InfoPanel>
```

## 12. Responsive Visualization Strategy

### 12.1 Desktop (Full Interactivity)
- All visualizations at full resolution
- Hover effects and tooltips
- Multiple visualizations visible simultaneously
- Advanced interaction modes

### 12.2 Tablet (Optimized Touch)
- Touch-friendly controls
- Simplified visualizations
- Single visualization focus
- Swipe between views

### 12.3 Mobile (Essential Information)
- Static images with key annotations
- Simplified charts
- Critical information only
- Link to desktop for full view

## Implementation Guidelines

1. **Performance**: Use WebGL for complex visualizations (3D structures, large heatmaps)
2. **Accessibility**: Provide text alternatives for all visual information
3. **Consistency**: Use consistent color schemes across all visualizations
4. **Modularity**: Build reusable visualization components
5. **Caching**: Cache rendered visualizations for performance
6. **Progressive Enhancement**: Start with basic view, add complexity as needed

Each visualization type provides the most clinically relevant view of that specific annotation type, making complex genomic information immediately understandable and actionable.