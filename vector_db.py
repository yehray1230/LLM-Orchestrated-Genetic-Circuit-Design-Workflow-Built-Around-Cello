from __future__ import annotations


class InMemoryVectorDB:
    def __init__(self):
        self.records: list[dict] = []

    def add(self, record: dict) -> None:
        self.records.append(record)

    def all(self) -> list[dict]:
        return list(self.records)

    def search(self, query: str, k: int = 5) -> list[dict]:
        query_terms = set(query.lower().split())
        if not query_terms:
            return []
        scored = []
        for record in self.records:
            text = " ".join(str(value) for value in record.values()).lower()
            overlap = len(query_terms.intersection(text.split()))
            if overlap:
                scored.append((overlap, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:k]]
