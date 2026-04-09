import asyncio
import pathlib
import sys

import httpx


BACKEND_DIR = pathlib.Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import main


async def _call_json(client, method, url, **kwargs):
    response = await client.request(method, url, **kwargs)
    assert response.status_code == 200, response.text
    return response.json()


def test_restored_genai_routes_smoke():
    transport = httpx.ASGITransport(app=main.app)

    async def _exercise():
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver", timeout=120.0) as client:
            trending = await _call_json(client, "GET", "/api/genai/trending-locations", params={"top_n": 3})
            assert len(trending.get("trending_locations", [])) == 3

            alerts = await _call_json(client, "GET", "/api/genai/market-alerts/Mumbai", params={"n_results": 3})
            assert "articles" in alerts

            cross_modal = await _call_json(
                client,
                "POST",
                "/api/genai/cross-modal-match",
                json={
                    "query": "Family-friendly apartment near metro",
                    "lifestyle": "Family with Kids",
                    "top_k": 3,
                    "use_cross_modal": True,
                },
            )
            assert "matches" in cross_modal
            assert len(cross_modal.get("matches", [])) <= 3

            contract = await _call_json(
                client,
                "POST",
                "/api/genai/contract-analyze",
                json={
                    "contract_type": "lease",
                    "contract_text": (
                        "The lessee shall pay rent monthly, the premises shall be used only for residential "
                        "purposes, notice for termination shall be thirty days, and any defects reported by "
                        "the tenant shall be rectified by the owner within a reasonable period."
                    ),
                },
            )
            assert contract.get("success") is True
            assert "compliance_score" in contract

    asyncio.run(_exercise())
