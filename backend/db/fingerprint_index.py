"""
FingerprintIndex — Index de recherche par similarité (FAISS).

Remplace la recherche séquentielle O(n) par une recherche approximative
FAISS en O(log n) ou O(1), permettant le passage à des catalogues de
plusieurs millions d'œuvres.

Architecture de stockage :
  fingerprints.json      → métadonnées des œuvres (titre, artiste, CID, etc.)
  fingerprints.faiss     → index binaire FAISS (vecteurs d'empreintes)
  fingerprints_ids.json  → mapping FAISS ID (int) → work_hash (str)

Sélection automatique du type d'index selon la taille du catalogue :
  < INDEX_FLAT_THRESHOLD  → IndexFlatIP  (exact,     O(n))
  < INDEX_IVF_THRESHOLD   → IndexIVFFlat (approx.,   O(√n))
  ≥ INDEX_IVF_THRESHOLD   → IndexIVFPQ   (approx. compressé, O(1))
"""
import json
import logging
import numpy  as np
import faiss
from pathlib   import Path
from typing    import Optional
from datetime  import datetime

logger = logging.getLogger(__name__)

# ── Seuils de sélection du type d'index ──────────────────────────────────────
INDEX_FLAT_THRESHOLD = 1_000       # < 1 000 œuvres  → recherche exacte
INDEX_IVF_THRESHOLD  = 100_000     # < 100 000 œuvres → IVFFlat
# ≥ 100 000 œuvres → IVFPQ (compressé)

# ── Hyperparamètres FAISS ─────────────────────────────────────────────────────
IVF_NLIST        = 64    # Nombre de clusters IVF (nlist)
IVF_NPROBE       = 10    # Nombre de clusters inspectés à la recherche
IVFPQ_M          = 16    # Nombre de sous-quantificateurs PQ (divise la dim)
IVFPQ_NBITS      = 8     # Bits par sous-quantificateur


