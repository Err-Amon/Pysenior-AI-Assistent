from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def health_check() -> dict:
    from datetime import datetime, UTC

    return {
        "status": "healthy",
        "service": "PySenior",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "version": "1.0.0",
    }
