"""Test for global View Mode Toggle (General vs Advanced mode).
"""
from __future__ import annotations

from pathlib import Path


def _get_path(rel_path: str) -> Path:
    root = Path(__file__).resolve().parent.parent
    p = root / "src" / rel_path
    if p.exists():
        return p
    return root / rel_path


def test_toggle_ui_in_base_html():
    base_html = _get_path("web/templates/base.html")
    assert base_html.exists()
    content = base_html.read_text(encoding="utf-8")
    assert 'id="global-mode-toggle"' in content
    assert 'class="switch-toggle"' in content
    assert "進階模式" in content


def test_styles_in_app_css():
    app_css = _get_path("web/static/app.css")
    assert app_css.exists()
    content = app_css.read_text(encoding="utf-8")
    assert ".advanced-only" in content
    assert "body.view-mode-advanced" in content
    assert ".switch-toggle" in content


def test_js_controller_in_app_js():
    app_js = _get_path("web/static/app.js")
    assert app_js.exists()
    content = app_js.read_text(encoding="utf-8")
    assert "global-mode-toggle" in content
    assert "view_mode" in content
    assert "view-mode-advanced" in content


def test_templates_annotated_with_advanced_only():
    compare_html = _get_path("web/templates/compare.html")
    assert compare_html.exists()
    assert 'class="advanced-only"' in compare_html.read_text(encoding="utf-8")

    run_detail_html = _get_path("web/templates/run_detail.html")
    assert run_detail_html.exists()
    assert 'class="section-space advanced-only"' in run_detail_html.read_text(encoding="utf-8")

    history_html = _get_path("web/templates/run_decision_history.html")
    assert history_html.exists()
    assert 'class="card advanced-only"' in history_html.read_text(encoding="utf-8")
