#!/usr/bin/env python3
"""
Test script to update trace.json with specific keys for debugging
"""
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TRACE_FILE = BASE_DIR / "trace.json"

def trace_step(key, status="active"):
    """Update trace.json with a new key and status"""
    data = {
        "key": int(key),
        "status": status,
        "ts": time.time()
    }
    TRACE_FILE.write_text(json.dumps(data), encoding="utf-8")
    print(f"✓ Updated trace.json: Key={key}, Status={status}, TS={data['ts']}")

if __name__ == "__main__":
    print("Trace.json Test Utility")
    print("=" * 50)
    print("This script updates trace.json for debugging")
    print()
    
    # Test sequence
    test_keys = [100, 110, 121, 123, 130]
    
    print("Starting test sequence...")
    for key in test_keys:
        trace_step(key, "active")
        print(f"  → Set key {key} to 'active'")
        time.sleep(2)  # Wait 2 seconds between updates
        
        trace_step(key, "done")
        print(f"  → Set key {key} to 'done'")
        time.sleep(1)
    
    print()
    print("✓ Test complete! Check your browser.")
    print(f"Current trace.json: {TRACE_FILE.read_text()}")
