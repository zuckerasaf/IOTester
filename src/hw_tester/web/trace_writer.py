import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TRACE_FILE = BASE_DIR / "trace.json"

def trace_step(key, status="active"):
    data = {
        "key": int(key),
        "status": status,
        "ts": time.time()
    }
    TRACE_FILE.write_text(json.dumps(data), encoding="utf-8")

# example usage
if __name__ == "__main__":
    for k in [100, 200, 300, 450]:
        trace_step(k, "active")
        time.sleep(1)
        trace_step(k, "done")
