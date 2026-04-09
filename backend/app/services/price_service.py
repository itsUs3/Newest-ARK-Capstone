from typing import Dict, Optional


class PriceService:
    """Service adapter around the legacy PricePredictor class.

    Keeps behavior parity while enabling route/service/model separation.
    """

    def __init__(self, predictor):
        self._predictor = predictor

    def predict(self, features: Dict, image_path: Optional[str] = None) -> Dict:
        return self._predictor.predict(features, image_path)

    def market_analysis(self, location: str) -> Dict:
        return self._predictor.analyze_market(location)
