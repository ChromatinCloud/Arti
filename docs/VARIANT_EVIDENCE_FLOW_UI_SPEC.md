# Variant Evidence Flow UI Specification

> Visual representation of the complete annotation → rules → tier → interpretation pipeline

## Core Concept: Evidence Flow Visualization

The UI must clearly show how we go from a raw variant to a clinical interpretation, displaying each step in the decision-making process.

```
VARIANT → ANNOTATIONS → RULES TRIGGERED → TIER ASSIGNMENT → INTERPRETATION
   ↓           ↓              ↓                 ↓               ↓
 Input    Evidence Base   Logic Engine    Classification    Clinical Text
```

## 1. Main Evidence Flow Interface

### 1.1 Visual Pipeline Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│ BRAF p.V600E (chr7:140,753,336 A>T)                          [Tier I-A] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────┐ │
│  │   VARIANT   │───▶│ ANNOTATIONS │───▶│    RULES    │───▶│  TIER   │ │
│  │    INFO     │    │  COLLECTED  │    │  TRIGGERED  │    │ ASSIGN  │ │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────┘ │
│         │                   │                   │               │       │
│         ▼                   ▼                   ▼               ▼       │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    INTERPRETATION SYNTHESIS                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Expandable Evidence Cards

Each stage in the flow can be expanded to show details:

## 2. Stage 1: Variant Information

```jsx
<VariantCard expanded={true}>
  <CardHeader>
    <Icon>🧬</Icon>
    <Title>Variant Details</Title>
    <Badge>Input</Badge>
  </CardHeader>
  
  <CardContent>
    <Grid>
      <DataPoint label="Gene" value="BRAF" />
      <DataPoint label="Position" value="chr7:140,753,336" />
      <DataPoint label="Change" value="A>T" />
      <DataPoint label="HGVS.c" value="c.1799T>A" />
      <DataPoint label="HGVS.p" value="p.Val600Glu" />
      <DataPoint label="VAF" value="45%" highlight={true} />
      <DataPoint label="Depth" value="250x" />
      <DataPoint label="Consequence" value="Missense" />
    </Grid>
  </CardContent>
  
  <FlowConnector to="annotations" animated={true} />
</VariantCard>
```

## 3. Stage 2: Annotations Collected

```jsx
<AnnotationsCard expanded={true}>
  <CardHeader>
    <Icon>📚</Icon>
    <Title>Evidence Collected</Title>
    <Badge>5 Sources</Badge>
  </CardHeader>
  
  <TabPanel>
    <Tab label="OncoKB" badge="Level 1">
      <EvidenceItem>
        <Source>OncoKB v3.14</Source>
        <Finding type="therapeutic">
          FDA-approved: Vemurafenib, Dabrafenib for Melanoma
        </Finding>
        <Level>Level 1</Level>
        <Confidence>High</Confidence>
      </EvidenceItem>
    </Tab>
    
    <Tab label="ClinVar" badge="Pathogenic">
      <EvidenceItem>
        <Source>ClinVar 2025.01</Source>
        <Finding type="pathogenicity">
          Pathogenic (5-star review)
        </Finding>
        <Conditions>Melanoma, CRC, NSCLC</Conditions>
        <Submissions>147 concordant</Submissions>
      </EvidenceItem>
    </Tab>
    
    <Tab label="COSMIC" badge="Hotspot">
      <EvidenceItem>
        <Source>COSMIC v98</Source>
        <Finding type="frequency">
          Tier 1 Hotspot - 12,847 samples
        </Finding>
        <Distribution>
          <Bar label="Melanoma" value={45} />
          <Bar label="Thyroid" value={40} />
          <Bar label="CRC" value={10} />
        </Distribution>
      </EvidenceItem>
    </Tab>
    
    <Tab label="Functional" badge="Damaging">
      <EvidenceGrid>
        <Score name="AlphaMissense" value={0.98} status="pathogenic" />
        <Score name="REVEL" value={0.95} status="pathogenic" />
        <Score name="CADD" value={29.4} status="damaging" />
        <Score name="Conservation" value={5.29} status="conserved" />
      </EvidenceGrid>
    </Tab>
    
    <Tab label="Population" badge="Rare">
      <PopulationData>
        <Database name="gnomAD" af={0.00001} status="rare" />
        <Database name="ExAC" af={0.00002} status="rare" />
        <Note>Absent in matched population</Note>
      </PopulationData>
    </Tab>
  </TabPanel>
  
  <FlowConnector to="rules" animated={true} />
</AnnotationsCard>
```

