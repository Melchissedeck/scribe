import http.server
import ssl

PORT = 5500
CERT = 'cert.pem'
KEY  = 'key.pem'


def main() -> None:
    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT, KEY)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    print(f'Serveur frontend disponible sur https://127.0.0.1:{PORT}')
    httpd.serve_forever()


if __name__ == '__main__':
    main()
