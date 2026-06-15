"""
Fixtures partagées entre tous les tests.
Fournit des objets de test réutilisables, des mocks
et des helpers de génération de données audio synthétiques.
"""
import os
import sys
import json
import uuid
import tempfile
import hashlib
from pathlib   import Path
from datetime  import datetime
from unittest.mock import MagicMock, AsyncMock, patch

import numpy   as np
import soundfile as sf
import pytest
from fastapi.testclient import TestClient

# ── Chemins ───────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config                   import settings
from backend.core.fingerprint_engine  import FingerprintEngine
from backend.core.ipfs_storage        import IPFSStorage
from backend.core.blockchain_manager  import BlockchainManager
from backend.core.piracy_detector     import PiracyDetector
from backend.db.fingerprint_index     import FingerprintIndex
from backend.models.audio_track       import AudioTrack
from backend.models.match_result      import MatchResult
from backend.models.proof             import Proof
from backend.models.takedown_request  import TakedownRequest, TakedownStatus


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS AUDIO
# ═══════════════════════════════════════════════════════════════════════════════

def make_audio_bytes(
    freq:     float = 440.0,
    duration: float = 5.0,
    sr:       int   = 8000,
    noise:    float = 0.02
) -> bytes:
    """Génère des bytes WAV synthétiques pour les tests."""
    t      = np.linspace(0, duration, int(sr * duration))
    signal = np.sin(2 * np.pi * freq * t).astype(np.float32)
    signal += noise * np.random.randn(len(signal)).astype(np.float32)
    signal /= np.abs(signal).max()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, signal, sr)
    tmp.close()
    with open(tmp.name, "rb") as f:
        data = f.read()
    os.unlink(tmp.name)
    return data


def make_audio_file(
    freq:     float = 440.0,
    duration: float = 5.0,
    sr:       int   = 8000,
    noise:    float = 0.02
) -> str:
    """Génère un fichier WAV temporaire et retourne son chemin."""
    t      = np.linspace(0, duration, int(sr * duration))
    signal = np.sin(2 * np.pi * freq * t).astype(np.float32)
    signal += noise * np.random.randn(len(signal)).astype(np.float32)
    signal /= np.abs(signal).max()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, signal, sr)
    return tmp.name


def make_embedding(seed: int = 42, dim: int = 128) -> np.ndarray:
    """Génère un vecteur d'empreinte déterministe."""
    rng = np.random.default_rng(seed)
    v   = rng.random(dim).astype(np.float32)
    return v / np.linalg.norm(v)


def make_work_hash(seed: int = 42) -> str:
    """Génère un hash SHA-256 déterministe."""
    return hashlib.sha256(f"work_{seed}".encode()).hexdigest()


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES — DONNÉES DE TEST
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_audio_bytes():
    """Fichier audio WAV valide (440Hz, 5s)."""
    return make_audio_bytes(freq=440.0, noise=0.02)


@pytest.fixture
def sample_audio_bytes_pirate():
    """Copie piratée (même fréquence, plus de bruit)."""
    return make_audio_bytes(freq=440.0, noise=0.08)


@pytest.fixture
def sample_audio_bytes_legal():
    """Contenu légal (fréquence différente)."""
    return make_audio_bytes(freq=880.0, noise=0.02)


@pytest.fixture
def sample_embedding():
    return make_embedding(seed=42, dim=128)


@pytest.fixture
def sample_embedding_similar():
    """Vecteur proche de sample_embedding (légèrement bruité)."""
    base  = make_embedding(seed=42, dim=128)
    noise = np.random.default_rng(99).random(128).astype(np.float32) * 0.05
    v     = base + noise
    return v / np.linalg.norm(v)


@pytest.fixture
def sample_embedding_different(sample_embedding):
    return -sample_embedding   # opposé → similarité cosinus = 0.0


@pytest.fixture
def sample_work_hash():
    return make_work_hash(42)


@pytest.fixture
def sample_match_result_positive(sample_work_hash):
    return MatchResult(
        is_match       = True,
        score          = 0.9742,
        threshold      = 0.85,
        original_hash  = sample_work_hash,
        original_title = "Oeuvre Test",
        suspect_hash   = make_work_hash(99),
        timestamp      = datetime.utcnow()
    )


@pytest.fixture
def sample_match_result_negative():
    return MatchResult(
        is_match       = False,
        score          = 0.4123,
        threshold      = 0.85,
        original_hash  = None,
        original_title = None,
        suspect_hash   = make_work_hash(88),
        timestamp      = datetime.utcnow()
    )


@pytest.fixture
def sample_proof(sample_work_hash):
    return Proof(
        id                 = str(uuid.uuid4()),
        suspect_cid        = "QmSuspect001",
        original_cid       = "QmOriginal001",
        report_cid         = "QmReport001",
        evidence_hash      = "a" * 64,
        tx_hash            = "0x" + "b" * 64,
        match_score        = 0.9742,
        original_work_hash = sample_work_hash,
        timestamp          = datetime.utcnow()
    )


