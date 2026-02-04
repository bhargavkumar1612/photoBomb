import http.server
import socketserver
import os
import sys

PORT = int(os.getenv("PORT", 10000))

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Worker is running")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

try:
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Dummy server listening on port {PORT}")
        httpd.serve_forever()
except Exception as e:
    print(f"Error starting dummy server: {e}")
    sys.exit(1)
