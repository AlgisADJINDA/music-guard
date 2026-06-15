"""
Routes FastAPI — Détection d'une copie illicite.
POST /analyze
"""
import logging
from fastapi           import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic          import BaseModel
from typing            import Optional

from backend.core.piracy_detector    import PiracyDetector
from backend.models.match_result     import MatchResult
from backend.models.proof            import Proof
from backend.models.takedown_request import TakedownRequest, TakedownStatus
from backend.dependencies            import get_piracy_detector
import uuid, requests as _requests
from backend.config import settings

router = APIRouter(prefix="/analyze", tags=["Détection"])
logger = logging.getLogger(__name__)

# ── Schémas de réponse ────────────────────────────────────────────────────────

class DetectionResponse(BaseModel):
    match:            MatchResult
    proof:            Optional[Proof]           = None
    takedown_request: Optional[TakedownRequest] = None
    message:          str


# ── Route principale ──────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model = DetectionResponse,
    summary        = "Analyser un fichier audio suspect",
    description    = (
        "Extrait l'empreinte GraFPrint du fichier suspect, "
        "la compare aux empreintes de référence, et si une correspondance "
        "est détectée, génère une preuve certifiée on-chain et "
        "simule une notification de retrait DMCA via webhook."
    )
)
async def analyze_audio(
    file:     UploadFile   = File(..., description="Fichier audio suspect WAV ou MP3"),
    detector: PiracyDetector = Depends(get_piracy_detector),
):
    audio_bytes = await file.read()

    if len(audio_bytes) == 0:
        raise HTTPException(status_code=422, detail="Fichier audio vide")

    logger.info(
        f"Analyse suspect : {file.filename} "
        f"({len(audio_bytes)} bytes)"
    )

    try:
        # ── Étape 2 : Détection ───────────────────────────────────────────
        match = detector.analyze_content(audio_bytes)

        if not match.is_match:
            return DetectionResponse(
                match   = match,
                message = (
                    f"Aucune correspondance détectée. "
                    f"Score : {match.score:.4f} < seuil {match.threshold}"
                )
            )

        # ── Étape 3 : Génération de preuve ────────────────────────────────
        logger.info(
            f"Correspondance détectée ! "
            f"Score : {match.score:.4f} | "
            f"Œuvre : {match.original_title}"
        )

        proof = detector.generate_proof(match, audio_bytes)

        # ── Étape 4 (simulée) : Notification DMCA via webhook ─────────────
        takedown = _simulate_dmca_takedown(proof, match)

        return DetectionResponse(
            match            = match,
            proof            = proof,
            takedown_request = takedown,
            message          = (
                f"PIRATERIE DÉTECTÉE — "
                f"Œuvre : {match.original_title} | "
                f"Score : {match.score:.4f} | "
                f"Preuve certifiée on-chain : {proof.tx_hash[:16]}..."
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse : {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Simulation DMCA ───────────────────────────────────────────────────────────

def _simulate_dmca_takedown(proof: Proof, match: MatchResult) -> TakedownRequest:
    """
    Simule l'envoi d'une notification DMCA via webhook.site.
    Dans un déploiement réel, ce webhook serait remplacé par
    l'API YouTube Content ID, Spotify, TikTok, etc.
    """
    takedown_id = str(uuid.uuid4())

    payload = {
        "takedown_id":    takedown_id,
        "evidence_cid":   proof.report_cid,
        "evidence_hash":  proof.evidence_hash,
        "tx_hash":        proof.tx_hash,
        "match_score":    proof.match_score,
        "original_work":  proof.original_work_hash,
        "timestamp":      proof.timestamp.isoformat(),
        "dmca_notice":    (
            "This content matches a copyrighted work registered "
            "on the blockchain. Please remove it immediately."
        )
    }

    webhook_url      = "https://webhook.site/your-unique-id"  # ← Remplacer
    webhook_response = None
    status           = TakedownStatus.SIMULATED

    try:
        r = _requests.post(webhook_url, json=payload, timeout=5)
        webhook_response = {"status_code": r.status_code, "body": r.text[:200]}
        status           = TakedownStatus.SENT
        logger.info(f"Webhook DMCA envoyé : {r.status_code}")
    except Exception as e:
        logger.warning(f"Webhook DMCA simulé localement (inaccessible : {e})")
        webhook_response = {"simulated": True, "payload": payload}

    return TakedownRequest(
        id               = takedown_id,
        proof_hash       = proof.evidence_hash or "",
        proof_cid        = proof.report_cid,
        tx_hash          = proof.tx_hash,
        status           = status,
        webhook_response = webhook_response
    )