from fastapi import FastAPI
from api.webhook import router as webhook_router

# The config is automatically loaded when imported by the services
# We import it here just to trigger the environment checks on startup
import config

app = FastAPI()

# Include the webhook router
app.include_router(webhook_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)