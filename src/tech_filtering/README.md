# Technical Variant Filtering Module

This module provides a modern web interface for technical variant filtering as a pre-processor to the Arti clinical interpretation system.

## Overview

The technical filtering module allows clinicians to apply standard quality filters to VCF files before sending variants for clinical interpretation. It supports both tumor-only and tumor-normal analysis modes with mode-specific filtering logic.

## Features

- **Dual Mode Support**: Tumor-only and tumor-normal workflows with distinct visual themes
- **13 Configurable Filters**: Quality, allele, technical, and population filters
- **Interactive UI**: Sliders, checkboxes, and range controls for intuitive filtering
- **Real-time Variant Counting**: Shows reduction in variant count after filtering
- **Seamless Arti Integration**: One-click handoff to clinical interpretation

## Quick Start

### Frontend Development
```bash
cd src/tech_filtering
npm install
npm run dev
# Opens at http://localhost:3001
```

### Backend API
The FastAPI backend should be running at http://localhost:8000
```bash
cd src/annotation_engine/api
uvicorn main:app --reload
```

## Reference Files Required

Place these files in the appropriate directories:

1. **Panel BED file**: `resources/assay/default_assay/panel.bed`
2. **Assay blacklist**: `resources/assay/default_assay/blacklist.assay.bed`
3. **gnomAD frequencies**: `resources/reference/genome/grch38/gnomad.freq.vcf.gz`

The genome reference blacklists are already in place:
- `resources/reference/genome/grch38/blacklist.grch38.bed.gz`
- `resources/reference/genome/grch37/blacklist.grch37.bed.gz`

## Architecture

### Frontend (React + TypeScript)
- **State Management**: Zustand for lightweight state handling
- **Styling**: Tailwind CSS with mode-specific themes
- **Components**: Modular, reusable filter controls

### Backend (FastAPI)
- **BCFtools Integration**: Sequential filter application
- **File Management**: Temporary file handling for pipeline operations
- **API Endpoints**: RESTful endpoints for filtering and file operations

## Filter Specifications

### Quality Filters
- PASS variants only
- Minimum variant quality (QUAL)
- Minimum genotype quality (GQ)
- Minimum read depth (DP)

### Allele Filters
- Minimum ALT read support
- Minimum variant allele fraction (VAF)
- Heterozygote allele balance range

### Technical Filters
- Maximum strand bias (FS/SOR)
- Minimum mapping quality (MQ)
- Panel region restriction

### Population & Impact Filters
- Maximum population allele frequency
- VEP impact categories (HIGH/MODERATE)
- Blacklist removal

## Mode-Specific Behavior

### Tumor-Only Mode
- Warm red color theme
- Standard somatic variant filtering
- 5% default VAF threshold

### Tumor-Normal Mode
- Cool blue color theme
- Additional filters for normal sample
- Tumor/normal VAF ratio checking
- Germline variant subtraction

## API Integration

The module integrates with the main Arti API through:
- `/api/v1/tech-filtering/apply`: Apply filters to VCF
- `/api/v1/tech-filtering/variant-count`: Get variant counts
- `/api/v1/variants/annotate`: Send filtered VCF to Arti

## Future Enhancements

- Germline mode support
- Multiple assay configurations
- Custom filter presets
- Batch processing
- Progress monitoring for large files