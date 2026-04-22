from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from core.engine import process_incident

router = APIRouter()


# Schema for an individual alert
class AlertItem(BaseModel):
    status: Optional[str] = "firing"
    labels: Dict[str, Any] = {}
    annotations: Dict[str, Any] = {}


# Schema for the incoming webhook from Prometheus/Grafana
class WebhookPayload(BaseModel):
    alerts: List[AlertItem] = Field(..., min_length=1)


@router.post("/webhook")
async def webhook_receiver(payload: WebhookPayload, background_tasks: BackgroundTasks):
    # FastAPI automatically validates payload and throws 422 Unprocessable Entity
    # if it is malformed, missing 'alerts', or if 'alerts' is empty.
    background_tasks.add_task(process_incident, payload.model_dump())
    return {"status": "processing"}
