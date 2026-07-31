# Serveur HTTPS local pour le frontend statique, utilise les certificats mkcert

import http.server
import ssl
from pathlib import Path

CERT_DIR = Path(__file__).parent / "certs"
CERT_FILE = CERT_DIR / "localhost+1.pem"
KEY_FILE = CERT_DIR / "localhost+1-key.pem"
PORT = 5500


def main() -> None:
    if not CERT_FILE.exists() or not KEY_FILE.exists():
        raise SystemExit(
            "Certificats introuvables. Generez-les avec mkcert dans frontend/certs/."
        )

    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), handler)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=str(CERT_FILE), keyfile=str(KEY_FILE))
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    print(f"Serveur frontend disponible sur https://127.0.0.1:{PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
