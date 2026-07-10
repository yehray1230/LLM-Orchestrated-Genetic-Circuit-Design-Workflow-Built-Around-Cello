"""Stage G verification tests.

Covers:
- Pin / unpin, archive / unarchive, soft-delete / restore, and purge.
- Global search and filtering in designs.
- Deletion impact preview and deliverable cleanup.
- i18n translation key mapping in template helper.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_services
from api.main import app
from application.services import create_application_services
from schemas.design_ir_v2 import (
    BiologicalPartV2,
    DesignIRV2,
    DesignSpecification,
    BiologicalContext,
    AttributedValue,
)


@pytest.fixture
def test_services(tmp_path: Path):
    return create_application_services(tmp_path / "api_data")


@pytest.fixture
def client(test_services):
    app.dependency_overrides[get_services] = lambda: test_services
    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


def _sample_design(design_id: str, host: str = "Escherichia coli") -> DesignIRV2:
    return DesignIRV2(
        design_id=design_id,
        name=f"Design {design_id}",
        specification=DesignSpecification(
            inputs=["iptg"],
            outputs=["YFP"],
        ),
        parts=[
            BiologicalPartV2(
                id="p_lac",
                name="pLac",
                part_type="promoter",
                role="sensor",
                sequence="TACC",
                evidence_level="experimentally_characterized",
            )
        ],
        interactions=[],
        constructs=[],
        biological_context=BiologicalContext(
            host_organism=AttributedValue(value=host)
        ),
    )


def test_sqlite_repository_stage_g_actions(test_services):
    """Test repository level pin, archive, soft-delete, restore, and purge."""
    design_id = "g_repo_test"
    design = _sample_design(design_id)
    test_services.designs.save_v2(design)

    # Initially all false
    loaded = test_services.designs.get_v2(design_id)
    assert loaded is not None
    assert not loaded.is_pinned
    assert not loaded.is_archived
    assert not loaded.is_deleted

    # 1. Test Pin
    test_services.designs.pin(design_id)
    loaded = test_services.designs.get_v2(design_id)
    assert loaded.is_pinned

    # 2. Test Unpin
    test_services.designs.unpin(design_id)
    loaded = test_services.designs.get_v2(design_id)
    assert not loaded.is_pinned

    # 3. Test Archive
    test_services.designs.archive(design_id)
    loaded = test_services.designs.get_v2(design_id)
    assert loaded.is_archived

    # 4. Test Unarchive
    test_services.designs.unarchive(design_id)
    loaded = test_services.designs.get_v2(design_id)
    assert not loaded.is_archived

    # 5. Test Soft Delete
    test_services.designs.soft_delete(design_id)
    loaded = test_services.designs.get_v2(design_id)
    assert loaded.is_deleted

    # 6. Test Restore
    test_services.designs.restore(design_id)
    loaded = test_services.designs.get_v2(design_id)
    assert not loaded.is_deleted

    # 7. Test Purge
    purged = test_services.designs.purge(design_id)
    assert purged
    assert test_services.designs.get_v2(design_id) is None


def test_search_and_filtering(client, test_services):
    """Test search, filtering by host, status, archived, and deleted."""
    d1 = _sample_design("search_1", host="Escherichia coli")
    d2 = _sample_design("search_2", host="Bacillus subtilis")
    test_services.designs.save_v2(d1)
    test_services.designs.save_v2(d2)

    # Default listing (no archived, no deleted)
    response = client.get("/web/designs")
    assert response.status_code == 200
    assert "search_1" in response.text
    assert "search_2" in response.text

    # Search by text
    response = client.get("/web/designs?q=search_1")
    assert response.status_code == 200
    assert "search_1" in response.text
    assert "search_2" not in response.text

    # Filter by host
    response = client.get("/web/designs?host=Bacillus")
    assert response.status_code == 200
    assert "search_2" in response.text
    assert "search_1" not in response.text


def test_i18n_translation_keys(client, test_services):
    """Test language switcher cookie and Jinja translation helper."""
    # Request English
    response = client.get("/web/designs?lang=en")
    assert response.status_code == 200
    assert "lang" in response.cookies
    assert response.cookies["lang"] == "en"

    # Verify translated texts are shown in English
    assert "Design Library" in response.text

    # Request Chinese (or default)
    response = client.get("/web/designs?lang=zh-Hant")
    assert response.status_code == 200
    assert response.cookies["lang"] == "zh-Hant"
    assert "設計資料庫" in response.text


@pytest.mark.parametrize(
    ("path", "expected", "forbidden"),
    [
        ("/web", "Research Dashboard", ["研究工作台", "快速開始"]),
        ("/web/new-design", "Create a New Design", ["建立新設計", "自然語言設計需求"]),
        ("/web/settings", "Key and Model Settings", ["金鑰與模型設定", "儲存設定"]),
    ],
)
def test_p0_english_pages_do_not_render_known_chinese_copy(
    client,
    path: str,
    expected: str,
    forbidden: list[str],
):
    response = client.get(f"{path}?lang=en")

    assert response.status_code == 200
    assert expected in response.text
    assert "New Design" in response.text
    assert "Advanced mode" in response.text
    for text in forbidden:
        assert text not in response.text


def test_p0_localization_sources_require_explicit_bilingual_pairs():
    repository_root = Path(__file__).parents[1]
    template_paths = [
        repository_root / "src/web/templates/base.html",
        repository_root / "src/web/templates/dashboard.html",
        repository_root / "src/web/templates/new_design.html",
        repository_root / "src/web/templates/settings.html",
        repository_root / "src/web/templates/research.html",
        repository_root / "src/web/templates/research_compare.html",
        repository_root / "src/web/templates/research_run.html",
        repository_root / "src/web/templates/assembly.html",
        repository_root / "src/web/templates/assembly_backbones.html",
        repository_root / "src/web/templates/assembly_new.html",
        repository_root / "src/web/templates/assembly_report.html",
        repository_root / "src/web/templates/assembly_downloads.html",
        repository_root / "src/web/templates/candidates.html",
        repository_root / "src/web/templates/benchmarks.html",
        repository_root / "src/web/templates/benchmark_detail.html",
    ]
    untranslated_template_lines: list[str] = []
    for path in template_paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not re.search(r"[\u3400-\u9fff\uf900-\ufaff]", line):
                continue
            if "_tr(" in line or "中文</a>" in line or "<!--" in line:
                continue
            untranslated_template_lines.append(f"{path.name}:{line_number}: {line.strip()}")

    app_js = repository_root / "src/web/static/app.js"
    untranslated_js_lines = [
        f"app.js:{line_number}: {line.strip()}"
        for line_number, line in enumerate(app_js.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"[\u3400-\u9fff\uf900-\ufaff]", line) and "uiText(" not in line
    ]

    assert untranslated_template_lines == []
    assert untranslated_js_lines == []


@pytest.mark.parametrize(
    ("path", "zh_expected", "en_expected"),
    [
        ("/web/research", "研究工作區", "Research Workspace"),
        ("/web/research/compare", "比較研究執行", "Compare Research Runs"),
        ("/web/assembly", "裝配交付中心", "Assembly Delivery"),
        ("/web/assembly/backbones", "骨架註冊庫", "Backbone Registry"),
        ("/web/assembly/new", "新裝配交付物", "New Assembly Deliverable"),
    ],
)
def test_research_and_assembly_landing_pages_follow_language(
    client,
    path: str,
    zh_expected: str,
    en_expected: str,
):
    zh_response = client.get(f"{path}?lang=zh-Hant")
    en_response = client.get(f"{path}?lang=en")

    assert zh_response.status_code == en_response.status_code == 200
    assert zh_expected in zh_response.text
    assert en_expected not in zh_response.text
    assert en_expected in en_response.text
    assert zh_expected not in en_response.text


def test_deletion_impact_preview_and_purge_cleanup(client, test_services):
    """Test that delete preview correctly queries resources and purge cleans up on-disk deliverables."""
    design_id = "purge_cleanup_test"
    design = _sample_design(design_id)
    test_services.designs.save_v2(design)

    # 1. Create a dummy deliverable linked to this design
    deliverable_id = "deliv_purge_test"
    deliv_dir = test_services.assembly_deliverables.output_dir / deliverable_id
    deliv_dir.mkdir(parents=True, exist_ok=True)
    test_file = deliv_dir / "assembly_map.gb"
    test_file.write_text("DUMMY_GENBANK_CONTENT", encoding="utf-8")

    test_services.assembly_deliverables.repository.save(deliverable_id, {
        "deliverable_id": deliverable_id,
        "source_context": {
            "design_id": design_id,
            "revision_number": 1,
            "revision_id": f"{design_id}_revision_1",
        }
    })

    # 2. Verify delete preview loads
    response = client.get(f"/web/designs/{design_id}/delete_preview")
    assert response.status_code == 200
    assert "受影響資料類別" in response.text
    assert "裝配與交付下載" in response.text

    # 3. Purge the design
    response = client.post(
        f"/web/designs/{design_id}/purge",
        data={"understand": "true", "confirm_design_id": design_id},
        follow_redirects=False,
    )
    assert response.status_code == 303  # Redirect to /web/designs

    # Verify design is purged
    assert test_services.designs.get_v2(design_id) is None

    # Verify deliverable record is deleted
    assert test_services.assembly_deliverables.get(deliverable_id) is None

    # Verify on-disk files are purged
    assert not deliv_dir.exists()


def test_purge_requires_server_side_confirmation(client, test_services):
    design_id = "purge_guard_test"
    test_services.designs.save_v2(_sample_design(design_id))

    missing = client.post(
        f"/web/designs/{design_id}/purge",
        follow_redirects=False,
    )
    assert missing.status_code == 422
    assert test_services.designs.get_v2(design_id) is not None

    mismatch = client.post(
        f"/web/designs/{design_id}/purge",
        data={"understand": "true", "confirm_design_id": "different_design"},
        follow_redirects=False,
    )
    assert mismatch.status_code == 403
    assert test_services.designs.get_v2(design_id) is not None


def test_delete_preview_counts_only_runs_for_design(client, test_services, monkeypatch):
    design_id = "run_scope_test"
    test_services.designs.save_v2(_sample_design(design_id))
    monkeypatch.setattr(
        test_services.research,
        "list",
        lambda limit=100: {
            "runs": [
                {"run_id": "research_match", "request": {"design_id": design_id}},
                {"run_id": "research_other", "request": {"design_id": "other"}},
                {"run_id": "research_unbound", "summary": {}},
            ]
        },
    )

    response = client.get(f"/web/designs/{design_id}/delete_preview")
    assert response.status_code == 200
    assert "1 個執行過的模擬或分析" in response.text


def test_pagination_status_filter_and_language_are_stable(client, test_services):
    for index in range(12):
        test_services.designs.save_v2(_sample_design(f"page_design_{index:02d}"))

    first_page = client.get("/web/designs?page=1&lang=zh-Hant")
    second_page = client.get("/web/designs?page=2&lang=zh-Hant")
    assert first_page.status_code == second_page.status_code == 200
    assert "1 / 2" in first_page.text
    assert "2 / 2" in second_page.text

    from benchmark_suite.readiness_evaluator import evaluate_readiness

    saved = test_services.designs.get_v2("page_design_00")
    assert saved is not None
    status = evaluate_readiness(saved).readiness_status
    zh = client.get(
        f"/web/designs?q=page_design_00&status={status}&lang=zh-Hant"
    )
    en = client.get(f"/web/designs?q=page_design_00&status={status}&lang=en")
    assert "page_design_00" in zh.text
    assert "page_design_00" in en.text
    assert '<html lang="zh-Hant">' in zh.text
    assert '<html lang="en">' in en.text


def test_keyboard_landmarks_are_present(client):
    response = client.get("/web/designs")
    assert response.status_code == 200
    assert 'class="skip-link" href="#main-content"' in response.text
    assert 'id="main-content" tabindex="-1"' in response.text
