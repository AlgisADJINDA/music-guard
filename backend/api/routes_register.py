"""
Routes FastAPI — Enregistrement d'une œuvre.
POST /register
"""
import uuid
import logging
from fastapi            import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses  import JSONResponse
from typing             import Annotated

from backend.core.fingerprint_engine import FingerprintEngine
from backend.core.ipfs_storage       import IPFSStorage
from backend.core.blockchain_manager import BlockchainManager
from backend.db.fingerprint_index    import FingerprintIndex
from backend.models.audio_track      import AudioTrack, AudioTrackCreate
from backend.dependencies            import (
    get_fingerprint_engine,
    get_ipfs_storage,
    get_blockchain_manager,
    get_fingerprint_index
)

router = APIRouter(prefix="/register", tags=["Enregistrement"])
logger = logging.getLogger(__name__)


@router.post(
    "/",
    response_model  = AudioTrack,
    summary         = "Enregistrer une œuvre musicale",
    description     = (
        "Extrait l'empreinte GraFPrint du fichier audio, "
        "la stocke sur IPFS, et certifie l'enregistrement "
        "dans le smart contract MusicRegistry on-chain."
    )
)
async def register_work(
    file:       UploadFile                  = File(...,  description="Fichier audio WAV ou MP3"),
    title:      str                         = Form(...,  description="Titre de l'œuvre"),
    artist:     str                         = Form(...,  description="Artiste principal"),
    recipients: str                         = Form(...,  description='Adresses Ethereum JSON ex: ["0xABC","0xDEF"]'),
    shares:     str                         = Form(...,  description='Parts en % JSON ex: [70,30]'),
    engine:     FingerprintEngine           = Depends(get_fingerprint_engine),
    ipfs:       IPFSStorage                 = Depends(get_ipfs_storage),
    blockchain: BlockchainManager           = Depends(get_blockchain_manager),
    index:      FingerprintIndex            = Depends(get_fingerprint_index),
):
    import json as _json

    # ── Validation des entrées ────────────────────────────────────────────
    if file.content_type not in ("audio/wav", "audio/mpeg", "audio/mp3",
                                  "audio/x-wav", "application/octet-stream"):
        raise HTTPException(
            status_code = 422,
            detail      = f"Format audio non supporté : {file.content_type}. "
                          f"Utiliser WAV ou MP3."
        )

    try:
        recipients_list: list[str] = _json.loads(recipients)
        shares_list:     list[int] = _json.loads(shares)
    except _json.JSONDecodeError:
        raise HTTPException(
            status_code = 422,
            detail      = "recipients et shares doivent être des tableaux JSON valides"
        )

    if sum(shares_list) != 100:
        raise HTTPException(
            status_code = 422,
            detail      = f"La somme des parts doit être égale à 100 (actuelle : {sum(shares_list)})"
        )

    # ── Lecture du fichier ────────────────────────────────────────────────
    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=422, detail="Fichier audio vide")

    logger.info(f"Enregistrement : {title} — {artist} ({len(audio_bytes)} bytes)")

    try:
        # ── Étape 1a : Extraction de l'empreinte GraFPrint ────────────────
        embedding    = engine.extract_fingerprint_from_bytes(audio_bytes)
        work_hash    = engine.embedding_to_hash(embedding)

        # Vérification doublon
        if index.exists(work_hash):
            raise HTTPException(
                status_code = 409,
                detail      = f"Œuvre déjà enregistrée (hash : {work_hash[:16]}...)"
            )

        # ── Étape 1b : Upload IPFS ────────────────────────────────────────
        ipfs_cid = ipfs.upload_file(audio_bytes, filename=f"{work_hash[:8]}.audio")

        # ── Étape 1c : Enregistrement on-chain ───────────────────────────
        tx_hash = blockchain.register_work(
            work_hash  = work_hash,
            cid        = ipfs_cid,
            recipients = recipients_list,
            shares     = shares_list
        )

        # ── Étape 1d : Mise à jour de l'index local ───────────────────────
        index.add(
            embedding  = embedding,
            title      = title,
            artist     = artist,
            ipfs_cid   = ipfs_cid,
            tx_hash    = tx_hash,
            recipients = recipients_list,
            shares     = shares_list
        )

        return AudioTrack(
            id               = str(uuid.uuid4()),
            title            = title,
            artist           = artist,
            file_path        = file.filename,
            fingerprint_hash = work_hash,
            ipfs_cid         = ipfs_cid,
            tx_hash          = tx_hash,
            recipients       = recipients_list,
            shares           = shares_list
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur enregistrement : {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))