#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
from pathlib import Path

# Whitelist of standard modules allowed before sys.path patch
ALLOWED_BEFORE_PATCH = {
    "__future__",
    "sys",
    "pathlib",
    "os",
    "json",
    "math",
    "re",
    "uuid",
    "dataclasses",
    "typing",
    "types",
}

FILES_TO_CHECK = [
    "app.py",
    "src/api/main.py",
    "tests/conftest.py",
]

def verify_file(filepath: Path) -> bool:
    if not filepath.exists():
        print(f"[ERROR] File not found: {filepath}")
        return False

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    patch_found = False
    for line_idx, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Check for the path insert patch
        if "sys.path.insert" in stripped and "Path(__file__)" in stripped:
            patch_found = True
            print(f"[OK] Found sys.path patch in {filepath.name} at line {line_idx}")
            break

        # Check for import statements before the patch
        if stripped.startswith("import ") or stripped.startswith("from "):
            # Extract first module name
            parts = stripped.split()
            if len(parts) > 1:
                module_name = parts[1].split(".")[0]
                if module_name not in ALLOWED_BEFORE_PATCH:
                    print(
                        f"[ERROR] Violation in {filepath.name} at line {line_idx}:\n"
                        f"  Non-standard import '{stripped}' occurs BEFORE sys.path override.\n"
                        f"  This will break root imports when src is not in PYTHONPATH."
                    )
                    return False

    if not patch_found:
        print(f"[ERROR] No sys.path override patch found in {filepath.name}")
        return False

    return True

def main() -> int:
    root_dir = Path(__file__).resolve().parent.parent
    success = True

    for relative_path in FILES_TO_CHECK:
        filepath = root_dir / relative_path
        if not verify_file(filepath):
            success = False

    if success:
        print("[SUCCESS] All sys.path import patches are correctly positioned!")
        return 0
    else:
        print("[FAILURE] One or more files have misplaced or missing sys.path patches.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
