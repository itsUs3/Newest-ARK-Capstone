from datetime import datetime

from fastapi import APIRouter

router = APIRouter(prefix="/api/v2", tags=["v2-health"])


@router.get("/health")
async def health_check_v2():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "v2",
    }
