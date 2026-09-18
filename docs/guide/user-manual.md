# User Manual

**Version 1.0 | June 2026**

---

## 1. Overview

IO Tester is a hardware verification application used to test the electrical integrity of connector pins on a unit under test (UUT). It drives stimulus signals through IO cards (C1-C5) and measures the resulting voltages through a Controllino Mega microcontroller, then compares them to expected values defined in a test Excel file.

Three test types are supported per pin:

- **Power Test** - measures DC voltage on the pin
- **Pull-Up Test** - activates a pull-up and measures the resulting voltage
- **Logic Test** - commands a digital output and reads a digital input

Results are colour-coded in the pin table and can be exported to an Excel report.

---

## 2. System requirements

**Hardware:**

- Controllino Mega connected via USB (serial COM port)
- IO Cards C1-C5 connected to the test network (192.168.195.x)
- UUT connected to the test fixture

**Software / OS:**

- Windows 10 or later (64-bit)
- No additional installation required - `IO_Tester.exe` is self-contained

**Files required at runtime** (same folder as the EXE or configured path):

- `config\Comm_settings.yaml` - communication settings
- `config\pin_map.json` - Controllino pin assignments
- `config\board_pin_config.json` - board-specific pin names
- `config\connector_Address_A_map.xlsx` - connector A mux mapping
- `config\connector_Address_B_map.xlsx` - connector B mux mapping

---

## 3. Application layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Pin Table  (scrollable, 22 columns)                                     │
│  Rows colour: yellow=testing  green=pass  pink=fail  dark=not tested     │
├──────────────────┬──────────────────────────┬───────┬────────────────────┤
│ Connector / File │     Run Controls          │  Log  │  Test / Debug      │
│ Settings  Load   │ Test  Test_All  Stop      │  INF  │ Comm Check  Sim    │
│ Report    DOC    │ Testing Pin:  Power:  …   │  SUC  │ IBIT        Local  │
│                  │                           │  WRN  │ Stop IBIT   Next   │
│                  │                           │  ERR  │             Debug  │
│                  │                           │  DBG  │        [html file] │
│                  │                           │ Clear │                    │
├──────────────────┴──────────────────────────┴───────┴────────────────────┤
│  Operational Log                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Connector / File group

| Button | Action |
|---|---|
| **Settings** | Opens `Comm_settings.yaml` in the system text editor. Changes take effect on the next application launch. |
| **Load** | Opens a file browser to select an Excel test file (`.xlsx` or `.xlsm`). Populates the pin table and enables Test / Test_All. |
| **Report** | Saves the current pin table (including all test results) to an Excel file. |
| **DOC** | Opens the HTML flow diagram for the currently selected debug scenario in the default web browser. A local HTTP server starts automatically. Click DOC again to stop the server. |

The **Connector** field (read-only) displays the name of the currently loaded connector / test file.

---

## 5. Run Controls group

| Button | Action |
|---|---|
| **Test** | Runs tests only on the rows currently selected in the pin table. Disabled until a test file is loaded. |
| **Test_All** | Runs tests on every pin in the table sequentially, top to bottom. Disabled until a test file is loaded. |
| **Stop** | Stops the running test after the current pin finishes. Active only while a test is in progress. |

The **status bar** (updated live during a test run) shows:

- **Testing Pin** - ID of the pin currently under test
- **Power** - Pass / Fail result of the last power measurement
- **Pullup** - Pass / Fail result of the last pull-up measurement
- **Logic** - Pass / Fail result of the last logic measurement

All labels reset to "---" when a new test sequence starts.

---

## 6. Log group

The checkboxes filter which message types appear in the Operational Log:

| Filter | Colour | Meaning |
|---|---|---|
| INF | White / light grey | General information messages |
| SUC | Green | Test pass events |
| WRN | Yellow / orange | Warnings - tests failed, pins skipped |
| ERR | Red | Errors - hardware faults, file errors |
| DBG | Dark grey | Verbose debug messages (normally off) |

**[ Clear ]** removes all text from the Operational Log. Test results in the pin table are unaffected.

---

## 7. Test / Debug group

