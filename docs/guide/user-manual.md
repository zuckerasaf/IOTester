# User Manual

**Version 2.0.0 | September 2026**

---

## 1. Overview

IO Tester is a hardware verification application used to test the electrical integrity of connector pins on a unit under test (UUT). It drives stimulus signals through IO Spider cards and measures the resulting voltages through a Controllino Mega microcontroller, then compares them to expected values defined in a test Excel file.

## Four UUT test types are supported per pin

- **Power Test** - measures DC voltage on the pin, the test can include Analog Output (AO) command 
- **Pull-Up Test** - activates a pull-up and measures the resulting voltage enbale , the test can include  Digital Output (DO) command  
- **Logic Test** - create connetion betaeen pins on the connecter and reads the outcome Digital Input (DI) or Analog  Input (AI) or Incrametal Encoder (IE), the test can include  Digital Output (DO) command  
- **Cable Test** - checks continuity from a source connector pin to expected pins on one or more output connectors, and detects unexpected connections.

## Two internal system tests

- **Comm Test** - Checks communication with the Controllino board and IO Box. reports whether the hardware connection is available for testing.
- **I-BIT Test** - Scans connector pins on systems A and B for circuit faults, then optionally checks the card fuses paths using the fuse-test cable.

The separate test guides describe each procedure, configuration field, result,
and failure condition in detail.

Results are colour-coded in the pin table and can be exported to an Excel report.

---

## 2. System requirements

**Hardware:**

- Teste box (Controllino Mega) connected via USB (serial COM port)
- IO Box Connected to the test network (192.168.195.x)
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

The Qt application window is organized into three vertical areas:

1. **Pin Table** at the top, showing loaded connector pins and results.
2. **Control groups** in the middle: Connector / File, Run Controls, Log, and Test/Debug.
3. **Operational Log** at the bottom, showing live application and test messages.

![IO Tester application layout](../assets/images/application-layout.svg)

The layout contains the pin table at the top, four control groups in the
middle, and the Operational Log across the bottom.

---

## 4. Connector / File group

| Button | Action |
|---|---|
| **Settings** | Opens `Comm_settings.yaml` in the system text editor. Changes take effect on the next application launch. |
| **Load** | Opens a file browser to select an Excel test file (`.xlsx` or `.xlsm`). Populates the pin table and enables Test / Test_All. |
| **Report** | Saves the current pin table (including all test results) to an Excel file. |
| **DOC** | Opens a dialog to generate a Word document report from the available test data. |
| **Fails** | Opens a dialog to create a combined Excel report containing rows with failed results. |

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
When the sequence finishes, the Operational Log reports whether failures were recorded.

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
| **LocalHost / IO Box** | Switches IO card communication between network mode (192.168.195.x) and loopback mode (127.0.0.1). Setting is saved automatically. Switching from LocalHost to IO Box displays a restart-required message; restart IO Tester for IO Box mode to take effect. |
| **Next** | Used in Debug/Step mode only. Advances the test to the next checkpoint. |
| **Debug: True/False** | Enables or disables step-by-step debug mode. |
| **Wiki** | Opens the local HTML documentation site generated from the Markdown guides. |
| **Preset** | Selects the visible pin-table column preset. |

---

## 8. The pin table

The pin table displays all pins from the loaded test file. It has 22 columns:

| Column | Description | Editable |
|---|---|---|
| ID | Unique pin identifier (row number in test file) | No |
| Connect | Connector identifier (e.g. J1, J2) | No |
| Discrete Name | Functional name of the signal | No |
| Signal Name | Electrical signal name | No |
| Plug | Physical plug designation (e.g. 1P2) | No |
| Type | Pin type (Gnd/open, Open, RELAY, or `Cable`) | No |
| Pin | Physical pin number on the connector | No |
| Power Expected | Expected voltage (V) for power test | Yes |
| Power Input | IO card AO/DO command that applies the voltage | Yes |
| Power Measured | Voltage actually measured during power test | No |
| Power Result | Pass / Fail | No |
| Power Reason | Explanation of the result | No |
| PullUp Expected | Expected voltage after pull-up is activated | Yes |
| PullUp Input | Pull-up value or IO card DO command | Yes |
| PullUp Measured | Voltage measured after pull-up | No |
| PullUp Result | Pass / Fail | No |
| PullUp Reason | Explanation of the result | No |
| Logic Pin Input | Related pin for Logic tests; source connector name for Cable tests | Yes |
| Logic Command | Command sent to the IO card | Yes |
| Logic Expected | Expected DI, AI, or IE value; for Cable, allowed output connector pins | Yes |
| Logic DI Result | Pass / Fail | No |
| Logic DI Reason | Explanation of the result | No |

