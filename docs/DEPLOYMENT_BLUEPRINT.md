# Deployment Blueprint

## Overview

This document defines deployment strategies based on proven patterns from leading clinical annotation tools (PCGR, Hartwig, OncoKB, Nirvana, nf-core). We adopt a **containerized Nextflow approach** with **versioned data bundles** and **clinical-grade security**.

## Deployment Architecture

### Primary Templates & Implementation Strategy

**Primary Templates:**
- **nf-core/oncoanalyser** (Hartwig): Fork and strip to DNA-only MVP, keeping proven workflow patterns
- **PCGR**: Data bundle approach and workflow patterns (re-implement in clean environment)
- **nf-core**: Container build patterns and CI/CD workflows

**Implementation Approach:**
- **Clean Re-implementation:** Take PCGR's proven patterns but build in modern, maintainable environment
- **Avoid Complex Environments:** Don't use PCGR's actual environment (known to be messy)
- **Local Knowledge Bases:** No external API dependencies, all KB data in versioned bundles

### Core Principles (Based on Industry Leaders)

1. **Containerized Everything** (nf-core pattern): Docker/Singularity for reproducibility
2. **Nextflow Orchestration** (Hartwig pattern, clean implementation): Workflow engine for complex pipelines  
3. **Versioned Data Bundles** (PCGR pattern, re-implemented): Locked KB snapshots for reproducibility
4. **Clinical Security** (Enterprise pattern): HIPAA-compliant infrastructure
5. **Modern Standards** (Our approach): Poetry, FastAPI, React, current best practices

## Container Strategy

### 1. Multi-Stage Container Build

Following **PCGR's** container optimization and **nf-core's** best practices:

```dockerfile
# Base image with common dependencies
FROM ubuntu:22.04 AS base
LABEL org.opencontainers.image.description="Annotation Engine Base"
LABEL org.opencontainers.image.source="https://github.com/org/annotation-engine"

# System dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    python3-dev \
    build-essential \
    curl \
    wget \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python environment
RUN pip3 install --no-cache-dir poetry==1.7.1
WORKDIR /app
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# VEP installation stage
FROM base AS vep-installer
RUN apt-get update && apt-get install -y \
    cpanminus \
    libdbi-perl \
    libdbd-mysql-perl \
    && rm -rf /var/lib/apt/lists/*

# Install VEP and plugins
WORKDIR /opt/vep
RUN git clone https://github.com/Ensembl/ensembl-vep.git
WORKDIR /opt/vep/ensembl-vep
RUN perl INSTALL.pl -a cf -s homo_sapiens -y GRCh38 \
    --PLUGINS dbNSFP,SpliceAI,AlphaMissense,CADD,gnomADv4

# Final production image
FROM base AS production
COPY --from=vep-installer /opt/vep /opt/vep
COPY . /app
WORKDIR /app

# Runtime configuration
ENV PATH="/opt/vep/ensembl-vep:$PATH"
ENV PYTHONPATH="/app/src:$PYTHONPATH"
ENV VEP_CACHE="/data/vep_cache"
ENV KB_DATA="/data/kb"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8000/health')"

EXPOSE 8000
CMD ["uvicorn", "src.annotation_engine.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Specialized Service Containers

Following **Hartwig's** microservice approach:

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Main annotation service
  annotation-api:
    build:
      context: .
      target: production
    image: annotation-engine:${VERSION:-latest}
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - ONCOKB_API_TOKEN=${ONCOKB_API_TOKEN}
      - KB_DATA_VERSION=${KB_DATA_VERSION}
    volumes:
      - ./data/kb:/data/kb:ro
      - ./data/vep_cache:/data/vep_cache:ro
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    networks:
      - annotation-network
    restart: unless-stopped
    
  # Database
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=annotation_engine
      - POSTGRES_USER=${DB_USER}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - annotation-network
    restart: unless-stopped
    
  # Task queue
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - annotation-network
    restart: unless-stopped
    
  # Background worker
  worker:
    image: annotation-engine:${VERSION:-latest}
    command: ["python", "-m", "src.annotation_engine.worker"]
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379
      - KB_DATA_VERSION=${KB_DATA_VERSION}
    volumes:
      - ./data/kb:/data/kb:ro
      - ./data/vep_cache:/data/vep_cache:ro
      - ./logs:/app/logs
    depends_on:
      - postgres
      - redis
    networks:
      - annotation-network
    restart: unless-stopped
    deploy:
      replicas: 2
      
  # Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    image: annotation-frontend:${VERSION:-latest}
    ports:
      - "3000:80"
    environment:
      - REACT_APP_API_URL=http://annotation-api:8000
    depends_on:
      - annotation-api
    networks:
      - annotation-network
    restart: unless-stopped

  # Nginx reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - annotation-api
      - frontend
    networks:
      - annotation-network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:

networks:
  annotation-network:
    driver: bridge
```

