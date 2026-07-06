from __future__ import annotations

import re


IUPAC_DNA_PATTERN = re.compile(r"^[ACGTRYSWKMBDHVN]+$", re.IGNORECASE)


def normalize_dna(sequence: str | None) -> str | None:
    if sequence is None:
        return None
    normalized = "".join(str(sequence).split()).upper()
    return normalized or None


def is_valid_iupac_dna(sequence: str | None) -> bool:
    normalized = normalize_dna(sequence)
    return bool(normalized and IUPAC_DNA_PATTERN.fullmatch(normalized))
