# System Flows

This document describes the operational flows in the IO Tester application. The application is implemented as a Qt/PySide6 desktop client. Update this file when adding new features or modifying existing workflows.

---

## Operator workflow summary

This is the single source of truth for the end-to-end user workflow. The [design document](design-document.md#8-user-workflow) links here instead of duplicating it. Detailed flows are in the sections referenced below.

| Step | Operator action | What the system does | Details |
|---|---|---|---|
| 1. Startup | Launch the application | Loads settings, initializes hardware (real board or simulation), loads pin map and board config, creates the Qt window and controller, wires buttons | Section 1 |
| 2. Load connector | Click **LOAD** and pick an Excel file | Parses the file, maps connector metadata to table rows, populates the pin table, enables **TEST** and **TEST ALL** | Section 2 |
| 3. Run pin tests | Select rows and click **TEST**, or click **TEST ALL** | Per pin: highlights the row, clears the mux, runs the applicable Power / PullUp / Logic / Cable test, applies pass/fail logic, updates row colors, logs results | Sections 3, 16 |
| 4. I-BIT | Click **IBIT** (no connector file needed) | Prompted circuit check on systems A and B, then prompted fuse check on system A; stops at the next pin when **STOP IBIT** is pressed | Section 4 |
| 5. Report | Click **REPORT** | Exports all table rows to a timestamped Excel file after the operator confirms the filename | Section 9 |

Notes:

- **TEST** and **TEST ALL** require a loaded connector; otherwise a "Not connected" warning is shown.
- Cable rows (`Type` or `Card` is `Cable`) run only the Cable Test and skip Power, PullUp, and Logic tests (Section 3.3). It reads the input connector from `Logic_Pin_Input` and allowed output pins from `Logic_Expected` (for example, `G(11,13,14,15)`), validates connector roles and combinations before routing, scans all pins on each named output connector, and deactivates the pull-up and relay during cleanup.
- I-BIT detects short circuits, open circuits, wiring failures, and unexpected leakage or stuck states.

---

## 1. Application initialization flow

```
START → main() in app.py
  |
  ├─→ LOAD SETTINGS
  |     └─→ load_settings() from config/Comm_settings.yaml
  |           ├─→ Board: Type, Port, BaudRate, simulation flag
  |           ├─→ CardSettings: C1–C7 UDP IPs and ports
  |           ├─→ Test: voltage_degredation tolerance
  |           ├─→ Timeouts: pins_to_stabilize, etc.
  |           ├─→ Measure_value: Scale_1 factor
  |           └─→ Debug: per-section debug flags
  |
  ├─→ HARDWARE INITIALIZATION
  |     └─→ initialize_hardware(settings, log_callback=_buffer_log)
  |           ├─→ Check Board->Type ("ControllinoMega", "none", …)
  |           ├─→ Create ControllinoIO instance
  |           |     ├─→ Open serial port (default COM5, 115200 baud)
  |           |     ├─→ Wait 2s for Arduino reset
  |           |     ├─→ Clear input buffer
  |           |     ├─→ Send ping command "?"
  |           |     ├─→ Wait for "OK" response
  |           |     └─→ IF fail AND simulation=True: continue in no-connection mode
  |           ├─→ Load connector address mapping (Excel)
  |           └─→ RETURN hardware object (or None if type=="none")
  |
  ├─→ LOAD PIN MAP AND BOARD CONFIG
  |     ├─→ get_board_pin_map(settings)    → pin_map dict  (pin_map.json)
  |     └─→ get_board_pin_config(settings) → board_config dict (board_pin_config.json)
  |
  ├─→ CREATE Qt APPLICATION
  |     └─→ QApplication(sys.argv)
  |
  ├─→ CREATE MAIN WINDOW
  |     └─→ MainWindowQt
  |           ├─→ Apply dark.css stylesheet
  |           ├─→ Build layout: PinTableQt / Run Controls / LogView
  |           └─→ Initialize _pending_callbacks dict
  |
  ├─→ CREATE MAIN CONTROLLER
  |     └─→ MainController(main_window)
  |           ├─→ Create Measurer, PinPulser, UDPCardManager
  |           ├─→ Create TestHandle
  |           └─→ Wire all button signals to controller slots
  |
  ├─→ FLUSH BUFFERED INIT LOGS → append to LogView
  |
  └─→ START Qt EVENT LOOP
        └─→ sys.exit(app.exec())
```

---

## 2. Pin configuration loading flow

```
USER CLICKS "LOAD":
  MainController.on_load()
    ↓
  QFileDialog.getOpenFileName() — start dir: Paths.database (default tests/DB); filters: *.xlsx *.xls, all files
    ↓
  Connector name = file stem → shown in connector field
    ↓
  load_connector_from_excel(filepath)
    ├─→ Open workbook with openpyxl
    ├─→ Read "Connectors" worksheet (or first sheet)
    ├─→ FOR each data row: parse columns and build row dict
    └─→ RETURN List[dict]
    ↓
  main_window.table.set_rows(rows)
    ├─→ beginResetModel()
    ├─→ Convert each dict to list[str] ordered by COLUMNS tuple
    ├─→ Build _row_id_map {pin_id → row_index}
    └─→ endResetModel() — table repaints
    ↓
  Enable btn_test, btn_test_all
    ↓
  Log: "Loaded {count} pins from {filename}"
```

**Excel column mapping (22 display columns):**

```
ID, Connect, Discrete_Name, Signal_Name, Plug, Type, Pin,
Power_Expected, Power_Input, Power_Measured, Power_Result, Power_Result_Reason,
PullUp_Expected, PullUp_Input, PullUp_Measured, PullUp_Result, PullUp_Result_Reason,
Logic_Pin_Input, Logic_Command, Logic_Expected, Logic_DI_Result, Logic_DI_Result_Reason
```

---

## 3. Test execution flow (Power / Pullup / Logic / Cable)

### 3.1 Single pin test

```
USER SELECTS ROW(S) AND CLICKS "TEST":
  MainController.on_test()
    ↓
  IF not connected (no connector loaded) → warning → RETURN
    ↓
  selected_ids = main_window.table.get_selected_ids()
    ↓
  IF empty → show warning → RETURN
    ↓
  clear_test_results(), table.clear_selection()
    ↓
  Create QtTableAdapter(main_window, controller)
    ↓
  threading.Thread(target=run_test, daemon=True).start()

INSIDE run_tests() — background thread:
  FOR each pin_id in selected_ids:
    ├─→ IF not self.running: break
    ├─→ Look up pin_row from all_rows by ID
    ├─→ Create Pin object from row data
    ├─→ Highlight row yellow: pin_table.set_testing_pin(pin.Id)
    ├─→ Determine which tests to run:
    |     run_power_test  = Power_Expected not empty or "-"
    |     run_pullup_test = PullUp_Input not empty or "-"
    |     run_logic_test  = Logic_Expected not empty or "-"
    |     run_cable_test  = Type == "Cable" or Card == "Cable"
    |     if run_cable_test, disable power, pull-up, and logic tests for this row
    ├─→ clear_mux_bits(pin_map, hardware, log)
    ├─→ IF run_power_test:
    |     power_test(self, pin)
    |     pin_table.update_row(pin.Id, {Power_Measured, Power_Result, …})
    ├─→ IF run_pullup_test (and power passed at 0V):
    |     pullup_test(self, pin)
    |     pin_table.update_row(pin.Id, {PullUp_Measured, PullUp_Result, …})
    ├─→ IF run_logic_test:
    |     logic_test(self, pin, all_rows)
    |     pin_table.update_row(pin.Id, {Logic_DI_Result, …})
    ├─→ IF run_cable_test:
    |     Cable_test(self, pin, all_rows)
    |     pin_table.update_row(pin.Id, {Logic_DI_Result, Logic_DI_Result_Reason})
    └─→ pin_table.set_testing_pin(None) — clear yellow highlight
```

### 3.2 Test all

Same as above but `selected_ids` = ALL row IDs from the table.

### 3.3 Cable Test

```text
run_tests() identifies a cable row (Type or Card == "Cable")
  ↓
Cable_test(test_handle, pin, all_rows)
  ├─→ Read source connector from Logic_Pin_Input and source pin from ID
  ├─→ Parse Logic_Expected connector groups and comma-separated pin numbers
  ├─→ Validate connector Type values from settings:
  |     source must be Type: input; targets must be Type: output
  ├─→ Validate the supported input-to-output connector combination
  ├─→ Resolve pin mapping, route source pin, activate pull-up and general relay
  ├─→ FOR each named output connector:
  |     └─→ Scan every connector pin through the mux and measure voltage
  ├─→ Compare listed pins to fuse_voltage_test and unlisted pins to zero_voltage_threshold
  ├─→ Log each pin's voltage and pass/fail result
  └─→ Deactivate pull-up and relay; clear mux on every return path
```

`Logic_Expected` examples:

```text
K(1),L(1)
G(11,13,14,15)
```

Supported connector combinations are validated by the cable test:

| Input | Output connector combinations |
|---|---|
| `C` | `D`, `G`, `K`, `K` + `L` |
| `E` | `F`, `F` + `G`, `F` + `L`, `J`, `J` + `K`, `J` + `K` + `L` |
| `H` | `I`, `I` + `J`, `I` + `J` + `K`, `I` + `J` + `K` + `L` |

Connector roles, sizes, and offsets are read from the active `Connectors` settings. An invalid role or unsupported combination returns a failed test with a `Wrong connector configuration` message before routing the test pins.

---

## 4. I-BIT test flow

```
USER CLICKS "IBIT":
  MainController.on_ibit()
    ↓
  test_handler.running_ibit = True  (ignored with a warning if already running)
    ↓
  threading.Thread(target=run_ibit_thread, daemon=True).start()

INSIDE run_ibit_thread():
  ├─→ ibit_test(test_handler, _request_fuse_test_prompt, _request_ibit_test_prompt)
  |     ├─→ Prompt: run circuit checks? (No → skip to fuse prompt)
  |     ├─→ ibit_A = measure_all_pins_system("a", 4.0, is_simulation, 51)
  |     ├─→ ibit_B = measure_all_pins_system("b", 4.0, is_simulation, 51)
  |     ├─→ Compute: total / passed / failed counts
  |     ├─→ Prompt: run fuse test? (Continue → Fuses_test("a", …) on system A only)
  |     └─→ Log summary and result: SUCCESS or FAILURE (circuit AND fuse must pass)
  ├─→ Update IBIT button color by result
  └─→ _on_ibit_complete (UI thread): reset buttons, log "I_Bit test sequence completed"

measure_all_pins_system(system, voltage, isSimulate, pinNumber):
  ├─→ relay_general_operate(True)    — close relay 15
  ├─→ FOR current_pin in range(1, pinNumber):
  |     ├─→ IF not running_ibit: break
  |     ├─→ clear_mux_bits()
  |     ├─→ get_pin_pair_info_controlino(current_pin)
  |     ├─→ connector_pin_to_bits(current_pin, system) → bits dict
  |     ├─→ set_mux_bits(bits, …) → route pin to ADC
  |     ├─→ STEP 3: Measure voltage BEFORE pullup (expected ~0V)
  |     ├─→ STEP 4: Validate ~0V; log SUCCESS or append to failed_pins
  |     ├─→ STEP 6: Activate pullup; time.sleep(pins_to_stabilize)
  |     ├─→ STEP 8: Measure voltage AFTER pullup (expected ~4V)
  |     ├─→ STEP 9: Validate against expected voltage; log result
  |     └─→ STEP 10: Deactivate pullup
  ├─→ relay_general_operate(False)   — open relay 15
  └─→ RETURN (voltage_measurements, all_tests_passed, failed_pins)
```

**Stop I-BIT:**

```
MainController.on_stop_ibit()
  ↓
test_handler.running_ibit = False
  ↓
Background thread exits its pin loop at next iteration check
  ↓
Buttons reset and clear_mux_bits() is called so all mux pins are shut down
```

See the [I-BIT guide](../guide/ibit-test.md) for the per-pin circuit and fuse steps.

---

## 5. Hardware communication flow

### 5.1 Serial communication (Controllino)

**Digital write:**

```python
hardware.digital_write(port, value)
  ├─→ IF not connected: return (no-op)
  ├─→ Acquire thread lock
  ├─→ Send: "W,{port},{1 or 0}\n"
  ├─→ Read: serial.readline()
  ├─→ Expect: "OK:W,{port},{value}"
  └─→ Release lock
```

**Analog read:**

```python
hardware.analog_read(port)
  ├─→ IF not connected: return simulated value
  ├─→ Acquire thread lock
  ├─→ Send: "R,{port}\n"
  ├─→ Read: serial.readline()
  ├─→ Expect: "OK:R,{port},{voltage}"
  ├─→ Parse float
  └─→ RETURN voltage (or 0.0 on error)
```

**Serial protocol (Arduino firmware):**

| Command | Response |
|---|---|
| `?\n` | `OK` (ping) |
| `W,{p},{v}\n` | `OK:W,{p},{v}` (digital write) |
| `R,{p}\n` | `OK:R,{p},{voltage}` (analog read) |

### 5.2 Simulation mode

When `settings['Board']['simulation'] == True`:

- `digital_write` is a no-op
- `analog_read` / `measure_voltage` returns a random value in a test-specific range

---

## 6. Mux matrix control flow

The mux routes one of 50 connector pins through a 16-bit MUX to the ADC.

```python
set_mux_bits(bits, current_pin, pin_map, hardware, settings, log):
  # bits: dict {digital_pin_name → True/False}
  FOR each (name, value) in bits:
    port = pin_map['D'][name]
    hardware.digital_write(port, value)
  RETURN True on success, False on error

clear_mux_bits(pin_map, hardware, log):
  # Sets ALL digital outputs in pin_map['D'] to False (0V)

connector_pin_to_bits(connector_pin_number, system):
  # Reads connector_Address_{system}_map.xlsx
  # Returns bit dict: {D0..D15 column names → True/False}

relay_general_operate(operate: bool):
  # Controls the general relay (relay 15)
  hardware.digital_write(pin, operate)
  time.sleep(pins_to_stabilize)
```

---

## 7. Voltage measurement flow

```python
measurer.measure_voltage(analog_port):
  IF simulation:
    RETURN simulated voltage

  Sample loop over configured duration:
    WHILE time < end_time:
      reading = hardware.analog_read(analog_port)
      readings.append(reading)
      sleep(sample_interval)

  average = mean(readings)
  scaled  = average * scale_factor   # from settings['Measure_value']['Scale_1']
  RETURN scaled voltage
```

**Key parameters (settings.yaml):**

| Setting | Default | Description |
|---|---|---|
| `Measure_value.Scale_1` | 1.0 | Voltage divider / ADC calibration factor |
| `Timeouts.pins_to_stabilize` | 0.5 s | Wait time after relay/pin change |
| `Test.voltage_degredation` | 3.0 V | Measurement tolerance |

---

## 8. UDP card control flow

### 8.1 Initialization

```
UDPCardManager(settings)
  ├─→ Read CardSettings for each card C1–C7
  ├─→ Create UDPSender for each enabled card
  └─→ start_all(): bind UDP socket, start receive thread
```

### 8.2 Operations

Each card runs two threads (`UDPSender`): a send loop that transmits the 32-byte `SendData` packet cyclically, and a receive loop that parses the 64-byte `ReceiveData` packet. `set_*` methods only update the outgoing packet in memory; `get_*` methods read the latest received packet. No per-command request/response is used.

All methods live in `UDPCardManager` (`udp_card_manager.py`) and take `card_id` (1–7). Setters return `False` if the card is not found; getters return `None`.

| Group | Method | Description |
|---|---|---|
| Digital output (1–32) | `set_digital_output(card_id, do_number, state)` | Set one DO on/off |
| | `set_digital_outputs(card_id, do_list)` | Set listed DOs on, all others off |
| | `get_digital_output(card_id, do_number)` | Read DO state (always `True` in simulation) |
| TTL output (1–16) | `set_ttl_output(card_id, ttl_number, state)` | Set one TTL on/off |
| | `set_ttl_outputs(card_id, ttl_list)` | Set listed TTLs on, all others off |
| | `get_ttl_output(card_id, ttl_number)` | Read TTL state |
| Analog output (0–7, ±13.5 V) | `set_analog_output(card_id, ao_number, voltage)` | Set one AO voltage |
| | `set_multiple_analog_outputs(card_id, {ao: voltage})` | Set several AOs |
| | `get_analog_output(card_id, ao_number)` | Read AO setpoint |
| Matrix | `set_matrix_dimensions(card_id, rows, columns)` | Set matrix size (0–8 each) |
| | `get_matrix_dimensions(card_id)` | Read matrix size |
| | `get_Matrix_rows(card_id, row_number=None)` | Read one 8-bit row (1–8) or all rows |
| Digital input (1–64) | `get_digital_input(card_id, di_number)` | Read one DI |
| | `get_digital_inputs_active(card_id)` | List of active DIs |
| Analog input (1–16) | `get_analog_input(card_id, ai_number)` | Read AI voltage (fixed 5.0 V in simulation) |
| Encoder (1–2) | `get_encoder_words(card_id, encoder_id)` | Both 16-bit words of an encoder |
| | `get_encoder_word(card_id, encoder_id, word_index)` | One 16-bit word (index 1 or 2) |
| Utility | `clear_all_outputs(card_id=None)` | Clear outputs on one card or all |
| | `is_communication_active(card_id)` | Card communication status |
| | `get_all_communication_status()` | Status of all cards |
| | `get_statistics(card_id=None)` | Packet statistics |
| | `print_data_binary(card_id)` | Dump received data in binary (debug) |
| Lifecycle | `start_all()` / `stop_all()` / `stop_card(card_id)` | Start or stop card threads |

### 8.3 Localhost mode

When `settings['CardSettings']['localhost'] == True`, all card IPs are overridden to `127.0.0.1` and a `LocalhostSimulator` handles responses on loopback.

---

## 9. User interface interaction flow (Qt)

All user events go through `MainController` slots.

| Button | Controller method | See section |
|---|---|---|
| LOAD | `on_load()` | Section 2 |
| TEST | `on_test()` | Section 3.1 |
| TEST ALL | `on_test_all()` | Section 3.2 |
| STOP | `on_stop()` → `test_handler.running = False` | - |
| IBIT | `on_ibit()` | Section 4 |
| STOP IBIT | `on_stop_ibit()` → `test_handler.running_ibit = False` | - |
| COMM CHECK | `on_comm_check()` → `hardware.ping()` | - |
| SIMULATION | `on_simulation_toggle()` → toggle + save | - |
| LOCALHOST | `on_localhost_toggle()` → toggle + save | - |
| NEXT | `on_next()` → `test_handler.next_event.set()` | Section 10 |
| CLEAR LOG | `on_clear_log()` → `main_window.log.clear()` | - |
| REPORT | `on_report()` → build Excel from table rows; filename `<connector>_<timestamp>.xlsx` confirmed in a dialog, saved to `Paths.reports` (default `Results/`) | - |
| DOC | `on_doc()` → generate Word report via `create_doc_report_via_dialog()` | - |
| SETTINGS | `on_settings()` → open `Comm_settings.yaml` in system editor | - |

**Pin table interactions:**

- Click column header → sort by that column (toggle ascending/descending)
- Double-click editable cell → inline editor (QLineEdit with blue border)
- Hover cell → tooltip showing full cell text
- Multi-row selection (Ctrl/Shift+click) for batch test

---

## 10. Debug mode flow

Debug flags live under `settings['Debug']` keyed by section name: `Test_Sequence`, `Ibit_Test`, `Power_Test`, `PullUp_Test`, `Logic_Test`.

**When debug is active during test execution:**

```
test_handler.wait_debug(ID, "active")
  ├─→ Log: "in node {ID} Waiting for Next button press to continue..."
  └─→ next_event.wait()  — BLOCK until user clicks Next

User clicks NEXT → on_next() → next_event.set() → wait_debug() clears the event and execution resumes
```

**Flow diagrams:** live HTML visualization (trace.json, local HTTP server on port 8000, node highlighting) is no longer active. Follow progress through the log messages and the node IDs; the static flow diagrams are in the test guides (for example [Power test](../guide/power-test.md#power-test-flow-viewer)).

---

## 11. Error handling flow

| Error type | Handler | Behavior |
|---|---|---|
| Hardware connection error | `initialize_hardware()` catches `SerialException` | If simulation=True: log warning, continue. If simulation=False: log error, auto-enable simulation, retry. |
| UDP binding error | `card_manager.start_all()` catches `OSError` | Collect error per card; after all cards: show `QMessageBox.critical()`. |
| File not found (Excel) | `load_connector_from_excel()` catches `FileNotFoundError` | Log error, return empty list. |
| Test execution error | `run_tests()` per-pin `try/except` | Log error with traceback, continue to next pin. |
| Measurement error | `measure_voltage()` wrapper catches `Exception` | Log error, return 0.0. |
| Settings load error | `load_settings()` catches `yaml.YAMLError` | Print to console, return default settings dict. |

---

## 12. Shutdown flow

```
Window close event (X button or app.quit()):
  MainWindowQt.closeEvent()
    ├─→ STOP TESTS:
    |     test_handler.running = False
    |     test_handler.running_ibit = False
    ├─→ STOP UDP CARDS:
    |     card_manager.stop_all() → stop thread, close socket per card
    ├─→ CLEANUP HARDWARE:
    |     IF hardware.connected:
    |       clear_mux_bits()
    |       hardware.close()  → serial.close()
    └─→ QApplication.quit() → sys.exit()
```

---

## 13. Data flow between components

### 13.1 Component architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                     app.py  (Entry Point)                            │
│  - Load settings, pin_map, board_config                              │
│  - Initialize hardware                                               │
│  - Create QApplication, MainWindowQt, MainController                 │
└─────┬─────────────────────────────────────┬────────────────────────-─┘
      │                                     │
┌─────▼──────────────────┐     ┌────────────▼───────────────────────┐
│  MainWindowQt           │     │  MainController                    │
│  - PinTableQt           │◄────│  - on_test(), on_ibit(), …         │
│  - LogView              │     │  - _log_callback()                 │
│  - Run Controls         │     │  - QtTableAdapter (bridge)         │
└─────────────────────────┘     └────────────┬───────────────────────┘
                                             │
                            ┌────────────────┘
                            │
                ┌───────────▼────────────────────────────────────┐
                │            TestHandle  (core/test_handle.py)    │
                │  run_tests()                                    │
                │  (I-BIT: ibit_test() in core/test_Ibit.py)      │
                │  measure_all_pins_system(), Fuses_test()        │
                └───────┬────────────────┬────────────────────────┘
                        │                │
           ┌────────────▼──┐     ┌───────▼──────────────┐
           │  Measurer      │     │  UDPCardManager       │
           │ measure_volt() │     │ set_digital_output()  │
           └────────┬───────┘     │ set_analog_output()   │
                    │             └──────────┬────────────┘
           ┌────────▼──────────────────────▼────────────┐
           │              Hardware Layer                  │
           │  ControllinoIO          UDPSender           │
           │  (serial protocol)      (UDP sockets)       │
           └─────────────────────────────────────────────┘
```

### 13.2 Pin table data flow

```
Excel file
  ↓ load_connector_from_excel()
List[dict]  (all string values)
  ↓ PinTableQt.set_rows()
PinTableModel._rows + _row_id_map {id → row_idx}
  ↓ test run updates
PinTableModel.update_row(pin_id, {col: value})
  ├─→ _rows[row_idx][col_idx] = value
  └─→ dataChanged.emit() → repaint
```

### 13.3 State synchronization

| Variable | Controls |
|---|---|
| `test_handler.running` | Stops `run_tests()` loop |
| `test_handler.running_ibit` | Stops the `measure_all_pins_system()` / `Fuses_test()` loops |
| `MainController.running_ibit` | UI-side I-BIT flag; `on_ibit()` / `on_stop_ibit()` set it together with `test_handler.running_ibit`, and it blocks a second concurrent I-BIT start |
| `test_handler.next_event` | `threading.Event`, set by `on_next()` |
| `PinTableModel._testing_pin_id` | Which row is yellow (thread-safe via `postEvent`) |

---

## 14. Qt threading and thread-safety model

All tests run in daemon background threads. Qt widgets must only be touched from the main thread. Three mechanisms keep this safe:

### 14.1 QMetaObject.invokeMethod (fire-and-forget to main thread)

Used for: log appends, `_on_test_complete`, `_on_ibit_complete`.

```python
QMetaObject.invokeMethod(
    target_widget,
    "slot_name",
    Qt.ConnectionType.QueuedConnection,
    Q_ARG(str, value)
)
```

### 14.2 QTimer.singleShot(0, callback) (schedule on next event-loop tick)

Used for: `pin_table.update_row()`, `_apply_ibit_button_color()`.

```python
# QtTableAdapter.after() pattern:
QMetaObject.invokeMethod(main_window, "_schedule_callback", QueuedConnection, ...)
  └─→ main thread: QTimer.singleShot(delay_ms, callback)
```

### 14.3 QApplication.postEvent (thread-safe custom event)

Used for: `PinTableQt.set_testing_pin()` (row yellow highlight).

```python
QApplication.postEvent(widget, _SetTestingPinEvent(pin_id))
  └─→ PinTableQt.customEvent() [main thread]:
        model.set_testing_pin(pin_id)
        table.viewport().update()
```

---

## 15. Pin table row highlighting flow

**Purpose:** Show a yellow background on the row currently being tested. Must be thread-safe (called from background test thread).

**Flow:**

```
1. test_handle.run_tests() calls pin_table.set_testing_pin(pin.Id)
     └─→ QApplication.postEvent(self, _SetTestingPinEvent(pin_id))
           ← thread-safe: postEvent can be called from any thread

2. Qt event loop (main thread) delivers the event:
     PinTableQt.customEvent(event):
       model.set_testing_pin(event.pin_id)
         ├─→ self._testing_pin_id = pin_id
         └─→ dataChanged.emit(all rows) — triggers repaint

3. PinTableEditDelegate.paint() called for each visible cell:
     Priority order for background color:
       1. Currently testing (yellow)  — highest priority
       2. Any result is Fail  (pink)
       3. Any result is Pass  (green)
       4. Zebra stripe dark   (default)

4. After test completes:
     pin_table.set_testing_pin(None) → clears yellow
```

---

## 16. Power test detailed flow

```python
power_test(test_handle, pin):   # core/test_power.py
  get_pin_pair_info_controlino(pin.Id)
    └─→ Returns pin pair mapping (voltage_pin_key, pullup_pin_key, …)

  Resolve voltage_pin_name from board_config
  Resolve analog_port from pin_map['A'][voltage_pin_name]
  set_mux_bits(…)   # route connector pin to ADC

  Parse Power_Input (e.g. "C2_AO2_10"):
    card_id=2, type="AO", output_num=2, value=10.0

  IF Power_Input present:
    ├─→ Verify initial voltage ≈ 0V
    ├─→ card_manager.set_analog_output(card_id, num, value)   # apply stimulus
    ├─→ time.sleep(stabilize)
    ├─→ measured = measurer.measure_voltage(analog_port)
    └─→ card_manager.set_analog_output(card_id, num, 0.0)     # remove stimulus

  ELSE (passive pin — no stimulus):
    └─→ measured = measurer.measure_voltage(analog_port)

  Compare measured vs pin.Power_Expected ± tolerance:
    Pass → TestResult.PASS
    Fail → TestResult.FAIL

  clear_mux_bits(…)
  RETURN (measured_voltage, pass/fail, reason_string)
```

PullUp test and Logic test follow similar patterns in `core/test_pullUp.py` and `core/test_logic.py`.

---

## 17. Future / planned flows

| Flow | Status |
|---|---|
| Relay / Fuse test | Partially implemented - `relay_general_operate()` exists; full procedure TBD |
| Short circuit detection | Planned - detect unexpected voltage on pins that should read 0V |
| Cable / continuity test | Implemented - `Cable_test()` scans configured output connectors, validates expected and unexpected continuity, and reports results in the Logic result fields |
| Automated scheduling | Planned - scheduled test runs at configured intervals |
| Multi-board testing | Future - test multiple boards simultaneously via parallel threads |

