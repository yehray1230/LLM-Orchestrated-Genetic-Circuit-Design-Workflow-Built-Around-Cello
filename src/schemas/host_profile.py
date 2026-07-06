from __future__ import annotations

from copy import deepcopy
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

    # Biophysical parameters for Phase 2 modeling
    rnap_total: float | None = None
    ribosome_total: float | None = None
    transcription_rate: float | None = None
    translation_rate: float | None = None
    mrna_degradation_rate: float | None = None
    protein_degradation_rate: float | None = None
    growth_rate_dilution: float | None = None
    km_rnap: float | None = None
    km_ribosome: float | None = None
    burden_soft_limit: float | None = None
    toxicity_threshold: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def host_profile_from_dict(payload: dict[str, Any]) -> HostProfile:
    def _float_or_none(key: str) -> float | None:
        val = payload.get(key)
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

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
        rnap_total=_float_or_none("rnap_total"),
        ribosome_total=_float_or_none("ribosome_total"),
        transcription_rate=_float_or_none("transcription_rate"),
        translation_rate=_float_or_none("translation_rate"),
        mrna_degradation_rate=_float_or_none("mrna_degradation_rate"),
        protein_degradation_rate=_float_or_none("protein_degradation_rate"),
        growth_rate_dilution=_float_or_none("growth_rate_dilution"),
        km_rnap=_float_or_none("km_rnap"),
        km_ribosome=_float_or_none("km_ribosome"),
        burden_soft_limit=_float_or_none("burden_soft_limit"),
        toxicity_threshold=_float_or_none("toxicity_threshold"),
    )


def default_ecoli_profile() -> HostProfile:
    return HostProfile(
        profile_id="ecoli_k12_default",
        name="E. coli K-12 default biophysical profile",
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
        rare_codon_threshold=0.10,
        evidence_level="defaulted",
        source="built_in_ecoli_k12_reference_profile",
        metadata={
            "intended_use": (
                "Computational biophysical and codon-optimization baseline."
            )
        },
        rnap_total=5000.0,
        ribosome_total=25000.0,
        transcription_rate=0.08,
        translation_rate=0.045,
        mrna_degradation_rate=0.0038,
        protein_degradation_rate=0.00058,
        growth_rate_dilution=0.0004,
        km_rnap=75.0,
        km_ribosome=120.0,
        burden_soft_limit=45000.0,
        toxicity_threshold=65000.0,
    )


def default_yeast_profile() -> HostProfile:
    return HostProfile(
        profile_id="yeast_sc_default",
        name="S. cerevisiae default biophysical profile",
        host_organism="Saccharomyces cerevisiae",
        strain="S288C",
        codon_usage={},
        forbidden_motifs=[],
        rare_codon_threshold=0.10,
        evidence_level="defaulted",
        source="built_in_yeast_reference_profile",
        metadata={
            "intended_use": (
                "Eukaryotic yeast expression biophysical modeling baseline."
            )
        },
        rnap_total=3000.0,
        ribosome_total=120000.0,
        transcription_rate=0.05,
        translation_rate=0.012,
        mrna_degradation_rate=0.0012,
        protein_degradation_rate=0.0001,
        growth_rate_dilution=0.0001,
        km_rnap=50.0,
        km_ribosome=150.0,
        burden_soft_limit=200000.0,
        toxicity_threshold=300000.0,
    )


def default_mammalian_profile() -> HostProfile:
    return HostProfile(
        profile_id="mammalian_cho_default",
        name="Mammalian CHO default biophysical profile",
        host_organism="Homo sapiens",
        strain="CHO",
        codon_usage={},
        forbidden_motifs=[],
        rare_codon_threshold=0.10,
        evidence_level="defaulted",
        source="built_in_mammalian_reference_profile",
        metadata={
            "intended_use": (
                "Mammalian host expression biophysical modeling baseline."
            )
        },
        rnap_total=1500.0,
        ribosome_total=500000.0,
        transcription_rate=0.03,
        translation_rate=0.008,
        mrna_degradation_rate=0.0002,
        protein_degradation_rate=0.00005,
        growth_rate_dilution=0.00001,
        km_rnap=40.0,
        km_ribosome=200.0,
        burden_soft_limit=800000.0,
        toxicity_threshold=1200000.0,
    )


def apply_host_profile_to_topology(
    topology: dict[str, Any],
    host_profile: HostProfile,
) -> dict[str, Any]:
    topology = deepcopy(topology)
    biokinetic = topology.setdefault("biokinetic_parameters", {})
    biokinetic["host"] = host_profile.host_organism

    parameters = biokinetic.setdefault("parameters", {})
    if not parameters:
        from agents.data_miner_agent import DEFAULT_BIOKINETIC_PARAMETERS
        parameters.update(deepcopy(DEFAULT_BIOKINETIC_PARAMETERS))

    host_fields = {
        "rnap_total": host_profile.rnap_total,
        "ribosome_total": host_profile.ribosome_total,
        "transcription_rate": host_profile.transcription_rate,
        "translation_rate": host_profile.translation_rate,
        "mrna_degradation_rate": host_profile.mrna_degradation_rate,
        "protein_degradation_rate": host_profile.protein_degradation_rate,
        "growth_rate_dilution": host_profile.growth_rate_dilution,
        "km_rnap": host_profile.km_rnap,
        "km_ribosome": host_profile.km_ribosome,
        "burden_soft_limit": host_profile.burden_soft_limit,
        "toxicity_threshold": host_profile.toxicity_threshold,
    }

    from schemas.parameter_governance import (
        normalize_parameter_metadata,
        summarize_parameter_governance,
    )

    default_origin = "inferred" if host_profile.source == "local_user" else "default"
    data_boundary = "local_private" if host_profile.source == "local_user" else "public"
    confidence = 0.85 if host_profile.evidence_level == "experimental" else 0.65
    context = {
        "host_profile_id": host_profile.profile_id,
        "host": host_profile.host_organism,
        "source": host_profile.source,
        "source_version": host_profile.version,
        "context_scope": "host_profile_application",
    }

    for key, val in host_fields.items():
        if val is not None:
            parameters[key] = normalize_parameter_metadata(
                {
                    **dict(parameters.get(key) or {}),
                    "value": float(val),
                    "source": f"host_profile:{host_profile.profile_id}",
                    "confidence": confidence,
                    "parameter_origin": default_origin,
                    "confidence_category": default_origin,
                    "measurement_context": context,
                    "data_boundary": data_boundary,
                    "is_override": True,
                },
                default_origin=default_origin,
                default_context=context,
                is_override=True,
            )
    gov = summarize_parameter_governance(parameters)
    mining = biokinetic.setdefault("mining_summary", {})
    mining.update(gov)

    if host_profile.source == "local_user":
        local_count = sum(
            1 for p in parameters.values() if p.get("data_boundary") == "local_private"
        )
        mining["local_private_parameter_count"] = local_count

    return topology
