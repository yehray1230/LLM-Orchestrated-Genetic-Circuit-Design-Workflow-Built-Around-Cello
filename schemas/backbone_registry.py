from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from io import StringIO
import re
from typing import Any

from Bio import SeqIO

from exporters.sequence_utils import is_valid_iupac_dna, normalize_dna


TRUSTED_SOURCE_TYPES = {
    "addgene",
    "ncbi",
    "igem",
    "institutional",
    "literature",
    "manufacturer",
    "user_verified",
}
COPY_NUMBER_CLASSES = {"low", "medium", "high", "very_high", "unknown"}


@dataclass(frozen=True)
class SequenceRegion:
    region_id: str
    name: str
    start: int
    end: int
    description: str = ""

    def contains(self, start: int, end: int) -> bool:
        return self.start <= start and end <= self.end

    def overlaps(self, start: int, end: int) -> bool:
        return self.start < end and self.end > start


@dataclass(frozen=True)
class BackboneRegistryEntry:
    backbone_id: str
    version: str
    name: str
    source_type: str
    source_uri: str
    genbank: str
    sequence_checksum: str
    record_id: str
    sequence_length: int
    host_organisms: tuple[str, ...]
    origin_of_replication: str
    selection_marker: str
    copy_number_class: str
    insertion_regions: tuple[SequenceRegion, ...]
    essential_regions: tuple[SequenceRegion, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def registry_key(self) -> str:
        return registry_key(self.backbone_id, self.version)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_backbone_entry(payload: dict[str, Any]) -> BackboneRegistryEntry:
    genbank = str(payload.get("genbank") or "")
    record = parse_backbone_genbank(genbank)
    sequence = normalize_dna(str(record.seq)) or ""
    checksum = sequence_checksum(sequence)
    expected_checksum = str(payload.get("sequence_checksum") or "").strip()
    if expected_checksum and expected_checksum != checksum:
        raise ValueError(
            "Backbone sequence checksum does not match the GenBank record."
        )
    source_type = str(payload.get("source_type") or "").strip().lower()
    source_uri = str(payload.get("source_uri") or "").strip()
    if source_type not in TRUSTED_SOURCE_TYPES:
        raise ValueError(
            "Backbone source_type must identify a trusted source category."
        )
    if not source_uri:
        raise ValueError("Backbone source_uri is required.")
    host_organisms = tuple(
        str(item).strip()
        for item in payload.get("host_organisms") or []
        if str(item).strip()
    )
    if not host_organisms:
        raise ValueError("At least one backbone host organism is required.")
    origin = str(payload.get("origin_of_replication") or "").strip()
    marker = str(payload.get("selection_marker") or "").strip()
    if not origin:
        raise ValueError("Backbone origin_of_replication is required.")
    if not marker:
        raise ValueError("Backbone selection_marker is required.")
    copy_number = str(payload.get("copy_number_class") or "").strip().lower()
    if copy_number not in COPY_NUMBER_CLASSES:
        raise ValueError(
            "copy_number_class must be low, medium, high, very_high, or unknown."
        )
    insertion_regions = _regions(
        payload.get("insertion_regions"),
        label="insertion",
        sequence_length=len(sequence),
    )
    essential_regions = _regions(
        payload.get("essential_regions"),
        label="essential",
        sequence_length=len(sequence),
    )
    if not insertion_regions:
        raise ValueError("At least one legal insertion region is required.")
    for insertion in insertion_regions:
        conflicts = [
            essential.name
            for essential in essential_regions
            if essential.overlaps(insertion.start, insertion.end)
        ]
        if conflicts:
            raise ValueError(
                f"Insertion region {insertion.region_id} overlaps essential "
                f"region(s): {', '.join(conflicts)}."
            )
    return BackboneRegistryEntry(
        backbone_id=_required(payload, "backbone_id"),
        version=_required(payload, "version"),
        name=_required(payload, "name"),
        source_type=source_type,
        source_uri=source_uri,
        genbank=genbank,
        sequence_checksum=checksum,
        record_id=str(record.id),
        sequence_length=len(sequence),
        host_organisms=host_organisms,
        origin_of_replication=origin,
        selection_marker=marker,
        copy_number_class=copy_number,
        insertion_regions=insertion_regions,
        essential_regions=essential_regions,
        metadata=dict(payload.get("metadata") or {}),
    )


def backbone_entry_from_dict(payload: dict[str, Any]) -> BackboneRegistryEntry:
    return BackboneRegistryEntry(
        backbone_id=str(payload["backbone_id"]),
        version=str(payload["version"]),
        name=str(payload["name"]),
        source_type=str(payload["source_type"]),
        source_uri=str(payload["source_uri"]),
        genbank=str(payload["genbank"]),
        sequence_checksum=str(payload["sequence_checksum"]),
        record_id=str(payload["record_id"]),
        sequence_length=int(payload["sequence_length"]),
        host_organisms=tuple(payload.get("host_organisms") or []),
        origin_of_replication=str(payload["origin_of_replication"]),
        selection_marker=str(payload["selection_marker"]),
        copy_number_class=str(payload["copy_number_class"]),
        insertion_regions=tuple(
            SequenceRegion(**item)
            for item in payload.get("insertion_regions") or []
        ),
        essential_regions=tuple(
            SequenceRegion(**item)
            for item in payload.get("essential_regions") or []
        ),
        metadata=dict(payload.get("metadata") or {}),
    )


def parse_backbone_genbank(genbank: str):
    if not genbank.strip():
        raise ValueError("Backbone GenBank content is empty.")
    try:
        records = list(SeqIO.parse(StringIO(genbank), "genbank"))
    except Exception as exc:
        raise ValueError(f"Invalid backbone GenBank: {exc}") from exc
    if len(records) != 1:
        raise ValueError("Backbone GenBank must contain exactly one record.")
    sequence = normalize_dna(str(records[0].seq))
    if not sequence or not is_valid_iupac_dna(sequence):
        raise ValueError("Backbone contains invalid or missing IUPAC DNA.")
    return records[0]


def sequence_checksum(sequence: str) -> str:
    normalized = normalize_dna(sequence)
    if not normalized:
        raise ValueError("Cannot checksum an empty DNA sequence.")
    return f"sha256:{sha256(normalized.encode('ascii')).hexdigest()}"


def registry_key(backbone_id: str, version: str) -> str:
    raw = f"{backbone_id}__{version}".replace(".", "_")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", raw):
        raise ValueError(
            "Backbone ID and version must use letters, numbers, dots, "
            "underscores, or hyphens."
        )
    return raw


def _regions(
    value: Any,
    *,
    label: str,
    sequence_length: int,
) -> tuple[SequenceRegion, ...]:
    if not isinstance(value, list):
        return ()
    regions: list[SequenceRegion] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Invalid {label} region at position {index}.")
        start = int(item.get("start", -1))
        end = int(item.get("end", -1))
        if start < 0 or end <= start or end > sequence_length:
            raise ValueError(
                f"Invalid {label} region coordinates {start}:{end} for "
                f"sequence length {sequence_length}."
            )
        regions.append(
            SequenceRegion(
                region_id=str(
                    item.get("region_id") or f"{label}_region_{index}"
                ),
                name=str(item.get("name") or f"{label.title()} region {index}"),
                start=start,
                end=end,
                description=str(item.get("description") or ""),
            )
        )
    return tuple(regions)


def _required(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ValueError(f"Backbone {key} is required.")
    return value
