# Point d'entree de l'application FastAPI

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import auth, recording, dictaphone
from app.services.pyannote_service import PyannoteService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Charge le pipeline Pyannote au démarrage de l'application
    app.state.pyannote_service = PyannoteService()

    yield

    # Libère la référence au pipeline à l'arrêt
    app.state.pyannote_service = None


app = FastAPI(
    title='Scribe API',
    lifespan=lifespan,
)

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
app.include_router(dictaphone.router)


@app.get('/health')
def health_check() -> dict[str, str]:
    # Route utilisee pour verifier que l'API est en ligne
    return {'status': 'ok'}