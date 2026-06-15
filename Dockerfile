# ─────────────────────────────────────────────────────────────────────────────
# MusicGuard Backend — Dockerfile de production
# Gère l'installation de torch-geometric avec les wheels PyG officielles
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.10-slim

WORKDIR /app

# ── Dépendances système ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# ── Étape 1 : PyTorch CPU (sans CUDA pour réduire la taille) ─────────────────
# On installe torch séparément depuis le mirror CPU officiel
RUN pip install --no-cache-dir \
    torch==2.6.0+cpu \
    torchaudio==2.6.0+cpu \
    torchvision==0.21.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# ── Étape 2 : torch-geometric + extensions (wheels PyG pour torch 2.6 CPU) ───
RUN pip install --no-cache-dir torch-geometric==2.5.3

RUN pip install --no-cache-dir \
    torch-scatter \
    torch-sparse \
    torch-cluster \
    torch-spline-conv \
    -f https://data.pyg.org/whl/torch-2.6.0+cpu.html

# ── Étape 3 : reste des dépendances ──────────────────────────────────────────
COPY backend/requirements.txt ./requirements.txt

# On exclut torch/torchaudio/torchvision/torch-geometric déjà installés
RUN pip install --no-cache-dir \
    $(grep -v -E "^(torch|torchaudio|torchvision|torch-geometric)" requirements.txt | tr '\n' ' ')

# ── Copie du code source ──────────────────────────────────────────────────────
COPY backend/ ./backend/
COPY grafp/   ./grafp/
COPY model/   ./model/

# ── Santé du container ────────────────────────────────────────────────────────
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# ── Lancement ─────────────────────────────────────────────────────────────────
# Lancé depuis /app → les imports "from backend.xxx" et "from grafp.xxx" fonctionnent
CMD ["uvicorn", "backend.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1"]