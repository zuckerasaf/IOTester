# Error Messages Reference

This document centralizes the main operator-facing error and warning messages produced by the IO Tester application, along with the likely reason behind each one and the recommended corrective action.

It is intended to help troubleshooting during setup, hardware validation, pin testing, and report generation.

---

## 1. Startup and hardware initialization errors

### 1.1 "Hardware initialization failed: ..."

**Source files:** `main_controller.py`, `hardware_factory.py`

**Likely reasons:**

- Board is disconnected or not powered.
- COM port is wrong or blocked by another application.
- Arduino/Controllino firmware is not running the expected serial protocol.
- Serial library or board driver is unavailable.

**Recommended action:**

- Check USB cable and board power.
- Confirm the configured COM port in the board settings.
- Reflash or restart the board firmware.
- Re-run the communication check.

---

### 1.2 "Failed to connect to board on COMx"

**Likely reasons:**

- The port exists but no board is responding.
- Wrong board type selected.
- The board is not in a valid serial state.

**Recommended action:**

- Verify the COM port setting.
- Check board power and USB connection.
- Try another serial port if the board was moved.

---

### 1.3 "Hardware not initialized - test components disabled"

**Likely reasons:**

- The board could not be created during startup.
- Initialization failed and hardware object remained unavailable.

**Recommended action:**

- Investigate the earlier startup error.
- Re-check the board configuration and simulation state.
- Restart the application after fixing the hardware connection.

---

### 1.4 "Failed to initialize ControllinoMega: ..."

**Likely reasons:**

- Board unavailable or unresponsive.
- Missing pyserial or communication dependency issue.
- Firmware mismatch.

**Recommended action:**

- Confirm the board is connected and powered.
- Ensure the correct serial interface is installed.
- Check the board type and COM settings.

---

## 2. UDP and network communication errors

### 2.1 "UDP Binding Error"

**Source file:** `main_controller.py`

**Likely reasons:**

- Another application is already using one or more UDP server ports.
- A previous IO Tester instance is still running.
- Card network configuration conflicts with local system ports.

**Recommended action:**

- Close other apps that may be using the same ports.
- Restart the application.
- Switch to localhost mode if the environment is meant to use a simulated network.

---

### 2.2 "Failed to bind to one or more UDP cards"

**Likely reasons:**

- Port conflict.
- Cards not present or network not reachable.
- Localhost simulator not active when required.

**Recommended action:**

- Check open ports and running instances.
- Restart the test environment.
- Review the card IP and port configuration in the settings.

---

### 2.3 "no binding errors in the UDP connections"

This is an **informational success message**, not an error. Startup completed without UDP port conflicts.

---

## 3. Excel and file loading errors

### 3.1 "File not found - ..."

**Source file:** `main_controller.py`

**Likely reasons:**

- The connector Excel file was moved or renamed.
- The selected DB folder path is incorrect.
- The Excel file is not present in the expected test database location.

**Recommended action:**

- Confirm the file exists in the configured test folder.
- Select the correct database path.
- Reload the connector file from the correct directory.

---

### 3.2 "Could not find Excel file: ..."

**Likely reasons:**

- The user selected a missing file or the stored path is stale.

**Recommended action:**

- Reopen the file browser and reselect the correct connector workbook.

---

### 3.3 "Failed to load connector - ..."

**Likely reasons:**

- Excel workbook is corrupted.
- Worksheet structure does not match the expected connector format.
- Data is incomplete or uses an unexpected column layout.

**Recommended action:**

- Inspect the workbook structure.
- Confirm the file matches the expected connector schema.
- Validate the Excel file can be opened and parsed.

---

## 4. Configuration and settings errors

### 4.1 "Board 'X' not found in pin_map.json"

**Source file:** `config_loader.py`

**Likely reasons:**

- The configured board type does not exist in the pin map.
- The pin map JSON is stale or incomplete.

**Recommended action:**

- Check the `Board.Type` value in the settings.
- Update the board definition in the pin map or select a valid board type.

---

### 4.2 "Pin map file not found"

**Likely reasons:**

- The configuration file is missing from the deployment or source tree.
- Runtime path resolution failed.

**Recommended action:**

- Verify that the config files are present in the expected folder.
- Reinstall or redeploy the application with config assets included.

---

### 4.3 "Board pin config file not found"

**Likely reasons:**

- The `board_pin_config.json` file is absent.
- The packaged app is missing bundled config files.

**Recommended action:**

- Restore the config directory.
- Confirm the app is running with the expected files next to the executable or in the source tree.

---

## 5. Test execution and mux errors

### 5.1 "Failed to set mux bits for pin X"

**Source files:** `test_power.py`, `test_logic.py`, `test_pullUp.py`

**Likely reasons:**

- Mux routing failed because the pin address could not be translated.
- Board wiring or digital pin mapping is incorrect.
- Wrong pin selected or wrong connector map loaded.

**Recommended action:**

- Verify the correct pin map is loaded.
- Check that the board is connected and the mux lines are wired properly.
- Review the selected pin number against the actual fixture layout.

---

### 5.2 "Analog pin X not found in pin map"

**Likely reasons:**

- The voltage pin name is missing from the board config or pin map.
- The board configuration is inconsistent with the actual hardware layout.

**Recommended action:**

