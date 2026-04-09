from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PriceRequestV2(BaseModel):
    location: str
    bhk: int
    size: float
    amenities: List[str] = Field(default_factory=list)
    furnishing: Optional[str] = "Semi-Furnished"
    construction_status: Optional[str] = "Ready to Move"


class PriceResponseV2(BaseModel):
    predicted_price: float
    price_range: Dict
    confidence: float
    factors: Dict
    comparables: Optional[List[Dict]] = Field(default_factory=list)
    market_trend: Optional[str] = ""
