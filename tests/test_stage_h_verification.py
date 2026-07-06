"""Stage H verification tests.

Verifies that the Streamlit interface is correctly marked as legacy / in maintenance-only mode
in both the application code and documentation.
"""
from __future__ import annotations

from pathlib import Path


def test_app_py_has_deprecation_warning():
    """Verify that app.py contains the st.warning banner about maintenance mode."""
    app_path = Path("app.py")
    assert app_path.exists(), "app.py should exist"
    
    content = app_path.read_text(encoding="utf-8")
    assert "st.warning(" in content
    assert "維護模式" in content
    assert "Legacy / Maintenance-only" in content
    assert "http://127.0.0.1:8000/web" in content


def test_documentation_references_are_updated():
    """Verify that documentation files reference Streamlit as legacy/maintenance-only and HTML as primary."""
    doc_checks = {
        "README.md": [
            "FastAPI/OpenAPI, server-rendered research workspace, MCP tools, and legacy Streamlit interface (maintenance-only)",
            "Legacy Streamlit interface (maintenance-only)"
        ],
        "QUICKSTART.md": [
            "FastAPI / Web Workspace (預設主介面 / Default Interface)",
            "Streamlit Research UI (Legacy / Maintenance-only)",
            "This interface has entered maintenance-only mode"
        ],
        "DEMO_CHECKLIST.md": [
            "FastAPI / Web Workspace (Primary)",
            "Streamlit Research UI (Legacy / Maintenance-only)",
            "This interface has entered maintenance-only mode"
        ],
        "ARCHITECTURE.md": [
            "The server-rendered HTML interface (FastAPI `/web` workspace) is the default user interface, while the legacy Streamlit interface in [app.py](app.py) remains for maintenance-only backup",
            "Legacy Streamlit UI (maintenance-only)"
        ],
        "README_FOR_AI.md": [
            "FastAPI server-rendered web, MCP, and legacy Streamlit entry points",
            "Legacy Streamlit demo interface (maintenance-only)"
        ],
        "WORKFLOW.md": [
            "Run the FastAPI Web Workspace (Default Interface):",
            "For the legacy Streamlit UI (maintenance-only):"
        ],
        "api/README.md": [
            "FastAPI serves both the versioned JSON API and the server-rendered HTML workspace (default interface)",
            "The legacy Streamlit application (app.py) is kept in maintenance-only mode"
        ]
    }

    for filename, expected_substrings in doc_checks.items():
        filepath = Path(filename)
        assert filepath.exists(), f"{filename} should exist"
        content = filepath.read_text(encoding="utf-8")
        for substring in expected_substrings:
            assert substring in content, f"'{substring}' should be present in {filename}"
