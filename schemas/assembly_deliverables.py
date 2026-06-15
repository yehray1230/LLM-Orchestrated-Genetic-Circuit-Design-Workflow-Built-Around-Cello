from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class PrimerWarning:
    code: str
    message: str
    severity: str = "warning"


@dataclass
class Primer:
    primer_id: str
    name: str
    direction: str
    sequence: str
    annealing_sequence: str
    adapter_sequence: str
    length: int
    annealing_length: int
    tm: float
    gc_percent: float
    hairpin_tm: float | None = None
    homodimer_tm: float | None = None
    warnings: list[PrimerWarning] = field(default_factory=list)


@dataclass
class FragmentPrimerSet:
    fragment_id: str
    fragment_name: str
    source_type: str
    preparation: str
    template_length: int
    product_length: int
    forward_primer: Primer | None = None
    reverse_primer: Primer | None = None
    heterodimer_tm: float | None = None
    warnings: list[PrimerWarning] = field(default_factory=list)


@dataclass
class PrimerDesignResult:
    status: str
    fragment_primer_sets: list[FragmentPrimerSet]
    warnings: list[PrimerWarning] = field(default_factory=list)
    tool_versions: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

