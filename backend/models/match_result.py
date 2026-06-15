"""
Modèle de données MatchResult.
Objet valeur transportant le résultat d'une comparaison d'empreintes.
Correspond à la classe MatchResult du diagramme de classes.
"""
from pydantic import BaseModel, Field
from typing   import Optional
from datetime import datetime


class MatchResult(BaseModel):
    """Résultat d'une comparaison d'empreinte audio contre la base de référence."""
    is_match:      bool             = Field(...,  description="True si similarité > seuil")
    score:         float            = Field(...,  ge=0.0, le=1.0,
                                           description="Score de similarité [0.0 – 1.0]")
    threshold:     float            = Field(0.85, description="Seuil utilisé pour la décision")
    original_hash: Optional[str]    = Field(None, description="Hash de l'œuvre originale correspondante")
    original_title: Optional[str]   = Field(None, description="Titre de l'œuvre originale")
    suspect_hash:  Optional[str]    = Field(None, description="Hash calculé sur le fichier suspect")
    timestamp:     datetime         = Field(default_factory=datetime.utcnow)

    @property
    def confidence_label(self) -> str:
        """Étiquette humaine du niveau de confiance."""
        if self.score >= 0.95:
            return "TRÈS HAUTE"
        elif self.score >= 0.85:
            return "HAUTE"
        elif self.score >= 0.70:
            return "MOYENNE"
        else:
            return "FAIBLE"