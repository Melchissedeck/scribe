# Serveur HTTP statique pour le frontend en production.
#
# Contrairement a serve.py (usage local, HTTPS via mkcert), le HTTPS est
# termine par la plateforme de deploiement en amont du conteneur : ce
# serveur n'a besoin de parler qu'en HTTP simple sur le port fourni.

import http.server
import os

PORT = int(os.environ.get("PORT", 8080))


def main() -> None:
    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), handler)

    print(f"Serveur frontend disponible sur le port {PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
