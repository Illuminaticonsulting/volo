"""
VOLO — Health Check Route
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "volo-api",
        "version": "0.1.0",
    }