## Nextflow Pipeline Integration

### 1. Nextflow Configuration

Following **nf-core** and **PCGR** pipeline patterns:

```groovy
// nextflow.config
profiles {
    standard {
        process.executor = 'local'
        process.cpus = 4
        process.memory = '8 GB'
        docker.enabled = true
    }
    
    cluster {
        process.executor = 'slurm'
        process.queue = 'genomics'
        process.clusterOptions = '--account=clinical-genomics'
        singularity.enabled = true
        singularity.autoMounts = true
    }
    
    cloud {
        process.executor = 'awsbatch'
        aws.region = 'us-east-1'
        aws.batch.cliPath = '/home/ec2-user/miniconda/bin/aws'
        docker.enabled = true
    }
    
    test {
        params.input = 'data/test/test_samples.csv'
        params.genome = 'GRCh38'
        params.kb_bundle = 'data/test/kb_bundle_test.tar.gz'
    }
}

// Resource allocation by process
process {
    // VEP annotation
    withName: 'VEP_ANNOTATION' {
        cpus = 2
        memory = '4 GB'
        time = '1 h'
        container = 'annotation-engine/vep:latest'
    }
    
    // Knowledge base lookup
    withName: 'KB_ANNOTATION' {
        cpus = 1
        memory = '2 GB' 
        time = '30 min'
        container = 'annotation-engine/kb-annotator:latest'
    }
    
    // Rule engine
    withName: 'RULE_ENGINE' {
        cpus = 1
        memory = '1 GB'
        time = '15 min'
        container = 'annotation-engine/rules:latest'
    }
    
    // Report generation
    withName: 'GENERATE_REPORT' {
        cpus = 1
        memory = '2 GB'
        time = '20 min'
        container = 'annotation-engine/reporter:latest'
    }
}

// Parameter validation
includeConfig 'conf/params.config'
includeConfig 'conf/modules.config'
```

### 2. Pipeline Workflow Definition

Based on **PCGR's** annotation workflow:

```groovy
// main.nf
#!/usr/bin/env nextflow

nextflow.enable.dsl = 2

include { VEP_ANNOTATION } from './modules/vep.nf'
include { KB_ANNOTATION } from './modules/kb_lookup.nf'
include { RULE_ENGINE } from './modules/rules.nf'
include { GENERATE_REPORT } from './modules/report.nf'

workflow ANNOTATION_ENGINE {
    take:
    vcf_channel
    kb_bundle
    
    main:
    // VEP annotation
    VEP_ANNOTATION(
        vcf_channel,
        params.genome,
        params.vep_cache
    )
    
    // Knowledge base annotation  
    KB_ANNOTATION(
        VEP_ANNOTATION.out.annotated_vcf,
        kb_bundle
    )
    
    // Rule engine processing
    RULE_ENGINE(
        KB_ANNOTATION.out.annotated_json,
        params.guidelines_config
    )
    
    // Report generation
    GENERATE_REPORT(
        RULE_ENGINE.out.tiering_results,
        params.report_config
    )
    
    emit:
    annotated_vcf = VEP_ANNOTATION.out.annotated_vcf
    tiering_results = RULE_ENGINE.out.tiering_results
    html_report = GENERATE_REPORT.out.html_report
    json_output = GENERATE_REPORT.out.json_output
}

workflow {
    // Input validation
    if (!params.input) {
        error "Please specify input VCF with --input"
    }
    
    // Create input channel
    vcf_channel = Channel
        .fromPath(params.input)
        .map { vcf -> [vcf.baseName, vcf] }
    
    // Download/prepare KB bundle
    kb_bundle = Channel
        .fromPath(params.kb_bundle)
        .ifEmpty { error "KB bundle not found: ${params.kb_bundle}" }
    
    // Run main workflow
    ANNOTATION_ENGINE(vcf_channel, kb_bundle)
    
    // Publish results
    ANNOTATION_ENGINE.out.html_report
        .publishDir(params.outdir, mode: 'copy')
        
    ANNOTATION_ENGINE.out.json_output
        .publishDir(params.outdir, mode: 'copy')
}
```

## Data Bundle Management

### 1. Knowledge Base Bundle Builder

Following **PCGR's** data bundle approach:

