from __future__ import annotations

from benchmark_suite.functional_scorer import score_functional
from benchmark_suite.kinetic_scorer import score_kinetic
from benchmark_suite.static_plausibility_evaluator import score_static_plausibility


def evaluate_candidate(candidate: dict) -> dict:
    results = [
        score_functional(candidate),
        score_kinetic(candidate),
        score_static_plausibility(candidate),
    ]
    score = sum(result.score for result in results) / len(results)
    return {"score": score, "details": [result.details for result in results]}
