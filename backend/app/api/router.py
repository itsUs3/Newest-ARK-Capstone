from fastapi import APIRouter

from app.api.routes.health import router as health_router
from app.api.routes.price import router as price_router

v2_router = APIRouter()
v2_router.include_router(health_router)
v2_router.include_router(price_router)