```bash
#!/bin/bash
# scripts/build_kb_bundle.sh
set -euo pipefail

VERSION=${1:-$(date +%Y%m%d)}
BUNDLE_NAME="kb_bundle_${VERSION}"
WORK_DIR="/tmp/${BUNDLE_NAME}"
OUTPUT_DIR="./data/bundles"

echo "Building knowledge base bundle: ${BUNDLE_NAME}"

# Create working directory
mkdir -p "${WORK_DIR}"
cd "${WORK_DIR}"

# Download knowledge bases with version tracking
echo "Downloading OncoKB data..."
if [[ -n "${ONCOKB_API_TOKEN:-}" ]]; then
    # Download OncoKB data for local bundle (no runtime API calls)
    curl -H "Authorization: Bearer ${ONCOKB_API_TOKEN}" \
         "https://oncokb.org/api/v1/utils/allAnnotatedVariants" \
         -o oncokb_variants.json
    
    curl -H "Authorization: Bearer ${ONCOKB_API_TOKEN}" \
         "https://oncokb.org/api/v1/genes" \
         -o oncokb_genes.json
    
    curl -H "Authorization: Bearer ${ONCOKB_API_TOKEN}" \
         "https://oncokb.org/api/v1/utils/allCuratedGenes" \
         -o oncokb_curated_genes.json
else
    echo "Warning: ONCOKB_API_TOKEN not set, using cached OncoKB data"
    # Use previously downloaded data or public subset
    cp "${CACHE_DIR}/oncokb_variants_backup.json" oncokb_variants.json
    cp "${CACHE_DIR}/oncokb_genes_backup.json" oncokb_genes.json
fi

echo "Downloading ClinVar data..."
wget -O clinvar.vcf.gz \
    "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz"
wget -O clinvar_summary.txt.gz \
    "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"

echo "Downloading COSMIC data..."
# Note: Requires COSMIC account and authentication
if [[ -n "${COSMIC_TOKEN:-}" ]]; then
    curl -H "Authorization: Bearer ${COSMIC_TOKEN}" \
         "https://cancer.sanger.ac.uk/cosmic/file_download/GRCh38/cosmic/v99/CosmicMutantExport.tsv.gz" \
         -o cosmic_mutations.tsv.gz
fi

echo "Downloading CIViC data..."
wget -O civic_variants.tsv \
    "https://civicdb.org/downloads/nightly/nightly-VariantSummaries.tsv"
wget -O civic_evidence.tsv \
    "https://civicdb.org/downloads/nightly/nightly-EvidenceSummaries.tsv"

echo "Downloading gnomAD data..."
wget -O gnomad_genomes.vcf.gz \
    "https://gnomad-public-us-east-1.s3.amazonaws.com/release/4.0/vcf/genomes/gnomad.genomes.v4.0.sites.vcf.bgz"

echo "Downloading Cancer Hotspots..."
wget -O cancer_hotspots.maf \
    "https://cancerhotspots.org/files/hotspots_v2.maf"

echo "Downloading dbNSFP..."
wget -O dbNSFP.zip \
    "https://dbnsfp.s3.amazonaws.com/dbNSFP4.4a.zip"
unzip dbNSFP.zip
rm dbNSFP.zip

# Create version metadata
cat > version.json << EOF
{
  "bundle_version": "${VERSION}",
  "created_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "data_sources": {
    "oncokb": {
      "downloaded": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "api_version": "v1"
    },
    "clinvar": {
      "downloaded": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "file_date": "$(zcat clinvar.vcf.gz | head -20 | grep fileDate | cut -d= -f2)"
    },
    "civic": {
      "downloaded": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "release": "nightly"
    },
    "gnomad": {
      "downloaded": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "version": "4.0"
    },
    "cosmic": {
      "downloaded": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "version": "v99"
    }
  }
}
EOF

# Create index for fast lookup
echo "Creating database indices..."
python3 << 'PYTHON'
import json
import gzip
import pandas as pd

# Index ClinVar variants
print("Indexing ClinVar...")
clinvar_df = pd.read_csv('clinvar_summary.txt.gz', sep='\t', low_memory=False)
clinvar_index = clinvar_df.set_index(['Chromosome', 'Start', 'ReferenceAllele', 'AlternateAllele'])
clinvar_index.to_pickle('clinvar_index.pkl')

# Index CIViC variants  
print("Indexing CIViC...")
civic_df = pd.read_csv('civic_variants.tsv', sep='\t')
civic_index = civic_df.set_index(['chromosome', 'start', 'reference_bases', 'variant_bases'])
civic_index.to_pickle('civic_index.pkl')

print("Indexing complete")
PYTHON

# Package bundle
cd ..
echo "Creating bundle archive..."
tar -czf "${OUTPUT_DIR}/${BUNDLE_NAME}.tar.gz" "${BUNDLE_NAME}/"

# Generate checksums
cd "${OUTPUT_DIR}"
sha256sum "${BUNDLE_NAME}.tar.gz" > "${BUNDLE_NAME}.sha256"

# Cleanup
rm -rf "${WORK_DIR}"

echo "Bundle created: ${OUTPUT_DIR}/${BUNDLE_NAME}.tar.gz"
echo "Checksum: ${OUTPUT_DIR}/${BUNDLE_NAME}.sha256"
```

