from __future__ import annotations


class VectorRetriever:
    def __init__(self, records: list[dict] | None = None):
        self.records = records or []

    def search(self, query: str, k: int = 5) -> list[dict]:
        query_terms = set(query.lower().split())
        scored = []
        for record in self.records:
            text = " ".join(str(value) for value in record.values()).lower()
            scored.append((len(query_terms.intersection(text.split())), record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:k]]
