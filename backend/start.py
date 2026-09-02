"""Lance le serveur backend FastAPI avec HTTPS (mkcert)."""

from pathlib import Path

import uvicorn

CERT_DIR  = Path(__file__).parent.parent / 'frontend' / 'certs'
CERT_FILE = str(CERT_DIR / 'localhost+1.pem')
KEY_FILE  = str(CERT_DIR / 'localhost+1-key.pem')

if __name__ == '__main__':
    uvicorn.run(
        'app.main:app',
        host='127.0.0.1',
        port=8000,
        ssl_certfile=CERT_FILE,
        ssl_keyfile=KEY_FILE,
        reload=True,
    )
