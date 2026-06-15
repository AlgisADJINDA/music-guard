"""
Tests unitaires — FingerprintEngine
Couverture : extract_fingerprint, compare_fingerprints,
             embedding_to_hash, extract_fingerprint_from_bytes
"""
import os
import pytest
import numpy  as np
import hashlib
import tempfile
import soundfile as sf

from tests.conftest import make_audio_bytes, make_audio_file, make_embedding

pytestmark = pytest.mark.unit


class TestFingerprintExtraction:
    """Tests de l'extraction d'empreinte."""

    def test_extract_fingerprint_returns_1d_float32(self, real_engine):
        path = make_audio_file(freq=440.0)
        try:
            emb = real_engine.extract_fingerprint(path)
        finally:
            os.unlink(path)

        assert emb.ndim  == 1,           "L'empreinte doit être un vecteur 1D"
        assert emb.dtype == np.float32,  "L'empreinte doit être float32"
        assert len(emb)  > 0,            "L'empreinte ne doit pas être vide"

    def test_extract_fingerprint_no_nan_inf(self, real_engine):
        path = make_audio_file(freq=440.0)
        try:
            emb = real_engine.extract_fingerprint(path)
        finally:
            os.unlink(path)

        assert np.isfinite(emb).all(), "L'empreinte contient NaN ou Inf"

    def test_extract_fingerprint_deterministic(self, real_engine):
        """Même fichier → même empreinte."""
        path = make_audio_file(freq=440.0, noise=0.02)
        try:
            emb1 = real_engine.extract_fingerprint(path)
            emb2 = real_engine.extract_fingerprint(path)
        finally:
            os.unlink(path)

        np.testing.assert_array_equal(emb1, emb2)

    def test_extract_fingerprint_different_files_differ(self, real_engine):
        """Fichiers différents → empreintes différentes."""
        p1 = make_audio_file(freq=440.0)
        p2 = make_audio_file(freq=880.0)
        try:
            emb1 = real_engine.extract_fingerprint(p1)
            emb2 = real_engine.extract_fingerprint(p2)
        finally:
            os.unlink(p1)
            os.unlink(p2)

        assert not np.array_equal(emb1, emb2)

    def test_extract_fingerprint_from_bytes_consistent(self, real_engine):
        """extract_fingerprint et extract_fingerprint_from_bytes doivent concorder."""
        path  = make_audio_file(freq=440.0)
        with open(path, "rb") as f:
            b = f.read()
        try:
            emb_path  = real_engine.extract_fingerprint(path)
            emb_bytes = real_engine.extract_fingerprint_from_bytes(b)
        finally:
            os.unlink(path)

        score = real_engine.compare_fingerprints(emb_path, emb_bytes)
        assert score >= 0.99, f"Cohérence path/bytes insuffisante : {score:.4f}"

    def test_extract_fingerprint_from_bytes_returns_valid(self, real_engine):
        audio_bytes = make_audio_bytes(freq=440.0)
        emb = real_engine.extract_fingerprint_from_bytes(audio_bytes)

        assert emb.ndim  == 1
        assert emb.dtype == np.float32
        assert len(emb)  > 0
        assert np.isfinite(emb).all()

    def test_extract_features_shape(self, real_engine):
        """extract_features retourne un spectrogramme mel valide."""
        audio_bytes = make_audio_bytes(freq=440.0)
        import librosa
        audio, _ = librosa.load(
            __import__("io").BytesIO(audio_bytes),
            sr=real_engine.SAMPLE_RATE,
            mono=True
        )
        mel = real_engine.extract_features(audio)

        assert mel.ndim  == 2
        assert mel.shape[0] == real_engine.N_MELS
        assert mel.min() >= 0.0
        assert mel.max() <= 1.0

    def test_model_loaded_or_fallback(self, real_engine):
        """Le moteur doit être opérationnel (modèle ou fallback)."""
        path = make_audio_file(freq=440.0)
        try:
            emb = real_engine.extract_fingerprint(path)
            assert len(emb) > 0
        finally:
            os.unlink(path)


