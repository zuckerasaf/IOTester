#!/usr/bin/env python3
"""
Diagnostic script to test trace.json update timing and verify browser can see changes
"""
import json
import time
from pathlib import Path

# Import the actual trace_step function
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hw_tester.web.trace_writer import trace_step

TRACE_FILE = Path(__file__).resolve().parent / "trace.json"

def read_trace():
    """Read current trace.json content"""
    if TRACE_FILE.exists():
        return json.loads(TRACE_FILE.read_text())
    return None

def test_write_timing():
    """Test how quickly trace.json updates are visible"""
    print("=" * 70)
    print("TRACE.JSON UPDATE TIMING TEST")
    print("=" * 70)
    print()
    
    test_keys = [100, 110, 121, 123, 130]
    
    print("Starting rapid update test...")
    print("Open browser to http://localhost:8000/IO_Tester_logic_Power_test.html")
    print("Watch the console (F12) for updates")
    print()
    input("Press ENTER when ready...")
    print()
    
    for i, key in enumerate(test_keys, 1):
        print(f"\n[Test {i}/{len(test_keys)}] Updating to key {key}")
        
        # Write trace
        trace_step(key, "active")
        
        # Verify write
        time.sleep(0.01)  # 10ms
        current = read_trace()
        
        if current and current['key'] == key:
            print(f"  ✓ Write verified: {current}")
        else:
            print(f"  ✗ Write FAILED! Expected key={key}, got: {current}")
        
        # Wait for user to verify in browser
        print(f"  → Check browser: Is node {key} highlighted?")
        response = input("    Type 'y' if yes, 'n' if no, or ENTER to continue: ").lower().strip()
        
        if response == 'n':
            print(f"  ✗ PROBLEM DETECTED: Node {key} not visible in browser")
            print(f"     Current trace.json content: {TRACE_FILE.read_text()}")
        elif response == 'y':
            print(f"  ✓ Browser update confirmed")
        
        # Mark as done
        time.sleep(0.5)
        trace_step(key, "done")
        print(f"  → Marked key {key} as 'done'")
    
    print("\n" + "=" * 70)
    print("Test complete!")
    print("=" * 70)

def test_rapid_updates():
    """Test rapid consecutive updates (simulating Next button clicks)"""
    print("\n" + "=" * 70)
    print("RAPID UPDATE TEST (Simulating Next Button)")
    print("=" * 70)
    print()
    print("This simulates clicking Next button rapidly.")
    print("Watch browser for smooth transitions between nodes.")
    print()
    input("Press ENTER to start rapid updates...")
    print()
    
    keys = [100, 110, 121, 123, 130, 140]
    
    for key in keys:
        print(f"→ Key {key} (active)")
        trace_step(key, "active")
        time.sleep(0.3)  # 300ms between updates (faster than typical user clicking)
    
    print("\n✓ Rapid update test complete")
    print("Did all nodes light up smoothly? (check browser)")

def test_file_permissions():
    """Test if there are any file permission or locking issues"""
    print("\n" + "=" * 70)
    print("FILE SYSTEM TEST")
    print("=" * 70)
    print()
    
    print(f"Trace file path: {TRACE_FILE}")
    print(f"File exists: {TRACE_FILE.exists()}")
    
    if TRACE_FILE.exists():
        print(f"File size: {TRACE_FILE.stat().st_size} bytes")
        print(f"Current content: {TRACE_FILE.read_text()}")
    
    print("\nTesting write access...")
    try:
        test_data = {"key": 999, "status": "test", "ts": time.time()}
        TRACE_FILE.write_text(json.dumps(test_data))
        print("✓ Write successful")
        
        # Read back
        read_back = json.loads(TRACE_FILE.read_text())
        if read_back == test_data:
            print("✓ Read-back verified")
        else:
            print(f"✗ Read-back mismatch: {read_back}")
    except Exception as e:
        print(f"✗ Write failed: {e}")

if __name__ == "__main__":
    print("\nTRACE.JSON DIAGNOSTIC TOOL\n")
    print("This tool helps diagnose timing issues with trace.json updates")
    print()
    
    while True:
        print("\nSelect test:")
        print("  1) Write timing test (interactive)")
        print("  2) Rapid updates test (automatic)")
        print("  3) File system test")
        print("  4) Run all tests")
        print("  q) Quit")
        print()
        choice = input("Enter choice: ").strip().lower()
        
        if choice == '1':
            test_write_timing()
        elif choice == '2':
            test_rapid_updates()
        elif choice == '3':
            test_file_permissions()
        elif choice == '4':
            test_file_permissions()
            test_rapid_updates()
            test_write_timing()
        elif choice == 'q':
            print("\nExiting...")
            break
        else:
            print("Invalid choice")
