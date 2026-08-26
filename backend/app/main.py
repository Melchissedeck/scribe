# Point d'entree de l'application FastAPI

from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import (
    InvalidCredentialsError,
    LLMError,
    TokenExpiredError,
    VexaConnectionError,
    VexaInvalidMeetingError,
)
from app.routes import (
    action_status,
    actions,
    admin,
    auth,
    dictaphone,
    meetings,
    recording,
    summary,
    users,
)

# No-op si SENTRY_DSN est vide (pas de projet Sentry configure) : voir
# app/config.py. traces_sample_rate a 100% est volontaire vu le volume de
# requetes de ce projet ; a revoir si le trafic reel augmente.
sentry_sdk.init(
    dsn=settings.sentry_dsn,
    send_default_pii=False,
    traces_sample_rate=1.0,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Le pipeline Pyannote (torch + poids du modèle) est chargé au besoin,
    # au premier appel de diarisation, pas au démarrage : voir
    # app.services.pyannote_service.get_pyannote_service().
    app.state.pyannote_service = None

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


@app.exception_handler(VexaInvalidMeetingError)
def handle_vexa_invalid_meeting(
    request: Request,
    exc: VexaInvalidMeetingError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "Le lien de réunion est invalide ou inaccessible."},
    )


@app.exception_handler(VexaConnectionError)
def handle_vexa_connection_error(
    request: Request,
    exc: VexaConnectionError,
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": "Le service de réunion est temporairement indisponible. Veuillez réessayer dans quelques instants."},
    )


@app.exception_handler(LLMError)
def handle_llm_error(
    request: Request,
    exc: LLMError,
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"detail": exc.message, "error_type": exc.error_type},
    )


app.include_router(auth.router)
app.include_router(recording.router)
app.include_router(dictaphone.router)
app.include_router(summary.router)
app.include_router(meetings.router)
app.include_router(users.router)
app.include_router(actions.router)
app.include_router(action_status.router)
app.include_router(admin.router)

@app.get("/health")
def health_check() -> dict[str, str]:
    # Route utilisée pour vérifier que l'API est en ligne
    return {"status": "ok"}