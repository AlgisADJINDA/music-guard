"""
Injection de dépendances FastAPI.
Instancie et met en cache les singletons partagés entre les routes.
"""
from functools import lru_cache
from backend.config import settings

from backend.core.fingerprint_engine import FingerprintEngine
from backend.core.ipfs_storage       import IPFSStorage
from backend.core.blockchain_manager import BlockchainManager
from backend.core.piracy_detector    import PiracyDetector
from backend.db.fingerprint_index    import FingerprintIndex

@lru_cache(maxsize=1)
def get_fingerprint_engine() -> FingerprintEngine:
    engine = FingerprintEngine()
    engine.load_grafprint_model()
    return engine

@lru_cache(maxsize=1)
def get_ipfs_storage() -> IPFSStorage:
    return IPFSStorage()

@lru_cache(maxsize=1)
def get_blockchain_manager() -> BlockchainManager:
    manager = BlockchainManager()
    manager.connect_web3()
    return manager

@lru_cache(maxsize=1)
def get_fingerprint_index() -> FingerprintIndex:
    return FingerprintIndex(settings.fingerprint_db)

@lru_cache(maxsize=1)
def get_piracy_detector() -> PiracyDetector:
    return PiracyDetector(
        fingerprinter = get_fingerprint_engine(),
        index         = get_fingerprint_index(),
        ipfs          = get_ipfs_storage(),
        blockchain    = get_blockchain_manager()
    )
