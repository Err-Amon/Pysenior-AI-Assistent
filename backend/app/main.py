import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import github_webhook, health

# Configure logging once at startup based on the LOG_LEVEL env variable
settings = get_settings()
logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(
    title="PySenior - AI Python Code Review Assistant",
    description="A Senior Python Engineer in your PRs 24/7",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["Health"])
app.include_router(github_webhook.router, prefix="/webhook", tags=["GitHub Webhook"])


@app.get("/")
async def root():
    return {
        "service": "PySenior",
        "tagline": "A Senior Python Engineer in your PRs 24/7",
        "status": "running",
        "version": "1.0.0",
    }
