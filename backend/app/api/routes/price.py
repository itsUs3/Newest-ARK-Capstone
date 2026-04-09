from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas.price import PriceRequestV2, PriceResponseV2
from app.core.providers import get_price_predictor
from app.services.price_service import PriceService

router = APIRouter(prefix="/api/v2/price", tags=["v2-price"])


def get_price_service(predictor=Depends(get_price_predictor)) -> PriceService:
    return PriceService(predictor)


@router.post("/predict", response_model=PriceResponseV2)
async def predict_price_v2(
    request: PriceRequestV2,
    service: PriceService = Depends(get_price_service),
):
    try:
        payload = request.model_dump() if hasattr(request, "model_dump") else request.dict()
        prediction = service.predict(payload)
        return PriceResponseV2(
            predicted_price=prediction["predicted_price"],
            price_range=prediction["price_range"],
            confidence=prediction["confidence"],
            factors=prediction["factors"],
            comparables=prediction.get("comparables", []),
            market_trend=prediction.get("market_trend", ""),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/market-analysis/{location}")
async def market_analysis_v2(
    location: str,
    service: PriceService = Depends(get_price_service),
):
    try:
        return service.market_analysis(location)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
