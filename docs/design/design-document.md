# IO Tester Application Design Document

---

## 1. Overview

IO Tester is a hardware validation and diagnostics application for testing connector pin integrity, power behavior, pull-up behavior, and logic states on Controllino/Arduino-based hardware. It supports both real-board operation and simulation mode so engineers can validate fixtures and connectors without physical hardware present.

The application loads connector definitions from Excel files, presents them in a spreadsheet-like pin table, runs automated tests, and produces a report that captures pass/fail outcomes. It also includes a built-in I-BIT (initial built-in test) workflow for validating the test fixture and network of IO paths.

This document describes the current architecture of the application as implemented in the repository, with emphasis on the modules, workflows, runtime configuration, and operational behavior.

---

## 2. Purpose and goals

### 2.1 Primary goals

- Test connector pins and associated fixture paths automatically.
- Detect power, pull-up, and logic faults with a consistent pass/fail model.
- Bridge hardware control, UI workflow, and test execution logic cleanly.
- Work with hardware simulation where physical boards are unavailable.
- Save reports in Excel or other export-friendly formats.

### 2.2 Business value

- Reduces manual validation time for hardware assemblies.
- Standardizes test execution across multiple connectors and pin maps.
- Provides quick visual feedback in the Qt UI, including the operational log and live pin status.
- Enables debugging of fixture or board-level issues via communication checks and I-BIT tests.

### 2.3 Non-goals

- This is not a general-purpose PLC or industrial control system.
- It is not intended to replace a full manufacturing execution system (MES).
- It does not aim to provide a web-based multi-user architecture in the current implementation.

---

## 3. Scope

### In scope

- Qt-based desktop user interface
- Configuration loading from YAML/JSON
- Excel-based connector data import
- Hardware abstraction layer for Controllino/Arduino boards
- Measurement routines for voltage and continuity operations
- Mux matrix / pin-selection logic for selecting specific connector pins
- Test execution engine for power, pull-up, and logic checks
- Report generation and operational logs
- UDP card communication and simulation support

### Out of scope

- Full remote deployment across multiple workstations
- Cloud-based reporting or centralized dashboards
- Generalized hardware support beyond the Controllino/Arduino ecosystem used by the project

---

## 4. System context

The application sits between three major domains:

1. User/operator and desktop GUI
2. Hardware interface to the test fixture and board
3. Data/configuration layer for connector definitions and board-specific settings

At runtime the app:

- loads configuration from YAML and JSON files
- initializes hardware or simulation mode
- loads an Excel connector map
- allows the operator to run test sequences
- updates the UI with pass/fail, logs, and operational state
- stores report data for later review

---

## 5. High-level architecture

### 5.1 Main entry point

The application bootstraps from `src/hw_tester/app.py`. This module sets up the Python import path and launches the Qt UI by delegating to the Qt application entry point.

### 5.2 UI layer

The user interface is implemented in the Qt package:

- `src/hw_tester/ui/qt/app.py`
- `src/hw_tester/ui/qt/main_window_qt.py`
- `src/hw_tester/ui/qt/controllers/main_controller.py`

This layer handles:

- window layout and widgets
- button wiring and events
- settings toggles (simulation, localhost mode, debug mode)
- log rendering
- interactions with the back-end test system

### 5.3 Core business logic

The test and measurement logic resides in the core components:

- `src/hw_tester/core/test_handle.py`
- `src/hw_tester/core/measurer.py`
- `src/hw_tester/core/test_power.py`
- `src/hw_tester/core/test_pullUp.py`
- `src/hw_tester/core/test_logic.py`
- `src/hw_tester/core/udp_card_manager.py`
- `src/hw_tester/core/pin_pulser.py`

These classes coordinate selection of a connector pin, trigger of measurement or logic checks, state transitions for pass/fail processing, and management of hardware and test execution flows.

### 5.4 Hardware abstraction layer

The physical device interface is isolated in the hardware package:

- `src/hw_tester/hardware/controllino_io.py`
- `src/hw_tester/hardware/hardware_factory.py`
- `src/hw_tester/hardware/pin.py`

This layer hides board-specific details from the rest of the application. The factory method chooses the correct board implementation based on settings, and each hardware object exposes methods such as pin control, analog reads, digital writes, and board initialization.

### 5.5 Configuration layer

Configuration data is centralized under:

- `src/hw_tester/config/`
- `src/hw_tester/utils/config_loader.py`

The system loads settings from YAML and JSON files using the resolved configuration path logic, including support for executable packaging scenarios.

---

## 6. Runtime components

### 6.1 Main controller

The main controller is the primary orchestrator of UI events and behavior. It:

- initializes hardware
- loads user settings
- creates the test and measurement components
- handles user actions (load, test, report, settings, I-BIT)
- updates the log and result labels in the GUI

This controller centralizes state transitions and is the primary integration point between the UI and the backend engine.

### 6.2 Measurer

The Measurer component performs voltage measurements and sampling over a configured duration. It can operate in real hardware mode or simulation mode based on the board settings.

It exposes logic for:

- reading analog values
- applying scaling based on configuration
- timing sample windows
- returning stable averaged values used by the test logic

### 6.3 Test handler

The `TestHandle` object is responsible for run-time testing of individual pins and complete connector tests. It coordinates:

- pin selection
- signal routing
- measurement windows
- pass/fail classification
- debug-step pauses

It can also drive the built-in I-BIT path to validate many pins in sequence.

### 6.4 UDP card manager

The UDP card manager is used for communication with IO cards and network-connected fixtures. It starts UDP listeners or senders and surfaces binding errors if ports are occupied.

---

## 7. Data model and configuration

### 7.1 Core settings

The configuration system merges values from `settings.yaml` and `Comm_settings.yaml` through the helper functions in the config loader.

