"""
Routes FastAPI — Simulation de distribution des redevances.
POST /simulate-royalty
"""
import logging
from fastapi    import APIRouter, HTTPException, Depends
from pydantic   import BaseModel, Field

from backend.core.blockchain_manager import BlockchainManager
from backend.db.fingerprint_index    import FingerprintIndex
from backend.dependencies            import get_blockchain_manager, get_fingerprint_index

router = APIRouter(prefix="/royalty", tags=["Redevances"])
logger = logging.getLogger(__name__)


# ── Schémas ───────────────────────────────────────────────────────────────────

class RoyaltySimulationRequest(BaseModel):
    work_hash:    str = Field(..., description="Hash de l'œuvre enregistrée")
    total_amount: int = Field(..., gt=0, description="Montant fictif total à distribuer")

    model_config = {
        "json_schema_extra": {
            "example": {
                "work_hash":    "a3f5c7b2d1e9...",
                "total_amount": 1000
            }
        }
    }


class PaymentDetail(BaseModel):
    beneficiary: str
    amount:      int
    share:       int


class RoyaltySimulationResponse(BaseModel):
    tx_hash:      str
    work_hash:    str
    total_amount: int
    payments:     list[PaymentDetail]
    message:      str


# ── Route principale ──────────────────────────────────────────────────────────

@router.post(
    "/simulate",
    response_model = RoyaltySimulationResponse,
    summary        = "Simuler la distribution des redevances",
    description    = (
        "Appelle simulateRoyaltyPayment() dans MusicRegistry. "
        "Pour chaque bénéficiaire enregistré, calcule le montant "
        "proportionnel et émet un événement PaymentSimulated on-chain. "
        "Aucun transfert réel n'est effectué."
    )
)
async def simulate_royalty(
    body:       RoyaltySimulationRequest,
    blockchain: BlockchainManager  = Depends(get_blockchain_manager),
    index:      FingerprintIndex   = Depends(get_fingerprint_index),
):
    logger.info(
        f"Simulation redevances : work={body.work_hash[:16]}... "
        f"montant={body.total_amount}"
    )

    # Vérification on-chain
    if not blockchain.verify_registration(body.work_hash):
        raise HTTPException(
            status_code = 404,
            detail      = f"Œuvre introuvable on-chain : {body.work_hash[:16]}..."
        )

    try:
        tx_hash, raw_payments = blockchain.simulate_royalty_payment(
            work_hash    = body.work_hash,
            total_amount = body.total_amount
        )

        # Récupération des parts depuis l'index local
        entry = index.get(body.work_hash)
        shares_map = {}
        if entry:
            for addr, share in zip(entry["recipients"], entry["shares"]):
                shares_map[addr.lower()] = share

        payments = [
            PaymentDetail(
                beneficiary = p["beneficiary"],
                amount      = p["amount"],
                share       = shares_map.get(p["beneficiary"].lower(), 0)
            )
            for p in raw_payments
        ]

        return RoyaltySimulationResponse(
            tx_hash      = tx_hash,
            work_hash    = body.work_hash,
            total_amount = body.total_amount,
            payments     = payments,
            message      = (
                f"Simulation terminée — "
                f"{len(payments)} bénéficiaire(s) | "
                f"Événements PaymentSimulated émis on-chain"
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur simulation redevances : {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))