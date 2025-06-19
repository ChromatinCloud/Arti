# Real-time Backend-Frontend Integration

## Overview

The Arti annotation engine now supports real-time updates as annotations, tiers, canned text, and interpretations are generated. This document describes the implementation details and usage.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   React App     │────▶│   WebSocket     │◀────│   RQ Worker     │
│  (JobDetail)    │     │   Connection    │     │  (tasks.py)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │                         │
                                ▼                         ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  Redis PubSub   │     │  PostgreSQL     │
                        │   (Channels)    │     │   (Variants)    │
                        └─────────────────┘     └─────────────────┘
```

## Backend Implementation

### 1. RQ Worker with Real-time Updates (`src/api/tasks.py`)

The worker processes variants individually and sends updates via Redis pubsub:

```python
def process_annotation_job(job_id: str):
    # ... initialization ...
    
    def progress_callback(current, total, message, variant_result=None):
        # Send progress update
        send_progress(job_id, "running", progress, message, "annotation")
        
        # If we have a variant result, save to DB and send update
        if variant_result:
            variant = Variant(...)
            db.add(variant)
            db.commit()
            
            # Send real-time variant update
            send_variant_update(job_id, {
                "variant_id": variant.id,
                "chromosome": variant.chromosome,
                "position": variant.position,
                "amp_tier": variant.amp_tier,
                "confidence_score": variant.confidence_score,
                "canned_text": variant_result.get("canned_text", {}).get("summary"),
                "interpretation": variant_result.get("clinical_interpretation")
            })
```

### 2. WebSocket Handler (`src/api/websocket.py`)

Subscribes to Redis channels and streams updates to connected clients:

```python
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    # Subscribe to job updates channel
    channel = f"job_updates:{job_id}"
    await pubsub.subscribe(channel)
    
    # Handle messages from Redis pubsub
    async for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'])
            await websocket.send_json(data)
```

### 3. Update Types

Three types of real-time updates are sent:

1. **Progress Updates**
   ```json
   {
     "type": "progress",
     "job_id": "uuid",
     "status": "running",
     "progress": 45,
     "message": "Processing variant 45/100",
     "current_step": "annotation"
   }
   ```

2. **Variant Updates**
   ```json
   {
     "type": "variant_update",
     "job_id": "uuid",
     "variant": {
       "variant_id": 123,
       "chromosome": "chr7",
       "position": 140453136,
       "amp_tier": "Tier I",
       "confidence_score": 0.95,
       "canned_text": "This BRAF V600E variant...",
       "interpretation": "Strong clinical significance..."
     }
   }
   ```

3. **Connection Status**
   ```json
   {
     "type": "connected",
     "job_id": "uuid",
     "message": "Connected to job progress stream"
   }
   ```

## Frontend Implementation

### 1. JobDetail Component (`frontend/src/pages/JobDetail.tsx`)

Connects to WebSocket and displays real-time updates:

```typescript
const JobDetail: React.FC = () => {
  const [variants, setVariants] = useState<Variant[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  
  useEffect(() => {
    const ws = new WebSocket(wsUrl)
    
    ws.onmessage = (event) => {
      const update: JobUpdate = JSON.parse(event.data)
      handleUpdate(update)
    }
  }, [jobId, job?.status])
  
  const handleUpdate = (update: JobUpdate) => {
    switch (update.type) {
      case 'variant_update':
        if (update.variant) {
          setVariants(prev => [...prev, update.variant!])
        }
        break
    }
  }
}
```

### 2. Real-time Variant Table

The JobDetail component displays variants as they're processed:

- Shows position, gene, consequence, tier, confidence score
- Color-coded tiers (Tier I = red, Tier II = yellow, etc.)
- Confidence icons (✓ for high, ⚠ for medium, ✗ for low)
- Truncated interpretations with tooltips
- Click to view full variant details

### 3. Progress Visualization

- Linear progress bar showing overall completion
- Current processing step (validation, routing, annotation)
- Live message updates ("Processing variant 45/100")
- WebSocket connection status indicator

## Usage

### Starting the System

1. **Start Redis**
   ```bash
   docker-compose up -d redis
   ```

2. **Start PostgreSQL**
   ```bash
   docker-compose up -d postgres
   ```

3. **Start API Server**
   ```bash
   uvicorn src.api.main:app --reload --port 8000
   ```

4. **Start RQ Worker**
   ```bash
   python -m src.api.tasks
   ```

5. **Start Frontend**
   ```bash
   cd frontend
   npm run dev
   ```

### Viewing Real-time Updates

1. Upload a VCF file through the Dashboard
2. Click on the job name to navigate to JobDetail page
3. Watch as variants appear in real-time with:
   - Tier assignments (AMP/ASCO/CAP 2017)
   - Confidence scores
   - Canned text summaries
   - Clinical interpretations

## Performance Considerations

- Variants are processed individually to enable real-time updates
- Each variant update is ~500 bytes
- WebSocket reconnects automatically if connection drops
- Database writes are batched per variant
- Redis pubsub ensures reliable message delivery

## Error Handling

- WebSocket automatically reconnects on disconnect
- Failed variant processing doesn't stop the job
- Progress persists in database for recovery
- Errors are logged and displayed in UI

## Future Enhancements

1. **Batch Updates**: Send multiple variants in one message
2. **Compression**: Compress WebSocket messages
3. **Filtering**: Client-side variant filtering during stream
4. **Export**: Export real-time results as they generate
5. **Notifications**: Browser notifications for key variants