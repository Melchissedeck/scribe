# Point d'entree de l'application FastAPI

from fastapi import FastAPI

from app.routes import auth

app = FastAPI(title='Scribe API')

app.include_router(auth.router)


@app.get('/health')
def health_check() -> dict[str, str]:
    # Route utilisee pour verifier que l'API est en ligne
    return {'status': 'ok'}