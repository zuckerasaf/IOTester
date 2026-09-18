# Logic Tree View Presentation - Standard Operating Procedure

## Overview
The Logic Tree View is a **real-time visualization system** that shows the current execution state of hardware tests. It displays test flow as an interactive flowchart where nodes light up as tests execute, allowing visual monitoring of test progress.

---

## System Architecture

### Components

1. **Excel Test Definition Files** (`*.xlsm`)
   - Define test logic flows with keys, steps, parent relationships
   - Located in: `src/hw_tester/web/`
   - Files: `IO_Tester_logic_Power_test.xlsm`, `_Logic_test.xlsm`, `_Pullup_test.xlsm`, `_keepalive.xlsm`

2. **Web_Presentation.py** (Generator Script)
   - Converts Excel test definitions to visual flowcharts
   - Generates `.dot`, `.svg`, and `.html` files using Graphviz
   - Run this when test logic changes

3. **HTML Logic Tree Files** (Viewers)
   - Interactive flowcharts with JavaScript polling
   - Auto-refresh every 200ms to detect test state changes
   - Files: `IO_Tester_logic_*.html`

4. **trace.json** (State File)
   - Single JSON file with current test state: `{"key": 130, "status": "active", "ts": 1768739569.18}`
   - Updated by main application during test execution
   - Polled by all HTML viewers simultaneously

5. **serve_nocache.py** (Web Server)
   - Serves HTML files with cache-busting for trace.json
   - Runs on `http://localhost:8000`
   - Disables browser caching to ensure real-time updates

6. **trace_writer.py** (Helper Module)
   - Utility function: `trace_step(key, status)` 
   - Used by main application to update trace.json
   - Imported in `main_window.py`

---

## Standard Workflow

### Phase 1: Setup (One-Time or After Test Logic Changes)

#### 1.1 Update Test Logic (If Needed)
```
Edit Excel files: src/hw_tester/web/IO_Tester_logic_*.xlsm
  - Modify test steps, keys, flow relationships
  - Save the file
```

#### 1.2 Regenerate HTML Files
```powershell
cd c:\ArduinoProject\IO_Tester\src\hw_tester\web

# Edit Web_Presentation.py to select which test to generate
# Line 11: file_name = "IO_Tester_logic_Power_test"  # Change this

python Web_Presentation.py
```
**Output**: Updates corresponding `.dot`, `.svg`, and `.html` files

#### 1.3 Start Web Server
```powershell
cd c:\ArduinoProject\IO_Tester\src\hw_tester\web
python serve_nocache.py
```
**Output**:
```
Serving HTTP on port 8000 from c:\ArduinoProject\IO_Tester\src\hw_tester\web
Open: http://localhost:8000/IO_Tester_logic_Power_test.html
trace.json will NOT be cached
```

**⚠️ Keep this terminal running during testing!**

---

### Phase 2: Testing Session

#### 2.1 Open Logic Tree Viewer in Browser
```
Navigate to one of:
  http://localhost:8000/IO_Tester_logic_Power_test.html
  http://localhost:8000/IO_Tester_logic_Logic_test.html
  http://localhost:8000/IO_Tester_logic_Pullup_test.html
  http://localhost:8000/IO_Tester_logic_keepalive.html
```

**Choose the viewer matching the test type you're running**

#### 2.2 Open Browser Developer Console (Optional but Recommended)
- Press `F12`
- Go to Console tab
- You'll see: `✓ Trace viewer initialized. Polling every 200ms.`

#### 2.3 Start Main Application
```powershell
# In a NEW terminal window
cd c:\ArduinoProject\IO_Tester
.\.venv\Scripts\Activate.ps1
python src/hw_tester/app.py
```

#### 2.4 Run Tests in GUI
1. Select connector from dropdown
2. Click "Start Tests"
3. **Watch the Logic Tree Viewer in your browser**
   - Nodes will highlight in real-time as tests execute
   - Active nodes have thick borders and bold text
   - Page auto-scrolls to show current step
   - Previous nodes change to "done" status (thin border)

#### 2.5 Monitor Test Progress

**In Browser Console** (F12):
```
Every 10 seconds you'll see:
  Poll #50: Current=130/1768739569.18, Last=121/1768739567.12

When tests advance:
  ✓ Trace update detected: Key=130, Status=active, TS=1768739569.18
  ✓ Node 130 highlighted as active
```

**In Main App GUI**:
- Log view shows detailed test execution
- Pin table updates with measurements
- Use "Next" button for step-by-step debugging

---

### Phase 3: Debugging & Troubleshooting

#### 3.1 Debug Commands in Browser Console

| Command | Purpose |
|---------|---------|
| `checkStatus()` | Show current state: lastKey, lastTs, pollActive, pollCount |
| `manualRefresh()` | Force immediate refresh (resets state and polls) |
| `highlight(123)` | Manually highlight node 123 |
| `stopPolling()` | Pause automatic updates |
| `startPolling()` | Resume automatic updates |

#### 3.2 Manual Testing (Without Running Full App)

**Option A: Use Test Script**
```powershell
cd c:\ArduinoProject\IO_Tester\src\hw_tester\web
python test_trace_update.py
```
Cycles through test keys with 2-second delays

