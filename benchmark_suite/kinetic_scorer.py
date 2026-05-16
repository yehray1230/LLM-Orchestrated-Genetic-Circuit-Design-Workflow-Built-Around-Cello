from __future__ import annotations

from benchmark_suite.base_evaluator import EvaluationResult


def score_kinetic(candidate: dict) -> EvaluationResult:
    score = float(candidate.get("kinetic_score", candidate.get("score", 0.0)))
    return EvaluationResult(score=score, details={"metric": "kinetic"})
