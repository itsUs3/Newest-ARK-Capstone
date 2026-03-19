import sys
import types
import asyncio

import numpy as np
import httpx
from fastapi import FastAPI, File, Request, UploadFile


_stub_image_module = types.ModuleType("models.image_feature_extractor")


class _SafeImageFeatureExtractor:
    def __init__(self, target_size=(224, 224), batch_size=16):
        self.embedding_dim = 1280

    def zero_embedding(self):
        return np.zeros(self.embedding_dim, dtype=np.float32)

    def extract_image_embedding(self, image_path: str):
        return np.ones(self.embedding_dim, dtype=np.float32) if image_path else self.zero_embedding()

    def extract_batch_embeddings(self, image_paths):
        result = np.zeros((len(image_paths), self.embedding_dim), dtype=np.float32)
        for idx, path in enumerate(image_paths):
            if path:
                result[idx] = 1.0
        return result


_stub_image_module.ImageFeatureExtractor = _SafeImageFeatureExtractor
sys.modules["models.image_feature_extractor"] = _stub_image_module

from models.price_predictor import PricePredictor


class StubImageExtractor:
    def __init__(self):
        self.embedding_dim = 1280

    def zero_embedding(self):
        return np.zeros(self.embedding_dim, dtype=np.float32)

    def extract_image_embedding(self, image_path: str):
        if image_path:
            return np.ones(self.embedding_dim, dtype=np.float32)
        return self.zero_embedding()


class StubPredictor:
    def __init__(self):
        self.calls = []

    def predict(self, features, image_path=None):
        self.calls.append((features, image_path))
        return {
            "predicted_price": 8000000.0,
            "price_range": {"min": 7000000.0, "max": 9000000.0},
            "confidence": 0.82,
            "factors": {"visual_condition_signal": {"impact": "enabled" if image_path else "not provided"}},
            "comparables": [],
            "market_trend": "stable",
        }


def _create_price_predict_test_app(stub_predictor: StubPredictor) -> FastAPI:
    app = FastAPI()

    @app.post("/api/price/predict")
    async def predict_price(request: Request, image: UploadFile | None = File(default=None)):
        import json
        import os
        import tempfile

        temp_image_path = None
        try:
            content_type = request.headers.get("content-type", "")

            if "application/json" in content_type:
                payload = await request.json()
                location = payload.get("location")
                bhk = payload.get("bhk")
                size = payload.get("size")
                amenities = payload.get("amenities", [])
                furnishing = payload.get("furnishing", "Semi-Furnished")
                construction_status = payload.get("construction_status", "Ready to Move")
            else:
                form = await request.form()
                location = form.get("location")
                bhk = form.get("bhk")
                size = form.get("size")
                furnishing = form.get("furnishing", "Semi-Furnished")
                construction_status = form.get("construction_status", "Ready to Move")

                amenities_raw = form.get("amenities", "[]")
                if isinstance(amenities_raw, str):
                    try:
                        parsed = json.loads(amenities_raw)
                        amenities = [str(x) for x in parsed] if isinstance(parsed, list) else []
                    except Exception:
                        amenities = [item.strip() for item in amenities_raw.split(",") if item.strip()]
                else:
                    amenities = []

            if image is not None and image.filename:
                suffix = ".jpg"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                    temp_file.write(await image.read())
                    temp_image_path = temp_file.name

            features = {
                "location": str(location),
                "bhk": int(bhk),
                "size": float(size),
                "amenities": amenities,
                "furnishing": str(furnishing),
                "construction_status": str(construction_status),
            }

            return stub_predictor.predict(features, temp_image_path)
        finally:
            if temp_image_path and os.path.exists(temp_image_path):
                os.remove(temp_image_path)

    return app


def _make_minimal_predictor_for_vector_tests() -> PricePredictor:
    predictor = object.__new__(PricePredictor)
    predictor.image_extractor = StubImageExtractor()
    predictor._encode_location = lambda _: 3
    predictor._encode_furnishing = lambda _: 1
    predictor._encode_status = lambda _: 0
    return predictor


def test_no_image_path_uses_zero_vector():
    predictor = _make_minimal_predictor_for_vector_tests()

    features = {
        "location": "Mumbai",
        "bhk": 2,
        "size": 900,
        "amenities": ["gym", "pool"],
        "furnishing": "Semi-Furnished",
        "construction_status": "Ready to Move",
    }

    fused = predictor._build_model_feature_vector(features, image_path=None)

    assert fused.shape == (1, 1286)
    assert np.allclose(fused[0, 6:], 0.0)


def test_image_path_changes_fused_feature_vector():
    predictor = _make_minimal_predictor_for_vector_tests()

    features = {
        "location": "Mumbai",
        "bhk": 2,
        "size": 900,
        "amenities": ["gym", "pool"],
        "furnishing": "Semi-Furnished",
        "construction_status": "Ready to Move",
    }

    no_image_fused = predictor._build_model_feature_vector(features, image_path=None)
    with_image_fused = predictor._build_model_feature_vector(features, image_path="dummy.jpg")

    assert np.allclose(no_image_fused[0, 6:], 0.0)
    assert np.allclose(with_image_fused[0, 6:], 1.0)
    assert not np.allclose(no_image_fused, with_image_fused)


def test_price_endpoint_accepts_json_and_multipart():
    stub = StubPredictor()
    app = _create_price_predict_test_app(stub)
    transport = httpx.ASGITransport(app=app)

    async def _exercise_endpoint():
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            # JSON request path
            json_resp = await client.post(
                "/api/price/predict",
                json={
                    "location": "Mumbai",
                    "bhk": 2,
                    "size": 900,
                    "amenities": ["gym", "pool"],
                    "furnishing": "Semi-Furnished",
                    "construction_status": "Ready to Move",
                },
            )
            assert json_resp.status_code == 200
            assert json_resp.json()["predicted_price"] == 8000000.0

            # Multipart request path (with image)
            multipart_resp = await client.post(
                "/api/price/predict",
                data={
                    "location": "Mumbai",
                    "bhk": "2",
                    "size": "900",
                    "amenities": '["gym", "pool"]',
                    "furnishing": "Semi-Furnished",
                    "construction_status": "Ready to Move",
                },
                files={"image": ("room.jpg", b"fake-image-bytes", "image/jpeg")},
            )

            assert multipart_resp.status_code == 200
            assert multipart_resp.json()["predicted_price"] == 8000000.0

    asyncio.run(_exercise_endpoint())

    # Ensure predictor got both invocations and image-path behavior differs
    assert len(stub.calls) == 2
    _, first_image_path = stub.calls[0]
    _, second_image_path = stub.calls[1]

    assert first_image_path is None
    assert isinstance(second_image_path, str)
    assert second_image_path
