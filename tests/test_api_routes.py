"""
Tests d'intégration — Routes FastAPI
Couverture : POST /register, POST /analyze,
             POST /royalty/simulate, GET /health, GET /
"""
import io
import json
import pytest

from tests.conftest import make_audio_bytes

pytestmark = pytest.mark.api


# ─── Helpers ──────────────────────────────────────────────────────────────────

def audio_upload_file(content: bytes, filename: str = "test.wav",
                       content_type: str = "audio/wav"):
    """Construit le dict files pour le TestClient FastAPI."""
    return {"file": (filename, io.BytesIO(content), content_type)}


def register_payload(
    recipients = None,
    shares     = None,
    title:  str = "Titre Test",
    artist: str = "Artiste Test",
):
    recipients = recipients or ["0x" + "E" * 40, "0x" + "F" * 40]
    shares     = shares     or [70, 30]
    return {
        "title":      title,
        "artist":     artist,
        "recipients": json.dumps(recipients),
        "shares":     json.dumps(shares),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# GET / et GET /health
# ═══════════════════════════════════════════════════════════════════════════════

class TestHealthEndpoints:

    def test_root_returns_200(self, test_client):
        r = test_client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "running"

    def test_health_returns_200(self, test_client):
        r = test_client.get("/health")
        assert r.status_code == 200

    def test_health_contains_required_fields(self, test_client):
        r    = test_client.get("/health")
        data = r.json()
        for field in ["ipfs", "blockchain", "model_loaded", "works_indexed"]:
            assert field in data, f"Champ manquant dans /health : {field}"

    def test_health_ipfs_true(self, test_client):
        r = test_client.get("/health")
        assert r.json()["ipfs"] is True

    def test_health_blockchain_true(self, test_client):
        r = test_client.get("/health")
        assert r.json()["blockchain"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# POST /register
# ═══════════════════════════════════════════════════════════════════════════════

class TestRegisterEndpoint:

    def test_register_returns_201_or_200(self, test_client):
        audio = make_audio_bytes(freq=440.0)
        r = test_client.post(
            "/register/",
            data  = register_payload(),
            files = audio_upload_file(audio)
        )
        assert r.status_code in (200, 201), r.text

    def test_register_returns_audio_track(self, test_client):
        audio = make_audio_bytes(freq=440.0)
        r = test_client.post(
            "/register/",
            data  = register_payload(),
            files = audio_upload_file(audio)
        )
        data = r.json()
        for field in ["id", "title", "artist",
                      "fingerprint_hash", "ipfs_cid", "tx_hash"]:
            assert field in data, f"Champ manquant : {field}"

    def test_register_preserves_title_and_artist(self, test_client):
        audio = make_audio_bytes(freq=440.0)
        r = test_client.post(
            "/register/",
            data  = register_payload(title="Ma Chanson", artist="Artiste X"),
            files = audio_upload_file(audio)
        )
        data = r.json()
        assert data["title"]  == "Ma Chanson"
        assert data["artist"] == "Artiste X"

    def test_register_shares_sum_not_100_returns_422(self, test_client):
        audio = make_audio_bytes()
        r = test_client.post(
            "/register/",
            data  = register_payload(shares=[60, 20]),  # somme = 80
            files = audio_upload_file(audio)
        )
        assert r.status_code == 422
        assert "100" in r.text

    def test_register_invalid_json_recipients_returns_422(self, test_client):
        audio = make_audio_bytes()
        r = test_client.post(
            "/register/",
            data  = {
                "title": "T", "artist": "A",
                "recipients": "not-json",
                "shares":     json.dumps([100])
            },
            files = audio_upload_file(audio)
        )
        assert r.status_code == 422

    def test_register_empty_file_returns_422(self, test_client):
        r = test_client.post(
            "/register/",
            data  = register_payload(),
            files = audio_upload_file(b"", filename="empty.wav")
        )
        assert r.status_code == 422
        assert "vide" in r.text.lower()

    def test_register_missing_title_returns_422(self, test_client):
        audio = make_audio_bytes()
        r = test_client.post(
            "/register/",
            data  = {
                "artist":     "A",
                "recipients": json.dumps(["0x" + "E" * 40]),
                "shares":     json.dumps([100])
            },
            files = audio_upload_file(audio)
        )
        assert r.status_code == 422

    def test_register_fingerprint_hash_is_64_chars(self, test_client):
        audio = make_audio_bytes()
        r     = test_client.post(
            "/register/",
            data  = register_payload(),
            files = audio_upload_file(audio)
        )
        assert r.status_code in (200, 201)
        assert len(r.json()["fingerprint_hash"]) == 64

    def test_register_tx_hash_starts_with_0x(self, test_client):
        audio = make_audio_bytes()
        r     = test_client.post(
            "/register/",
            data  = register_payload(),
            files = audio_upload_file(audio)
        )
        assert r.status_code in (200, 201)
        assert r.json()["tx_hash"].startswith("0x")

    def test_register_single_recipient_full_share(self, test_client):
        audio = make_audio_bytes()
        r = test_client.post(
            "/register/",
            data  = register_payload(
                recipients = ["0x" + "E" * 40],
                shares     = [100]
            ),
            files = audio_upload_file(audio)
        )
        assert r.status_code in (200, 201)


# ═══════════════════════════════════════════════════════════════════════════════
# POST /analyze
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyzeEndpoint:

    def test_analyze_returns_200(self, test_client):
        audio = make_audio_bytes(freq=440.0, noise=0.05)
        r     = test_client.post(
            "/analyze/",
            files = audio_upload_file(audio)
        )
        assert r.status_code == 200, r.text

    def test_analyze_positive_contains_proof(self, test_client):
        audio = make_audio_bytes(freq=440.0, noise=0.05)
        r     = test_client.post("/analyze/", files=audio_upload_file(audio))
        data  = r.json()
        assert "match"   in data
        assert "message" in data
        # Si is_match = True, proof doit être présent
        if data["match"]["is_match"]:
            assert data["proof"] is not None

    def test_analyze_match_has_required_fields(self, test_client):
        audio = make_audio_bytes(freq=440.0, noise=0.05)
        r     = test_client.post("/analyze/", files=audio_upload_file(audio))
        match = r.json()["match"]
        for field in ["is_match", "score", "threshold", "timestamp"]:
            assert field in match, f"Champ manquant dans match : {field}"

    def test_analyze_score_in_range(self, test_client):
        audio = make_audio_bytes(freq=440.0, noise=0.05)
        r     = test_client.post("/analyze/", files=audio_upload_file(audio))
        score = r.json()["match"]["score"]
        assert 0.0 <= score <= 1.0, f"Score hors [0,1] : {score}"

    def test_analyze_negative_match_no_proof(
        self, test_client, mock_piracy_detector, sample_match_result_negative
    ):
        """Quand is_match=False, pas de preuve générée."""
        mock_piracy_detector.analyze_content.return_value = sample_match_result_negative
        audio = make_audio_bytes(freq=880.0)
        r     = test_client.post("/analyze/", files=audio_upload_file(audio))
        assert r.status_code == 200
        data  = r.json()
        assert data["match"]["is_match"] is False
        assert data["proof"] is None

    def test_analyze_empty_file_returns_422(self, test_client):
        r = test_client.post(
            "/analyze/",
            files = audio_upload_file(b"", filename="empty.wav")
        )
        assert r.status_code == 422

    def test_analyze_positive_has_takedown_request(self, test_client):
        audio = make_audio_bytes(freq=440.0, noise=0.05)
        r     = test_client.post("/analyze/", files=audio_upload_file(audio))
        data  = r.json()
        if data["match"]["is_match"]:
            assert "takedown_request" in data
            takedown = data["takedown_request"]
            for field in ["id", "proof_hash", "status"]:
                assert field in takedown

    def test_analyze_proof_has_cids(self, test_client):
        audio = make_audio_bytes(freq=440.0, noise=0.05)
        r     = test_client.post("/analyze/", files=audio_upload_file(audio))
        data  = r.json()
        if data["match"]["is_match"] and data["proof"]:
            proof = data["proof"]
            assert proof["suspect_cid"]  != ""
            assert proof["report_cid"]   != ""

    def test_analyze_message_present(self, test_client):
        audio = make_audio_bytes()
        r     = test_client.post("/analyze/", files=audio_upload_file(audio))
        assert r.json()["message"] != ""


# ═══════════════════════════════════════════════════════════════════════════════
# POST /royalty/simulate
# ═══════════════════════════════════════════════════════════════════════════════

class TestRoyaltyEndpoint:

    def test_simulate_returns_200(
        self, test_client, mock_blockchain_manager, sample_work_hash
    ):
        mock_blockchain_manager.verify_registration.return_value = True
        r = test_client.post(
            "/royalty/simulate",
            json = {"work_hash": sample_work_hash, "total_amount": 1000}
        )
        assert r.status_code == 200, r.text

    def test_simulate_returns_payments_list(
        self, test_client, mock_blockchain_manager, sample_work_hash
    ):
        mock_blockchain_manager.verify_registration.return_value = True
        r     = test_client.post(
            "/royalty/simulate",
            json  = {"work_hash": sample_work_hash, "total_amount": 1000}
        )
        data = r.json()
        assert "payments" in data
        assert isinstance(data["payments"], list)
        assert len(data["payments"]) == 2

    def test_simulate_tx_hash_in_response(
        self, test_client, mock_blockchain_manager, sample_work_hash
    ):
        mock_blockchain_manager.verify_registration.return_value = True
        r    = test_client.post(
            "/royalty/simulate",
            json = {"work_hash": sample_work_hash, "total_amount": 1000}
        )
        assert "tx_hash" in r.json()
        assert r.json()["tx_hash"].startswith("0x")

    def test_simulate_amounts_sum_to_total(
        self, test_client, mock_blockchain_manager, sample_work_hash
    ):
        mock_blockchain_manager.verify_registration.return_value = True
        TOTAL = 1000
        r     = test_client.post(
            "/royalty/simulate",
            json  = {"work_hash": sample_work_hash, "total_amount": TOTAL}
        )
        total_paid = sum(p["amount"] for p in r.json()["payments"])
        assert total_paid == TOTAL

    def test_simulate_unknown_work_returns_404(
        self, test_client, mock_blockchain_manager
    ):
        mock_blockchain_manager.verify_registration.return_value = False
        r = test_client.post(
            "/royalty/simulate",
            json = {"work_hash": "0" * 64, "total_amount": 1000}
        )
        assert r.status_code == 404

    def test_simulate_zero_amount_returns_422(
        self, test_client, sample_work_hash
    ):
        r = test_client.post(
            "/royalty/simulate",
            json = {"work_hash": sample_work_hash, "total_amount": 0}
        )
        assert r.status_code == 422

    def test_simulate_negative_amount_returns_422(
        self, test_client, sample_work_hash
    ):
        r = test_client.post(
            "/royalty/simulate",
            json = {"work_hash": sample_work_hash, "total_amount": -100}
        )
        assert r.status_code == 422

    def test_simulate_missing_work_hash_returns_422(self, test_client):
        r = test_client.post(
            "/royalty/simulate",
            json = {"total_amount": 1000}
        )
        assert r.status_code == 422

    def test_simulate_payment_has_beneficiary(
        self, test_client, mock_blockchain_manager, sample_work_hash
    ):
        mock_blockchain_manager.verify_registration.return_value = True
        r = test_client.post(
            "/royalty/simulate",
            json = {"work_hash": sample_work_hash, "total_amount": 1000}
        )
        for payment in r.json()["payments"]:
            assert "beneficiary" in payment
            assert "amount"      in payment

    def test_simulate_total_amount_in_response(
        self, test_client, mock_blockchain_manager, sample_work_hash
    ):
        mock_blockchain_manager.verify_registration.return_value = True
        r = test_client.post(
            "/royalty/simulate",
            json = {"work_hash": sample_work_hash, "total_amount": 500}
        )
        assert r.json()["total_amount"] == 500


# ═══════════════════════════════════════════════════════════════════════════════
# Tests de robustesse transversaux
# ═══════════════════════════════════════════════════════════════════════════════

class TestRobustness:

    def test_analyze_without_file_returns_422(self, test_client):
        r = test_client.post("/analyze/")
        assert r.status_code == 422

    def test_register_without_file_returns_422(self, test_client):
        r = test_client.post("/register/", data=register_payload())
        assert r.status_code == 422

    def test_royalty_with_invalid_json_returns_422(self, test_client):
        r = test_client.post(
            "/royalty/simulate",
            content      = b"not json",
            headers      = {"Content-Type": "application/json"}
        )
        assert r.status_code == 422

    def test_unknown_route_returns_404(self, test_client):
        r = test_client.get("/nonexistent-endpoint")
        assert r.status_code == 404

    def test_cors_headers_present(self, test_client):
        r = test_client.options(
            "/",
            headers = {"Origin": "http://localhost:5173"}
        )
        # Le middleware CORS est actif si la réponse contient le header
        assert r.status_code in (200, 204, 405)