FROM python:3.12-slim

WORKDIR /app

COPY . .

# $PORT est fourni par la plateforme de deploiement (Railway) ; 8080 par
# defaut pour un lancement en local (docker run sans -e PORT=...).
CMD ["python", "serve_prod.py"]
