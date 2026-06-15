"""
IPFSStorage — Couche stockage décentralisé.

Deux backends supportés :
  - LOCAL  : daemon IPFS local (port 5001) — développement
  - PINATA : API Pinata cloud              — production (Fly.io)

Le backend est sélectionné automatiquement :
  → Si PINATA_API_KEY est défini dans l'environnement → Pinata
  → Sinon                                             → daemon local
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
    Client IPFS avec basculement automatique local ↔ Pinata.
    """

    PINATA_UPLOAD_URL  = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    PINATA_JSON_URL    = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
    PINATA_GATEWAY     = "https://gateway.pinata.cloud"

    def __init__(self):
        self.api_url     = settings.ipfs_api_url
        self.gateway_url = settings.ipfs_gateway_url
        self._session    = requests.Session()
        self._session.headers.update({"User-Agent": "MusicAntiPiracy/1.0"})

        # ── Détection automatique du backend ─────────────────────────────
        self._use_pinata = bool(
            getattr(settings, "pinata_api_key", None) and
            getattr(settings, "pinata_secret_key", None)
        )

        if self._use_pinata:
            self._pinata_headers = {
                "pinata_api_key":        settings.pinata_api_key,
                "pinata_secret_api_key": settings.pinata_secret_key,
            }
            self.gateway_url = self.PINATA_GATEWAY
            logger.info("IPFSStorage initialisé — backend : Pinata Cloud")
        else:
            logger.info(f"IPFSStorage initialisé — backend : daemon local ({self.api_url})")

    # ─────────────────────────────────────────────────────────────────────
    # UPLOAD
    # ─────────────────────────────────────────────────────────────────────

    def upload_file(self, file_content: bytes, filename: str = "file") -> str:
        """
        Téléverse un fichier sur IPFS et retourne son CID.
        """
        if self._use_pinata:
            return self._pinata_upload_file(file_content, filename)
        return self._local_upload_file(file_content, filename)

    def upload_json(self, data: dict, filename: str = "data.json") -> str:
        """
        Sérialise un dictionnaire en JSON et l'uploade sur IPFS.
        """
        if self._use_pinata:
            return self._pinata_upload_json(data)
        json_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        return self._local_upload_file(json_bytes, filename)

    # ── Backend local ─────────────────────────────────────────────────────

    def _local_upload_file(self, file_content: bytes, filename: str) -> str:
        try:
            response = self._session.post(
                f"{self.api_url}/api/v0/add",
                files  = {"file": (filename, file_content)},
                params = {"pin": "true"},
                timeout= 30
            )
            response.raise_for_status()
            cid = response.json()["Hash"]
            logger.info(f"[local] Fichier uploadé : {cid} ({len(file_content)} bytes)")
            return cid
        except requests.ConnectionError:
            raise RuntimeError(
                "Nœud IPFS inaccessible. Démarrer : ipfs daemon"
            )
        except Exception as e:
            raise RuntimeError(f"Erreur IPFS local upload : {e}")

    # ── Backend Pinata ────────────────────────────────────────────────────

    def _pinata_upload_file(self, file_content: bytes, filename: str) -> str:
        try:
            response = requests.post(
                self.PINATA_UPLOAD_URL,
                headers= self._pinata_headers,
                files  = {"file": (filename, file_content)},
                timeout= 60
            )
            response.raise_for_status()
            cid = response.json()["IpfsHash"]
            logger.info(f"[Pinata] Fichier uploadé : {cid} ({len(file_content)} bytes)")
            return cid
        except requests.HTTPError as e:
            raise RuntimeError(f"Erreur Pinata upload : {e} — {e.response.text}")
        except Exception as e:
            raise RuntimeError(f"Erreur Pinata upload : {e}")

    def _pinata_upload_json(self, data: dict) -> str:
        try:
            response = requests.post(
                self.PINATA_JSON_URL,
                headers= {**self._pinata_headers, "Content-Type": "application/json"},
                json   = {"pinataContent": data},
                timeout= 30
            )
            response.raise_for_status()
            cid = response.json()["IpfsHash"]
            logger.info(f"[Pinata] JSON uploadé : {cid}")
            return cid
        except Exception as e:
            raise RuntimeError(f"Erreur Pinata JSON upload : {e}")

    # ─────────────────────────────────────────────────────────────────────
    # RÉCUPÉRATION
    # ─────────────────────────────────────────────────────────────────────

    def retrieve_file(self, cid: str) -> bytes:
        """
        Récupère le contenu d'un fichier IPFS par son CID.
        En mode Pinata, passe par la gateway publique.
        """
        if self._use_pinata:
            return self._pinata_retrieve(cid)
        return self._local_retrieve(cid)

    def _local_retrieve(self, cid: str) -> bytes:
        try:
            response = self._session.post(
                f"{self.api_url}/api/v0/cat",
                params = {"arg": cid},
                timeout= 30
            )
            response.raise_for_status()
            return response.content
        except requests.HTTPError as e:
            raise RuntimeError(f"CID introuvable sur IPFS local : {cid} ({e})")
        except Exception as e:
            raise RuntimeError(f"Erreur IPFS local retrieve : {e}")

    def _pinata_retrieve(self, cid: str) -> bytes:
        try:
            url = f"{self.PINATA_GATEWAY}/ipfs/{cid}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            logger.info(f"[Pinata] Fichier récupéré : {cid}")
            return response.content
        except Exception as e:
            raise RuntimeError(f"Erreur Pinata retrieve : {e}")

    # ─────────────────────────────────────────────────────────────────────
    # VÉRIFICATION D'INTÉGRITÉ
    # ─────────────────────────────────────────────────────────────────────

    def verify_integrity(self, cid: str, expected_hash: Optional[str] = None) -> bool:
        try:
            content = self.retrieve_file(cid)
            if expected_hash is not None:
                actual_hash = hashlib.sha256(content).hexdigest()
                match = actual_hash == expected_hash
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

    # ─────────────────────────────────────────────────────────────────────
    # UTILITAIRES
    # ─────────────────────────────────────────────────────────────────────

    def get_gateway_url(self, cid: str) -> str:
        """Retourne l'URL publique d'accès au fichier."""
        return f"{self.gateway_url}/ipfs/{cid}"

    def is_available(self) -> bool:
        """Vérifie que le backend IPFS est accessible."""
        if self._use_pinata:
            try:
                r = requests.get(
                    "https://api.pinata.cloud/data/testAuthentication",
                    headers= self._pinata_headers,
                    timeout= 5
                )
                return r.status_code == 200
            except Exception:
                return False
        else:
            try:
                r = self._session.post(
                    f"{self.api_url}/api/v0/id", timeout=5
                )
                return r.status_code == 200
            except Exception:
                return False