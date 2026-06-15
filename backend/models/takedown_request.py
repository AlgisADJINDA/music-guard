"""
Modèle de données TakedownRequest.
Représente l'acte juridique de retrait (notification DMCA).
Correspond à la classe TakedownRequest du diagramme de classes.
"""
from pydantic import BaseModel, Field
from typing   import Optional
from datetime import datetime
from enum     import Enum


class TakedownStatus(str, Enum):
    PENDING  = "PENDING"   # Générée, en attente d'envoi
    SENT     = "SENT"      # Envoyée à la plateforme tierce
    SIMULATED = "SIMULATED" # Simulée via webhook (prototype)
    CONFIRMED = "CONFIRMED" # Confirmée par la plateforme


class TakedownRequest(BaseModel):
    """Demande de retrait DMCA générée à partir d'une preuve certifiée."""
    id:              str                = Field(...,  description="Identifiant unique de la demande")
    infringing_url:  Optional[str]      = Field(None, description="URL de la plateforme hébergeant le contenu illicite")
    proof_hash:      str                = Field(...,  description="Hash de la preuve certifiée blockchain")
    proof_cid:       str                = Field(...,  description="CID IPFS du rapport forensique")
    tx_hash:         Optional[str]      = Field(None, description="Hash de transaction de certification on-chain")
    status:          TakedownStatus     = Field(TakedownStatus.PENDING)
    timestamp:       datetime           = Field(default_factory=datetime.utcnow)
    webhook_response: Optional[dict]    = Field(None, description="Réponse du webhook de simulation")

    def generate_dmca_notice(self) -> str:
        """
        Génère la notification DMCA formelle à destination
        d'une plateforme tierce.
        """
        return (
            f"=== NOTIFICATION DMCA DE RETRAIT ===\n"
            f"Date              : {self.timestamp.isoformat()}\n"
            f"ID demande        : {self.id}\n"
            f"URL infreignante  : {self.infringing_url or 'Non spécifiée'}\n"
            f"Preuve on-chain   : {self.proof_hash}\n"
            f"Rapport IPFS      : {self.proof_cid}\n"
            f"Transaction       : {self.tx_hash or 'En attente'}\n"
            f"Statut            : {self.status.value}\n"
            f"=====================================\n"
            f"Ce document constitue une preuve d'infraction certifiée\n"
            f"par la blockchain. Le CID IPFS permet de vérifier\n"
            f"l'intégrité du dossier forensique à tout moment.\n"
        )