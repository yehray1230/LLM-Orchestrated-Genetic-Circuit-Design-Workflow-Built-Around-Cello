from __future__ import annotations

import math
import re


class InMemoryVectorDB:
    def __init__(self, persist_path: str | None = None):
        self.records: list[dict] = []
        self.persist_path = persist_path
        if persist_path:
            self.load()

    def add(self, record: dict) -> None:
        self.records.append(record)
        if self.persist_path:
            self.persist()

    def all(self) -> list[dict]:
        return list(self.records)

    def persist(self) -> None:
        if not self.persist_path:
            return
        import json
        try:
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load(self) -> None:
        if not self.persist_path:
            return
        import json
        import os
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
            except Exception:
                pass

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def search(self, query: str, k: int = 5) -> list[dict]:
        query_tokens = self._tokenize(query)
        if not query_tokens or not self.records:
            return []

        docs_tokens = []
        for r in self.records:
            text = r.get("search_text", "")
            if not text:
                text = " ".join(str(val) for val in r.values())
            docs_tokens.append(self._tokenize(text))

        all_vocab = set(query_tokens)
        for doc in docs_tokens:
            all_vocab.update(doc)

        N = len(self.records)
        df = {term: 0 for term in all_vocab}
        for doc in docs_tokens:
            doc_set = set(doc)
            for term in doc_set:
                df[term] += 1

        idf = {}
        for term in all_vocab:
            idf[term] = math.log(1.0 + N / (1.0 + df[term])) + 1.0

        doc_vectors = []
        doc_norms = []
        for doc in docs_tokens:
            tf = {}
            for term in doc:
                tf[term] = tf.get(term, 0.0) + 1.0
            
            vector = {}
            sum_sq = 0.0
            for term, count in tf.items():
                val = count * idf[term]
                vector[term] = val
                sum_sq += val * val
            doc_vectors.append(vector)
            doc_norms.append(math.sqrt(sum_sq))

        q_tf = {}
        for term in query_tokens:
            if term in idf:
                q_tf[term] = q_tf.get(term, 0.0) + 1.0
        
        q_vector = {}
        q_sum_sq = 0.0
        for term, count in q_tf.items():
            val = count * idf[term]
            q_vector[term] = val
            q_sum_sq += val * val
        q_norm = math.sqrt(q_sum_sq)

        if q_norm == 0.0:
            return []

        scored = []
        for i, doc_vec in enumerate(doc_vectors):
            norm = doc_norms[i]
            if norm == 0.0:
                similarity = 0.0
            else:
                dot_product = sum(q_vector[term] * doc_vec.get(term, 0.0) for term in q_vector)
                similarity = dot_product / (q_norm * norm)
            
            if similarity > 0.0:
                scored.append((similarity, self.records[i]))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:k]]
