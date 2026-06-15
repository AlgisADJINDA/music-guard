"""
Configuration centralisée du backend.
Toutes les valeurs sont lues depuis le fichier .env à la racine du projet.
"""
from pydantic_settings import BaseSettings
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):

    # ── Blockchain ────────────────────────────────────────────────────────
    ganache_url:          str   = "http://127.0.0.1:7545"
    deployer_private_key: str   = ""

    # ── IPFS ──────────────────────────────────────────────────────────────
    ipfs_api_url:     str = "http://127.0.0.1:5001"
    ipfs_gateway_url: str = "http://127.0.0.1:8080"

    # ── Backend ───────────────────────────────────────────────────────────
    backend_host: str   = "0.0.0.0"
    backend_port: int   = 8000
    debug:        bool  = True

    # ── Détection ─────────────────────────────────────────────────────────
    detection_threshold: float = 0.85

    # ── GraFPrint ─────────────────────────────────────────────────────────
    grafp_model_path: Path = PROJECT_ROOT / "model" / "model_tc_29_best.pth"

    # ── Chemins internes ──────────────────────────────────────────────────
    # Racine du projet (2 niveaux au-dessus de backend/)
    project_root:     Path = Path(__file__).parent.parent
    grafp_root:       Path = Path(__file__).parent.parent / "grafp"
    deployment_json:  Path = Path(__file__).parent / "db" / "deployment.json"
    fingerprint_db:   Path = Path(__file__).parent / "db" / "fingerprints.json"

    class Config:
        env_file     = "../.env"
        env_file_encoding = "utf-8"
        extra        = "ignore"


# Instance unique importée partout dans le projet
settings = Settings()