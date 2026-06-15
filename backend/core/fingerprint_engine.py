"""
FingerprintEngine — Couche IA du pipeline.

Corrections v2 :
  - Hyperparamètres alignés sur grafp.yaml (SR=16000, n_mels=64, hop=512, n_frames=32)
  - Mel segment forcé à (64, 32) pour correspondre au GraphEncoder (N=1024)
  - Protection NaN dans compare_fingerprints et validate_model
  - Fallback robuste (chroma + MFCC + ZCR normalisés)
"""
import sys
import logging
import hashlib
import tempfile
from pathlib import Path
from typing  import Optional

import numpy  as np
import librosa
import torch

from backend.config import settings

logger = logging.getLogger(__name__)


class FingerprintEngine:
    """
    Moteur d'extraction et de comparaison d'empreintes audio.

    Attributs
    ---------
    model  : Module SimCLR chargé en mémoire (None si indisponible)
    device : torch.device ("cpu")
    cfg    : Configuration grafp.yaml
    """

    # ── Hyperparamètres audio — DOIVENT correspondre à grafp.yaml ─────────
    SAMPLE_RATE  = 16000   # fs: 16000
    N_MELS       = 64      # n_mels: 64
    N_FFT        = 1024    # n_fft: 1024
    HOP_LENGTH   = 512     # hop_len: 512
    N_FRAMES     = 32      # n_frames: 32  →  N = 64 * 32 // 2 = 1024
    # Durée d'un segment : N_FRAMES * HOP_LENGTH / SAMPLE_RATE = 1.024s
    SEGMENT_SAMPLES = N_FRAMES * HOP_LENGTH   # 16 384 échantillons

    def __init__(self):
        self.device = torch.device("cpu")
        self.model: Optional[torch.nn.Module] = None
        self.cfg   = None
        logger.info("FingerprintEngine initialisé — device : cpu")

    # ─────────────────────────────────────────────────────────────────────────
    # CHARGEMENT DU MODÈLE
    # ─────────────────────────────────────────────────────────────────────────

    def load_grafprint_model(self) -> None:
        """
        Charge le modèle GraFPrint pré-entraîné model_tc_29_best.pth.
        Active le fallback Librosa si le chargement échoue.
        """
        grafp_root = settings.grafp_root
        model_path = Path(settings.grafp_model_path)

        if str(grafp_root) not in sys.path:
            sys.path.insert(0, str(grafp_root))

        if not model_path.exists():
            logger.warning(
                f"Modèle introuvable : {model_path}\n"
                "Télécharger : https://huggingface.co/chymaera96/grafp_db/resolve/main/checkpoint.zip\n"
                "→ Fallback Librosa activé."
            )
            self.model = None
            return

        try:
            from grafp.encoder.graph_encoder import GraphEncoder
            from grafp.simclr.simclr         import SimCLR
            from grafp.util                  import load_config

            # ── Chargement de la config ───────────────────────────────────
            config_path = Path(grafp_root) / "config" / "grafp.yaml"
            self.cfg    = load_config(str(config_path))

            # ── Reconstruction de l'architecture ─────────────────────────
            # in_channels = n_filters = 8  (validé : stem.0.weight=[64,8,1,1])
            encoder    = GraphEncoder(
                cfg        = self.cfg,
                in_channels= self.cfg["n_filters"],   # 8
                k          = 3
            )
            self.model = SimCLR(self.cfg, encoder=encoder)

            # ── Chargement des poids ──────────────────────────────────────
            checkpoint = torch.load(
                model_path, map_location=self.device, weights_only=False
            )
            state_dict = checkpoint.get("state_dict", checkpoint)

            # Retirer le préfixe DataParallel "module."
            clean_sd = {
                k.replace("module.", ""): v
                for k, v in state_dict.items()
            }

            missing, unexpected = self.model.load_state_dict(clean_sd, strict=False)

            if len(missing) > 30:
                logger.warning(
                    f"{len(missing)} poids manquants — architecture incompatible.\n"
                    "→ Fallback Librosa activé."
                )
                self.model = None
                return

            self.model.to(self.device)
            self.model.eval()

            # ── Validation : le modèle produit-il des embeddings non dégénérés ? ──
            if not self._validate_model():
                logger.warning("Modèle produit des embeddings invalides → Fallback Librosa.")
                self.model = None
                return

            logger.info("✅ Modèle GraFPrint chargé et validé")

        except Exception as e:
            logger.warning(f"Échec chargement GraFPrint ({e}) → Fallback Librosa activé.")
            self.model = None

    def _validate_model(self) -> bool:
        """
        Vérifie que le modèle produit des embeddings finis et non constants
        sur deux signaux différents.
        Retourne True si le modèle est opérationnel.
        """
        try:
            t  = np.linspace(0, 1.0, self.SEGMENT_SAMPLES, dtype=np.float32)
            s1 = np.sin(2 * np.pi * 440 * t)
            s2 = np.sin(2 * np.pi * 880 * t)

            mel1 = self._compute_mel_segment(s1)
            mel2 = self._compute_mel_segment(s2)

            e1 = self._grafprint_inference(mel1)
            e2 = self._grafprint_inference(mel2)

            if e1 is None or e2 is None:
                return False
            if not np.isfinite(e1).all() or not np.isfinite(e2).all():
                logger.debug("Validation : NaN/Inf détecté dans les embeddings.")
                return False
            if np.std(e1) < 1e-6:
                logger.debug("Validation : embedding constant (modèle mal chargé).")
                return False

            # Les deux signaux doivent produire des embeddings différents
            sim = float(np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2)))
            if sim > 0.999:
                logger.debug(f"Validation : embeddings trop similaires (sim={sim:.4f}).")
                return False

            logger.info(
                f"Validation OK — dim={len(e1)}, "
                f"sim(440Hz, 880Hz)={sim:.4f}"
            )
            return True

        except Exception as e:
            logger.debug(f"Validation échouée : {e}")
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # CALCUL DU SPECTROGRAMME MEL
    # ─────────────────────────────────────────────────────────────────────────

    def _compute_mel_segment(self, audio_segment: np.ndarray) -> np.ndarray:
        """
        Calcule un spectrogramme mel de forme exacte (N_MELS, N_FRAMES) = (64, 32).

        Parameters
        ----------
        audio_segment : np.ndarray
            Signal audio float32 à SAMPLE_RATE Hz.
            Idéalement de longueur SEGMENT_SAMPLES (16 384).

        Returns
        -------
        np.ndarray, shape (64, 32), dtype float32, valeurs dans [0, 1]
        """
        # Assurer une longueur minimale
        if len(audio_segment) < self.N_FFT:
            audio_segment = np.pad(
                audio_segment, (0, self.N_FFT - len(audio_segment))
            )

        # Spectrogramme mel
        mel = librosa.feature.melspectrogram(
            y          = audio_segment,
            sr         = self.SAMPLE_RATE,
            n_mels     = self.N_MELS,
            n_fft      = self.N_FFT,
            hop_length = self.HOP_LENGTH,
            center     = True
        )
        # mel.shape : (64, T) avec T ≈ 32–33 selon la longueur du signal

        # Forcer exactement N_FRAMES colonnes
        if mel.shape[1] > self.N_FRAMES:
            mel = mel[:, :self.N_FRAMES]
        elif mel.shape[1] < self.N_FRAMES:
            mel = np.pad(
                mel, ((0, 0), (0, self.N_FRAMES - mel.shape[1])),
                mode="constant"
            )
        # mel.shape : (64, 32) ✓

        # Conversion dB + normalisation [0, 1]
        mel_db  = librosa.power_to_db(mel, ref=np.max)
        mel_min = mel_db.min()
        mel_max = mel_db.max()

        if mel_max - mel_min > 1e-8:
            mel_db = (mel_db - mel_min) / (mel_max - mel_min)
        else:
            # Signal silencieux ou constant → spectre nul
            mel_db = np.zeros((self.N_MELS, self.N_FRAMES), dtype=np.float32)

        return mel_db.astype(np.float32)

    # Alias public pour compatibilité
    def extract_features(self, audio_blocks: np.ndarray) -> np.ndarray:
        return self._compute_mel_segment(audio_blocks)

    # ─────────────────────────────────────────────────────────────────────────
    # INFÉRENCE GRAFPRINT
    # ─────────────────────────────────────────────────────────────────────────

    def _grafprint_inference(self, mel_segment: np.ndarray) -> Optional[np.ndarray]:
        """
        Inférence GraFPrint sur un segment mel.

        Flux :
          mel_segment (64, 32)
            → peak_extractor (1, 64, 32) → (1, n_filters=8, N=1024)
            → GraphEncoder   (1, 8, 1024) → (1, 1024)
            → projector      (1, 1024)    → (1, 128)
            → L2-normalize   → (128,)

        Parameters
        ----------
        mel_segment : np.ndarray, shape (64, 32)

        Returns
        -------
        np.ndarray, shape (128,) ou None si erreur
        """
        if self.model is None:
            return None

        try:
            import torch.nn.functional as F

            # (1, n_mels, n_frames) = (1, 64, 32)
            spec = torch.from_numpy(mel_segment).unsqueeze(0).to(self.device)

            with torch.no_grad():
                # Peak extractor : (1, 64, 32) → (1, 8, 1024)
                features = self.model.peak_extractor(spec)

                # GraphEncoder : (1, 8, 1024) → (1, 1024)
                h = self.model.encoder(features)

                # Projecteur + normalisation : (1, 1024) → (1, 128) → (128,)
                z = self.model.projector(h)
                z = F.normalize(z, p=2, dim=1)

            result = z.squeeze(0).cpu().numpy().astype(np.float32)

            # Valider la sortie
            if not np.isfinite(result).all():
                logger.debug("GraFPrint : NaN/Inf dans l'embedding → ignoré.")
                return None

            return result

        except Exception as e:
            logger.debug(f"GraFPrint inference échouée : {e}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # EXTRACTION D'EMPREINTE (API PUBLIQUE)
    # ─────────────────────────────────────────────────────────────────────────

    def extract_fingerprint(self, audio_path: str) -> np.ndarray:
        """
        Extrait l'empreinte numérique d'un fichier audio.

        Stratégie :
          1. Charge et rééchantillonne à SAMPLE_RATE=16000 Hz
          2. Découpe en segments de SEGMENT_SAMPLES avec 50% de chevauchement
          3. Calcule l'embedding GraFPrint pour chaque segment
          4. Retourne la moyenne des embeddings valides (average pooling)
          5. Fallback Librosa si aucun embedding GraFPrint valide

        Parameters
        ----------
        audio_path : str
            Chemin vers le fichier audio (WAV ou MP3)

        Returns
        -------
        np.ndarray : vecteur d'empreinte float32, normalisé L2
        """
        audio, _ = librosa.load(audio_path, sr=self.SAMPLE_RATE, mono=True)
        audio    = audio.astype(np.float32)

        if self.model is None:
            return self._compute_robust_embedding(audio)

        # Segmentation avec 50% de chevauchement
        hop     = self.SEGMENT_SAMPLES // 2
        total   = len(audio)

        # Padding si le signal est plus court qu'un segment
        if total < self.SEGMENT_SAMPLES:
            audio = np.pad(audio, (0, self.SEGMENT_SAMPLES - total))
            total = self.SEGMENT_SAMPLES

        embeddings = []
        for start in range(0, total - self.SEGMENT_SAMPLES + 1, hop):
            segment = audio[start : start + self.SEGMENT_SAMPLES]
            mel     = self._compute_mel_segment(segment)
            emb     = self._grafprint_inference(mel)
            if emb is not None and np.isfinite(emb).all():
                embeddings.append(emb)

        if not embeddings:
            logger.warning(
                "Aucun embedding GraFPrint valide → Fallback Librosa."
            )
            return self._compute_robust_embedding(audio)

        # Average pooling sur les segments
        result = np.stack(embeddings).mean(axis=0).astype(np.float32)

        # Normalisation L2 finale
        norm = np.linalg.norm(result)
        if norm > 1e-8:
            result = result / norm

        return result

    def extract_fingerprint_from_bytes(self, audio_bytes: bytes) -> np.ndarray:
        """Variante acceptant des bytes bruts (upload HTTP)."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            return self.extract_fingerprint(tmp_path)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    # ─────────────────────────────────────────────────────────────────────────
    # FALLBACK LIBROSA
    # ─────────────────────────────────────────────────────────────────────────

    def _compute_robust_embedding(self, audio: np.ndarray) -> np.ndarray:
        """
        Empreinte de secours basée sur chroma (24) + MFCC (40) + ZCR (2) = 66 dims.
        Utilisée quand GraFPrint n'est pas disponible ou produit des NaN.
        """
        sr = self.SAMPLE_RATE

        if len(audio) < self.N_FFT:
            audio = np.pad(audio, (0, self.N_FFT - len(audio)))

        parts = []

        # Chroma : 12 × (mean + std) = 24 dims
        try:
            ch = librosa.feature.chroma_stft(y=audio, sr=sr, n_chroma=12)
            parts += [ch.mean(axis=1), ch.std(axis=1)]
        except Exception:
            parts += [np.zeros(12), np.zeros(12)]

        # MFCC : 20 × (mean + std) = 40 dims
        try:
            mf = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=20)
            parts += [mf.mean(axis=1), mf.std(axis=1)]
        except Exception:
            parts += [np.zeros(20), np.zeros(20)]

        # ZCR : mean + std = 2 dims
        try:
            zcr = librosa.feature.zero_crossing_rate(y=audio)
            parts.append(np.array([zcr.mean(), zcr.std()]))
        except Exception:
            parts.append(np.zeros(2))

        result = np.concatenate(parts).astype(np.float32)

        # Nettoyage NaN/Inf éventuels
        result = np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)

        norm = np.linalg.norm(result)
        if norm > 1e-8:
            result = result / norm

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # COMPARAISON ET HASH
    # ─────────────────────────────────────────────────────────────────────────

    def compare_fingerprints(self, fp1: np.ndarray, fp2: np.ndarray) -> float:
        """
        Similarité cosinus normalisée dans [0.0, 1.0].

        Protection explicite contre NaN/Inf : tout embedding invalide
        produit un score de 0.0 (aucune correspondance).
        """
        # ── Protection NaN/Inf ────────────────────────────────────────────
        if not np.isfinite(fp1).all() or not np.isfinite(fp2).all():
            return 0.0

        norm1 = np.linalg.norm(fp1)
        norm2 = np.linalg.norm(fp2)

        if norm1 < 1e-8 or norm2 < 1e-8:
            return 0.0

        # Similarité cosinus ∈ [-1, 1]
        cosine = float(np.dot(fp1, fp2) / (norm1 * norm2))

        # Clamp IEEE
        cosine = max(-1.0, min(1.0, cosine))

        # Normalisation linéaire → [0, 1]
        return (cosine + 1.0) / 2.0

    @staticmethod
    def embedding_to_hash(embedding: np.ndarray) -> str:
        """Hash SHA-256 déterministe d'un vecteur d'empreinte."""
        return hashlib.sha256(
            embedding.astype(np.float32).tobytes()
        ).hexdigest()