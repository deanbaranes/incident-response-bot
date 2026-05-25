import hmac
import hashlib
import logging
import uuid
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
from aiokafka import AIOKafkaProducer  # type: ignore

from core.engine import process_incident
from config import (
    WEBHOOK_SECRET,
    USE_KAFKA_QUEUE,
    KAFKA_BOOTSTRAP_SERVERS,
    KAFKA_INCIDENT_TOPIC,
)

logger = logging.getLogger(__name__)

router = APIRouter()

producer: Optional[AIOKafkaProducer] = None


async def init_producer():
    global producer
    if USE_KAFKA_QUEUE:
        try:
            producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await producer.start()
            logger.info("Kafka Producer started.")
        except Exception as e:
            logger.error(f"Failed to start Kafka Producer: {e}")


async def close_producer():
    global producer
    if producer:
        await producer.stop()
        logger.info("Kafka Producer stopped.")


# Schema for an individual alert
class AlertItem(BaseModel):
    status: Optional[str] = "firing"
    labels: Dict[str, Any] = {}
    annotations: Dict[str, Any] = {}


# Schema for the incoming webhook payload from Grafana
class WebhookPayload(BaseModel):
    alerts: List[AlertItem] = Field(..., min_length=1)


def _verify_signature(body: bytes, header: Optional[str]) -> bool:
    """Verify Grafana HMAC-SHA256 webhook signature."""
    if not WEBHOOK_SECRET:
        logger.warning("WEBHOOK_SECRET not set — signature verification skipped")
        return True
    if not header:
        return False
    expected = (
        "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    )
    return hmac.compare_digest(expected, header)


@router.post("/webhook")
async def webhook_receiver(request: Request, background_tasks: BackgroundTasks):
    """Receive and validate webhook alerts from Grafana."""
    body = await request.body()

    # Verify HMAC signature for security
    sig_header = request.headers.get("X-Grafana-Webhook-Signature")
    if not _verify_signature(body, sig_header):
        logger.warning("Rejected webhook: invalid or missing signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # FastAPI validates payload and returns 422 on error
    try:
        payload = WebhookPayload.model_validate_json(body)
    except Exception:
        logger.warning("Rejected webhook: malformed JSON or missing required fields")
        raise HTTPException(status_code=422, detail="Unprocessable Entity")

    incident_id = str(uuid.uuid4())
    logger.info(f"Received webhook for incident {incident_id}")

    if USE_KAFKA_QUEUE and producer:
        try:
            message = payload.model_dump()
            message["incident_id"] = incident_id
            key = payload.alerts[0].labels.get("alertname", "unknown").encode("utf-8")
            await producer.send_and_wait(
                topic=KAFKA_INCIDENT_TOPIC, value=message, key=key
            )
            logger.info(f"Published incident {incident_id} to Kafka")
        except Exception as e:
            logger.error(f"Failed to publish to Kafka: {e}")
            raise HTTPException(
                status_code=503, detail="Service Unavailable (Broker Down)"
            )
    else:
        background_tasks.add_task(process_incident, payload.model_dump(), incident_id)

    return {"status": "processing", "incident_id": incident_id}
