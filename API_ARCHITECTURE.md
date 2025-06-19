# Arti API Architecture

## Overview

The Arti API provides a RESTful interface for the annotation engine, built with:
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Primary database
- **Redis + RQ** - Job queue for async processing
- **WebSockets** - Real-time progress updates
- **React 18** - Frontend with Material-UI

## Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React App     │────▶│   FastAPI       │────▶│  RQ Worker      │
│  (Port 3000)    │◀────│  (Port 8000)    │◀────│  (Background)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                        │                        │
        │                        ▼                        ▼
        │               ┌─────────────────┐     ┌─────────────────┐
        │               │   PostgreSQL    │     │ Annotation      │
        │               │   Database      │     │ Engine          │
        │               └─────────────────┘     └─────────────────┘
        │                        │
        ▼                        ▼
┌─────────────────┐     ┌─────────────────┐
│   WebSocket     │     │     Redis       │
│   (Real-time)   │     │   (Job Queue)   │
└─────────────────┘     └─────────────────┘
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/token` - Login (OAuth2 compatible)
- `GET /api/auth/user` - Get current user
- `POST /api/auth/logout` - Logout

### Jobs
- `POST /api/jobs/create` - Upload VCF and create job
- `GET /api/jobs` - List user's jobs (paginated)
- `GET /api/jobs/{job_id}` - Get job details
- `DELETE /api/jobs/{job_id}` - Cancel job

### Variants
- `GET /api/variants/job/{job_id}` - List variants (paginated, filterable)
- `GET /api/variants/{variant_id}` - Get variant details
- `GET /api/variants/{variant_id}/igv` - Get IGV.js data

### Reports
- `POST /api/reports/{job_id}` - Generate report
- `GET /api/reports/download/{job_id}/{filename}` - Download report

### WebSocket
- `WS /ws/jobs/{job_id}` - Real-time job progress

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    username VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Jobs Table
```sql
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    name VARCHAR NOT NULL,
    description TEXT,
    status VARCHAR DEFAULT 'pending',
    input_file VARCHAR NOT NULL,
    cancer_type VARCHAR,
    case_uid VARCHAR,
    parameters JSONB DEFAULT '{}',
    progress INTEGER DEFAULT 0,
    total_variants INTEGER,
    current_step VARCHAR,
    error_message TEXT,
    result_summary JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

### Variants Table
```sql
CREATE TABLE variants (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    chromosome VARCHAR,
    position INTEGER,
    reference VARCHAR,
    alternate VARCHAR,
    gene_symbol VARCHAR,
    transcript_id VARCHAR,
    hgvs_c VARCHAR,
    hgvs_p VARCHAR,
    consequence VARCHAR,
    amp_tier VARCHAR,
    vicc_tier VARCHAR,
    confidence_score FLOAT,
    gnomad_af FLOAT,
    gnomad_af_popmax FLOAT,
    oncokb_evidence JSONB,
    civic_evidence JSONB,
    cosmic_evidence JSONB,
    annotations JSONB,
    INDEX idx_job_id (job_id),
    INDEX idx_gene (gene_symbol),
    INDEX idx_position (chromosome, position)
);
```

## Setup Instructions

### 1. Install Dependencies

```bash
# Backend
pip install -r requirements-api.txt

# Frontend
cd frontend
npm install
```

### 2. Start Services with Docker Compose

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

### 3. Initialize Database

```bash
# Run migrations (if using Alembic)
alembic upgrade head

# Or manually create tables
docker-compose exec postgres psql -U arti -d arti_db < schema.sql
```

### 4. Start Development Servers

```bash
# Backend API
uvicorn src.api.main:app --reload --port 8000

# RQ Worker
python -m src.api.tasks

# Frontend
cd frontend
npm run dev
```

### 5. Access the Application

- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- API Health: http://localhost:8000/health

## Environment Variables

Create a `.env` file:

```env
# Database
DATABASE_URL=postgresql://arti:arti@localhost/arti_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-change-in-production

# File Storage
UPLOAD_DIR=./uploads
RESULTS_DIR=./results

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

## Authentication Flow

1. User registers or logs in via `/api/auth/token`
2. Server returns JWT token
3. Frontend stores token in localStorage
4. All API requests include `Authorization: Bearer <token>`
5. Token expires after 24 hours

## Job Processing Flow

1. User uploads VCF via `/api/jobs/create`
2. API saves file and creates job record
3. Job is queued in Redis/RQ
4. Worker picks up job and runs annotation
5. Progress updates sent via WebSocket
6. Results saved to database
7. User can view/download results

## WebSocket Protocol

Connect to `ws://localhost:8000/ws/jobs/{job_id}`

Message format:
```json
{
  "type": "progress",
  "job_id": "uuid",
  "status": "running",
  "progress": 45,
  "message": "Running VEP annotation",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## Security Considerations

- JWT tokens for authentication
- CORS configured for frontend origin
- File upload size limits (500MB default)
- Rate limiting on job creation
- SQL injection prevention via SQLAlchemy
- Password hashing with bcrypt

## Performance Optimizations

- Database indexes on frequently queried fields
- Pagination for large result sets
- Async database operations
- Connection pooling
- Redis caching for frequent queries
- Compressed WebSocket messages

## Monitoring

- Health check endpoint at `/health`
- Structured logging with correlation IDs
- RQ job monitoring via Redis
- Database query performance tracking
- Error tracking integration ready

## Next Steps

1. Add API rate limiting
2. Implement result caching
3. Add batch job processing
4. Create admin interface
5. Add email notifications
6. Implement S3 storage option
7. Add API versioning
8. Create mobile app API