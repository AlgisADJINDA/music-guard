import numpy as np
import librosa
import hashlib
from scipy.ndimage import maximum_filter


class AudioFingerprint:

    def __init__(self,
                 sr=8000,
                 n_fft=2048,
                 hop_length=512,
                 fan_value=5,
                 amp_min=10):

        self.sr = sr
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.fan_value = fan_value
        self.amp_min = amp_min

    # ─────────────────────────────────────────────
    # 1. Spectrogramme
    # ─────────────────────────────────────────────
    def _spectrogram(self, audio):
        S = np.abs(librosa.stft(audio,
                                n_fft=self.n_fft,
                                hop_length=self.hop_length))
        S = librosa.amplitude_to_db(S)
        return S

    # ─────────────────────────────────────────────
    # 2. Détection de pics
    # ─────────────────────────────────────────────
    def _get_peaks(self, S):
        local_max = maximum_filter(S, size=20)
        peaks = (S == local_max)

        # filtrage bruit
        peaks &= (S > self.amp_min)

        coords = np.argwhere(peaks)

        return coords  # (time, freq)

    # ─────────────────────────────────────────────
    # 3. Construction des hashes
    # ─────────────────────────────────────────────
    def _hash_points(self, peaks):
        """
        peaks: array [ (freq, time) ]
        """

        fingerprints = []

        for i in range(len(peaks)):
            f1, t1 = peaks[i]

            for j in range(1, self.fan_value):
                if i + j < len(peaks):

                    f2, t2 = peaks[i + j]

                    dt = t2 - t1

                    if 0 <= dt <= 200:

                        h = hashlib.sha1(
                            f"{f1}|{f2}|{dt}".encode()
                        ).hexdigest()

                        fingerprints.append((h, t1))

        return fingerprints

    # ─────────────────────────────────────────────
    # API principale
    # ─────────────────────────────────────────────
    def fingerprint(self, audio_path):
        audio, _ = librosa.load(audio_path,
                                sr=self.sr,
                                mono=True)

        S = self._spectrogram(audio)
        peaks = self._get_peaks(S)

        return self._hash_points(peaks)