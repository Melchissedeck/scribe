# Point d'entree de l'application FastAPI

from fastapi import FastAPI

app = FastAPI(title='Scribe API')


@app.get('/health')
def health_check() -> dict[str, str]:
    # Route utilisee pour verifier que l'API est en ligne
    return {'status': 'ok'}
