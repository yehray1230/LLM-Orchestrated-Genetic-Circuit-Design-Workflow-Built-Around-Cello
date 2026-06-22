from __future__ import annotations

from pathlib import Path

from vector_db import InMemoryVectorDB


def test_vsm_tfidf_cosine_similarity_search() -> None:
    db = InMemoryVectorDB()

    # Add documents
    doc1 = {
        "title": "Ribosome Binding Site Design",
        "search_text": "ribosome binding site RBS translation initiation strength Shine-Dalgarno complementary sequence",
    }
    doc2 = {
        "title": "Logic Gate Crosstalk",
        "search_text": "logic gate crosstalk repressor promoter orthogonality mapping limits UCF constraints",
    }
    doc3 = {
        "title": "Plasmid Backbone",
        "search_text": "plasmid backbone copy number replication origin resistance marker selectable",
    }

    db.add(doc1)
    db.add(doc2)
    db.add(doc3)

    # Search for "crosstalk orthogonality"
    results = db.search("crosstalk orthogonality", k=1)
    assert len(results) == 1
    assert results[0]["title"] == "Logic Gate Crosstalk"

    # Search for "Shine-Dalgarno"
    results_rbs = db.search("Shine-Dalgarno", k=1)
    assert len(results_rbs) == 1
    assert results_rbs[0]["title"] == "Ribosome Binding Site Design"

    # Search for term not in any document
    results_none = db.search("nonexistentword", k=1)
    assert len(results_none) == 0


def test_vector_db_persistency(tmp_path: Path) -> None:
    db_file = tmp_path / "test_vector_db.json"
    db = InMemoryVectorDB(persist_path=str(db_file))

    doc = {
        "title": "Gibson Overlaps",
        "search_text": "gibson assembly overlap melting temperature Tm PCR primer design",
    }
    db.add(doc)

    assert db_file.exists()

    # Load from the same file in a new instance
    db_new = InMemoryVectorDB(persist_path=str(db_file))
    assert len(db_new.all()) == 1
    assert db_new.all()[0]["title"] == "Gibson Overlaps"

    # Search in the loaded instance
    res = db_new.search("gibson melting temp", k=1)
    assert len(res) == 1
    assert res[0]["title"] == "Gibson Overlaps"
