# Serveur HTTP statique pour le frontend en production.
#
# Contrairement a serve.py (usage local, HTTPS via mkcert), le HTTPS est
# termine par la plateforme de deploiement en amont du conteneur : ce
# serveur n'a besoin de parler qu'en HTTP simple sur le port fourni.

import http.server
import io
import os

PORT = int(os.environ.get("PORT", 8080))


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/":
            self.send_response(302)
            self.send_header("Location", "/pages/login.html")
            self.end_headers()
            return
        super().do_GET()

    def list_directory(self, path: str) -> io.BytesIO | None:  # type: ignore[override]
        self.send_error(403, "Directory listing disabled")
        return None


def main() -> None:
    httpd = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)

    print(f"Serveur frontend disponible sur le port {PORT}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
