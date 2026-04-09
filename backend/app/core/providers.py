from functools import lru_cache

from models.price_predictor import PricePredictor


@lru_cache(maxsize=1)
def get_price_predictor() -> PricePredictor:
    """Lazy singleton provider for price predictor.

    This avoids eager model loading at module import time for v2 routes.
    """
    return PricePredictor()
