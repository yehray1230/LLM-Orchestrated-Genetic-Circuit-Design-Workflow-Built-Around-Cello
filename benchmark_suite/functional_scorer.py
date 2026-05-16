from __future__ import annotations

from benchmark_suite.base_evaluator import EvaluationResult


def score_functional(candidate: dict) -> EvaluationResult:
    score = float(candidate.get("functional_score", candidate.get("score", 0.0)))
    return EvaluationResult(score=score, details={"metric": "functional"})
