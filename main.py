import logging
import core.settings  # noqa: F401 — imported for startup env-var validation side-effect
from fastapi import FastAPI
from contextlib import asynccontextmanager
from api.webhook import router as webhook_router, init_producer, close_producer
from prometheus_fastapi_instrumentator import Instrumentator

from core.log_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_producer()
    yield
    await close_producer()


app = FastAPI(lifespan=lifespan)
app.include_router(webhook_router)

# Instrument the app to expose /metrics for Prometheus
Instrumentator().instrument(app).expose(app)

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting Responder Bot Server...")
    uvicorn.run(app, host="0.0.0.0", port=5000)
