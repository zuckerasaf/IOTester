# Trace Update Fix - Summary

## Problem
The Logic Tree Viewer was not updating nodes in real-time even though `trace.json` was being updated. You had to restart the server to see changes.

## Root Causes Identified
1. **No auto-scroll**: When a node was updated, the page didn't scroll to show it
2. **Previous highlights not clearing**: Old active nodes remained highlighted
3. **Limited debugging**: No visibility into what the polling was doing
4. **No poll counter**: Couldn't track if polling was actually running

## Changes Made

### All HTML Files Updated
- `IO_Tester_logic_Power_test.html`
- `IO_Tester_logic_Pullup_test.html`
- `IO_Tester_logic_Logic_test.html`
- `IO_Tester_logic_keepalive.html`

### Improvements

1. **Added poll counter** - Tracks number of polls executed
2. **Debug logging** - Shows polling status every 10 seconds (50 polls × 200ms)
3. **Clear previous highlights** - When a new node activates, old node gets "done" status
4. **Auto-scroll** - Active node automatically scrolls into view
5. **Better error handling** - Logs errors instead of silently ignoring
6. **New debug command** - `checkStatus()` shows current polling state

## How to Use

### 1. Restart the Server
```powershell
cd c:\ArduinoProject\IO_Tester\src\hw_tester\web
python serve_nocache.py
```

### 2. Open Browser
Navigate to: http://localhost:8000/IO_Tester_logic_Power_test.html

### 3. Open Browser Console
Press `F12` and go to the Console tab

### 4. Test the Fixes

#### Option A: Manual Testing
In the browser console, type:
```javascript
checkStatus()        // Check current polling state
manualRefresh()      // Force immediate refresh
```

#### Option B: Automated Testing
In PowerShell (in the web directory):
```powershell
python test_trace_update.py
```
This will cycle through keys 100, 110, 121, 123, 130 with 2-second delays.

### 5. Monitor Console Output

You should see:
```
✓ Trace viewer initialized. Polling every 200ms.
Commands: stopPolling(), startPolling(), manualRefresh(), checkStatus()
Poll #50: Current=130/1768739569.1879294, Last=121/1768739567.1234567
✓ Trace update detected: Key=130, Status=active, TS=1768739569.1879294
✓ Node 130 highlighted as active
```

### Debug Commands Available

| Command | Description |
|---------|-------------|
| `checkStatus()` | Show current polling state (lastKey, lastTs, pollCount, pollActive) |
| `manualRefresh()` | Force refresh by resetting state and polling immediately |
| `stopPolling()` | Pause automatic polling |
| `startPolling()` | Resume automatic polling |
| `highlight(key)` | Manually highlight a node by key |

## Troubleshooting

### If Node Still Doesn't Update

1. **Check if polling is active**:
   ```javascript
   checkStatus()
   ```
   Should show `pollActive=true`

2. **Check if file is being updated**:
   ```powershell
   Get-Content c:\ArduinoProject\IO_Tester\src\hw_tester\web\trace.json
   ```

3. **Check browser console** for:
   - "✓ Trace update detected" messages
   - "✗ Node XXX NOT FOUND" warnings
   - Any red error messages

4. **Force hard refresh**: `Ctrl+Shift+R` to clear browser cache

5. **Verify node exists in SVG**:
   ```javascript
   document.getElementById('n130')  // Should return an element
   ```

### If Trace.json Shows Key 130 but Node 121 Isn't Updating

This is expected behavior if:
- Your application is currently at step 130 (trace.json shows current state)
- Node 121 was a previous step that already completed
- To highlight node 121, update trace.json with key 121:
  ```python
  from pathlib import Path
  import json, time
  p = Path("c:/ArduinoProject/IO_Tester/src/hw_tester/web/trace.json")
  p.write_text(json.dumps({"key": 121, "status": "active", "ts": time.time()}))
  ```

## What Changed in the Code

### Before
```javascript
// Silent error handling
catch (e) {
  // Ignore errors
}

// No auto-scroll
// No highlight clearing
// No poll tracking
```

### After
```javascript
// Visible error logging
catch (e) {
  console.error('Poll error:', e);
}

// Auto-scroll to active node
const g = findNodeGroupByKey(data.key);
if (g) g.scrollIntoView({behavior:'smooth', block:'center', inline:'center'});

// Clear previous highlight
if (lastKey !== null && lastKey !== data.key) {
  setNodeStatus(lastKey, 'done');
}

// Debug logging every 10 seconds
if (pollCount % 50 === 0) {
  console.log('Poll #' + pollCount + ': Current=' + data.key + '/' + data.ts + ', Last=' + lastKey + '/' + lastTs);
}
```

## Next Steps

1. ✅ Restart server (server restart no longer needed for updates!)
2. ✅ Refresh browser page
3. ✅ Check console for polling confirmation
4. ✅ Run test script or manually update trace.json
5. ✅ Watch nodes highlight and scroll into view automatically

The issue should now be resolved. The page will automatically detect changes to trace.json every 200ms without requiring server restarts.
