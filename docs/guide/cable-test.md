# Cable Test

The Cable test checks continuity from one source connector pin to the configured output connectors. It verifies that the expected output pins are connected and that the other pins on those output connectors are not.

## Procedure

`Cable_test()` performs these steps:

1. Read the source connector from `Logic_Pin_Input` and the source pin number from the row's `ID`.
2. Resolve the source pin's analog measurement and pull-up pins from the active board configuration.
3. Route the source pin through the mux matrix.
4. Activate the pull-up and close the general relay.
5. Read the allowed output pins from `Logic_Expected`.
6. Scan every pin on each output connector named in `Logic_Expected` and measure its voltage.
7. Compare allowed pins with the configured high voltage and all other scanned pins with the configured low voltage.
8. Record each output pin's measured voltage and Pass/Fail status.
9. Deactivate the pull-up and general relay, then clear the mux matrix.

## Configuration

Cable tests are selected when a pin row's `Type` or `Card` field is `Cable`.

| Field | Purpose |
| --- | --- |
| `ID` | Source pin ID; the final number is used as the pin number on the input connector. |
| `Logic_Pin_Input` | Name of the source connector, such as `C`, `E`, or `H`. |
| `Logic_Expected` | Allowed output connector pins, written as connector names followed by pin numbers in parentheses. |

Multiple output connectors and multiple pins on one connector are supported. For example:

```text
K(1),L(1)
G(11,13,14,15)
```

For each connector named in `Logic_Expected`, the test scans all configured pins on that connector. The listed pins are expected to be connected; unlisted pins are expected not to be connected.

Connector sizes and offsets come from `Connectors` in the active settings. Voltage criteria use `fuse_voltage_test` for expected connected pins, `zero_voltage_threshold` for expected disconnected pins, and `voltage_tolerance` for both comparisons.

Before routing hardware, the test checks that the source connector is configured with `Type: input`, each target connector has `Type: output`, and the connector combination is supported:

| Input connector | Supported output connector combinations |
| --- | --- |
| `C` | `D`, `G`, `K`, `K` + `L` |
| `E` | `F`, `F` + `G`, `F` + `L`, `J`, `J` + `K`, `J` + `K` + `L` |
| `H` | `I`, `I` + `J`, `I` + `J` + `K`, `I` + `J` + `K` + `L` |

Connector role or combination errors return a failed result with a `Wrong connector configuration` message.

## Results

The function returns:

```text
(average_measured_voltage, success, message)
```

- `average_measured_voltage`: Average of the measured output-pin voltages.
- `success`: `True` when all allowed and disallowed pins meet their voltage criteria.
- `message`: Pass result or a list of output pins that failed.

The pin table receives the result and reason in its Logic result fields.

## Failure Conditions

The test fails when:

- The input or output connector is not configured.
- The source or an expected output pin is outside the connector's configured size.
- The pin list in `Logic_Expected` is malformed.
- The required analog or pull-up pin is missing from the board configuration.
- The mux matrix cannot route a source or output pin.
- An expected connection does not meet the high-voltage criterion, or an unexpected connection exceeds the low-voltage criterion.

The pull-up, general relay, and mux cleanup are attempted on every return path.

## Source

- `src/hw_tester/core/test_cable_one_box.py`
  - `Cable_test(test_handle, pin, pin_table_rows)`
- `src/hw_tester/core/test_handle.py`
  - Selects the test and updates the pin table.
