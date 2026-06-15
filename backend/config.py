"""
Configuration centralisée du backend.
Toutes les valeurs sont lues depuis le fichier .env à la racine du projet.
"""
from pydantic_settings import BaseSettings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):

    # ── Blockchain ────────────────────────────────────────────────────────
    # En local     : http://127.0.0.1:7545  (Ganache)
    # En production: https://rpc-amoy.polygon.technology
    ganache_url:          str = "http://127.0.0.1:7545"
    deployer_private_key: str = ""

    # ── IPFS / Pinata ────────────────────────────────────────────────────
    # En local     : daemon IPFS sur port 5001 (pinata_api_key vide)
    # En production: clés Pinata renseignées → bascule automatique
    ipfs_api_url:      str = "http://127.0.0.1:5001"
    ipfs_gateway_url:  str = "http://127.0.0.1:8080"
    pinata_api_key:    str = ""
    pinata_secret_key: str = ""

    # ── Backend ───────────────────────────────────────────────────────────
    backend_host: str  = "0.0.0.0"
    backend_port: int  = 8000
    debug:        bool = True

    # ── Détection ─────────────────────────────────────────────────────────
    detection_threshold: float = 0.85

    # ── GraFPrint ─────────────────────────────────────────────────────────
    grafp_model_path: Path = PROJECT_ROOT / "model" / "model_tc_29_best.pth"

    # ── Chemins internes ──────────────────────────────────────────────────
    project_root:    Path = PROJECT_ROOT
    grafp_root:      Path = PROJECT_ROOT / "grafp"
    deployment_json: Path = PROJECT_ROOT / "backend" / "db" / "deployment.json"
    fingerprint_db:  Path = PROJECT_ROOT / "backend" / "db" / "fingerprints.json"

    class Config:
        env_file          = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"
        extra             = "ignore"


settings = Settings()