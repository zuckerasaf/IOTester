import json
import time
import os
from pathlib import Path
import urllib.request
import urllib.error

BASE_DIR = Path(__file__).resolve().parent
TRACE_FILE = BASE_DIR / "trace.json"
SSE_NOTIFY_URL = "http://localhost:8000/notify"  # Optional: for external notification

def trace_step(key, status="active"):
    """Update trace.json with current test step and notify SSE clients."""
    data = {
        "key": int(key),
        "status": status,
        "ts": time.time()
    }
    
    try:
        with open(TRACE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        print(f"[TRACE] Updated: Key={key}, Status={status}")
        
        # Notify SSE server via HTTP POST
        try:
            req = urllib.request.Request('http://localhost:8000/notify', method='POST')
            urllib.request.urlopen(req, timeout=0.5)
            print(f"[TRACE] Notified SSE server")
        except Exception:
            # Server not running or not responding - that's OK, fail silently
            pass
            
    except Exception as e:
        print(f"[TRACE ERROR] Failed to write: {e}")

# def trace_step(key, status="active"):
#     """
#     Update trace.json with current test step.
#     Uses atomic write (temp file + rename) to prevent partial reads.
#     """
#     data = {
#         "key": int(key),
#         "status": status,
#         "ts": time.time()
#     }
    
#     # Write to temp file first, then atomic rename
#     temp_file = TRACE_FILE.with_suffix('.tmp')
    
#     try:
#         # Write with explicit flush
#         with open(temp_file, 'w', encoding='utf-8') as f:
#             json.dump(data, f)
#             f.flush()
#             os.fsync(f.fileno())  # Force write to disk
        
#         # Atomic rename on Windows
#         if temp_file.exists():
#             temp_file.replace(TRACE_FILE)
            
#         # Debug output
#         print(f"[TRACE] Updated: Key={key}, Status={status}, TS={data['ts']:.2f}")

#     except Exception as e:
#         print(f"[TRACE ERROR] Failed to write trace.json: {e}")
#         # Fallback to simple write
#         TRACE_FILE.write_text(json.dumps(data), encoding="utf-8")

# example usage
if __name__ == "__main__":
    for k in [100, 200, 300, 450]:
        trace_step(k, "active")
        time.sleep(1)
        trace_step(k, "done")
