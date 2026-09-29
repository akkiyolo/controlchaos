"""System endpoints: health, readiness, provider status."""

from fastapi import APIRouter

from app.config import get_settings
from app.db import check_db_connection
from app.services.agent.providers import llm_service

router = APIRouter(tags=["system"])
settings = get_settings()


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "synthetic_notice": "ALL DATA IN CONTROLCHAOS IS SYNTHETIC FOR DEMONSTRATION PURPOSES ONLY",
    }


@router.get("/ready")
def readiness_check():
    db_status = "ok"
    try:
        check_db_connection()
    except Exception as exc:
        db_status = f"unhealthy: {str(exc)}"

    return {
        "status": "ready" if db_status == "ok" else "degraded",
        "database": db_status,
        "providers": llm_service.get_provider_status(),
    }


@router.get("/providers/status")
def provider_status():
    """Returns safe provider status (configured/unconfigured) without exposing secrets."""
    return llm_service.get_provider_status()
