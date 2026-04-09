import pathlib
import sys

import httpx


BACKEND_DIR = pathlib.Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import main


def test_fastapi_app_imports_cleanly():
    assert main.app is not None


def test_health_endpoint_returns_ok():
    transport = httpx.ASGITransport(app=main.app)

    async def _exercise():
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/health")
            assert response.status_code == 200
            payload = response.json()
            assert payload.get("status") == "healthy"

    import asyncio

    asyncio.run(_exercise())
