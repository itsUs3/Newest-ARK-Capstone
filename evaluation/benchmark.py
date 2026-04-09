import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

import requests

from metrics import success_rate, summarize_latencies


def run_price_benchmark(base_url: str, queries: List[Dict]) -> Dict:
    endpoint = f"{base_url.rstrip('/')}/api/v2/price/predict"
    latencies_ms: List[float] = []
    success_flags: List[bool] = []
    failures: List[Dict] = []

    for idx, payload in enumerate(queries, start=1):
        start = time.perf_counter()
        ok = False
        error = ""
        status_code = None
        try:
            response = requests.post(endpoint, json=payload, timeout=90)
            status_code = response.status_code
            ok = response.ok
            if not ok:
                error = response.text[:300]
        except Exception as exc:
            error = str(exc)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies_ms.append(elapsed_ms)
            success_flags.append(ok)
            if not ok:
                failures.append(
                    {
                        "index": idx,
                        "status_code": status_code,
                        "error": error,
                    }
                )

    return {
        "target_endpoint": endpoint,
        "total_requests": len(queries),
        "latency": summarize_latencies(latencies_ms),
        "success_rate_percent": success_rate(success_flags),
        "failures": failures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark v2 price prediction endpoint")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument(
        "--queries",
        default=str(Path(__file__).with_name("test_queries.json")),
        help="Path to JSON query payload list",
    )
    parser.add_argument(
        "--out",
        default=str(Path(__file__).with_name("benchmark_report.json")),
        help="Output report JSON path",
    )
    args = parser.parse_args()

    queries_path = Path(args.queries)
    queries = json.loads(queries_path.read_text(encoding="utf-8"))

    result = run_price_benchmark(args.base_url, queries)

    out_path = Path(args.out)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"\nReport written to: {out_path}")


if __name__ == "__main__":
    main()
