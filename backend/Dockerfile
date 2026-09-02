FROM python:3.12-slim

WORKDIR /app

# ffmpeg est utilise par pyannote_service.py pour reconvertir l'audio
# dictaphone (webm) en wav avant diarisation.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Installe torch, torchaudio et torchcodec en version CPU-only avant le
# reste des dependances : le wheel par defaut de PyPI embarque les
# librairies CUDA (plusieurs centaines de Mo en plus, inutiles sans GPU),
# ce qui alourdit inutilement l'image et la memoire consommee au
# chargement du pipeline pyannote. Les trois doivent venir du meme index :
# - torchaudio depuis PyPI standard serait compile pour un build torch
#   different de celui installe ici (le .so natif echoue a se charger,
#   erreur ABI incompatible) ;
# - torchaudio >= 2.9 delegue le decodage audio a torchcodec, qui a son
#   tour doit etre la variante CPU (la variante par defaut de PyPI est
#   liee a CUDA et echoue au chargement faute de libnvrtc).
RUN pip install --no-cache-dir torch torchaudio torchcodec --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Applique les migrations avant de demarrer : necessaire au premier
# deploiement (base vide) et a chaque evolution du schema par la suite.
# $PORT est fourni par la plateforme de deploiement (Railway) ; 8000 par
# defaut pour un lancement en local (docker run sans -e PORT=...).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
