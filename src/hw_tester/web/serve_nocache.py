#!/usr/bin/env python3
"""
Custom HTTP server that disables caching for trace.json
"""
import http.server
import socketserver
from pathlib import Path

PORT = 8000

class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler that disables caching for trace.json"""
    
    def end_headers(self):
        # Disable caching for trace.json
        if self.path.endswith('trace.json') or 'trace.json' in self.path:
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        super().end_headers()
    
    def log_message(self, format, *args):
        # Suppress logging (optional - remove this method to see all requests)
        if 'trace.json' in args[0]:
            pass  # Don't log trace.json requests (too many)
        else:
            super().log_message(format, *args)

if __name__ == "__main__":
    # Change to the web directory
    web_dir = Path(__file__).parent
    import os
    os.chdir(web_dir)
    
    with socketserver.TCPServer(("", PORT), NoCacheHTTPRequestHandler) as httpd:
        print(f"Serving HTTP on port {PORT} from {web_dir}")
        print(f"Open: http://localhost:{PORT}/IO_Tester_logic_Power_test.html")
        print("trace.json will NOT be cached")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
