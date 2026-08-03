# Point d'entree de l'application FastAPI

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import auth, recording

app = FastAPI(title='Scribe API')

# Autorise uniquement le frontend declare a appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.allowed_origin],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth.router)
app.include_router(recording.router)


@app.get('/health')
def health_check() -> dict[str, str]:
    # Route utilisee pour verifier que l'API est en ligne
    return {'status': 'ok'}
