# Configuration centralisee de l'application, lue depuis les variables d'environnement

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://scribe:scribe@localhost:5433/scribe",
    )
    jwt_secret_key: str = os.getenv(
        "JWT_SECRET_KEY",
        "change-me-in-production",
    )
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 480
    allowed_origin: str = os.getenv(
        "ALLOWED_ORIGIN",
        "https://127.0.0.1:5500",
    )
    vexa_api_key: str = os.getenv("VEXA_API_KEY", "")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")

    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv(
        "ANTHROPIC_MODEL",
        "claude-sonnet-5",
    )

    pyannote_auth_token: str = os.getenv(
        "PYANNOTE_AUTH_TOKEN",
        "",
    )
    ffmpeg_bin: str = os.getenv(
        "FFMPEG_BIN",
        "",
    )

    admin_api_key: str = os.getenv(
        "ADMIN_API_KEY",
        "",
    )

    sentry_dsn: str = os.getenv(
        "SENTRY_DSN",
        "",
    )


settings = Settings()