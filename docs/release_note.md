# Release Notes

## Version 1.0.0 - July 1, 2026

### Released

- Delivered the first version to ESL.

## Version 2.0.0 - September 30, 2026

### Existing Test Features

- The I-BIT Fuse Test checks pins 1-50 on System A. It verifies the baseline is near `0 V`, activates the dedicated `pullup_fuse_test`, then checks the measured voltage against `scale.fuse_voltage_test` within the configured tolerance. The fuse phase can be skipped at its prompt.

### Added

- Cable Test support for multiple expected pins on one connector, such as `G(11,13,14,15)`, and pins across multiple connectors, such as `K(1),L(1)`.
- Cable configuration checks that require a configured input connector, configured output connectors, and a supported input-to-output connector combination. Invalid configurations return a failed test with a `Wrong connector configuration` message.
- Per-output-pin voltage and pass/fail logging during Cable Test. The test scans all pins on each named output connector, checking expected connections and unexpected continuity.
- A sequence-completion summary that reports whether the run had failures and how many were recorded.
- A restart-required popup when switching the connection mode from LocalHost to IO Box.

### Documentation

- Developed the MkDocs-based Wiki and included the project overview, quick-start guide, user manual, I-BIT guide, Power Test guide, PullUp Test guide, Logic Test guide, and Cable Test guide.
- Included the design document, system-flow documentation, error-message reference, and interactive logic, power, and pull-up test-flow diagrams.
- Added the Release Notes page to the Wiki and updated the system-flow and design documents for Cable Test selection, execution, validation, and cleanup.