## 4. Stage 3: Rules Triggered

```jsx
<RulesCard expanded={true}>
  <CardHeader>
    <Icon>⚙️</Icon>
    <Title>Classification Rules</Title>
    <Badge>12 Rules Evaluated</Badge>
  </CardHeader>
  
  <GuidelinePanel>
    {/* OncoKB Rules */}
    <GuidelineSection name="OncoKB" logo="/oncokb-logo.png">
      <RuleResult fired={true} impact="high">
        <RuleName>FDA_APPROVED_SAME_CANCER</RuleName>
        <RuleLogic>
          IF variant.oncokb_level == "1" 
          AND cancer_type IN approved_indications
          THEN assign Level 1
        </RuleLogic>
        <Evidence>
          ✓ Level 1 annotation found
          ✓ Melanoma in approved list
        </Evidence>
        <Outcome>→ OncoKB Level 1</Outcome>
      </RuleResult>
    </GuidelineSection>
    
    {/* CGC/VICC Rules */}
    <GuidelineSection name="CGC/VICC" logo="/vicc-logo.png">
      <RuleResult fired={true} impact="high">
        <RuleName>VICC_BIOMARKER_MATCH</RuleName>
        <RuleLogic>
          IF is_biomarker(variant, cancer_type)
          AND has_fda_approval
          THEN assign Tier I-A
        </RuleLogic>
        <Evidence>
          ✓ BRAF V600E is biomarker for melanoma
          ✓ FDA-approved therapies exist
        </Evidence>
        <Outcome>→ Tier I-A (Biomarker)</Outcome>
      </RuleResult>
      
      <RuleResult fired={true} impact="medium">
        <RuleName>ONCOGENICITY_SCORE</RuleName>
        <RuleLogic>
          Score = hotspot(3) + functional(2) + literature(3)
        </RuleLogic>
        <ScoreBreakdown>
          <ScoreItem>Hotspot: 3/3 (Tier 1 COSMIC)</ScoreItem>
          <ScoreItem>Functional: 2/3 (Multiple predictors)</ScoreItem>
          <ScoreItem>Literature: 3/3 (>100 papers)</ScoreItem>
          <Total>Total: 8/9 → Oncogenic</Total>
        </ScoreBreakdown>
      </RuleResult>
    </GuidelineSection>
    
    {/* AMP/ASCO Rules */}
    <GuidelineSection name="AMP/ASCO 2017" logo="/amp-logo.png">
      <RuleResult fired={true} impact="high">
        <RuleName>AMP_STRONG_CLINICAL</RuleName>
        <RuleLogic>
          IF FDA_approved_therapy
          AND professional_guideline_inclusion
          THEN Strong evidence (Tier I)
        </RuleLogic>
        <Evidence>
          ✓ FDA approved: Vemurafenib
          ✓ NCCN Guidelines: Recommended
        </Evidence>
        <Outcome>→ Tier I-A</Outcome>
      </RuleResult>
    </GuidelineSection>
  </GuidelinePanel>
  
  <RuleSummary>
    <Stat label="Rules Evaluated" value={12} />
    <Stat label="Rules Fired" value={4} color="green" />
    <Stat label="Conflicts" value={0} color="gray" />
  </RuleSummary>
  
  <FlowConnector to="tier" animated={true} />
</RulesCard>
```

