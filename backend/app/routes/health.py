from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/")
async def health_check():
    return {
        "status": "healthy",
        "service": "PySenior",
        "timestamp": datetime.utcnow().isoformat(),
    }
