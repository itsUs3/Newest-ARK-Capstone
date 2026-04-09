import json
import pickle
from pathlib import Path

import numpy as np


ROOT_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT_DIR / "backend" / "models"


def audit_price_predictor():
    path = MODELS_DIR / "price_predictor_smart.pkl"
    result = {
        "name": "price_predictor",
        "kind": "regression",
        "path": str(path),
        "present": path.exists(),
        "metric_name": "test_r2_score",
        "metric_value": None,
        "passes_90_percent_bar": False,
    }

    if not path.exists():
        return result

    with open(path, "rb") as handle:
        saved = pickle.load(handle)

    metric = float(saved.get("test_r2_score", 0.0))
    result["metric_value"] = metric
    result["trained_date"] = saved.get("trained_date")
    result["passes_90_percent_bar"] = metric >= 0.90
    return result


def audit_embedding_model():
    candidate_paths = [
        MODELS_DIR / "real_estate_embeddings",
        MODELS_DIR / "backend" / "models" / "real_estate_embeddings",
    ]
    resolved_path = next((path for path in candidate_paths if path.exists()), candidate_paths[0])

    result = {
        "name": "real_estate_embeddings",
        "kind": "embedding_similarity",
        "path": str(resolved_path),
        "present": resolved_path.exists(),
        "metric_name": "domain_similarity_test_accuracy",
        "metric_value": None,
        "passes_90_percent_bar": False,
    }

    if not resolved_path.exists():
        return result

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(str(resolved_path))
    test_cases = [
        ("2BHK apartment", "2-bedroom flat", "HIGH"),
        ("Metro connectivity", "Public transport access", "HIGH"),
        ("Ready to move", "Possession available", "HIGH"),
        ("Mumbai property", "Delhi property", "LOW"),
        ("Fraud alert", "Legitimate listing", "LOW"),
    ]

    correct = 0
    evaluations = []
    for text1, text2, expected in test_cases:
        emb1 = model.encode(text1)
        emb2 = model.encode(text2)
        similarity = float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))
        passed = (expected == "HIGH" and similarity >= 0.8) or (expected == "LOW" and similarity < 0.5)
        correct += int(passed)
        evaluations.append(
            {
                "text1": text1,
                "text2": text2,
                "expected": expected,
                "similarity": round(similarity, 3),
                "passed": passed,
            }
        )

    accuracy = correct / len(test_cases)
    result["metric_value"] = accuracy
    result["passes_90_percent_bar"] = accuracy >= 0.90
    result["evaluations"] = evaluations
    return result


def audit_non_benchmarkable_engines():
    return [
        {
            "name": "fraud_detector",
            "kind": "hybrid_rule_based",
            "present": True,
            "metric_name": None,
            "metric_value": None,
            "passes_90_percent_bar": None,
            "note": "No labeled benchmark in repo; trust score is heuristic and graph-augmented.",
        },
        {
            "name": "recommendation_engine",
            "kind": "rule_based_ranking",
            "present": True,
            "metric_name": None,
            "metric_value": None,
            "passes_90_percent_bar": None,
            "note": "No offline ranking benchmark in repo.",
        },
        {
            "name": "market_news_rag",
            "kind": "retrieval_pipeline",
            "present": True,
            "metric_name": None,
            "metric_value": None,
            "passes_90_percent_bar": None,
            "note": "No retrieval benchmark set in repo.",
        },
    ]


def main():
    report = {
        "audited_models": [
            audit_price_predictor(),
            audit_embedding_model(),
            *audit_non_benchmarkable_engines(),
        ]
    }

    measured = [item for item in report["audited_models"] if item.get("metric_value") is not None]
    report["all_measured_models_above_90"] = all(item["passes_90_percent_bar"] for item in measured)

    print(json.dumps(report, indent=2))

    if not report["all_measured_models_above_90"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
