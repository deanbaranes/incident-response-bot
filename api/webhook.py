import hmac
import hashlib
import logging
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from core.engine import process_incident
from config import WEBHOOK_SECRET

logger = logging.getLogger(__name__)

router = APIRouter()


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
    payload = WebhookPayload.model_validate_json(body)
    background_tasks.add_task(process_incident, payload.model_dump())
    return {"status": "processing"}
