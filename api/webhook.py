from fastapi import APIRouter, Request, BackgroundTasks
from core.engine import process_incident

router = APIRouter()

@router.post("/webhook")
async def webhook_receiver(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    background_tasks.add_task(process_incident, payload)
    return {"status": "processing"}
