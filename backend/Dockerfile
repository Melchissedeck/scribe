FROM python:3.12-slim

WORKDIR /app

# ffmpeg est utilise par pyannote_service.py pour reconvertir l'audio
# dictaphone (webm) en wav avant diarisation.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Installe torch en version CPU-only avant le reste des dependances :
# le wheel par defaut de PyPI embarque les librairies CUDA (plusieurs
# centaines de Mo en plus, inutiles sans GPU), ce qui alourdit inutilement
# l'image et la memoire consommee au chargement du pipeline pyannote.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# $PORT est fourni par la plateforme de deploiement (Railway) ; 8000 par
# defaut pour un lancement en local (docker run sans -e PORT=...).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