| Control | Action |
|---|---|
| **Comm Check** | Sends a ping to the Controllino and reports success or failure. Use before running tests to verify hardware connection. |
| **IBIT** | Starts the Built-In Test (see [Section 10](#10-i-bit-test-built-in-test)). Button turns GREEN (all pass) or RED (any fail). |
| **Stop IBIT** | Stops the I-BIT test after the current pin. Active only during I-BIT. |
| **Simulation: On/Off** | Toggles simulation mode. ON = simulated random voltages, no hardware needed. OFF = real hardware. Setting is saved automatically. |
| **LocalHost** | Switches IO card communication between network mode (192.168.195.x) and loopback mode (127.0.0.1). Setting is saved automatically. |
| **Next** | Used in Debug/Step mode only. Advances the test to the next checkpoint. |
| **Debug: True/False** | Enables or disables step-by-step debug mode. |
| **HTML file dropdown** | Selects which HTML flow diagram is opened by the DOC button. |

---

## 8. The pin table

The pin table displays all pins from the loaded test file. It has 22 columns:

| Column | Description |
|---|---|
| ID | Unique pin identifier (row number in test file) |
| Connect | Connector identifier (e.g. J1, J2) |
| Discrete Name | Functional name of the signal |
| Signal Name | Electrical signal name |
| Plug | Physical plug designation (e.g. 1P2) |
| Type | Pin type (Gnd/open, Open, RELAY, etc.) |
| Pin | Physical pin number on the connector |
| Power Expected | Expected voltage (V) for power test |
| Power Input | IO card command that applies the voltage (e.g. C1_AO2_10) |
| Power Measured | Voltage actually measured during power test |
| Power Result | Pass / Fail |
| Power Reason | Explanation of the result |
| PullUp Expected | Expected voltage after pull-up is activated |
| PullUp Input | IO card command for the pull-up signal |
| PullUp Measured | Voltage measured after pull-up |
| PullUp Result | Pass / Fail |
| PullUp Reason | Explanation of the result |
| Logic Pin Input | IO card command for the logic stimulus |
| Logic Command | Command sent to the IO card |
| Logic Expected | Expected digital state (High / Low) |
| Logic DI Result | Pass / Fail |
| Logic DI Reason | Explanation of the result |

### Row colours

| Colour | Meaning |
|---|---|
| Yellow (bright) | This row is currently being tested |
| Green | At least one test passed; no failures |
| Pink | At least one test failed |
| Dark (alternating) | Row has not been tested yet in this session |

### Sorting

Click any column header to sort ascending; click again for descending. A small arrow (↑ or ↓) shows the active sort column.

### Editing input cells

The following columns can be edited directly in the table by double-clicking:

- Power Expected, Power Input
- PullUp Expected, PullUp Input
- Logic Pin Input, Logic Command, Logic Expected

Changes take effect immediately for the next test run.

### Selection

- Click a row to select it
- `Ctrl+click` to add rows to the selection
- `Shift+click` to select a range
- Selected rows are tested when **[ Test ]** is clicked

---

## 9. Test types explained

For each pin the tester determines which tests to run based on whether the corresponding Expected / Input columns are filled in the test file. A column left empty or set to `-` means that test is skipped for that pin.

### 9.1 Power test

**Purpose:** Verify that the correct DC voltage is present on the pin.

**Procedure:**

1. The mux matrix routes the pin to the measurement ADC.
2. If a `Power_Input` is specified (e.g. `C2_AO2_10`), the IO card applies the stimulus voltage before measurement.
3. Voltage is measured via the Controllino analog input.
4. Measured value is compared to `Power_Expected` ± tolerance.
5. Result: Pass if within tolerance, Fail otherwise.

**Power_Input format:** `C{card}_{type}{num}_{value}`

```
C2_AO2_10  →  Card 2, Analog Output 2, set to 10V
C3_DO5_1   →  Card 3, Digital Output 5, set to HIGH
```

If `Power_Input` is empty, the voltage is measured passively.

### 9.2 Pull-up test

**Purpose:** Verify that a pull-up resistor network is functional.

**Prerequisite:** Power test must have passed AND `Power_Expected` must be 0V. If power is present on the line, the pull-up test is skipped.

**Procedure:**

1. The pull-up pin (defined in `PullUp_Input`) is activated via the IO card digital output.
2. The resulting voltage is measured.
3. Compared to `PullUp_Expected` ± tolerance.

### 9.3 Logic test

**Purpose:** Verify discrete digital input/output functionality.

**Procedure:**

1. A digital command is sent to the IO card (`Logic_Command`).
2. The resulting digital state of the pin is read back as a DI.
3. Compared to `Logic_Expected` ("High" or "Low").

---

## 10. I-BIT test (built-in test)

The I-BIT test is an automated scan of all 50 connector pins on both system A and system B (100 measurements total). It does **not** require a test file to be loaded.

**Purpose:** Detect short-circuit or open-circuit faults across the full connector before running individual pin tests.

**Procedure per pin:**

1. Mux matrix routes the pin to the measurement ADC.
2. Voltage measured BEFORE pull-up (expected: ~0V).
3. Pull-up activated.
4. Voltage measured AFTER pull-up (expected: ~4V).
5. Both measurements compared to tolerances from settings.

**Results:**

- IBIT button turns **GREEN** - all 100 pins passed both measurements.
- IBIT button turns **RED** - one or more pins failed.
- Full per-pin results in the Operational Log.

Runtime: approximately 3-8 minutes depending on stabilization delays.

To stop early: click **[ Stop IBIT ]**.

---

## 11. Log window

The Operational Log records all application events in real time.

**Message format:** `[HH:MM:SS]  message text`

| Colour | Level | Meaning |
|---|---|---|
| White / light grey | INFO | General events |
| Green | SUCCESS | Tests passed |
| Yellow / orange | WARNING | Tests failed, pins skipped |
| Red | ERROR | Hardware faults, file errors |
| Dark grey | DEBUG | Verbose internal messages |

Recommended settings during normal operation: INF ☑ SUC ☑ WRN ☑ ERR ☑ DBG ☐

---

## 12. Saving a report

Click **[ Report ]** after a test run to save results to Excel.

The report file contains:

- All 22 pin table columns
- All test results (Power, PullUp, Logic) and reason text
- A timestamp row at the top

**Recommended naming convention:**

```
UUT_serial_ConnectorID_YYYY-MM-DD.xlsx
Example: SN1042_J1_2026-06-25.xlsx
```

---

## 13. Configuration (Comm_settings.yaml)

Located in: `config\Comm_settings.yaml` (same folder as the EXE). Click **[ Settings ]** to open in a text editor.

### Board section

```yaml
Board:
  Type: ControllinoMega   # Hardware type (do not change)
  Port: COM5              # Serial COM port of the Controllino USB cable
  BaudRate: 115200        # Serial baud rate (do not change)
  simulation: false       # true = simulation mode, false = real hardware
```

!!! warning
    Change `Port` to match the actual COM port assigned by Windows.
    To find the COM port: Device Manager → Ports (COM & LPT)

### UDP_Settings section

```yaml
UDP_Settings:
  Frequency_Hz: 20.0
  Communication_Timeout: 2.0
  localhost_mode: false
```

Cards C1-C5 (C6-C7 disabled by default):

```yaml
  card_id: 1
  enabled: true
  send_ip: 192.168.195.11
  send_port: 2880
  receive_ip: 192.168.195.101
  receive_port: 1011
```

After editing `Comm_settings.yaml`, **restart the application** for changes to take effect.

---

## 14. Simulation and localhost modes

### 14.1 Simulation mode

Activated by clicking **[ Simulation: On ]** or by setting `Board.simulation: true` in `Comm_settings.yaml`.

In simulation mode:

- No serial communication with the Controllino occurs.
- Voltage measurements return random values within realistic ranges.
- Tests complete normally and produce Pass/Fail results.
- Use for demonstrations, training, or office testing without hardware.

The button label shows the current state:

- `Simulation: On` - simulation active (orange/yellow button)
- `Simulation: Off` - real hardware active (default button)

### 14.2 Localhost mode

Activated by clicking **[ LocalHost ]** or by setting `UDP_Settings.localhost_mode: true`.

In localhost mode:

- IO card commands are sent to 127.0.0.1 instead of the real card IPs.
- A local simulator responds to the commands.
- The Controllino (serial) still communicates normally unless Simulation mode is also ON.
- Use for bench testing when IO cards are not present.

---

## 15. Debug / step mode

Debug mode allows step-by-step execution of test procedures for verification or fault-finding.

**Activating:** Click **[ Debug: False ]** to toggle to **[ Debug: True ]**.

**Behaviour when active:** The test pauses at internal checkpoints and writes status to a trace file. The log shows:

```
in node {N} Waiting for Next button press...
```

**Advancing:** Click **[ Next ]** to proceed to the next checkpoint. Repeat until the test completes.

**HTML visualization:**

1. Select an HTML file in the dropdown (bottom of Test/Debug group).
2. Click **[ DOC ]** to open the flow diagram in your browser.
3. The currently active node in the flow is highlighted automatically.
4. The browser polls for updates every 500 ms.

**Turning off:** Click **[ Debug: True ]** to toggle back to **[ Debug: False ]**.

---

## 16. Understanding test results

### 16.1 Result values

| Value | Meaning |
|---|---|
| Pass | The measured value is within the defined tolerance of the expected. |
| Fail | The measured value is outside tolerance. |
| --- | The test was not run (column empty in the test file, or skipped due to a prerequisite). |

### 16.2 Pull-up test skip conditions

The PullUp test is automatically skipped if:

- `Power_Expected` is not 0V (the pin has DC power on it)
- The Power test for that pin failed

The log will explain the skip with a WARNING message.

### 16.3 Tolerances

The voltage tolerance is set in `Comm_settings.yaml`:

```yaml
Test:
  voltage_degredation: 3.0   # default: ±3 V
```

A measured voltage is considered Pass if: `|measured - expected| ≤ tolerance`

### 16.4 I-BIT pass/fail criteria

- Before pull-up: measured voltage ≤ tolerance from 0V
- After pull-up: `|measured - 4.0V| ≤ tolerance`

### 16.5 Common failure reasons

| Reason | Description |
|---|---|
| "Measurement is out of tolerance" | Voltage differs from expected by more than the configured tolerance. Check wiring and the UUT. |
| "Analog pin not found in pin map" | The board configuration does not have a mapping for the required analog channel. |
| "Failed to set mux bits" | The Controllino did not respond correctly to the matrix command. Run Comm Check. |
| "Relay did not operate" | (I-BIT only) The general relay did not close/open as expected. Check relay wiring. |

---

## 17. Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| Hardware warning at startup | Wrong COM port or cable not seated | Open Settings, change `Board.Port` to correct COM; reconnect cable |
| Comm Check fails | Controllino not ready or firmware issue | Unplug/replug USB, restart Controllino |
| "UDP binding error" on startup | Port already in use by another process | Close other IO Tester instances; reboot PC |
| All pins Fail | Simulation mode ON / wrong connector map / UUT not seated | Toggle Simulation: Off; check fixture seating |
| Test / Test_All greyed out | No file loaded | Click Load first |
| Pull-up tests all skipped | `Power_Expected` ≠ 0 in test file | PullUp only runs when Power Expected = 0V |
| I-BIT button stays dark | Test is complete | Normal - colour shows green=pass, red=fail |
| Application does not start | Missing config files | Verify `config\` folder is present next to EXE |
| Log window is empty | All log filters off | Check INF/SUC/WRN/ERR checkboxes in Log group |

---

## 18. Keyboard and mouse shortcuts

**Pin Table:**

| Action | Shortcut |
|---|---|
| Select single row | Click row |
| Add / remove row from selection | Ctrl + Click |
| Select a range of rows | Shift + Click |
| Sort by column | Click column header (click again to reverse) |
| Open inline editor | Double-click cell (editable columns only) |
| Show full cell content | Hover over cell |

!!! note
    There are no keyboard shortcuts for buttons - use the mouse.
    The Next button (debug mode) can be clicked rapidly to step quickly.