## 5. Stage 4: Tier Assignment

```jsx
<TierAssignmentCard expanded={true}>
  <CardHeader>
    <Icon>🎯</Icon>
    <Title>Classification Results</Title>
    <Badge>Consensus: Tier I-A</Badge>
  </CardHeader>
  
  <TierGrid>
    <TierResult guideline="OncoKB" tier="Level 1" confidence="High">
      <Justification>
        FDA-approved biomarker in patient's cancer type
      </Justification>
    </TierResult>
    
    <TierResult guideline="CGC/VICC" tier="Tier I-A" confidence="High">
      <Justification>
        Biomarker with regulatory approval
        Oncogenicity: Oncogenic (8/9 score)
      </Justification>
    </TierResult>
    
    <TierResult guideline="AMP/ASCO" tier="Tier I-A" confidence="High">
      <Justification>
        Strong clinical significance with FDA approval
      </Justification>
    </TierResult>
  </TierGrid>
  
  <ConsensusPanel>
    <ConsensusResult>
      <FinalTier>Tier I-A</FinalTier>
      <Agreement>100% concordance</Agreement>
      <Confidence>High (0.95)</Confidence>
    </ConsensusResult>
    
    <ActionButtons>
      <Button variant="primary">Accept Classification</Button>
      <Button variant="secondary">Override Tier</Button>
      <Button variant="ghost">View Details</Button>
    </ActionButtons>
  </ConsensusPanel>
  
  <FlowConnector to="interpretation" animated={true} />
</TierAssignmentCard>
```

## 6. Stage 5: Interpretation Options

```jsx
<InterpretationCard expanded={true}>
  <CardHeader>
    <Icon>📝</Icon>
    <Title>Clinical Interpretation</Title>
    <Badge>3 Templates Available</Badge>
  </CardHeader>
  
  <InterpretationOptions>
    <Template selected={true} confidence="0.98">
      <TemplateHeader>
        <Name>BRAF V600E - Melanoma Standard</Name>
        <Source>OncoKB + ClinVar Evidence</Source>
      </TemplateHeader>
      
      <Preview>
        <Text>
          The BRAF p.V600E (c.1799T>A) missense variant is a well-characterized 
          oncogenic driver mutation found in approximately 50% of melanomas. This 
          variant results in constitutive activation of the MAPK signaling pathway.
          
          <EvidenceHighlight>
            This variant is an FDA-approved biomarker for targeted therapy with 
            BRAF inhibitors (vemurafenib, dabrafenib, encorafenib) in combination 
            with MEK inhibitors.
          </EvidenceHighlight>
          
          Clinical trials have demonstrated significant improvement in progression-free 
          survival with combination BRAF/MEK inhibition compared to monotherapy...
        </Text>
        
        <CitationList>
          <Citation>[1] Chapman et al., NEJM 2011 (BRIM-3)</Citation>
          <Citation>[2] Robert et al., NEJM 2015 (COMBI-v)</Citation>
          <Citation>[3] NCCN Guidelines v2.2024</Citation>
        </CitationList>
      </Preview>
      
      <Actions>
        <Button>Use This Template</Button>
        <Button>Customize</Button>
      </Actions>
    </Template>
    
    <Template confidence="0.85">
      <TemplateHeader>
        <Name>BRAF V600E - Brief Clinical</Name>
        <Source>Condensed interpretation</Source>
      </TemplateHeader>
      <Preview collapsed={true} />
    </Template>
    
    <Template confidence="0.80">
      <TemplateHeader>
        <Name>Custom Interpretation</Name>
        <Source>Start from scratch</Source>
      </TemplateHeader>
    </Template>
  </InterpretationOptions>
  
  <InterpretationEditor>
    <Toolbar>
      <Button icon="bold" />
      <Button icon="italic" />
      <Button icon="citation" />
      <Dropdown label="Insert Evidence" />
      <Dropdown label="Add Citation" />
    </Toolbar>
    
    <TextArea 
      value={selectedInterpretation}
      onChange={handleEdit}
      placeholder="Begin typing interpretation..."
    />
    
    <FooterActions>
      <WordCount>245 words</WordCount>
      <Button>Save Draft</Button>
      <Button variant="primary">Finalize Interpretation</Button>
    </FooterActions>
  </InterpretationEditor>
</InterpretationCard>
```

