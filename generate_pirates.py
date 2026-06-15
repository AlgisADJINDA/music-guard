import numpy as np
import librosa
import soundfile as sf
from pathlib import Path

PROJECT_ROOT = Path(r"C:\Users\Algis ADJINDA\music-antipiracy")
REF_DIR   = PROJECT_ROOT / "data" / "references"
PIRATE_DIR = PROJECT_ROOT / "data" / "pirates"
PIRATE_DIR.mkdir(parents=True, exist_ok=True)

def degrade_audio(input_path: Path, output_path: Path):
    audio, sr = librosa.load(str(input_path), sr=16000, mono=True)   # 16000 Hz !
    # Bruit très faible
    audio += 0.005 * np.random.randn(len(audio))
    # Compression douce
    audio = np.tanh(1.05 * audio)
    # Pitch shift léger (+0.3 demi-ton)
    audio = librosa.effects.pitch_shift(audio, sr=sr, n_steps=0.3)
    # Normalisation
    audio = audio / (np.max(np.abs(audio)) + 1e-8)
    sf.write(str(output_path), audio.astype(np.float32), 16000)

for f in sorted(REF_DIR.glob("*.wav")):
    out = PIRATE_DIR / f"pirate_{f.name}"
    degrade_audio(f, out)
    print(f"  ✓ {f.name} → pirate_{f.name}")

print(f"\n{len(list(PIRATE_DIR.glob('*.wav')))} pirates générés.")