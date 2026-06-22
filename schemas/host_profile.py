from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


HOST_PROFILE_SCHEMA_VERSION = "1.0.0"


@dataclass
class HostProfile:
    profile_id: str
    name: str
    host_organism: str
    strain: str = ""
    codon_usage: dict[str, dict[str, float]] = field(default_factory=dict)
    forbidden_motifs: list[str] = field(default_factory=list)
    rare_codon_threshold: float = 0.10
    evidence_level: str = "defaulted"
    source: str = "built_in_default"
    version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = HOST_PROFILE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def host_profile_from_dict(payload: dict[str, Any]) -> HostProfile:
    return HostProfile(
        profile_id=str(payload.get("profile_id") or ""),
        name=str(payload.get("name") or ""),
        host_organism=str(payload.get("host_organism") or ""),
        strain=str(payload.get("strain") or ""),
        codon_usage={
            str(amino_acid): {
                str(codon).upper(): float(weight)
                for codon, weight in dict(codons).items()
            }
            for amino_acid, codons in dict(payload.get("codon_usage") or {}).items()
        },
        forbidden_motifs=[
            str(item).upper()
            for item in list(payload.get("forbidden_motifs") or [])
        ],
        rare_codon_threshold=float(payload.get("rare_codon_threshold") or 0.10),
        evidence_level=str(payload.get("evidence_level") or "defaulted"),
        source=str(payload.get("source") or "built_in_default"),
        version=str(payload.get("version") or "1.0.0"),
        metadata=dict(payload.get("metadata") or {}),
        schema_version=str(
            payload.get("schema_version") or HOST_PROFILE_SCHEMA_VERSION
        ),
    )


def default_ecoli_profile() -> HostProfile:
    return HostProfile(
        profile_id="ecoli_k12_default",
        name="E. coli K-12 default codon profile",
        host_organism="Escherichia coli",
        strain="K-12",
        codon_usage={
            "A": {"GCT": 0.18, "GCC": 0.26, "GCA": 0.23, "GCG": 0.33},
            "C": {"TGT": 0.45, "TGC": 0.55},
            "D": {"GAT": 0.63, "GAC": 0.37},
            "E": {"GAA": 0.68, "GAG": 0.32},
            "F": {"TTT": 0.58, "TTC": 0.42},
            "G": {"GGT": 0.35, "GGC": 0.37, "GGA": 0.13, "GGG": 0.15},
            "H": {"CAT": 0.57, "CAC": 0.43},
            "I": {"ATT": 0.49, "ATC": 0.39, "ATA": 0.12},
            "K": {"AAA": 0.74, "AAG": 0.26},
            "L": {
                "TTA": 0.13,
                "TTG": 0.13,
                "CTT": 0.10,
                "CTC": 0.10,
                "CTA": 0.04,
                "CTG": 0.50,
            },
            "M": {"ATG": 1.0},
            "N": {"AAT": 0.49, "AAC": 0.51},
            "P": {"CCT": 0.17, "CCC": 0.13, "CCA": 0.20, "CCG": 0.50},
            "Q": {"CAA": 0.34, "CAG": 0.66},
            "R": {
                "CGT": 0.36,
                "CGC": 0.36,
                "CGA": 0.07,
                "CGG": 0.11,
                "AGA": 0.07,
                "AGG": 0.04,
            },
            "S": {
                "TCT": 0.17,
                "TCC": 0.15,
                "TCA": 0.14,
                "TCG": 0.14,
                "AGT": 0.16,
                "AGC": 0.25,
            },
            "T": {"ACT": 0.19, "ACC": 0.40, "ACA": 0.17, "ACG": 0.25},
            "V": {"GTT": 0.28, "GTC": 0.20, "GTA": 0.17, "GTG": 0.35},
            "W": {"TGG": 1.0},
            "Y": {"TAT": 0.59, "TAC": 0.41},
            "*": {"TAA": 0.61, "TAG": 0.09, "TGA": 0.30},
        },
        forbidden_motifs=[
            "GGTCTC",
            "GAGACC",
            "CGTCTC",
            "GAGACG",
        ],
        evidence_level="defaulted",
        source="built_in_ecoli_k12_reference_profile",
        metadata={
            "intended_use": (
                "Computational codon-optimization baseline, not calibrated "
                "expression prediction."
            )
        },
    )
