"""
Modèle de données AudioTrack.
Représente une œuvre musicale enregistrée dans le système.
Correspond à la classe AudioTrack du diagramme de classes.
"""
from pydantic   import BaseModel, Field
from typing     import Optional
from datetime   import datetime


class AudioTrackCreate(BaseModel):
    """Schéma d'entrée pour l'enregistrement d'une nouvelle œuvre."""
    title:      str            = Field(..., description="Titre de l'œuvre")
    artist:     str            = Field(..., description="Nom de l'artiste principal")
    recipients: list[str]      = Field(..., description="Adresses Ethereum des ayants droit")
    shares:     list[int]      = Field(..., description="Parts en % (doit sommer à 100)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "title":      "Ma Chanson",
                "artist":     "Artiste A",
                "recipients": ["0xABC...123", "0xDEF...456"],
                "shares":     [70, 30]
            }
        }
    }


class AudioTrack(BaseModel):
    """Représentation complète d'une œuvre après enregistrement."""
    id:               str
    title:            str
    artist:           str
    file_path:        Optional[str]  = None
    fingerprint_hash: str            = Field(..., description="Hash SHA-256 de l'empreinte GraFPrint")
    ipfs_cid:         str            = Field(..., description="CID IPFS de l'empreinte complète")
    tx_hash:          str            = Field(..., description="Hash de transaction blockchain")
    recipients:       list[str]
    shares:           list[int]
    registered_at:    datetime       = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}