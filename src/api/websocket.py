"""
WebSocket handler for real-time job progress with Redis pubsub
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
import json
import asyncio
import logging
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Store active connections
connections: Dict[str, WebSocket] = {}


async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for job progress with Redis pubsub"""
    
    await websocket.accept()
    connections[job_id] = websocket
    
    # Create Redis connection for pubsub
    redis_client = await redis.from_url("redis://localhost:6379")
    pubsub = redis_client.pubsub()
    
    try:
        # Subscribe to job updates channel
        channel = f"job_updates:{job_id}"
        await pubsub.subscribe(channel)
        
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "job_id": job_id,
            "message": "Connected to job progress stream"
        })
        
        # Create tasks for handling messages
        async def handle_redis_messages():
            """Handle messages from Redis pubsub"""
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        await websocket.send_json(data)
                    except Exception as e:
                        logger.error(f"Error sending message: {e}")
        
        async def handle_websocket_messages():
            """Handle messages from WebSocket client"""
            while True:
                try:
                    data = await websocket.receive_text()
                    if data == "ping":
                        await websocket.send_text("pong")
                except WebSocketDisconnect:
                    break
                except Exception as e:
                    logger.error(f"WebSocket error: {e}")
                    break
        
        # Run both tasks concurrently
        await asyncio.gather(
            handle_redis_messages(),
            handle_websocket_messages()
        )
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
    finally:
        # Cleanup
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await redis_client.close()
        
        # Remove connection
        if job_id in connections:
            del connections[job_id]


async def send_progress_update(job_id: str, update: dict):
    """Send progress update to connected client (legacy - use Redis pubsub instead)"""
    
    if job_id in connections:
        try:
            await connections[job_id].send_json(update)
        except Exception as e:
            logger.error(f"Failed to send update for job {job_id}: {e}")
            # Remove dead connection
            if job_id in connections:
                del connections[job_id]