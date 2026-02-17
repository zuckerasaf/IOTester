#!/usr/bin/env python3
"""
Custom HTTP server with Server-Sent Events (SSE) support for trace updates
"""
import http.server
import socketserver
import threading
import queue
from pathlib import Path

PORT = 8000

# Use ThreadingMixIn to handle multiple connections simultaneously
class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Multi-threaded HTTP server that can handle SSE and POST requests simultaneously"""
    daemon_threads = True  # Exit threads cleanly when main thread exits
    allow_reuse_address = True  # Allow quick restarts

# Global queue for SSE clients
sse_clients = []
sse_lock = threading.Lock()

def notify_trace_update():
    """Notify all connected SSE clients that trace.json has been updated"""
    with sse_lock:
        dead_clients = []
        for client_queue in sse_clients:
            try:
                client_queue.put("update", block=False)
            except:
                dead_clients.append(client_queue)
        # Remove dead clients
        for dead in dead_clients:
            sse_clients.remove(dead)
        if sse_clients:
            print(f"[SSE] Notified {len(sse_clients)} client(s)")

class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler with SSE support and no caching"""
    
    def do_GET(self):
        # Handle SSE endpoint
        if self.path == '/events' or self.path.startswith('/events?'):
            self.handle_sse()
            return
        
        # Handle normal file requests
        super().do_GET()
    
    def do_POST(self):
        # Handle trace update notification
        if self.path == '/notify':
            print(f"[NOTIFY] Received trace update notification (from trace_writer.py)")
            notify_trace_update()
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
            print(f"[NOTIFY] Response sent")
        else:
            self.send_response(404)
            self.end_headers()
    
    def handle_sse(self):
        """Handle Server-Sent Events connection"""
        # Create a queue for this client
        client_queue = queue.Queue()
        
        with sse_lock:
            sse_clients.append(client_queue)
        
        print(f"[SSE] New client connected (total: {len(sse_clients)})")
        
        # Send SSE headers
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        # Send initial connection message
        self.wfile.write(b': SSE connection established\n\n')
        self.wfile.flush()
        
        try:
            # Keep connection alive and send updates
            while True:
                try:
                    # Wait for notification (with timeout for keep-alive)
                    msg = client_queue.get(timeout=30)
                    
                    # Send SSE event
                    self.wfile.write(f'data: {msg}\n\n'.encode('utf-8'))
                    self.wfile.flush()
                    
                except queue.Empty:
                    # Send keep-alive comment every 30 seconds
                    self.wfile.write(b': keep-alive\n\n')
                    self.wfile.flush()
                    
        except (BrokenPipeError, ConnectionResetError):
            print(f"[SSE] Client disconnected")
        finally:
            # Remove client from list
            with sse_lock:
                if client_queue in sse_clients:
                    sse_clients.remove(client_queue)
            print(f"[SSE] Client removed (remaining: {len(sse_clients)})")
    
    def end_headers(self):
        # Disable caching for trace.json and HTML files
        if (self.path.endswith('trace.json') or 
            self.path.endswith('.html') or 
            'trace.json' in self.path):
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            # Add CORS headers to allow cross-origin requests if needed
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def log_message(self, format, *args):
        # Log trace.json requests to help with debugging
        if 'trace.json' in args[0]:
            print(f"[TRACE REQ] {args[0]}")
        elif '/events' not in args[0]:  # Don't spam with SSE requests
            super().log_message(format, *args)

if __name__ == "__main__":
    # Change to the web directory
    web_dir = Path(__file__).parent
    import os
    os.chdir(web_dir)
    
    with ThreadedHTTPServer(("", PORT), NoCacheHTTPRequestHandler) as httpd:
        print("=" * 60)
        print(f"SSE HTTP Server Starting on port {PORT}")
        print(f"Server mode: MULTI-THREADED (SSE + POST notifications)")
        print(f"Serving from: {web_dir}")
        print(f"trace.json caching: DISABLED")
        print(f"Open: http://localhost:{PORT}/IO_Tester_logic_Power_test.html")
        print("=" * 60)
        print("Waiting for connections...")
        print()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
