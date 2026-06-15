"""
Tests unitaires — IPFSStorage (avec mocks HTTP)
Couverture : upload_file, upload_json, retrieve_file,
             verify_integrity, is_available, get_gateway_url
"""
import json
import hashlib
import pytest
from unittest.mock import patch, MagicMock

from backend.core.ipfs_storage import IPFSStorage

pytestmark = pytest.mark.unit


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_mock_response(status_code: int = 200, json_data: dict = None,
                        content: bytes = b""):
    mock          = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    mock.content   = content
    mock.text      = content.decode("utf-8", errors="ignore")
    mock.raise_for_status = MagicMock()
    if status_code >= 400:
        import requests
        mock.raise_for_status.side_effect = requests.HTTPError(
            f"HTTP {status_code}"
        )
    return mock


@pytest.fixture
def ipfs():
    return IPFSStorage()


# ═══════════════════════════════════════════════════════════════════════════════
class TestUploadFile:

    def test_upload_returns_cid(self, ipfs):
        response = make_mock_response(
            200, json_data={"Hash": "QmTestCID001", "Size": "100"}
        )
        with patch.object(ipfs._session, "post", return_value=response):
            cid = ipfs.upload_file(b"hello world", "test.txt")
        assert cid == "QmTestCID001"

    def test_upload_with_pin_param(self, ipfs):
        response = make_mock_response(200, {"Hash": "QmTest", "Size": "10"})
        with patch.object(ipfs._session, "post", return_value=response) as mock_post:
            ipfs.upload_file(b"data", "f.txt")
            call_kwargs = mock_post.call_args
            assert call_kwargs.kwargs.get("params") == {"pin": "true"}

    def test_upload_connection_error(self, ipfs):
        import requests
        with patch.object(ipfs._session, "post",
                          side_effect=requests.ConnectionError):
            with pytest.raises(RuntimeError, match="Nœud IPFS inaccessible"):
                ipfs.upload_file(b"data", "test.txt")

    def test_upload_json_serializes_correctly(self, ipfs):
        data     = {"key": "value", "number": 42}
        response = make_mock_response(200, {"Hash": "QmJSON001", "Size": "50"})

        captured = {}
        def mock_post(url, files=None, params=None, timeout=None):
            if files:
                captured["content"] = files["file"][1]
            return response

        with patch.object(ipfs._session, "post", side_effect=mock_post):
            cid = ipfs.upload_json(data, "data.json")

        assert cid == "QmJSON001"
        parsed = json.loads(captured["content"].decode("utf-8"))
        assert parsed["key"]    == "value"
        assert parsed["number"] == 42

    def test_upload_generic_error(self, ipfs):
        with patch.object(ipfs._session, "post",
                          side_effect=Exception("Unexpected")):
            with pytest.raises(RuntimeError, match="Erreur IPFS upload"):
                ipfs.upload_file(b"data", "test.txt")


# ═══════════════════════════════════════════════════════════════════════════════
class TestRetrieveFile:

    def test_retrieve_returns_bytes(self, ipfs):
        content  = b"audio content bytes"
        response = make_mock_response(200, content=content)
        with patch.object(ipfs._session, "post", return_value=response):
            result = ipfs.retrieve_file("QmTest001")
        assert result == content

    def test_retrieve_not_found_raises(self, ipfs):
        response = make_mock_response(500)
        with patch.object(ipfs._session, "post", return_value=response):
            with pytest.raises(RuntimeError, match="CID introuvable"):
                ipfs.retrieve_file("QmFakeCID")

    def test_retrieve_passes_cid_as_param(self, ipfs):
        response = make_mock_response(200, content=b"data")
        with patch.object(ipfs._session, "post", return_value=response) as mock_post:
            ipfs.retrieve_file("QmSpecificCID")
            call_kwargs = mock_post.call_args
            assert call_kwargs.kwargs.get("params") == {"arg": "QmSpecificCID"}


# ═══════════════════════════════════════════════════════════════════════════════
class TestVerifyIntegrity:

    def test_verify_accessible_without_hash(self, ipfs):
        response = make_mock_response(200, content=b"file content")
        with patch.object(ipfs._session, "post", return_value=response):
            result = ipfs.verify_integrity("QmTest")
        assert result is True

    def test_verify_with_correct_hash(self, ipfs):
        content       = b"exact content"
        expected_hash = hashlib.sha256(content).hexdigest()
        response      = make_mock_response(200, content=content)
        with patch.object(ipfs._session, "post", return_value=response):
            result = ipfs.verify_integrity("QmTest", expected_hash)
        assert result is True

    def test_verify_with_wrong_hash(self, ipfs):
        content  = b"original content"
        response = make_mock_response(200, content=content)
        with patch.object(ipfs._session, "post", return_value=response):
            result = ipfs.verify_integrity("QmTest", "0" * 64)
        assert result is False

    def test_verify_unavailable_cid(self, ipfs):
        import requests
        with patch.object(ipfs._session, "post",
                          side_effect=requests.ConnectionError):
            result = ipfs.verify_integrity("QmFake")
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
class TestAvailability:

    def test_is_available_true(self, ipfs):
        response = make_mock_response(200, {"ID": "Qm...", "AgentVersion": "kubo"})
        with patch.object(ipfs._session, "post", return_value=response):
            assert ipfs.is_available() is True

    def test_is_available_false_on_connection_error(self, ipfs):
        import requests
        with patch.object(ipfs._session, "post",
                          side_effect=requests.ConnectionError):
            assert ipfs.is_available() is False

    def test_get_gateway_url(self, ipfs):
        url = ipfs.get_gateway_url("QmABC123")
        assert "QmABC123" in url
        assert url.startswith("http")