### 2. Bundle Validation and Testing

```python
# scripts/validate_bundle.py
#!/usr/bin/env python3
"""Validate knowledge base bundle integrity"""

import json
import tarfile
import hashlib
import pandas as pd
from pathlib import Path
import argparse

def validate_bundle(bundle_path: Path) -> bool:
    """Validate knowledge base bundle"""
    
    print(f"Validating bundle: {bundle_path}")
    
    # Check file integrity
    checksum_file = bundle_path.with_suffix('.sha256')
    if checksum_file.exists():
        expected_hash = checksum_file.read_text().split()[0]
        actual_hash = calculate_sha256(bundle_path)
        
        if expected_hash != actual_hash:
            print(f"❌ Checksum mismatch: {expected_hash} != {actual_hash}")
            return False
        print("✅ Checksum validation passed")
    
    # Extract and validate contents
    with tarfile.open(bundle_path, 'r:gz') as tar:
        tar.extractall('/tmp/bundle_validation')
        bundle_dir = Path('/tmp/bundle_validation') / bundle_path.stem.replace('.tar', '')
        
        # Check version metadata
        version_file = bundle_dir / 'version.json'
        if not version_file.exists():
            print("❌ Missing version.json")
            return False
            
        with open(version_file) as f:
            version_data = json.load(f)
            
        print(f"✅ Bundle version: {version_data['bundle_version']}")
        
        # Validate required files
        required_files = [
            'oncokb_variants.json',
            'clinvar.vcf.gz',
            'civic_variants.tsv',
            'gnomad_genomes.vcf.gz',
            'cancer_hotspots.maf'
        ]
        
        for file_name in required_files:
            file_path = bundle_dir / file_name
            if not file_path.exists():
                print(f"❌ Missing required file: {file_name}")
                return False
            print(f"✅ Found: {file_name}")
        
        # Validate data format
        try:
            # Test CIViC loading
            civic_df = pd.read_csv(bundle_dir / 'civic_variants.tsv', sep='\t', nrows=10)
            required_columns = ['gene', 'chromosome', 'start', 'variant_bases']
            if not all(col in civic_df.columns for col in required_columns):
                print("❌ CIViC file missing required columns")
                return False
            print("✅ CIViC format validation passed")
            
            # Test OncoKB loading
            with open(bundle_dir / 'oncokb_variants.json') as f:
                oncokb_data = json.load(f)
            if not isinstance(oncokb_data, list):
                print("❌ OncoKB data format invalid")
                return False
            print("✅ OncoKB format validation passed")
            
        except Exception as e:
            print(f"❌ Data validation failed: {e}")
            return False
    
    print("✅ Bundle validation successful")
    return True

def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Validate KB bundle')
    parser.add_argument('bundle', type=Path, help='Path to bundle file')
    args = parser.parse_args()
    
    success = validate_bundle(args.bundle)
    exit(0 if success else 1)
```

## Environment Management

### 1. Environment Configuration

Following **clinical compliance** standards:

```bash
# .env.production
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/annotation_engine
DB_POOL_SIZE=20
DB_POOL_TIMEOUT=30

# API Configuration  
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
DEBUG=false

# Knowledge Base APIs
ONCOKB_API_TOKEN=your_oncokb_token_here
COSMIC_TOKEN=your_cosmic_token_here
CIVIC_API_URL=https://civicdb.org/api

# Data Paths
KB_BUNDLE_PATH=/data/kb/kb_bundle_20240101.tar.gz
VEP_CACHE_PATH=/data/vep_cache
OUTPUT_PATH=/data/outputs

# Security
SECRET_KEY=your_secret_key_here
ALLOWED_HOSTS=annotation.hospital.org,localhost
CORS_ORIGINS=https://annotation-ui.hospital.org

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
AUDIT_LOGGING=true

# Clinical Compliance
HIPAA_COMPLIANT=true
AUDIT_RETENTION_DAYS=2555  # 7 years
DATA_ENCRYPTION=true

# Performance
CACHE_BACKEND=redis://redis:6379/0
CACHE_TTL=3600
BACKGROUND_TASKS=true

# Monitoring
SENTRY_DSN=your_sentry_dsn_here
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=30
```

