from __future__ import annotations


class InMemoryVectorDB:
    def __init__(self):
        self.records: list[dict] = []

    def add(self, record: dict) -> None:
        self.records.append(record)

    def all(self) -> list[dict]:
        return list(self.records)