### Row colours

| Colour | Meaning |
|---|---|
| Yellow (bright) | This row is currently being tested |
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

For each selected pin, the tester chooses tests from the loaded row values:

| Row condition | Action |
|---|---|
| `Power_Expected` is populated and is not `-` | Run Power test |
| `PullUp_Input` is populated and is not `-` | Consider PullUp test |
| `Logic_Expected` is populated and is not `-` | Run Logic test |
| `Type` is `Cable` or `Card` is `Cable` | Run Cable test and skip Power, PullUp, and Logic |

An empty field or `-` skips that test. The PullUp test has an additional
prerequisite: the Power test must pass and `Power_Expected` must be `0.0 V`.

See the dedicated guides for complete procedures:

- [Power Test](power-test.md)
- [PullUp Test](pullup-test.md)
- [Logic Test](logic-test.md)
- [Cable Test](cable-test.md)

### Cable Test: connector continuity

A Cable Test is selected when the row's `Type` or `Card` field is `Cable`. It
replaces Power, PullUp, and Logic tests for that row. The source connector is
read from `Logic_Pin_Input`; the source pin number is taken from the trailing
number in the row's `ID` (for example, `J1-01` means pin 1). Connector sizes,
offsets, and input/output roles are read from the active `Connectors` settings.

Enter the allowed output pins in `Logic_Expected`, using a connector name and
parenthesized, comma-separated pin numbers:

```text
K(1),L(1)
G(11,13,14,15)
```

The test scans **every pin** on each output connector named in `Logic_Expected`.
Listed pins are expected to be connected; other pins on those connectors are
expected to remain disconnected.

| Input connector | Supported output connector combinations |
|---|---|
| `C` | `D`, `G`, `K`, `K` + `L` |
| `E` | `F`, `F` + `G`, `F` + `L`, `J`, `J` + `K`, `J` + `K` + `L` |
| `H` | `I`, `I` + `J`, `I` + `J` + `K`, `I` + `J` + `K` + `L` |

Before routing, the test requires the source connector to have `Type: input`,
each target connector to have `Type: output`, and the connector combination to
appear in the table above. Invalid connector roles or combinations fail with a
`Wrong connector configuration` message.

The source pin is routed through the mux, then the pull-up and general relay are
activated. Each output pin is routed and measured. Expected connected pins are
compared with `scale.fuse_voltage_test`; other scanned pins are compared with
`scale.zero_voltage_threshold`. Both comparisons use `scale.voltage_tolerance`.
The Operational Log records a voltage and Pass/Fail result for every scanned
pin. The Cable result and reason are written to the Logic result fields in the
pin table. Pull-up, relay, and mux cleanup are attempted on every return path.

For configuration examples and full failure conditions, see the [Cable Test
Guide](cable-test.md).

---

## 10. I-BIT test (built-in test)

For the complete I-BIT procedure, fuse-test cable instructions, configuration,
results, and troubleshooting, see the dedicated [I-BIT Test Guide](ibit-test.md).

The I-BIT test is an automated scan of all 50 connector pins on both system A and system B (100 circuit measurements total). It does **not** require a test file to be loaded.

**Purpose:** Detect short-circuit or open-circuit faults across the full connector before running individual pin tests.

**Procedure per pin:**

1. Mux matrix routes the pin to the measurement ADC.
2. Voltage measured BEFORE pull-up (expected: ~0V).
3. Pull-up activated.
4. Voltage measured AFTER pull-up (expected: ~4V).
5. Both measurements compared to tolerances from settings.

After the circuit scan, the application displays a fuse-test prompt:

