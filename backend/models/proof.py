"""
Modèle de données Proof.
Représente la preuve technique d'une infraction.
Correspond à la classe Proof du diagramme de classes.
"""
from pydantic import BaseModel, Field
from typing   import Optional
from datetime import datetime


class Proof(BaseModel):
    """Preuve technique d'une infraction, certifiée sur IPFS et blockchain."""
    id:           str            = Field(...,  description="Identifiant unique de la preuve")
    suspect_cid:  str            = Field(...,  description="CID IPFS du fichier audio suspect")
    original_cid: str            = Field(...,  description="CID IPFS de l'œuvre originale")
    report_cid:   str            = Field(...,  description="CID IPFS du rapport forensique")
    evidence_hash: Optional[str] = Field(None, description="Hash de preuve retourné par le smart contract")
    tx_hash:      Optional[str]  = Field(None, description="Hash de transaction blockchain de certification")
    match_score:  float          = Field(...,  description="Score de similarité ayant déclenché la preuve")
    original_work_hash: str      = Field(...,  description="Hash de l'œuvre originale dans MusicRegistry")
    timestamp:    datetime       = Field(default_factory=datetime.utcnow)

    def generate_dmca_rapport(self) -> str:
        """
        Génère un rapport forensique structuré exploitable dans
        une procédure de retrait DMCA.
        """
        return (
            f"=== RAPPORT FORENSIQUE DE PIRATERIE ===\n"
            f"Date              : {self.timestamp.isoformat()}\n"
            f"ID preuve         : {self.id}\n"
            f"Score similarité  : {self.match_score:.4f}\n"
            f"Œuvre originale   : {self.original_work_hash}\n"
            f"CID original      : {self.original_cid}\n"
            f"CID suspect       : {self.suspect_cid}\n"
            f"CID rapport       : {self.report_cid}\n"
            f"Hash preuve chain : {self.evidence_hash}\n"
            f"Tx blockchain     : {self.tx_hash}\n"
            f"=======================================\n"
        )