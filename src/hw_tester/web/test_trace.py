#!/usr/bin/env python3
"""
Diagnostic script to test trace update system end-to-end.
Run this AFTER starting the HTTP server to verify the pipeline.
"""
import time
import json
from pathlib import Path
import urllib.request
import urllib.error

# Get trace file path
BASE_DIR = Path(__file__).resolve().parent
TRACE_FILE = BASE_DIR / "trace.json"

def test_write_trace():
    """Test writing to trace.json"""
    print("\n=== Testing Trace File Write ===")
    test_data = {"key": 999, "status": "test", "ts": time.time()}
    
    try:
        with open(TRACE_FILE, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
            f.flush()
        print(f"✓ Successfully wrote to {TRACE_FILE}")
        
        # Verify it was written
        with open(TRACE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✓ Verified read back: {data}")
        return True
    except Exception as e:
        print(f"✗ FAILED to write trace.json: {e}")
        return False

def test_notify_server():
    """Test notifying the SSE server"""
    print("\n=== Testing SSE Server Notification ===")
    try:
        req = urllib.request.Request('http://localhost:8000/notify', method='POST')
        response = urllib.request.urlopen(req, timeout=2)
        result = response.read().decode('utf-8')
        print(f"✓ Server responded: {result}")
        return True
    except urllib.error.URLError as e:
        print(f"✗ FAILED to connect to server: {e}")
        print("  (Make sure HTTP server is running on port 8000)")
        return False
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False

def test_fetch_trace():
    """Test fetching trace.json via HTTP"""
    print("\n=== Testing HTTP Fetch of trace.json ===")
    try:
        response = urllib.request.urlopen('http://localhost:8000/trace.json', timeout=2)
        data = json.loads(response.read().decode('utf-8'))
        print(f"✓ Successfully fetched via HTTP: {data}")
        return True
    except Exception as e:
        print(f"✗ FAILED to fetch via HTTP: {e}")
        return False

def main():
    print("=" * 50)
    print("TRACE SYSTEM DIAGNOSTIC TEST")
    print("=" * 50)
    print(f"Working directory: {BASE_DIR}")
    print(f"Trace file: {TRACE_FILE}")
    print(f"Trace file exists: {TRACE_FILE.exists()}")
    
    results = []
    
    # Test 1: Write to file
    results.append(("File Write", test_write_trace()))
    
    # Test 2: Notify server
    results.append(("SSE Notification", test_notify_server()))
    
    # Test 3: Fetch via HTTP
    results.append(("HTTP Fetch", test_fetch_trace()))
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:20} {status}")
    
    all_passed = all(result[1] for result in results)
    print("\n" + ("=" * 50))
    if all_passed:
        print("✓ ALL TESTS PASSED - Trace system is working!")
    else:
        print("✗ SOME TESTS FAILED - Check errors above")
    print("=" * 50)

if __name__ == '__main__':
    main()
