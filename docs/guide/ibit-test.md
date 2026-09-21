# I-BIT Test

The I-BIT test checks the connector wiring and fuse paths without requiring a loaded test file. It is started from the **IBIT** button in the Test/Debug area of the application.

## Purpose

I-BIT performs two related checks:

1. A circuit check for every connector pin on systems A and B.
2. A fuse check for every connector pin on system A using the dedicated fuse-test pull-up.

The complete test passes only when the circuit checks and the fuse check pass.

## Before Starting

Before starting I-BIT:

- Disconnect the IO Box and test cables from the fixture.
- Confirm that the correct board and communication settings are loaded.
- Use simulation mode when hardware is not connected.
- Make sure the mux matrix and connector wiring are in a safe initial state.

The application displays a warning before the test starts because I-BIT drives and measures the connector pins directly.

## Test Sequence

```text
User clicks IBIT
    |
    v
Controller starts the IBIT worker thread
    |
    v
Run circuit test for system A, pins 1-50
    |
    v
Run circuit test for system B, pins 1-50
    |
    v
Count circuit-test passes and failures
    |
    v
Run fuse test for system A, pins 1-50
    |
    v
Return the combined result to the user interface
```

The test runs in a background thread so the user interface remains responsive. The **Stop IBIT** button sets the running flag to false; the active loop exits at its next pin boundary.

## Circuit Test: Systems A and B

The circuit test is implemented by `measure_all_pins_system()`.

For each pin, the test performs the following operations:

1. Clear the mux matrix before selecting the next pin.
2. Resolve the pin pair and the matching analog and pull-up pins from the board configuration.
3. Convert the connector pin number into mux bits.
4. Set the mux bits to route the connector pin to the analog measurement path.
5. Measure the voltage before the pull-up is enabled.
6. Verify that the voltage is approximately `0 V`.
7. Enable the pin pull-up and wait for the configured stabilization delay.
8. Close the general relay.
9. Measure the voltage again.
10. Verify that the measured voltage is close to the expected circuit-test voltage, normally `4.0 V`.
11. Disable the pull-up and continue with the next pin.

A pin is added to the failed-pin list when either voltage validation fails, a mux operation fails, a required mapping is missing, or an exception occurs.

## Fuse Test: System A

The fuse test is implemented by `Fuses_test()` and runs only for system A. It uses the dedicated fuse-test pull-up rather than the normal pin pull-up.

For each system-A pin, the test performs the following operations:

1. Clear the mux matrix.
2. Resolve the system-A analog measurement pin.
3. Use the board configuration entry `pullup_fuse_test` for the fuse-test pull-up.
4. Set the mux bits for the connector pin.
5. Measure the voltage before the fuse-test pull-up.
6. Verify that the voltage is approximately `0 V`.
7. Enable the fuse-test pull-up and wait for stabilization.
8. Measure the voltage after the pull-up is enabled.
9. Compare the result with `scale.fuse_voltage_test` from the settings file.
10. Disable the fuse-test pull-up and continue with the next pin.

The fuse test does not run on system B.

## Voltage Validation

The voltage tolerance is read from the test settings:

```yaml
scale:
  fuse_voltage_test: 5.0

Test:
  voltage_degredation: 3.0
```

The exact key layout depends on the active settings file. The fuse expected voltage is read from `scale.fuse_voltage_test`; the function argument is used as a fallback when that setting is not available.

A voltage check passes when:

```text
abs(measured_voltage - expected_voltage) <= tolerance
```

For the initial measurement, the expected voltage is approximately `0 V`, so the measured value must be within the configured tolerance of zero.

## Hardware Configuration

The fuse pull-up is defined in the board configuration:

```json
{
  "ControllinoMega": {
    "pullup_fuse_test": "D22"
  }
}
```

The board pin name is translated to a physical digital pin through the digital section of `pin_map.json`.

The analog measurement pin is selected from the board-specific voltage mapping for each connector pin pair.

## Result and Logging

The circuit test returns:

- The number of passed pins.
- The total number of circuit pins measured on systems A and B.
- A Boolean circuit result.

The fuse test returns:

- The initial voltage measurements.
- A Boolean fuse result.
- A list of failed fuse pins with measured and expected values.

The overall IBIT result is successful only when:

```text
circuit_result == True and fuse_result == True
```

The operational log reports circuit progress, fuse failures, and the final success or failure state.

## Troubleshooting

### Many pins fail at approximately 0 V

- Check the mux wiring and connector address mapping.
- Confirm that the selected board configuration matches the connected board.
- Check for an incorrect analog pin mapping.
- Confirm that the fixture is disconnected as required before I-BIT.

### Fuse pins fail after the fuse pull-up is enabled

- Confirm `pullup_fuse_test` is mapped to the correct physical pin.
- Confirm the fuse pull-up wiring.
- Check the configured `scale.fuse_voltage_test` value.
- Verify that the fuse path is connected to the expected system-A pin.

### The test stops early

- Check the application log for mux, mapping, or hardware errors.
- Confirm that **Stop IBIT** was not pressed.
- Check board communication and serial connection status.
- Run the test in simulation mode to separate software flow problems from hardware problems.

## Source Implementation

- `src/hw_tester/core/test_Ibit.py`
  - `ibit_test()` coordinates the complete test.
  - `measure_all_pins_system()` performs the A/B circuit checks.
  - `Fuses_test()` performs the system-A fuse checks.
- `src/hw_tester/ui/qt/controllers/main_controller.py`
  - Starts and stops the background IBIT operation.
