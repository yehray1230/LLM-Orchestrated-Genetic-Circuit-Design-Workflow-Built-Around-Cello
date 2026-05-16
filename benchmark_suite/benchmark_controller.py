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
    score = 1.0
    for result in results:
        score *= max(0.0, min(1.0, float(result.score)))
    return {
        "score": score,
        "grade": _grade(score),
        "details": [result.details | {"score": result.score} for result in results],
        "scoring_model": "multiplicative_penalty",
    }


def _grade(score: float) -> str:
    scaled = score * 100.0
    if scaled >= 80.0:
        return "Excellent"
    if scaled >= 60.0:
        return "Pass"
    return "Fail"
