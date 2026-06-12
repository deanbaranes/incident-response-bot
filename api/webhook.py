import hmac
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
from aiokafka import AIOKafkaProducer  # type: ignore
from prometheus_client import Counter

from core.engine import process_incident
from core.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

producer: Optional[AIOKafkaProducer] = None

# Prometheus Metrics
WEBHOOK_ALERTS_RECEIVED = Counter(
    "incident_bot_webhook_alerts_received_total",
    "Total number of alerts received via webhook",
    ["alertname", "status"],
)

WEBHOOK_KAFKA_PUBLISH_FAILURES = Counter(
    "incident_bot_webhook_kafka_publish_failures_total",
    "Total number of failures when publishing to Kafka",
)


async def init_producer():
    global producer
    if settings.USE_KAFKA_QUEUE:
        try:
            producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                acks="all",
                enable_idempotence=True,
                linger_ms=5,
                compression_type="zstd",
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
    if not header or not settings.WEBHOOK_SECRET:
        return False
    expected = (
        "sha256="
        + hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    )

    # Try comparing without prefix just in case (Grafana native)
    expected_no_prefix = hmac.new(
        settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    if hmac.compare_digest(expected_no_prefix, header):
        return True

    return hmac.compare_digest(expected, header)


MAX_PAYLOAD_SIZE = 1 * 1024 * 1024  # 1MB


@router.post("/webhook", status_code=202)
async def webhook_receiver(request: Request, background_tasks: BackgroundTasks):
    """Receive and validate webhook alerts from Grafana."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_PAYLOAD_SIZE:
        logger.warning(f"Rejected webhook: payload too large ({content_length} bytes)")
        raise HTTPException(status_code=413, detail="Payload Too Large")

    body = await request.body()

    # Verify HMAC signature for security
    sig_header = request.headers.get("X-Grafana-Webhook-Signature")
    if not _verify_signature(body, sig_header):
        logger.warning("Rejected webhook: invalid or missing signature")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # FastAPI validates payload and returns 422 on error
    try:
        payload = WebhookPayload.model_validate_json(body)
    except Exception as e:
        logger.warning(
            f"Rejected webhook: malformed JSON or missing required fields. Error: {e}"
        )
        raise HTTPException(status_code=422, detail="Unprocessable Entity")

    incident_id = str(uuid.uuid4())
    logger.info(f"Received webhook for incident {incident_id}")

    # Track metrics
    for alert in payload.alerts:
        alertname = alert.labels.get("alertname", "unknown")
        status = alert.status or "unknown"
        WEBHOOK_ALERTS_RECEIVED.labels(alertname=alertname, status=status).inc()

    if settings.USE_KAFKA_QUEUE and producer:
        try:
            message = payload.model_dump()
            message["incident_id"] = incident_id
            message["received_at"] = datetime.now(timezone.utc).isoformat()
            message["source_ip"] = request.client.host if request.client else "unknown"

            key = payload.alerts[0].labels.get("alertname", "unknown").encode("utf-8")
            await producer.send_and_wait(
                topic=settings.KAFKA_INCIDENT_TOPIC, value=message, key=key
            )
            logger.info(f"Published incident {incident_id} to Kafka")
        except Exception as e:
            WEBHOOK_KAFKA_PUBLISH_FAILURES.inc()
            logger.error(f"Failed to publish to Kafka: {e}")
            raise HTTPException(
                status_code=503, detail="Service Unavailable (Broker Down)"
            )
    else:
        background_tasks.add_task(process_incident, payload.model_dump(), incident_id)

    return {"status": "processing", "incident_id": incident_id}
