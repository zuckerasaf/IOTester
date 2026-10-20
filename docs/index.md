# IO Tester

[Open the board presentation](presentation.md) for a concise overview of the system, workflow, and testing capabilities.

IO Tester is a hardware verification application used to test the electrical integrity of connector pins on a unit under test (UUT). It drives stimulus signals through IO Spider cards and measures the resulting voltages through a Controllino Mega microcontroller, then compares them to expected values defined in a test Excel file.

![IO Tester](assets/images/IOTester.jpg)

## Product overview

**Tester Box:** A medium-sized electrical enclosure connected to IO Box and a standard PC or laptop.

**Software:** A dedicated application for managing I/O testing.

### Goals

- Verify that the IO Box wiring matches the HSID net list.
- Reduce a full IO Box test from one day to approximately 1.5 hours.
- Find IO Box issues early in hardware development and integration using an isolated test environment, without requiring a cockpit or a SimEngine machine.
- Generate official test reports and bug summaries.

### Concept

- Replace cockpit panels and panel logic with a single D-sub logic interface.
- Simplify testing: no voltmeter is required, and Excel files serve as the test database.

## Hardware at a glance

Testing uses three connected components: the IO Box (with Spider card), the
Tester Box, and a laptop or PC running the Tester application.

![IO Tester hardware architecture](assets/images/archi.jpg)

```
Controllino Mega  <->  USB/Serial   <->  IO Tester (this app)
IO Cards          <->  UDP/Network  <->  IO Tester (this app)
UUT               <->  Test Fixture
```

### Testing procedure

1. Launch the Tester application and run the I-BIT test to verify system readiness.
2. Power up the IO Box and connect all components.
3. Start the test:
   - **3.1** The application sends commands to the Tester Box and, when needed, the IO Box.
   - **3.2** The Tester Box measures voltage or closes a loop between connector pins.
   - **3.3** The application receives the results and reads the Spider card status.
   - **3.4** Test results are displayed in real time.
4. Generate a test report and bug list.

### Main components

#### Tester Box

- **Controllino Mega:** An open-source industrial programmable logic controller
  (PLC) based on the 16 MHz Arduino ATmega2560 microcontroller. It provides
  16 analog/digital inputs, 21 digital inputs (including interrupts), and
  16 relay outputs (maximum 6 A).
- **Power supply:** MEAN WELL MDR-20-24, 24 V, 1 A.
- **IO Tester board:** Designed by ESA, with two sets of four ADG5206 16:1
  multiplexers for the 50-pin connector. It supports loopback combinations for
  closing circuits and provides 0.2 A fuse protection on each line.
- **Connector distributor (FG):** Designed by ESA to route the 50-pin
  connector lines in the following pairs: 1–37, 2–25, 3–15, and 5–9.

#### Tester software

- The main user interface lets users load test data, schedule and run tests,
  stop them, monitor progress, and generate reports for the IO Box.
- The Python application runs as an `.exe` on a Windows laptop.
- Simulation mode supports test-data validation without hardware; Debug mode
  allows a test to be paused mid-run.

![IO Tester application layout](assets/images/application-layout.svg)

## Four UUT test types are supported per pin

- **Power Test** - Measures the pin's DC voltage. The test can include an
  Analog Output (AO) command.
- **Pull-Up Test** - Activates a pull-up and measures the resulting voltage.
  The test can include a Digital Output (DO) command.
- **Logic Test** - Creates a connection between connector pins and reads the
  result using a Digital Input (DI), Analog Input (AI), or Incremental Encoder
  (IE). The test can include a Digital Output (DO) command.
- **Cable Test** - Checks expected continuity between connector pins and detects
  unexpected connections.

Test data is loaded from Excel files containing a subset of the HSID net list.
A built-in safety mechanism helps prevent unintended circuit closures, such as
connecting 24 V directly to GND.

## Two internal system tests

- **Comm Test** - Checks communication with the Controllino board and IO Box and
  reports whether the hardware is available for testing.
- **I-BIT Test** - Scans connector pins on systems A and B for circuit faults,
  then optionally checks the card fuse paths using the fuse-test cable.

Results are colour-coded in the pin table and displayed in a real-time log with
filtering.

---

## Where to start

| I want to... | Go to |
|---|---|
| Get up and running quickly | [Quick Start Guide](guide/quick-start.md) |
| Learn the full application in detail | [User Manual](guide/user-manual.md) |
| Understand the system architecture | [Design Document](design/design-document.md) |
| Understand Cable Test configuration | [Cable Test Guide](guide/cable-test.md) |
| Understand how each workflow operates internally | [System Flows](design/system-flows.md) |
| Review version history and updates | [Release Notes](release_note.md) |
| Look up a specific error message | [Error Messages Reference](reference/error-messages.md) |

---

## Version

- Application: v2.0.0
- Documentation: September 2026
