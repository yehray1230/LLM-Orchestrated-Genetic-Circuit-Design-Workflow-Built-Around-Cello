from __future__ import annotations

from schemas.parameter_governance import (
    normalize_parameter_metadata,
    summarize_parameter_governance,
)


def test_parameter_governance_normalizes_default_records() -> None:
    record = normalize_parameter_metadata(
        {
            "value": 50,
            "unit": "nM",
            "source": "conservative_default",
            "confidence": 0.45,
        },
        default_context={"host": "Escherichia coli"},
    )

    assert record["parameter_origin"] == "default"
    assert record["confidence_category"] == "default"
    assert record["data_boundary"] == "public"
    assert record["measurement_context"]["host"] == "Escherichia coli"


def test_parameter_governance_marks_local_overrides() -> None:
    record = normalize_parameter_metadata(
        {
            "value": 75,
            "unit": "nM",
            "source": "local_fit_snapshot",
            "confidence": 0.7,
        },
        default_origin="inferred",
        is_override=True,
    )

    assert record["parameter_origin"] == "inferred"
    assert record["data_boundary"] == "local_private"
    assert record["is_override"] is True
    assert record["override_policy"] == "do_not_replace_defaults_silently"


def test_parameter_governance_summary_counts_origins_and_boundaries() -> None:
    summary = summarize_parameter_governance(
        {
            "kd": normalize_parameter_metadata(
                {"source": "local_fit_snapshot", "confidence": 0.7},
                default_origin="inferred",
                is_override=True,
            ),
            "hill": normalize_parameter_metadata(
                {"source": "conservative_default", "confidence": 0.45},
                default_origin="default",
            ),
        }
    )

    assert summary["origin_summary"]["inferred"] == 1
    assert summary["origin_summary"]["default"] == 1
    assert summary["local_private_parameter_count"] == 1
    assert summary["override_count"] == 1
    assert summary["all_parameters_have_origin"] is True