## 7. Evidence Flow Summary View

### 7.1 Collapsed Pipeline View
When not actively reviewing, show a compact flow:

```jsx
<CompactFlowView>
  <FlowStep status="complete" label="Variant" />
  <FlowArrow />
  <FlowStep status="complete" label="5 Annotations" />
  <FlowArrow />
  <FlowStep status="complete" label="4 Rules Fired" />
  <FlowArrow />
  <FlowStep status="complete" label="Tier I-A" />
  <FlowArrow />
  <FlowStep status="active" label="Interpretation" />
</CompactFlowView>
```

### 7.2 Evidence Traceback
Hover over any element to see its provenance:

```jsx
<Tooltip trigger="hover">
  <TooltipTrigger>Tier I-A</TooltipTrigger>
  <TooltipContent>
    <TracebackPath>
      OncoKB Level 1 → FDA_APPROVED_SAME_CANCER → Tier I-A
      ClinVar Pathogenic → VICC_BIOMARKER_MATCH → Tier I-A
      COSMIC Hotspot → ONCOGENICITY_SCORE (8/9) → Oncogenic
    </TracebackPath>
  </TooltipContent>
</Tooltip>
```

## 8. Interactive Features

### 8.1 Rule Explorer
Click any rule to see:
- Full rule logic
- Input parameters
- Evidence that triggered it
- Historical performance
- Similar cases

### 8.2 Evidence Inspector
Click any annotation to see:
- Source database details
- Version information
- Confidence metrics
- Conflicting evidence
- Update history

### 8.3 What-If Analysis
- Modify VAF to see tier changes
- Toggle evidence sources on/off
- Adjust cancer type to see impact
- Compare guidelines side-by-side

## 9. Visual Design Principles

### 9.1 Color Coding
- **Green**: Strong evidence, high confidence
- **Yellow**: Moderate evidence, medium confidence  
- **Orange**: Weak evidence, low confidence
- **Red**: Conflicts or warnings
- **Blue**: Informational
- **Purple**: Computational predictions

### 9.2 Animation and Transitions
- Smooth flow between stages
- Animated connectors show data flow
- Expand/collapse with easing
- Highlight active elements
- Subtle pulse on updates

### 9.3 Information Hierarchy
1. Variant and final tier most prominent
2. Evidence summary next
3. Detailed rules on demand
4. Full annotations expandable

## 10. Implementation Architecture

### 10.1 Component Structure
```typescript
interface EvidenceFlowProps {
  variant: Variant;
  annotations: Annotation[];
  rulesEvaluated: RuleEvaluation[];
  tierAssignments: TierAssignment[];
  interpretations: Interpretation[];
  onTierOverride: (tier: string) => void;
  onInterpretationSelect: (id: string) => void;
}

interface RuleEvaluation {
  ruleId: string;
  ruleName: string;
  guideline: 'OncoKB' | 'CGC_VICC' | 'AMP_ASCO';
  fired: boolean;
  evidence: Evidence[];
  outcome: string;
  confidence: number;
  logic: string;
}
```

### 10.2 State Management
```typescript
interface EvidenceFlowState {
  expandedSections: Set<string>;
  selectedGuideline: string | null;
  highlightedRule: string | null;
  tracebackActive: boolean;
  whatIfMode: boolean;
}
```

This visual evidence flow interface makes the entire annotation → interpretation pipeline transparent and understandable, allowing users to see exactly how the system arrived at its conclusions.