@pytest.fixture
def sample_audio_track(sample_work_hash):
    return AudioTrack(
        id               = str(uuid.uuid4()),
        title            = "Oeuvre Test",
        artist           = "Artiste Test",
        file_path        = "test.wav",
        fingerprint_hash = sample_work_hash,
        ipfs_cid         = "QmTest001",
        tx_hash          = "0x" + "c" * 64,
        recipients       = ["0x" + "A" * 40],
        shares           = [100],
        registered_at    = datetime.utcnow()
    )


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURES — MOCKS DES SERVICES EXTERNES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_fingerprint_engine(sample_embedding, sample_work_hash):
    """
    Mock de FingerprintEngine.
    Par défaut retourne un embedding et un hash déterministes.
    """
    mock = MagicMock(spec=FingerprintEngine)
    mock.embedding_to_hash.return_value = sample_work_hash
    mock.model               = MagicMock()   # modèle chargé
    mock.device              = "cpu"
    mock.extract_fingerprint.return_value              = sample_embedding
    mock.extract_fingerprint_from_bytes.return_value   = sample_embedding
    mock.compare_fingerprints.return_value             = 0.9742
    
    return mock


@pytest.fixture
def mock_ipfs_storage():
    """Mock d'IPFSStorage — toujours disponible, CIDs déterministes."""
    mock = MagicMock(spec=IPFSStorage)
    mock.is_available.return_value      = True
    mock.upload_file.return_value       = "QmMockCID001"
    mock.upload_json.return_value       = "QmMockReport001"
    mock.retrieve_file.return_value     = b'{"proof": "data"}'
    mock.verify_integrity.return_value  = True
    mock.get_gateway_url.side_effect    = lambda cid: f"http://localhost:8080/ipfs/{cid}"
    return mock


@pytest.fixture
def mock_blockchain_manager(sample_work_hash):
    """Mock de BlockchainManager — transactions confirmées instantanément."""
    mock = MagicMock(spec=BlockchainManager)
    mock.is_connected.return_value         = True
    mock.verify_registration.return_value  = False   # par défaut non enregistré
    mock.register_work.return_value        = "0x" + "a" * 64
    mock.store_proof.return_value          = ("0x" + "b" * 64, "c" * 64)
    mock.simulate_royalty_payment.return_value = (
        "0x" + "d" * 64,
        [
            {"beneficiary": "0x" + "E" * 40, "amount": 700, "timestamp": 1700000000},
            {"beneficiary": "0x" + "F" * 40, "amount": 300, "timestamp": 1700000000},
        ]
    )
    mock.get_work.return_value = {
        "cid":           "QmTest001",
        "recipients":    ["0x" + "E" * 40, "0x" + "F" * 40],
        "shares":        [70, 30],
        "registered_at": 1700000000
    }
    return mock


@pytest.fixture
def tmp_index_path(tmp_path):
    """Chemin temporaire pour l'index d'empreintes."""
    return tmp_path / "test_fingerprints.json"


@pytest.fixture
def empty_index(tmp_index_path):
    """Index d'empreintes vide."""
    return FingerprintIndex(tmp_index_path)


@pytest.fixture
def populated_index(tmp_index_path, sample_embedding, sample_work_hash):
    """Index avec une empreinte pré-chargée."""
    idx = FingerprintIndex(tmp_index_path)
    idx.add(
        embedding  = sample_embedding,
        title      = "Oeuvre Test",
        artist     = "Artiste Test",
        ipfs_cid   = "QmTest001",
        tx_hash    = "0x" + "a" * 64,
        recipients = ["0x" + "A" * 40],
        shares     = [100]
    )
    return idx


@pytest.fixture
def mock_piracy_detector(
    mock_fingerprint_engine,
    populated_index,
    mock_ipfs_storage,
    mock_blockchain_manager,
    sample_match_result_positive,
    sample_proof
):
    """Mock de PiracyDetector retournant un match positif par défaut."""
    mock = MagicMock(spec=PiracyDetector)
    mock._threshold = 0.85
    mock.analyze_content.return_value  = sample_match_result_positive
    mock.generate_proof.return_value   = sample_proof
    mock.calculate_similarity.return_value = 0.9742
    return mock


# ═══════════════════════════════════════════════════════════════════════════════
# FIXTURE — APPLICATION FASTAPI AVEC DÉPENDANCES MOCKÉES
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def test_client(
    mock_fingerprint_engine,
    populated_index,
    mock_ipfs_storage,
    mock_blockchain_manager,
    mock_piracy_detector
):
    """
    TestClient FastAPI avec toutes les dépendances externes mockées.
    Permet de tester les routes sans Ganache, IPFS, ou modèle GraFPrint.
    """
    from backend.main import app
    import backend.dependencies as deps

    app.dependency_overrides = {
        deps.get_fingerprint_engine: lambda: mock_fingerprint_engine,
        deps.get_ipfs_storage:       lambda: mock_ipfs_storage,
        deps.get_blockchain_manager: lambda: mock_blockchain_manager,
        deps.get_fingerprint_index:  lambda: populated_index,
        deps.get_piracy_detector:    lambda: mock_piracy_detector,
    }

    with TestClient(app, raise_server_exceptions=True) as client:
        yield client

    app.dependency_overrides = {}


@pytest.fixture
def real_engine():
    """
    FingerprintEngine réel (sans modèle GraFPrint — fallback Librosa).
    Utilisé pour les tests unitaires qui nécessitent un vrai traitement audio.
    """
    engine = FingerprintEngine()
    engine.load_grafprint_model()
    return engine