- **Continue** - connect the fuse-test cable to system A and run the fuse test.
- **Ignore** - skip the fuse test; the skipped fuse result is treated as passed.

The fuse test runs only on system A. It uses the dedicated
`pullup_fuse_test` board pin and compares the post-pull-up voltage with
`scale.fuse_voltage_test`.

**Results:**

- IBIT button turns **GREEN** - all circuit checks passed and the fuse test passed or was ignored.
- IBIT button turns **RED** - one or more circuit checks failed or the fuse test failed.
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
- All test results (Power, PullUp, Logic, and Cable) and reason text
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

When switching from LocalHost to IO Box using the connection button, the
application displays a **Restart Required** message. Restart IO Tester for the
IO Box connection mode to take effect.

---

## 15. Debug / step mode

Debug mode allows step-by-step execution of test procedures for verification or fault-finding.

**Activating:** Click **[ Debug: False ]** to toggle to **[ Debug: True ]**.

**Behaviour when active:** The test pauses at internal checkpoints and writes status to a trace file. The log shows:

```
in node {N} Waiting for Next button press...
```

**Advancing:** Click **[ Next ]** to proceed to the next checkpoint. Repeat until the test completes.

**Documentation and reports:**

- Click **[ DOC ]** in the Connector / File group to generate a Word document report.
- Click **[ Wiki ]** in the Test/Debug group to open the local HTML documentation site.

**Turning off:** Click **[ Debug: True ]** to toggle back to **[ Debug: False ]**.

---

## 16. Understanding test results

### 16.1 Result values

| Value | Meaning |
|---|---|
| Pass | The measured value is within the defined tolerance of the expected. |
| Fail | The measured value is outside tolerance. |
| --- | The test was not run (column empty in the test file, or skipped due to a prerequisite). |

### 16.2 Test selection and test skip conditions

Power, PullUp, and Logic tests are selected from populated row fields. The
PullUp test is then automatically skipped if:

- `PullUp_Input` is empty or `-`
- `Power_Expected` is not 0V (the pin has DC power on it)
- The Power test for that pin failed

The Logic test is skipped when:

- `Logic_Expected` is empty or `-`, so the row does not select a Logic test.
- `Logic_Pin_Input` is empty or set to `none`; the Logic function logs that no
  related pin was specified and returns a successful skip.

Rows marked as Cable tests skip Power, PullUp, and Logic and use the Cable test
path instead.

After the selected rows finish, the Operational Log reports whether the run
recorded failures and, when applicable, the failure count.

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
- Fuse test, when Continue is selected: before fuse pull-up is approximately 0V and after fuse pull-up is within tolerance of `scale.fuse_voltage_test`
- Fuse test, when Ignore is selected: fuse result is treated as passed

### 16.5 Comm Test pass/fail criteria

The Comm Test passes only when both communication checks succeed:

- Every configured Controllino digital port accepts the pulse sequence.
- Every enabled IO card responds successfully to its network ping.

The Comm Test fails when a digital port reports an invalid state, a pulse
operation raises an error, an enabled IO card does not respond, or no enabled
UDP cards are available. The Comm Check button turns green for success and red
when the overall result fails.

### 16.6 Common failure reasons

| Reason | Description |
|---|---|
| "Measurement is out of tolerance" | Voltage differs from expected by more than the configured tolerance. Check wiring and the UUT. |
| "Analog pin not found in pin map" | The board configuration does not have a mapping for the required analog channel. |
| "Failed to set mux bits" | The Controllino did not respond correctly to the matrix command. Run Comm Check. |
| "Relay did not operate" | (I-BIT only) The general relay did not close/open as expected. Check relay wiring. |
| Fuse test fails | Check the system-A fuse cable, `pullup_fuse_test`, and `scale.fuse_voltage_test`, or choose Ignore when the fuse test is not required. |

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
| Logic test fails immediately | Related pin is missing or has no passing Power result | Check `Logic_Pin_Input` and run the related pin's Power test first |
| Fuse prompt appears | Circuit IBIT has completed | Connect the system-A fuse cable and choose Continue, or choose Ignore to skip |
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
