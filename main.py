import logging

import config  # noqa: F401 — imported for startup env-var validation side-effect
from fastapi import FastAPI
from api.webhook import router as webhook_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s\n'
)
logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(webhook_router)

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Responder Bot Server...")
    uvicorn.run(app, host="0.0.0.0", port=5000)
