# Point d'entree de l'application FastAPI

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import (
    InvalidCredentialsError,
    TokenExpiredError,
    VexaConnectionError,
)
from app.routes import (
    auth,
    recording,
    dictaphone,
    summary,
    meetings,
    users,
    actions,
    action_status,
)
from app.services.pyannote_service import PyannoteService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Charge le pipeline Pyannote au démarrage de l'application
    app.state.pyannote_service = PyannoteService()

    yield

    # Libère la référence au pipeline à l'arrêt
    app.state.pyannote_service = None


app = FastAPI(
    title="Scribe API",
    lifespan=lifespan,
)


# Autorise uniquement le frontend déclaré à appeler l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.allowed_origin,
        settings.allowed_origin.replace("127.0.0.1", "localhost"),
        settings.allowed_origin.replace("localhost", "127.0.0.1"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(TokenExpiredError)
def handle_token_expired(
    request: Request,
    exc: TokenExpiredError,
) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": exc.message},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(InvalidCredentialsError)
def handle_invalid_credentials(
    request: Request,
    exc: InvalidCredentialsError,
) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={"detail": exc.message},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(VexaConnectionError)
def handle_vexa_connection_error(
    request: Request,
    exc: VexaConnectionError,
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"detail": exc.message},
    )


app.include_router(auth.router)
app.include_router(recording.router)
app.include_router(dictaphone.router)
app.include_router(summary.router)
app.include_router(meetings.router)
app.include_router(users.router)
app.include_router(actions.router)
app.include_router(action_status.router)

@app.get("/health")
def health_check() -> dict[str, str]:
    # Route utilisée pour vérifier que l'API est en ligne
    return {"status": "ok"}