### 2. Kubernetes Deployment

For **enterprise clinical environments**:

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: annotation-engine
  namespace: clinical-genomics
  labels:
    app: annotation-engine
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: annotation-engine
  template:
    metadata:
      labels:
        app: annotation-engine
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 2000
      
      containers:
      - name: annotation-api
        image: annotation-engine:v1.0.0
        ports:
        - containerPort: 8000
          name: http
        
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: ONCOKB_API_TOKEN
          valueFrom:
            secretKeyRef:
              name: api-tokens
              key: oncokb
              
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
            
        volumeMounts:
        - name: kb-data
          mountPath: /data/kb
          readOnly: true
        - name: vep-cache
          mountPath: /data/vep_cache
          readOnly: true
        - name: logs
          mountPath: /app/logs
          
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
          
      volumes:
      - name: kb-data
        persistentVolumeClaim:
          claimName: kb-data-pvc
      - name: vep-cache
        persistentVolumeClaim:
          claimName: vep-cache-pvc
      - name: logs
        persistentVolumeClaim:
          claimName: logs-pvc
          
---
apiVersion: v1
kind: Service
metadata:
  name: annotation-engine-service
  namespace: clinical-genomics
spec:
  selector:
    app: annotation-engine
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: annotation-engine-ingress
  namespace: clinical-genomics
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - annotation.hospital.org
    secretName: annotation-tls
  rules:
  - host: annotation.hospital.org
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: annotation-engine-service
            port:
              number: 8000
```

## CI/CD Pipeline

### 1. GitHub Actions Workflow

Following **nf-core** testing patterns:

```yaml
# .github/workflows/ci.yml
name: Continuous Integration

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 6 * * *'  # Daily validation

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10']
        
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
        
    - name: Install Poetry
      uses: snok/install-poetry@v1
      
    - name: Install dependencies
      run: poetry install
      
    - name: Run unit tests
      run: poetry run pytest tests/unit/ -v --cov=src/
      
    - name: Run integration tests
      run: poetry run pytest tests/integration/ -v
      
    - name: Run clinical validation
      run: poetry run pytest tests/clinical/ -v
      env:
        ONCOKB_API_TOKEN: ${{ secrets.ONCOKB_API_TOKEN }}
        
    - name: Upload coverage
      uses: codecov/codecov-action@v3

  docker-build:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
      
    - name: Login to Container Registry
      uses: docker/login-action@v3
      with:
        registry: ghcr.io
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}
        
    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: |
          ghcr.io/${{ github.repository }}:latest
          ghcr.io/${{ github.repository }}:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  nextflow-test:
    runs-on: ubuntu-latest
    needs: docker-build
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install Nextflow
      uses: nf-core/setup-nextflow@v1
      with:
        version: 23.04.0
        
    - name: Run pipeline test
      run: |
        nextflow run . -profile test,docker \
          --input tests/data/test_samples.csv \
          --outdir results/ \
          --kb_bundle tests/data/kb_bundle_test.tar.gz

  security-scan:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'
        format: 'sarif'
        output: 'trivy-results.sarif'
        
    - name: Upload Trivy scan results
      uses: github/codeql-action/upload-sarif@v2
      with:
        sarif_file: 'trivy-results.sarif'
```

### 2. Automated Deployment

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Configure kubectl
      uses: azure/k8s-set-context@v3
      with:
        method: kubeconfig
        kubeconfig: ${{ secrets.KUBE_CONFIG }}
        
    - name: Deploy to Kubernetes
      run: |
        # Update image tag
        sed -i "s|annotation-engine:.*|annotation-engine:${GITHUB_REF_NAME}|g" k8s/deployment.yaml
        
        # Apply deployment
        kubectl apply -f k8s/ -n clinical-genomics
        
        # Wait for rollout
        kubectl rollout status deployment/annotation-engine -n clinical-genomics
        
    - name: Run deployment tests
      run: |
        # Health check
        kubectl run test-pod --image=curlimages/curl --rm -i --restart=Never -- \
          curl -f http://annotation-engine-service:8000/health
          
    - name: Notify deployment
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        text: 'Annotation Engine deployed to production: ${{ github.ref_name }}'
      env:
        SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

This deployment blueprint provides enterprise-grade infrastructure following proven patterns from leading clinical genomics tools, ensuring scalability, security, and regulatory compliance.