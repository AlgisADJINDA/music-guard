"""
Tests unitaires — FingerprintIndex
Couverture : add, search, get, exists, count, persistance
"""
import os
import json
import pytest
import numpy as np

from backend.db.fingerprint_index    import FingerprintIndex
from tests.conftest                   import make_embedding, make_work_hash

pytestmark = pytest.mark.unit


class TestFingerprintIndexAdd:

    def test_add_returns_hash_string(self, empty_index, sample_embedding):
        h = empty_index.add(
            embedding  = sample_embedding,
            title      = "Titre",
            artist     = "Artiste",
            ipfs_cid   = "QmTest",
            tx_hash    = "0x" + "a" * 64,
            recipients = ["0x" + "A" * 40],
            shares     = [100]
        )
        assert isinstance(h, str)
        assert len(h) == 64

    def test_add_increments_count(self, empty_index):
        assert empty_index.count() == 0
        for i in range(3):
            empty_index.add(
                make_embedding(seed=i), f"T{i}", "A",
                f"Qm{i}", "0x" + "a" * 64, ["0x" + "A" * 40], [100]
            )
        assert empty_index.count() == 3

    def test_add_persists_to_disk(self, tmp_index_path, sample_embedding):
        idx1 = FingerprintIndex(tmp_index_path)
        h = idx1.add(sample_embedding, "T", "A", "Qm001", "0x" + "a" * 64,
                     ["0x" + "A" * 40], [100])

        # Recharger depuis le fichier
        idx2 = FingerprintIndex(tmp_index_path)
        assert idx2.exists(h)
        assert idx2.count() == 1

    def test_add_same_embedding_same_hash(self, empty_index, sample_embedding):
        h1 = empty_index.add(sample_embedding, "T1", "A", "Qm1",
                              "0x" + "a" * 64, ["0x" + "A" * 40], [100])
        # Deuxième ajout écrase silencieusement (même hash)
        h2 = empty_index.add(sample_embedding, "T2", "A", "Qm2",
                              "0x" + "b" * 64, ["0x" + "A" * 40], [100])
        assert h1 == h2
        assert empty_index.count() == 1  # pas de doublon


class TestFingerprintIndexSearch:

    def test_search_empty_index_returns_empty(self, empty_index, sample_embedding):
        results = empty_index.search(sample_embedding, top_k=1)
        assert results == []

    def test_search_finds_exact_match(self, populated_index, sample_embedding):
        results = populated_index.search(sample_embedding, top_k=1)
        assert len(results) == 1
        assert results[0]["score"] >= 0.99

    def test_search_returns_correct_metadata(self, populated_index, sample_embedding):
        results = populated_index.search(sample_embedding, top_k=1)
        entry   = results[0]
        assert entry["title"]  == "Oeuvre Test"
        assert entry["artist"] == "Artiste Test"
        assert "work_hash" in entry
        assert "score"     in entry
        assert "ipfs_cid"  in entry

    def test_search_scores_in_range(self, populated_index, sample_embedding_different):
        results = populated_index.search(sample_embedding_different, top_k=1)
        for r in results:
            assert 0.0 <= r["score"] <= 1.0

    def test_search_top_k_limits_results(self, tmp_index_path):
        idx = FingerprintIndex(tmp_index_path)
        for i in range(5):
            idx.add(make_embedding(i), f"T{i}", "A", f"Qm{i}",
                    "0x" + "a" * 64, ["0x" + "A" * 40], [100])

        query   = make_embedding(seed=0)
        results = idx.search(query, top_k=3)
        assert len(results) <= 3

    def test_search_sorted_by_score_descending(self, tmp_index_path):
        idx = FingerprintIndex(tmp_index_path)
        for i in range(5):
            idx.add(make_embedding(i), f"T{i}", "A", f"Qm{i}",
                    "0x" + "a" * 64, ["0x" + "A" * 40], [100])

        query   = make_embedding(seed=0)
        results = idx.search(query, top_k=5)
        scores  = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)


class TestFingerprintIndexGet:

    def test_get_existing_returns_entry(self, populated_index, sample_embedding):
        from backend.core.fingerprint_engine import FingerprintEngine
        h     = FingerprintEngine.embedding_to_hash(sample_embedding)
        entry = populated_index.get(h)
        assert entry is not None
        assert entry["title"] == "Oeuvre Test"

    def test_get_missing_returns_none(self, populated_index):
        assert populated_index.get("0" * 64) is None

    def test_exists_true_for_registered(self, populated_index, sample_embedding):
        from backend.core.fingerprint_engine import FingerprintEngine
        h = FingerprintEngine.embedding_to_hash(sample_embedding)
        assert populated_index.exists(h) is True

    def test_exists_false_for_unknown(self, populated_index):
        assert populated_index.exists("0" * 64) is False