Useful configuration areas include:

- board type and simulation flag
- serial port and baud configuration
- UDP networking parameters
- timeout values
- measurement scaling and thresholds
- UI preferences

### 7.2 Pin map and board definitions

The project contains board pin map files including `pin_map.json` and `board_pin_config.json`. These define:

- board-specific pin names
- analog and digital mappings
- mux routing information
- test hardware references needed by the test execution functions

### 7.3 Connector definition files

The application loads Excel-based connector definitions, which include per-pin metadata and expected values referenced by the test engine.

---

## 8. User workflow

### 8.1 Startup sequence

1. Application loads the initial settings.
2. Qt app creates the main window.
3. The controller initializes hardware, using real board logic or simulation mode.
4. Board config and pin map are loaded.
5. Test components are initialized.
6. UI controls and log states are prepared.

### 8.2 Load connector workflow

1. User selects an Excel connector file.
2. The application parses the file.
3. Connector metadata is mapped into UI rows.
4. The pin table is populated with testable pin definitions.
5. Test actions become active once valid data is loaded.

### 8.3 Execute pin test workflow

1. User selects one or multiple rows or chooses Test_All.
2. The system identifies the selected pin or set of pins.
3. The board config, mux settings, and analog mapping are used to route the test.
4. The Measurer reads the relevant analog or digital state.
5. The test engine applies pass/fail logic.
6. UI status labels and row colors are updated.
7. Results are written to the log and stored in memory for reporting.

### 8.4 Built-in I-BIT testing

The I-BIT test is a broader diagnostic mode that runs against many pins automatically. It iterates through the board's pin systems, clears the mux state, selects each pin, reads expected measurements, checks tolerances, and logs the result.

This mode is designed to detect systemic issues such as:

- short circuits
- open circuits
- wiring failures
- unexpected leakage or stuck states

### 8.5 Report generation

The UI exposes report generation so the operator can export test results. This captures the outcome of a session for later review, customer output, or QA tracking.

---

## 9. Functional requirements

### 9.1 Hardware communication

- The application must initialize the board by type.
- It must support simulation mode and real hardware mode.
- It must validate port availability and log meaningful connection errors.
- It must recover gracefully when the board is missing or the port is busy.

### 9.2 Test execution

- The application must perform per-pin and multi-pin test runs.
- It must support power, pull-up, and logic validation.
- It must update live status while a test is running.
- It must allow early stopping.

### 9.3 Diagnostics

- The application must expose a communication check to validate board responsiveness.
- The application must allow debug stepping and pause/resume behavior.
- The operational log must show clear status types: INFO, SUCCESS, WARNING, ERROR, DEBUG.

### 9.4 Configuration

- The app must load board and test configuration from YAML/JSON files.
- It must resolve config paths correctly across both source and packaged deployments.
- It must preserve settings between runtime sessions when appropriate.

---

## 10. Key design decisions

### 10.1 Qt for the desktop interface

Qt was selected for a desktop UI with support for rich controls, responsive layout, and native stateful widgets.

### 10.2 Hardware abstraction

The hardware layer sits behind a factory-based initializer so the application does not depend directly on Controllino implementation details. This allows the software to support different board types and simulation without major rework in the test engine.

### 10.3 Configuration-driven behavior

Board pin maps, timings, thresholds, debug options, and UI settings are driven by configuration files rather than hard-coded values. This makes the systems easier to adapt for different fixtures and board revisions.

### 10.4 Separation of concerns

| Layer | Responsibility |
|---|---|
| UI | User interaction |
| Controller | Coordinates actions |
| Core | Logic and measurement |
| Hardware | Drives the board |
| Config | Supplies operational settings |

---

## 11. Security and safety considerations

### 11.1 Safety

The application is used for hardware testing, so operational safety depends on correct board and fixture wiring. The system should never assume that a connection is valid without validation.

### 11.2 Error handling

The code explicitly logs COM port, UDP binding, and hardware failures and degrades gracefully. This is important because hardware integration often fails in real-world conditions.

### 11.3 Configuration integrity

Because board pin maps and communication settings can affect test behavior, configuration files should be reviewed before changing production-run settings.

---

## 12. Risks and limitations

### Current risks

- Tight coupling between the UI controller and business logic in some areas.
- Complex hardware dependencies may make the system harder to test offline.
- The app is specialized to a narrow set of board and fixture assumptions.
- UDP and hardware initialization can fail under environmental conditions such as port conflicts or disconnected boards.

### Known operational dependencies

- The board firmware must be compatible with the communication layer.
- Connector definitions must match the actual fixture design.
- External config files must be present in the correct runtime location.

---

## 13. Future enhancements

Possible roadmap items include:

- Split the UI controller into smaller feature-specific controllers
- Add a cleaner domain model for test results
- Improve automated test coverage for hardware-to-logic flows
- Add export/report templating and historical trend analysis
- Support broader hardware families and board definitions
- Improve packaging and deployment configuration for multiple OS environments
- Add remote diagnostics or networked QA dashboards

---

## 14. Summary

The IO Tester application is a configuration-driven, Qt-based hardware validation framework designed to test connectors and fixture paths quickly and consistently. It combines hardware abstraction, pin-map logic, measurements, automated tests, and report generation in a single desktop workflow.

---

## 15. Relevant source files

- `src/hw_tester/app.py`
- `src/hw_tester/ui/qt/main_window_qt.py`
- `src/hw_tester/ui/qt/controllers/main_controller.py`
- `src/hw_tester/core/test_handle.py`
- `src/hw_tester/core/measurer.py`
- `src/hw_tester/hardware/hardware_factory.py`
- `src/hw_tester/hardware/controllino_io.py`
- `src/hw_tester/utils/config_loader.py`