**Option B: Manual Python Commands**
```python
from pathlib import Path
import json, time

trace_file = Path("c:/ArduinoProject/IO_Tester/src/hw_tester/web/trace.json")

# Highlight node 121
trace_file.write_text(json.dumps({"key": 121, "status": "active", "ts": time.time()}))

# Mark as done
trace_file.write_text(json.dumps({"key": 121, "status": "done", "ts": time.time()}))
```

#### 3.3 Common Issues

| Problem | Solution |
|---------|----------|
| **Node not highlighting** | Run `checkStatus()` - verify `pollActive=true` and check lastKey |
| **Page not updating** | Check server is running, refresh page (Ctrl+Shift+R) |
| **Wrong node highlighted** | Verify trace.json content: `Get-Content trace.json` |
| **Node doesn't exist** | Check console for "Node XXX NOT FOUND" - may need to regenerate HTML |
| **Server won't start** | Check if port 8000 is in use: `netstat -ano \| findstr :8000` |

---

## Integration with Main Application

### How trace_step() Works

In [main_window.py](src/hw_tester/ui/main_window.py#L605):
```python
from hw_tester.web.trace_writer import trace_step

def wait_debug(self, ID: int = 0, status: str = "active") -> None:
    """Pause for debugging and update logic tree viewer"""
    trace_step(ID, status)  # Updates trace.json
    self.next_event.wait()  # Wait for user to press Next button
```

### Test Execution Flow

```
Main App (app.py)
  ↓
MainWindow (main_window.py)
  ↓
run_power_test() / run_logic_test() / run_pullup_test()
  ↓
wait_debug(key=121, status="active")
  ↓
trace_writer.trace_step(121, "active")
  ↓
Writes to trace.json: {"key": 121, "status": "active", "ts": 1768739569.18}
  ↓
Browser polls trace.json every 200ms
  ↓
JavaScript detects change and highlights node 121
  ↓
User presses "Next" in GUI
  ↓
Test continues to next step (key=123)
  ↓
Cycle repeats
```

---

## Test Type Selection Guide

| Test Type | Excel File | HTML Viewer | When to Use |
|-----------|-----------|-------------|-------------|
| **Power Test** | `IO_Tester_logic_Power_test.xlsm` | `IO_Tester_logic_Power_test.html` | Voltage measurements, power supply validation |
| **Logic Test** | `IO_Tester_logic_Logic_test.xlsm` | `IO_Tester_logic_Logic_test.html` | Digital I/O testing, signal validation |
| **Pullup Test** | `IO_Tester_logic_Pullup_test.xlsm` | `IO_Tester_logic_Pullup_test.html` | Pull-up resistor testing |
| **Keepalive** | `IO_Tester_logic_keepalive.xlsm` | `IO_Tester_logic_keepalive.html` | Communication/heartbeat testing |

---

## Key Differences from Previous System

### ✅ What Changed (Recent Improvements)

| Before | After |
|--------|-------|
| Required server restart to see updates | **Auto-updates every 200ms** |
| No visibility into polling | **Debug logging every 10 seconds** |
| Nodes stayed highlighted | **Previous nodes clear to "done"** |
| No auto-scroll | **Active nodes scroll into view** |
| Silent errors | **Console shows all errors** |
| No debug commands | **`checkStatus()`, `manualRefresh()`, etc.** |

### ⚠️ Important Notes

1. **One trace.json for all viewers**: All HTML files poll the same `trace.json`. Only open the viewer matching your current test type.

2. **Node keys must match**: Keys in `trace_step(key)` calls must exist in the corresponding HTML file's SVG nodes (`<g id="n121">`).

3. **Server keeps running**: No need to restart server between tests - just refresh browser if needed.

4. **Step-by-step execution**: Use `wait_debug(key)` in test code + "Next" button in GUI for controlled stepping through tests.

---

## Quick Reference: Complete Test Session

```powershell
# Terminal 1: Start web server (leave running)
cd c:\ArduinoProject\IO_Tester\src\hw_tester\web
python serve_nocache.py

# Terminal 2: Start main app
cd c:\ArduinoProject\IO_Tester
.\.venv\Scripts\Activate.ps1
python src/hw_tester/app.py

# Browser: Open viewer
http://localhost:8000/IO_Tester_logic_Power_test.html

# Browser Console: Monitor (F12)
checkStatus()     # Check polling state

# Main App GUI:
1. Select connector
2. Click "Start Tests"
3. Watch browser for real-time visualization
4. Press "Next" to step through (if in debug mode)
```

---

## Future Enhancements (Planned)

- [ ] Multiple browser windows showing different test types simultaneously
- [ ] Visual indicators for pass/fail status (green/red nodes)
- [ ] Test timing information on nodes
- [ ] Replay mode to review past test sessions
- [ ] Export test execution trace as video/animation
- [ ] WebSocket-based updates (faster than polling)

---

## Related Files

- Application: [src/hw_tester/app.py](src/hw_tester/app.py)
- Main Window: [src/hw_tester/ui/main_window.py](src/hw_tester/ui/main_window.py)
- Trace Writer: [src/hw_tester/web/trace_writer.py](src/hw_tester/web/trace_writer.py)
- Web Server: [src/hw_tester/web/serve_nocache.py](src/hw_tester/web/serve_nocache.py)
- Test Script: [src/hw_tester/web/test_trace_update.py](src/hw_tester/web/test_trace_update.py)
- Generator: [src/hw_tester/web/Web_Presentation.py](src/hw_tester/web/Web_Presentation.py)

---

**Last Updated**: January 18, 2026  
**Version**: 2.0 (with auto-update improvements)