class TestFingerprintComparison:
    """Tests de la comparaison d'empreintes."""

    def test_compare_identical_vectors(self, real_engine, sample_embedding):
        score = real_engine.compare_fingerprints(sample_embedding, sample_embedding)
        assert score >= 0.99, f"Auto-similarité trop faible : {score}"

    def test_compare_returns_in_range(self, real_engine,
                                       sample_embedding,
                                       sample_embedding_different):
        score = real_engine.compare_fingerprints(
            sample_embedding, sample_embedding_different
        )
        assert 0.0 <= score <= 1.0, f"Score hors [0,1] : {score}"

    def test_compare_similar_higher_than_different(
        self, real_engine,
        sample_embedding,
        sample_embedding_similar,
        sample_embedding_different
    ):
        score_sim  = real_engine.compare_fingerprints(sample_embedding, sample_embedding_similar)
        score_diff = real_engine.compare_fingerprints(sample_embedding, sample_embedding_different)
        assert score_sim > score_diff, (
            f"Similaire ({score_sim:.4f}) devrait être > différent ({score_diff:.4f})"
        )

    def test_compare_symmetry(self, real_engine,
                               sample_embedding,
                               sample_embedding_different):
        s1 = real_engine.compare_fingerprints(sample_embedding, sample_embedding_different)
        s2 = real_engine.compare_fingerprints(sample_embedding_different, sample_embedding)
        assert abs(s1 - s2) < 1e-5, "La similarité doit être symétrique"

    def test_compare_zero_vector(self, real_engine, sample_embedding):
        """Vecteur nul → score = 0 sans crash."""
        zero_vec = np.zeros(len(sample_embedding), dtype=np.float32)
        score    = real_engine.compare_fingerprints(sample_embedding, zero_vec)
        assert score == 0.0

    def test_compare_real_audio_similar(self, real_engine):
        """Deux enregistrements de la même source → score > seuil."""
        p1 = make_audio_file(freq=440.0, noise=0.01)
        p2 = make_audio_file(freq=440.0, noise=0.06)  # copie avec plus de bruit
        try:
            emb1  = real_engine.extract_fingerprint(p1)
            emb2  = real_engine.extract_fingerprint(p2)
            score = real_engine.compare_fingerprints(emb1, emb2)
        finally:
            os.unlink(p1)
            os.unlink(p2)

        assert score > 0.5, (
            f"Une copie légèrement dégradée devrait avoir score > 0.5 : {score:.4f}"
        )

    def test_compare_real_audio_different(self, real_engine):
      p1 = make_audio_file(freq=440.0)
      # Générer un bruit blanc comme second fichier
      sr = 8000
      dur = 5.0
      noise = np.random.randn(int(sr * dur)).astype(np.float32)
      noise /= np.abs(noise).max()
      p2 = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
      sf.write(p2.name, noise, sr)
      p2.close()
      try:
          emb1 = real_engine.extract_fingerprint(p1)
          emb2 = real_engine.extract_fingerprint(p2.name)
          score = real_engine.compare_fingerprints(emb1, emb2)
      finally:
          os.unlink(p1)
          os.unlink(p2.name)

      assert score < 0.85, (
          f"Des fichiers très différents ne devraient pas dépasser le seuil : {score:.4f}"
      )


class TestEmbeddingToHash:
    """Tests de la conversion embedding → hash."""

    def test_hash_is_64_chars(self, sample_embedding):
        h = FingerprintEngine.embedding_to_hash(sample_embedding)
        assert len(h) == 64

    def test_hash_is_hex(self, sample_embedding):
        h = FingerprintEngine.embedding_to_hash(sample_embedding)
        int(h, 16)   # lève ValueError si non-hex

    def test_hash_deterministic(self, sample_embedding):
        h1 = FingerprintEngine.embedding_to_hash(sample_embedding)
        h2 = FingerprintEngine.embedding_to_hash(sample_embedding)
        assert h1 == h2

    def test_different_embeddings_different_hashes(
        self, sample_embedding, sample_embedding_different
    ):
        h1 = FingerprintEngine.embedding_to_hash(sample_embedding)
        h2 = FingerprintEngine.embedding_to_hash(sample_embedding_different)
        assert h1 != h2


from backend.core.fingerprint_engine import FingerprintEngine