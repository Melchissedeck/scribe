import http.server
import io
import ssl

PORT = 5500
CERT = 'cert.pem'
KEY  = 'key.pem'


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == '/':
            self.send_response(302)
            self.send_header('Location', '/pages/login.html')
            self.end_headers()
            return
        super().do_GET()

    def list_directory(self, path: str) -> io.BytesIO | None:  # type: ignore[override]
        self.send_error(403, 'Directory listing disabled')
        return None


def main() -> None:
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT, KEY)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    print(f'Serveur frontend disponible sur https://127.0.0.1:{PORT}')
    httpd.serve_forever()


if __name__ == '__main__':
    main()