- Confirm that the pin mapping file contains the required analog pin entry.
- Check the board configuration for the selected board type.

---

### 5.3 "Failed to parse Power_Input: ..."

**Likely reasons:**

- The `Power_Input` text format is wrong or incomplete.
- The value does not match the expected event syntax.

**Recommended action:**

- Validate the connector Excel data.
- Check that the input string uses the expected `card/event` format (e.g. `C2_AO2_10`).

---

### 5.4 "Unknown event type: ..."

**Likely reasons:**

- Unsupported input type was read from the test data.
- The event format does not match AO or DO patterns.

**Recommended action:**

- Correct the value in the Excel connector definition.
- Use a supported event type such as `AO` or `DO`.

---

### 5.5 "Initial voltage ... is not ~0V"

**Likely reasons:**

- The measured baseline is not near zero before activating the test output.
- There is a short, leakage, or unexpected hardware state.

**Recommended action:**

- Check the fixture wiring.
- Inspect the UUT and board input state.
- Verify the selected pin route is valid.

---

## 6. Measurement and validation errors

### 6.1 "Measurement error on pin_id: ..."

**Source file:** `test_handle.py`

**Likely reasons:**

- Hardware read returned an exception.
- Board communication was interrupted.
- Circuit state was invalid during measurement.

**Recommended action:**

- Check the board and connection state.
- Review the hardware logs.
- Re-run the communication check before testing.

---

### 6.2 "Measurement ... is NOT within tolerance ..."

**Likely reasons:**

- Actual output differs from expected voltage beyond allowable difference.
- Mechanical or electrical issue in the fixture.
- Scaling or calibration mismatch.

**Recommended action:**

- Inspect the actual measured voltage.
- Verify expected value and calibration factor.
- Check for incorrect pin mapping or damaged fixture wiring.

---

## 7. Communication check and board response

### 7.1 "COM port X is available and board connected."

This is a **success message**, not an error. The serial port responded successfully.

---

### 7.2 "Failed to connect to board on COMx"

**Likely reasons:**

- COM port mismatch.
- Board is powered off.
- Device not responding to the ping command.

**Recommended action:**

- Confirm the board is connected and the port is correct.
- Restart the board and try again.

---

## 8. I-BIT and built-in diagnostic errors

### 8.1 "Ibit result: FAILURE"

**Source file:** `test_handle.py`

**Likely reasons:**

- One or more pins failed the built-in validation checks.
- Short or open circuit conditions exist.
- The board or fixture produced unexpected voltage readings.

**Recommended action:**

- Review the I-BIT log for the failed pin numbers.
- Check the affected pins and harness wiring.
- Re-run with debug traces if more detail is needed.

---

### 8.2 "Ibit Circuit Test complete: X/Y pins PASSED"

Summary status for the built-in diagnostic sequence. A partial pass or failure count indicates which pins were problematic.

---

### 8.3 "I_Bit test stopped by user"

The user cancelled the built-in diagnostic run. This is not necessarily an error; the test was intentionally interrupted.

---

## 9. UI and user action messages

### 9.1 "Test button stays greyed out"

**Likely reasons:**

- No connector file has been loaded yet.
- The table is empty or not initialized.

**Recommended action:**

- Click **Load** and select a valid connector Excel file.

---

### 9.2 "Simulation: On / Simulation: Off"

Toggle indicates whether the app is using real hardware or simulated readings. The actual state is controlled by the `Board.simulation` setting.

- Turn simulation **Off** when working with actual hardware.
- Turn simulation **On** for demo or office validation without a board.

---

### 9.3 "LocalHost / IO Box"

The application is toggling the network behavior for UDP card communication.

- **LocalHost** means loopback / network simulation.
- **IO Box** indicates external hardware communication path.

---

## 10. Message categories

The application uses four message levels:

| Level | Meaning |
|---|---|
| INFO | Normal progress or status updates |
| SUCCESS | Operation completed as expected |
| WARNING | Something is off but the system may continue |
| ERROR | A required operation failed and needs attention |

---

## 11. Recommended troubleshooting order

1. Confirm the board is connected and powered.
2. Verify the configured COM port and board type.
3. Check for UDP port conflicts.
4. Load the correct connector file.
5. Review the log for the first red ERROR message.
6. Validate pin mapping and board configuration.
7. Re-run the communication check.
8. Run the smallest test that isolates the failure.

---

## 12. Key source files for error tracing

| File | Area |
|---|---|
| `src/hw_tester/ui/qt/controllers/main_controller.py` | UI events, hardware init, UDP binding |
| `src/hw_tester/hardware/hardware_factory.py` | Board creation and initialization |
| `src/hw_tester/core/test_handle.py` | Test execution, I-BIT, measurement errors |
| `src/hw_tester/core/test_power.py` | Power test mux and measurement |
| `src/hw_tester/core/test_pullUp.py` | Pull-up test |
| `src/hw_tester/core/test_logic.py` | Logic test |
| `src/hw_tester/utils/config_loader.py` | Pin map and board config loading |
| `src/hw_tester/core/udp_card_manager.py` | UDP card binding and communication |

---

## 13. Summary

The main rule for troubleshooting is simple: start from the first ERROR or WARNING in the log, match it to the relevant subsystem, and then verify the board connection, pin map, file input, and network configuration before running the next test.
