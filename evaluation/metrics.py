from statistics import mean
from typing import Dict, List


def summarize_latencies(latencies_ms: List[float]) -> Dict[str, float]:
    if not latencies_ms:
        return {
            "count": 0,
            "mean_ms": 0.0,
            "p50_ms": 0.0,
            "p95_ms": 0.0,
            "max_ms": 0.0,
        }

    sorted_vals = sorted(latencies_ms)
    count = len(sorted_vals)

    def _percentile(p: float) -> float:
        if count == 1:
            return sorted_vals[0]
        idx = int(round((count - 1) * p))
        idx = max(0, min(count - 1, idx))
        return sorted_vals[idx]

    return {
        "count": count,
        "mean_ms": round(mean(sorted_vals), 2),
        "p50_ms": round(_percentile(0.50), 2),
        "p95_ms": round(_percentile(0.95), 2),
        "max_ms": round(sorted_vals[-1], 2),
    }


def success_rate(success_flags: List[bool]) -> float:
    if not success_flags:
        return 0.0
    return round((sum(1 for ok in success_flags if ok) / len(success_flags)) * 100.0, 2)
