"""
PiracyDetector — Chef d'orchestre de la détection.

Coordonne FingerprintEngine, FingerprintIndex, IPFSStorage et
BlockchainManager pour exécuter le flux complet de détection de piraterie.

Correspond à la classe PiracyDetector du diagramme de classes.
"""
import uuid
import json
import logging
from datetime import datetime

from backend.config                   import settings
from backend.core.fingerprint_engine  import FingerprintEngine
from backend.core.ipfs_storage        import IPFSStorage
from backend.core.blockchain_manager  import BlockchainManager
from backend.db.fingerprint_index     import FingerprintIndex
from backend.models.match_result      import MatchResult
from backend.models.proof             import Proof

logger = logging.getLogger(__name__)


class PiracyDetector:
    """
    Orchestrateur du flux de détection de piraterie.

    Attributs privés
    ----------------
    _fingerprinter : FingerprintEngine   Moteur IA (GraFPrint + Librosa)
    _threshold     : float               Seuil de décision (défaut : 0.85)
    _index         : FingerprintIndex    Base des empreintes de référence
    _ipfs          : IPFSStorage         Couche de stockage IPFS
    _blockchain    : BlockchainManager   Couche blockchain
    """

    def __init__(
        self,
        fingerprinter: FingerprintEngine,
        index:         FingerprintIndex,
        ipfs:          IPFSStorage,
        blockchain:    BlockchainManager,
        threshold:     float = None
    ):
        self._fingerprinter = fingerprinter
        self._index         = index
        self._ipfs          = ipfs
        self._blockchain    = blockchain
        self._threshold     = threshold or settings.detection_threshold

        logger.info(
            f"PiracyDetector initialisé | "
            f"seuil : {self._threshold} | "
            f"empreintes indexées : {self._index.count()}"
        )

    # ── Analyse d'un contenu suspect ──────────────────────────────────────

    def analyze_content(self, audio_bytes: bytes) -> MatchResult:
        """
        Analyse un fichier audio suspect et détermine s'il correspond
        à une œuvre protégée enregistrée dans le système.

        Flux :
            audio_bytes
              → FingerprintEngine.extract_fingerprint_from_bytes()
              → FingerprintIndex.search()
              → MatchResult (is_match, score, original_hash...)

        Parameters
        ----------
        audio_bytes : bytes
            Contenu binaire du fichier audio suspect (WAV ou MP3)

        Returns
        -------
        MatchResult : Résultat de la comparaison
        """
        logger.info(f"Analyse d'un contenu suspect ({len(audio_bytes)} bytes)...")

        # 1. Extraction de l'empreinte du fichier suspect
        suspect_embedding = self._fingerprinter.extract_fingerprint_from_bytes(audio_bytes)
        suspect_hash      = FingerprintEngine.embedding_to_hash(suspect_embedding)

        # 2. Recherche dans l'index des empreintes de référence
        if self._index.count() == 0:
            logger.warning("Index vide — aucune œuvre enregistrée, détection impossible")
            return MatchResult(
                is_match      = False,
                score         = 0.0,
                threshold     = self._threshold,
                suspect_hash  = suspect_hash
            )

        results = self._index.search(suspect_embedding, top_k=1)

        if not results:
            return MatchResult(
                is_match     = False,
                score        = 0.0,
                threshold    = self._threshold,
                suspect_hash = suspect_hash
            )

        best    = results[0]
        score   = best["score"]
        is_match = score >= self._threshold

        logger.info(
            f"Résultat comparaison : score={score:.4f} | "
            f"seuil={self._threshold} | "
            f"match={'OUI' if is_match else 'NON'}"
        )

        return MatchResult(
            is_match       = is_match,
            score          = score,
            threshold      = self._threshold,
            original_hash  = best["work_hash"] if is_match else None,
            original_title = best.get("title")  if is_match else None,
            suspect_hash   = suspect_hash,
            timestamp      = datetime.utcnow()
        )

    def calculate_similarity(self, fp1_hex: str, fp2_hex: str) -> float:
        """
        Calcule la similarité entre deux empreintes identifiées par leur hash.
        Utile pour les comparaisons directes depuis le dashboard.
        """
        entry1 = self._index.get(fp1_hex)
        entry2 = self._index.get(fp2_hex)

        if not entry1 or not entry2:
            raise ValueError("Un ou plusieurs hash introuvables dans l'index")

        import numpy as np
        emb1 = np.array(entry1["embedding"], dtype=np.float32)
        emb2 = np.array(entry2["embedding"], dtype=np.float32)

        return self._fingerprinter.compare_fingerprints(emb1, emb2)

    # ── Génération de preuve ──────────────────────────────────────────────

    def generate_proof(self, match: MatchResult, suspect_audio_bytes: bytes) -> Proof:
        """
        Génère une preuve certifiée à partir d'un MatchResult positif.

        Flux :
            MatchResult (is_match=True)
              → Constitution du dossier de preuve (JSON)
              → IPFSStorage.upload_file(suspect_audio)   → suspect_cid
              → IPFSStorage.upload_json(rapport)         → report_cid
              → BlockchainManager.store_proof()          → tx_hash, evidence_hash
              → Proof

        Parameters
        ----------
        match              : MatchResult  Résultat de détection positif
        suspect_audio_bytes : bytes        Fichier audio suspect original

        Returns
        -------
        Proof : Preuve certifiée on-chain et sur IPFS

        Raises
        ------
        ValueError  : Si match.is_match est False
        RuntimeError : Si IPFS ou blockchain sont inaccessibles
        """
        if not match.is_match:
            raise ValueError(
                "generate_proof() appelé sur un MatchResult négatif. "
                "Vérifier que is_match=True avant d'appeler cette méthode."
            )

        proof_id = str(uuid.uuid4())
        logger.info(f"Génération de la preuve {proof_id}...")

        # 1. Récupération du CID original depuis l'index
        original_entry = self._index.get(match.original_hash)
        original_cid   = original_entry["ipfs_cid"] if original_entry else ""

        # 2. Upload du fichier suspect sur IPFS
        suspect_cid = self._ipfs.upload_file(
            suspect_audio_bytes,
            filename=f"suspect_{proof_id}.audio"
        )
        logger.info(f"Fichier suspect uploadé : {suspect_cid}")

        # 3. Constitution et upload du rapport forensique JSON
        forensic_report = {
            "proof_id":          proof_id,
            "generated_at":      datetime.utcnow().isoformat(),
            "match_score":       match.score,
            "threshold":         match.threshold,
            "original_work":     match.original_hash,
            "original_title":    match.original_title,
            "suspect_hash":      match.suspect_hash,
            "suspect_cid":       suspect_cid,
            "original_cid":      original_cid,
            "confidence_label":  match.confidence_label
        }

        report_cid = self._ipfs.upload_json(
            forensic_report,
            filename=f"report_{proof_id}.json"
        )
        logger.info(f"Rapport forensique uploadé : {report_cid}")

        # 4. Certification on-chain via MusicRegistry.certifyInfringement()
        tx_hash, evidence_hash = self._blockchain.store_proof(
            evidence_cid = report_cid,
            work_hash    = match.original_hash
        )
        logger.info(
            f"Preuve certifiée on-chain | "
            f"tx : {tx_hash[:16]}... | "
            f"evidence : {evidence_hash[:16]}..."
        )

        proof = Proof(
            id                = proof_id,
            suspect_cid       = suspect_cid,
            original_cid      = original_cid,
            report_cid        = report_cid,
            evidence_hash     = evidence_hash,
            tx_hash           = tx_hash,
            match_score       = match.score,
            original_work_hash = match.original_hash,
            timestamp         = datetime.utcnow()
        )

        logger.info(f"Preuve {proof_id} générée avec succès")
        return proof