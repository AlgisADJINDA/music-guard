"""
Point d'entrée FastAPI — Music Anti-Piracy System
Mémoire : L'IA et la Blockchain au service de la lutte contre la piraterie musicale
Auteur  : ADJINDA Adékin Olatobi Algis | Directeur : Pr. Eugène EZIN
"""
import logging
from contextlib import asynccontextmanager

from fastapi             import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses   import JSONResponse

from backend.config      import settings
from backend.api         import routes_register, routes_detection, routes_royalty
from backend.dependencies import (
    get_fingerprint_engine,
    get_ipfs_storage,
    get_blockchain_manager,
    get_fingerprint_index
)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialise les services au démarrage et libère les ressources à l'arrêt.
    Ordre : FingerprintIndex → FingerprintEngine → IPFSStorage → BlockchainManager
    """
    logger.info("=" * 60)
    logger.info("  Démarrage Music Anti-Piracy Backend")
    logger.info("=" * 60)

    # Index des empreintes
    index = get_fingerprint_index()
    logger.info(f"✅ FingerprintIndex    | {index.count()} empreintes")

    # Modèle GraFPrint
    engine = get_fingerprint_engine()
    status = "avec modèle GraFPrint" if engine.model else "fallback Librosa"
    logger.info(f"✅ FingerprintEngine   | {status}")

    # IPFS
    ipfs = get_ipfs_storage()
    ipfs_ok = ipfs.is_available()
    logger.info(f"{'✅' if ipfs_ok else '⚠️ '} IPFSStorage       | {'connecté' if ipfs_ok else 'DAEMON HORS LIGNE — démarrer : ipfs daemon'}")

    # Blockchain
    try:
        bc = get_blockchain_manager()
        logger.info(f"✅ BlockchainManager  | connecté à {settings.ganache_url}")
    except Exception as e:
        logger.warning(f"⚠️  BlockchainManager  | {e}")

    logger.info("=" * 60)
    logger.info(f"  API disponible sur http://{settings.backend_host}:{settings.backend_port}")
    logger.info(f"  Docs : http://{settings.backend_host}:{settings.backend_port}/docs")
    logger.info("=" * 60)

    yield  # ← L'application tourne ici

    logger.info("Arrêt du backend — libération des ressources")


# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title       = "Music Anti-Piracy API",
    description = (
        "Pipeline IA + Blockchain pour la détection de piraterie musicale "
        "et la simulation de distribution des redevances.\n\n"
        "**Flux 1** : `POST /register` → `POST /analyze`\n\n"
        "**Flux 2** : `POST /royalty/simulate`"
    ),
    version     = "1.0.0",
    lifespan    = lifespan
)

# ── CORS (Vue.js frontend sur port 5173) ──────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(routes_register.router)
app.include_router(routes_detection.router)
app.include_router(routes_royalty.router)


@app.get("/", tags=["Santé"])
async def root():
    return {
        "status":  "running",
        "service": "Music Anti-Piracy API",
        "docs":    "/docs"
    }


@app.get("/health", tags=["Santé"])
async def health():
    """Vérifie l'état de tous les services."""
    ipfs       = get_ipfs_storage()
    blockchain = get_blockchain_manager()
    index      = get_fingerprint_index()
    engine     = get_fingerprint_engine()

    return {
        "ipfs":         ipfs.is_available(),
        "blockchain":   blockchain.is_connected(),
        "model_loaded": engine.model is not None,
        "works_indexed": index.count()
    }


# ── Lancement direct ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host    = settings.backend_host,
        port    = settings.backend_port,
        reload  = settings.debug
    )