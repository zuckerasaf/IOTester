# IO Tester Documentation

IO Tester is a hardware verification application used to test the electrical integrity of connector pins on a unit under test (UUT). It drives stimulus signals through IO Spider cards and measures the resulting voltages through a Controllino Mega microcontroller, then compares them to expected values defined in a test Excel file.

## Four UUT test types are supported per pin

- **Power Test** - measures DC voltage on the pin, the test can include Analog Output (AO) command 
- **Pull-Up Test** - activates a pull-up and measures the resulting voltage enbale , the test can include  Digital Output (DO) command  
- **Logic Test** - create connetion betaeen pins on the connecter and reads the outcome Digital Input (DI) or Analog  Input (AI) or Incrametal Encoder (IE), the test can include  Digital Output (DO) command  
- **Cable Test** - TBD

## Two internal system tests

- **Comm Test** - Checks communication with the Controllino board and IO Box. reports whether the hardware connection is available for testing.
- **I-BIT Test** - Scans connector pins on systems A and B for circuit faults, then optionally checks the card fuses paths using the fuse-test cable. 

Results are colour-coded in the pin table and can be exported to an Excel report.

---

## Where to start

| I want to... | Go to |
|---|---|
| Get up and running quickly | [Quick Start Guide](guide/quick-start.md) |
| Learn the full application in detail | [User Manual](guide/user-manual.md) |
| Understand the system architecture | [Design Document](design/design-document.md) |
| Understand how each workflow operates internally | [System Flows](design/system-flows.md) |
| Look up a specific error message | [Error Messages Reference](reference/error-messages.md) |

---

## Hardware at a glance

```
Controllino Mega  ←→  USB/Serial  ←→  IO Tester (this app)
IO Cards  		  ←→  UDP/Network ←→  IO Tester (this app)
UUT               ←→  Test Fixture
```

## Version

- Application: v2.0
- Documentation: September 2026