class FingerprintIndex:
    """
    Index FAISS pour la recherche d'empreintes audio par similarité cosinus.

    Pour des vecteurs L2-normalisés (norme = 1), la similarité cosinus est
    équivalente au produit scalaire. FAISS IndexFlatIP (Inner Product) est
    donc utilisé, évitant toute conversion supplémentaire.

    Paramètres publics
    ------------------
    dim : int
        Dimension des vecteurs d'empreinte (128 pour GraFPrint GNN,
        66 pour fallback Librosa). Détectée automatiquement au premier add().
    """

    def __init__(self, db_path: Path):
        """
        Parameters
        ----------
        db_path : Path
            Chemin vers le fichier JSON de métadonnées.
            Les fichiers FAISS (.faiss) et IDs (.json) sont créés
            dans le même répertoire avec le même préfixe de nom.
        """
        self.db_path    = Path(db_path)
        self.faiss_path = self.db_path.with_suffix(".faiss")
        self.ids_path   = self.db_path.with_suffix("").with_name(
            self.db_path.stem + "_ids.json"
        )

        # Données en mémoire
        self._metadata: dict[str, dict] = {}  # work_hash → entry
        self._id_map:   list[str]       = []  # FAISS int ID → work_hash
        self._index:    Optional[faiss.Index] = None
        self.dim:       Optional[int]   = None

        self._load()
        logger.info(
            f"FingerprintIndex initialisé — "
            f"{self.count()} empreintes | "
            f"dim={self.dim} | "
            f"type={self._index_type_name()}"
        )

    # ═════════════════════════════════════════════════════════════════════════
    # PERSISTANCE
    # ═════════════════════════════════════════════════════════════════════════

    def _load(self) -> None:
        """Charge l'index FAISS et les métadonnées depuis le disque."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # ── Métadonnées JSON ──────────────────────────────────────────────
        if self.db_path.exists():
            with open(self.db_path, "r", encoding="utf-8") as f:
                self._metadata = json.load(f)
        else:
            self._metadata = {}

        # ── Mapping IDs ───────────────────────────────────────────────────
        if self.ids_path.exists():
            with open(self.ids_path, "r", encoding="utf-8") as f:
                self._id_map = json.load(f)
        else:
            self._id_map = []

        # ── Index FAISS ───────────────────────────────────────────────────
        if self.faiss_path.exists() and len(self._id_map) > 0:
            try:
                self._index = faiss.read_index(str(self.faiss_path))
                self.dim    = self._index.d
                logger.info(
                    f"Index FAISS chargé : {self._index.ntotal} vecteurs, "
                    f"dim={self.dim}, type={self._index_type_name()}"
                )
            except Exception as e:
                logger.warning(f"Impossible de charger l'index FAISS ({e}). Reconstruction...")
                self._rebuild_from_metadata()
        elif len(self._metadata) > 0:
            # Fichier FAISS absent mais métadonnées présentes → reconstruction
            logger.info("Reconstruction de l'index FAISS depuis les métadonnées...")
            self._rebuild_from_metadata()

    def _save(self) -> None:
        """Sauvegarde l'index FAISS et les métadonnées sur le disque."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Métadonnées JSON (sans les embeddings — stockés dans FAISS)
        meta_to_save = {
            k: {kk: vv for kk, vv in v.items() if kk != "embedding"}
            for k, v in self._metadata.items()
        }
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(meta_to_save, f, indent=2, ensure_ascii=False)

        # Mapping IDs
        with open(self.ids_path, "w", encoding="utf-8") as f:
            json.dump(self._id_map, f, indent=2)

        # Index FAISS binaire
        if self._index is not None:
            faiss.write_index(self._index, str(self.faiss_path))

    # ═════════════════════════════════════════════════════════════════════════
    # CONSTRUCTION ET SÉLECTION DE L'INDEX
    # ═════════════════════════════════════════════════════════════════════════

    def _create_empty_index(self, dim: int) -> faiss.Index:
        """
        Crée un index FAISS vide adapté à la taille courante du catalogue.

        Parameters
        ----------
        dim : int
            Dimension des vecteurs d'empreinte.

        Returns
        -------
        faiss.Index : index FAISS non entraîné (ou entraîné si Flat)
        """
        n = len(self._metadata)

        if n < INDEX_FLAT_THRESHOLD:
            # ── Recherche exacte par produit scalaire (cosinus pour vecteurs normalisés)
            logger.debug(f"Index sélectionné : FlatIP (n={n} < {INDEX_FLAT_THRESHOLD})")
            return faiss.IndexFlatIP(dim)

        elif n < INDEX_IVF_THRESHOLD:
            # ── Recherche approximative IVFFlat
            nlist = min(IVF_NLIST, max(1, n // 10))
            quantizer = faiss.IndexFlatIP(dim)
            index     = faiss.IndexIVFFlat(quantizer, dim, nlist,
                                           faiss.METRIC_INNER_PRODUCT)
            index.nprobe = min(IVF_NPROBE, nlist)
            logger.debug(f"Index sélectionné : IVFFlat (nlist={nlist}, nprobe={index.nprobe})")
            return index

        else:
            # ── Recherche approximative compressée IVFPQ
            nlist = min(256, max(64, n // 1000))
            m     = min(IVFPQ_M, dim // 4)   # m doit diviser dim
            while dim % m != 0 and m > 1:
                m -= 1
            quantizer = faiss.IndexFlatIP(dim)
            index     = faiss.IndexIVFPQ(quantizer, dim, nlist, m, IVFPQ_NBITS)
            index.nprobe = min(IVF_NPROBE, nlist)
            logger.debug(f"Index sélectionné : IVFPQ (nlist={nlist}, m={m})")
            return index

    def _rebuild_from_metadata(self) -> None:
        """
        Reconstruit l'index FAISS depuis les métadonnées.
        Utilisé après chargement d'un fichier JSON sans fichier .faiss,
        ou après changement de dimension des embeddings.
        """
        if not self._metadata:
            return

        # Vérifier que les embeddings sont présents dans les métadonnées
        entries_with_emb = {
            k: v for k, v in self._metadata.items()
            if "embedding" in v and v["embedding"]
        }

        if not entries_with_emb:
            logger.warning(
                "Reconstruction impossible : aucun embedding dans les métadonnées. "
                "Ré-enregistrer les œuvres pour peupler l'index FAISS."
            )
            return

        # Détection de la dimension
        sample_emb = next(iter(entries_with_emb.values()))["embedding"]
        dim = len(sample_emb)
        self.dim = dim

        # Construction de l'index
        self._id_map = []
        all_vectors  = []

        for work_hash, entry in entries_with_emb.items():
            emb = np.array(entry["embedding"], dtype=np.float32)
            if len(emb) != dim:
                logger.warning(
                    f"Dimension incohérente pour {work_hash[:16]}... "
                    f"({len(emb)} ≠ {dim}) — ignoré."
                )
                continue
            all_vectors.append(emb)
            self._id_map.append(work_hash)

        if not all_vectors:
            return

        matrix = np.stack(all_vectors).astype(np.float32)
        faiss.normalize_L2(matrix)

        self._index = self._create_empty_index(dim)

        # Entraînement si nécessaire (IVF*)
        if hasattr(self._index, "is_trained") and not self._index.is_trained:
            logger.info(f"Entraînement de l'index sur {len(matrix)} vecteurs...")
            self._index.train(matrix)

        self._index.add(matrix)
        self._save()
        logger.info(
            f"Index FAISS reconstruit : {self._index.ntotal} vecteurs, dim={dim}"
        )

    def _index_type_name(self) -> str:
        """Retourne le nom lisible du type d'index courant."""
        if self._index is None:
            return "Non initialisé"
        name = type(self._index).__name__
        mapping = {
            "IndexFlatIP":  "FlatIP (exact)",
            "IndexIVFFlat": "IVFFlat (approx.)",
            "IndexIVFPQ":   "IVFPQ (compressé)",
        }
        return mapping.get(name, name)

    def _should_upgrade_index(self) -> bool:
        """
        Retourne True si la taille du catalogue a franchi un seuil
        nécessitant un changement de type d'index.
        """
        if self._index is None:
            return False
        n    = self._index.ntotal
        name = type(self._index).__name__
        if name == "IndexFlatIP" and n >= INDEX_FLAT_THRESHOLD:
            return True
        if name == "IndexIVFFlat" and n >= INDEX_IVF_THRESHOLD:
            return True
        return False

    def _upgrade_index(self) -> None:
        """
        Reconstruit l'index avec un type plus performant si le catalogue
        a dépassé un seuil de taille.
        """
        old_type = self._index_type_name()
        self._rebuild_from_metadata()
        new_type = self._index_type_name()
        logger.info(f"Index mis à niveau : {old_type} → {new_type}")

    # ═════════════════════════════════════════════════════════════════════════
    # ÉCRITURE
    # ═════════════════════════════════════════════════════════════════════════

    def add(
        self,
        embedding:  np.ndarray,
        title:      str,
        artist:     str,
        ipfs_cid:   str,
        tx_hash:    str,
        recipients: list[str],
        shares:     list[int],
    ) -> str:
        """
        Ajoute une empreinte à l'index.

        Parameters
        ----------
        embedding : np.ndarray
            Vecteur d'empreinte GraFPrint (float32, L2-normalisé).
        title, artist : str
            Métadonnées de l'œuvre.
        ipfs_cid : str
            CID IPFS de l'empreinte audio.
        tx_hash : str
            Hash de transaction blockchain d'enregistrement.

        Returns
        -------
        str : Hash SHA-256 de l'empreinte (clé dans l'index et dans MusicRegistry)
        """
        embedding = embedding.astype(np.float32)

        # ── Détection automatique de la dimension ─────────────────────────
        if self.dim is None:
            self.dim = len(embedding)
            logger.info(f"Dimension de l'index fixée à {self.dim}")
        elif len(embedding) != self.dim:
            raise ValueError(
                f"Dimension incompatible : attendu {self.dim}, reçu {len(embedding)}. "
                f"Vider l'index (reset()) avant de changer de modèle."
            )

        # ── Calcul du hash de l'empreinte ────────────────────────────────
        import hashlib
        work_hash = hashlib.sha256(embedding.tobytes()).hexdigest()

        # ── Mise à jour des métadonnées ───────────────────────────────────
        self._metadata[work_hash] = {
            "title":         title,
            "artist":        artist,
            "ipfs_cid":      ipfs_cid,
            "tx_hash":       tx_hash,
            "recipients":    recipients,
            "shares":        shares,
            "embedding":     embedding.tolist(),   # conservé pour rebuild
            "registered_at": datetime.utcnow().isoformat()
        }

        # ── Initialisation ou mise à jour de l'index FAISS ───────────────
        vec = embedding.reshape(1, -1).copy()
        faiss.normalize_L2(vec)   # garantir la normalisation L2

        if self._index is None:
            self._index = self._create_empty_index(self.dim)
            # Entraînement si IVF (nécessite des données)
            if hasattr(self._index, "is_trained") and not self._index.is_trained:
                # Pas encore assez de données → fallback FlatIP temporaire
                self._index = faiss.IndexFlatIP(self.dim)

        # Ajout dans FAISS
        self._index.add(vec)
        self._id_map.append(work_hash)

        # ── Mise à niveau de l'index si seuil franchi ────────────────────
        if self._should_upgrade_index():
            self._upgrade_index()
        else:
            self._save()

        logger.info(
            f"Empreinte ajoutée : {work_hash[:16]}... | "
            f"{title} — {artist} | "
            f"Total : {self.count()}"
        )
        return work_hash

    # ═════════════════════════════════════════════════════════════════════════
    # LECTURE ET RECHERCHE
    # ═════════════════════════════════════════════════════════════════════════

    def search(
        self,
        query_embedding: np.ndarray,
        top_k:           int = 1
    ) -> list[dict]:
        """
        Recherche les œuvres les plus similaires via FAISS.

        Parameters
        ----------
        query_embedding : np.ndarray
            Vecteur d'empreinte du fichier suspect (float32).
        top_k : int
            Nombre de résultats à retourner.

        Returns
        -------
        list[dict] : Résultats triés par score décroissant.
            Chaque dict contient : work_hash, score, title, artist, ipfs_cid, tx_hash.
        """
        if self._index is None or self._index.ntotal == 0:
            logger.warning("Index FAISS vide — aucune œuvre enregistrée.")
            return []

        if self.dim is None or len(query_embedding) != self.dim:
            logger.warning(
                f"Dimension incompatible : index={self.dim}, "
                f"requête={len(query_embedding)}. Aucun résultat."
            )
            return []

        # Normalisation L2 de la requête (cosinus = produit scalaire normalisé)
        vec = query_embedding.astype(np.float32).reshape(1, -1).copy()
        faiss.normalize_L2(vec)

        # Ajustement de top_k si l'index est plus petit
        k = min(top_k, self._index.ntotal)

        # ── Recherche FAISS ───────────────────────────────────────────────
        scores, indices = self._index.search(vec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._id_map):
                continue   # FAISS peut retourner -1 en cas d'index IVF non entraîné

            work_hash = self._id_map[idx]
            entry     = self._metadata.get(work_hash)
            if entry is None:
                continue

            # Les scores FAISS IP sont déjà des cosinus (vecteurs normalisés)
            # Normalisation dans [0, 1] : cosinus ∈ [-1, 1] → [(cos+1)/2]
            cosine       = float(np.clip(score, -1.0, 1.0))
            score_01     = (cosine + 1.0) / 2.0

            results.append({
                "work_hash": work_hash,
                "score":     score_01,
                "title":     entry.get("title",    ""),
                "artist":    entry.get("artist",   ""),
                "ipfs_cid":  entry.get("ipfs_cid", ""),
                "tx_hash":   entry.get("tx_hash",  ""),
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def get(self, work_hash: str) -> Optional[dict]:
        """Récupère les métadonnées d'une empreinte par son hash."""
        return self._metadata.get(work_hash)

    def exists(self, work_hash: str) -> bool:
        """Vérifie si une empreinte est dans l'index."""
        return work_hash in self._metadata

    def count(self) -> int:
        """Retourne le nombre d'empreintes indexées."""
        return len(self._metadata)

    # ═════════════════════════════════════════════════════════════════════════
    # ADMINISTRATION
    # ═════════════════════════════════════════════════════════════════════════

    def reset(self) -> None:
        """
        Vide entièrement l'index (métadonnées + FAISS + IDs).
        À utiliser avant de changer de modèle (changement de dimension).
        """
        self._metadata = {}
        self._id_map   = []
        self._index    = None
        self.dim       = None

        for path in [self.db_path, self.faiss_path, self.ids_path]:
            if path.exists():
                path.unlink()

        logger.info("Index réinitialisé.")

    def rebuild(self) -> None:
        """
        Force la reconstruction complète de l'index FAISS depuis les métadonnées.
        Utile après une corruption du fichier .faiss.
        """
        logger.info("Reconstruction forcée de l'index FAISS...")
        self._id_map = []
        self._index  = None
        self._rebuild_from_metadata()

    def stats(self) -> dict:
        """Retourne les statistiques de l'index."""
        return {
            "count":      self.count(),
            "dim":        self.dim,
            "index_type": self._index_type_name(),
            "faiss_total": self._index.ntotal if self._index else 0,
            "db_path":    str(self.db_path),
            "faiss_path": str(self.faiss_path),
        }