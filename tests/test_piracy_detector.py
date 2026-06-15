"""
Tests unitaires — PiracyDetector
Couverture : analyze_content, generate_proof, calculate_similarity
"""
import pytest
from unittest.mock import MagicMock
from datetime      import datetime

from backend.core.piracy_detector   import PiracyDetector
from backend.models.match_result    import MatchResult
from tests.conftest                  import make_audio_bytes, make_embedding

pytestmark = pytest.mark.unit


@pytest.fixture
def detector(
    mock_fingerprint_engine,
    populated_index,
    mock_ipfs_storage,
    mock_blockchain_manager
):
    return PiracyDetector(
        fingerprinter = mock_fingerprint_engine,
        index         = populated_index,
        ipfs          = mock_ipfs_storage,
        blockchain    = mock_blockchain_manager,
        threshold     = 0.85
    )


class TestAnalyzeContent:

    def test_returns_match_result(self, detector):
        result = detector.analyze_content(make_audio_bytes())
        assert isinstance(result, MatchResult)

    def test_positive_match_when_score_above_threshold(
        self, detector, mock_fingerprint_engine, sample_embedding
    ):
        """Score élevé → piraterie détectée."""
        mock_fingerprint_engine.extract_fingerprint_from_bytes.return_value = \
            sample_embedding   # identique à l'empreinte de référence dans l'index
        result = detector.analyze_content(make_audio_bytes())
        assert result.is_match is True
        assert result.score >= 0.85

    def test_negative_match_when_score_below_threshold(
        self, detector, mock_fingerprint_engine, sample_embedding_different
    ):
        """Score faible → pas de piraterie."""
        mock_fingerprint_engine.extract_fingerprint_from_bytes.return_value = \
            sample_embedding_different
        result = detector.analyze_content(make_audio_bytes())
        assert result.is_match is False

    def test_empty_index_returns_no_match(
        self, mock_fingerprint_engine, empty_index,
        mock_ipfs_storage, mock_blockchain_manager
    ):
        det = PiracyDetector(
            mock_fingerprint_engine, empty_index,
            mock_ipfs_storage, mock_blockchain_manager,
            threshold=0.85
        )
        result = det.analyze_content(make_audio_bytes())
        assert result.is_match is False
        assert result.score == 0.0

    def test_match_result_has_timestamp(self, detector):
        result = detector.analyze_content(make_audio_bytes())
        assert result.timestamp is not None
        assert isinstance(result.timestamp, datetime)

    def test_match_result_has_suspect_hash(self, detector):
        result = detector.analyze_content(make_audio_bytes())
        assert result.suspect_hash is not None
        assert len(result.suspect_hash) == 64

    def test_positive_match_includes_original_hash(
        self, detector, mock_fingerprint_engine, sample_embedding
    ):
        mock_fingerprint_engine.extract_fingerprint_from_bytes.return_value = \
            sample_embedding
        result = detector.analyze_content(make_audio_bytes())
        if result.is_match:
            assert result.original_hash is not None

    def test_threshold_respected(
        self, mock_fingerprint_engine, populated_index,
        mock_ipfs_storage, mock_blockchain_manager, sample_embedding
    ):
        """Vérifier que le seuil configuré est bien appliqué."""
        for threshold in [0.70, 0.85, 0.95]:
            mock_fingerprint_engine.extract_fingerprint_from_bytes.return_value = \
                sample_embedding
            det = PiracyDetector(
                mock_fingerprint_engine, populated_index,
                mock_ipfs_storage, mock_blockchain_manager,
                threshold=threshold
            )
            result = det.analyze_content(make_audio_bytes())
            assert result.threshold == threshold


class TestGenerateProof:

    def test_raises_on_negative_match(
        self, detector, sample_match_result_negative
    ):
        with pytest.raises(ValueError, match="generate_proof.*MatchResult négatif"):
            detector.generate_proof(sample_match_result_negative, b"audio")

    def test_returns_proof_object(
        self, detector, sample_match_result_positive
    ):
        from backend.models.proof import Proof
        proof = detector.generate_proof(
            sample_match_result_positive, make_audio_bytes()
        )
        assert isinstance(proof, Proof)

    def test_proof_has_all_cids(
        self, detector, sample_match_result_positive
    ):
        proof = detector.generate_proof(
            sample_match_result_positive, make_audio_bytes()
        )
        assert proof.suspect_cid  != ""
        assert proof.report_cid   != ""

    def test_proof_has_tx_hash(
        self, detector, sample_match_result_positive
    ):
        proof = detector.generate_proof(
            sample_match_result_positive, make_audio_bytes()
        )
        assert proof.tx_hash is not None

    def test_proof_match_score_preserved(
        self, detector, sample_match_result_positive
    ):
        proof = detector.generate_proof(
            sample_match_result_positive, make_audio_bytes()
        )
        assert proof.match_score == sample_match_result_positive.score

    def test_ipfs_called_twice(
        self, detector, mock_ipfs_storage, sample_match_result_positive
    ):
        """Upload suspect + upload rapport = 2 appels IPFS."""
        detector.generate_proof(sample_match_result_positive, make_audio_bytes())
        assert mock_ipfs_storage.upload_file.call_count >= 1
        assert mock_ipfs_storage.upload_json.call_count >= 1

    def test_blockchain_certify_called(
        self, detector, mock_blockchain_manager, sample_match_result_positive
    ):
        detector.generate_proof(sample_match_result_positive, make_audio_bytes())
        mock_blockchain_manager.store_proof.assert_called_once()


class TestMatchResultProperties:

    def test_confidence_label_very_high(self):
        m = MatchResult(is_match=True, score=0.97, threshold=0.85)
        assert m.confidence_label == "TRÈS HAUTE"

    def test_confidence_label_high(self):
        m = MatchResult(is_match=True, score=0.88, threshold=0.85)
        assert m.confidence_label == "HAUTE"

    def test_confidence_label_medium(self):
        m = MatchResult(is_match=False, score=0.72, threshold=0.85)
        assert m.confidence_label == "MOYENNE"

    def test_confidence_label_low(self):
        m = MatchResult(is_match=False, score=0.40, threshold=0.85)
        assert m.confidence_label == "FAIBLE"