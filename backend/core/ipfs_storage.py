"""
IPFSStorage — Couche stockage décentralisé.

Gère toutes les interactions avec le nœud IPFS local via son API HTTP :
  - Upload de fichiers (retourne le CID)
  - Récupération de fichiers par CID
  - Vérification d'intégrité

Correspond à la classe IPFSStorage du diagramme de classes.
"""
import json
import logging
import hashlib
from typing import Optional

import requests

from backend.config import settings

logger = logging.getLogger(__name__)


class IPFSStorage:
    """
    Client IPFS utilisant l'API HTTP du daemon local (port 5001).

    L'API IPFS est appelée via requests sur les endpoints :
      POST /api/v0/add        → upload
      POST /api/v0/cat        → download
      POST /api/v0/pin/add    → épingle (empêche garbage collection)
    """

    def __init__(self):
        self.api_url     = settings.ipfs_api_url
        self.gateway_url = settings.ipfs_gateway_url
        self._session    = requests.Session()
        self._session.headers.update({"User-Agent": "MusicAntiPiracy/1.0"})
        logger.info(f"IPFSStorage initialisé — API : {self.api_url}")

    # ── Upload ────────────────────────────────────────────────────────────

    def upload_file(self, file_content: bytes, filename: str = "file") -> str:
        """
        Téléverse un fichier sur IPFS et retourne son CID.

        Parameters
        ----------
        file_content : bytes
            Contenu binaire du fichier
        filename : str
            Nom de fichier pour l'affichage dans IPFS

        Returns
        -------
        str : CID IPFS du fichier (ex: QmXyz...)

        Raises
        ------
        RuntimeError : Si le nœud IPFS est inaccessible ou l'upload échoue
        """
        try:
            response = self._session.post(
                f"{self.api_url}/api/v0/add",
                files   = {"file": (filename, file_content)},
                params  = {"pin": "true"},   # épingle immédiatement
                timeout = 30
            )
            response.raise_for_status()
            cid = response.json()["Hash"]
            logger.info(f"Fichier uploadé sur IPFS : {cid} ({len(file_content)} bytes)")
            return cid

        except requests.ConnectionError:
            raise RuntimeError(
                "Nœud IPFS inaccessible. "
                "Vérifier que le daemon est démarré : ipfs daemon"
            )
        except Exception as e:
            raise RuntimeError(f"Erreur IPFS upload : {e}")

    def upload_json(self, data: dict, filename: str = "data.json") -> str:
        """
        Sérialise un dictionnaire en JSON et l'uploade sur IPFS.

        Utilisé pour les rapports forensiques et les métadonnées.
        """
        json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        return self.upload_file(json_bytes, filename)

    # ── Récupération ──────────────────────────────────────────────────────

    def retrieve_file(self, cid: str) -> bytes:
        """
        Récupère le contenu d'un fichier IPFS par son CID.

        Parameters
        ----------
        cid : str
            Content Identifier IPFS

        Returns
        -------
        bytes : Contenu binaire du fichier

        Raises
        ------
        RuntimeError : Si le CID est introuvable ou le nœud inaccessible
        """
        try:
            response = self._session.post(
                f"{self.api_url}/api/v0/cat",
                params  = {"arg": cid},
                timeout = 30
            )
            response.raise_for_status()
            logger.info(f"Fichier récupéré depuis IPFS : {cid}")
            return response.content

        except requests.HTTPError as e:
            raise RuntimeError(f"CID introuvable sur IPFS : {cid} ({e})")
        except Exception as e:
            raise RuntimeError(f"Erreur IPFS retrieve : {e}")

    # ── Vérification d'intégrité ──────────────────────────────────────────

    def verify_integrity(self, cid: str, expected_hash: Optional[str] = None) -> bool:
        """
        Vérifie qu'un CID IPFS est accessible et que son contenu
        n'a pas été altéré.

        Si expected_hash est fourni, compare le SHA-256 du contenu
        récupéré avec la valeur attendue.

        Parameters
        ----------
        cid           : str           CID IPFS à vérifier
        expected_hash : str, optional SHA-256 attendu du contenu

        Returns
        -------
        bool : True si le fichier est accessible et intègre
        """
        try:
            content = self.retrieve_file(cid)

            if expected_hash is not None:
                actual_hash = hashlib.sha256(content).hexdigest()
                match       = actual_hash == expected_hash
                if not match:
                    logger.warning(
                        f"Intégrité compromise pour {cid} : "
                        f"attendu {expected_hash[:16]}..., "
                        f"obtenu  {actual_hash[:16]}..."
                    )
                return match

            return True

        except RuntimeError:
            return False

    # ── Utilitaire ────────────────────────────────────────────────────────

    def get_gateway_url(self, cid: str) -> str:
        """Retourne l'URL publique d'accès au fichier via la gateway IPFS."""
        return f"{self.gateway_url}/ipfs/{cid}"

    def is_available(self) -> bool:
        """Vérifie que le daemon IPFS est accessible."""
        try:
            r = self._session.post(
                f"{self.api_url}/api/v0/id",
                timeout=5
            )
            return r.status_code == 200
        except Exception:
            return False