# IO Tester - User Manual

**Version:** 1.0.0  
**Last Updated:** April 2026

---

## Table of Contents

1. [Introduction](#introduction)
2. [System Requirements](#system-requirements)
3. [Installation & Setup](#installation--setup)
4. [Configuration](#configuration)
5. [Operating Modes](#operating-modes)
6. [Running the Application](#running-the-application)
7. [API Reference](#api-reference)
8. [Test Types](#test-types)
9. [Troubleshooting](#troubleshooting)

---

## Introduction

### Application Overview

The **IO Tester** is an advanced, automated hardware testing framework specifically engineered for validating and diagnosing electrical and digital I/O systems in Controllino Mega and Arduino-based industrial control platforms. Designed with reliability and efficiency in mind, this comprehensive application serves as a critical tool for hardware engineers, quality assurance teams, and system integrators who need to verify complex pin configurations, electrical connections, and circuit integrity in automated test environments.

The application addresses a common challenge in hardware testing: the need to systematically verify hundreds of pin connections, voltage levels, and logic states across multiple connectors and IO cards without manual intervention. By automating the test process and providing real-time feedback, the IO Tester dramatically reduces testing time while increasing accuracy and consistency.

At its core, the IO Tester acts as a bridge between test definitions (stored in Excel spreadsheets for easy modification by non-programmers) and physical hardware, executing sophisticated test sequences that would be impractical to perform manually. The system can control routing matrices, measure voltages, verify logic levels, and detect fault conditions such as short circuits or open connections—all while generating detailed reports for documentation and quality control purposes.

### Key Capabilities

The IO Tester provides automated testing of:
- **Pin Voltage Measurements** - Precise analog voltage readings with configurable sampling rates
- **Power Tests** - Verify pins can deliver expected power levels within tolerance
- **Pullup/Pulldown Tests** - Validate resistor configurations and floating pin behavior
- **Logic Tests** - Confirm digital pins correctly interpret HIGH/LOW states
- **I-bit Tests** - Full system integrity checks across all communication channels
- **Relay and Fuse Tests** - Test switching circuits and verify fuse continuity
- **Short Circuit Detection** - Systematically identify unintended electrical connections
- **Continuity Testing** - Verify expected connections between connector pins

### Major Features

#### 🎨 **Dual User Interface Options**
The application offers flexibility in how you interact with it:
- **Qt UI (Modern):** A contemporary, responsive interface with tabbed panels, expandable test trees, color-coded status indicators, and real-time progress visualization. Recommended for most users.
- **Tkinter UI (Legacy):** A traditional desktop interface maintained for compatibility with older systems and users familiar with the original design.

Both interfaces provide full access to all testing features, configuration options, and result viewing capabilities, allowing you to choose based on your environment and preferences.

#### 🔄 **Flexible Operating Modes**
Work the way that suits your development stage:
- **Hardware Mode:** Direct control of physical Controllino/Arduino boards and IO cards via serial and UDP communication, perfect for real-world validation and production testing.
- **Localhost Simulation Mode:** Complete offline development and testing without any physical hardware. The built-in simulator responds to all commands with configurable simulated data, enabling rapid development, training, and demonstration scenarios.
- **Hybrid Mode:** Mix simulation and real hardware, useful when some components are available while others are still in development.

#### 🌐 **Real-Time Web Visualization**
Monitor test execution in your web browser with interactive flowcharts:
- **Live Test Flow Diagrams:** Watch as the test progresses through decision trees generated from your Excel test definitions
- **Step-by-Step Debugging:** Pause execution at any node, examine current state, and step through tests manually
- **Visual Test Traces:** Automatically generated HTML visualizations of test logic with color-coded pass/fail indicators
- **GraphViz Integration:** Professional-quality flow diagrams exported to SVG and DOT formats

This feature transforms abstract test sequences into visual, understandable workflows—invaluable for debugging complex test logic and presenting results to stakeholders.

#### 📡 **Multi-Card UDP Communication**
Enterprise-grade distributed IO control:
- **Simultaneous Card Management:** Control up to 7 independent IO cards over UDP/Ethernet with 20 Hz bidirectional communication
- **Parallel Operations:** Execute tests across multiple cards concurrently, dramatically reducing overall test time
- **Network Flexibility:** Support for both local network (real hardware) and localhost (simulation) configurations with automatic failover
- **Data Synchronization:** Coordinated send/receive cycles ensure timing-critical operations remain synchronized across all cards
- **Live Statistics:** Monitor packet transmission rates, response times, and connection health for each card in real-time

#### 📊 **Excel-Driven Test Definitions**
Empower non-programmers to create and modify tests:
- **No Coding Required:** Test engineers define complete test sequences using familiar Excel spreadsheets (XLSM format)
- **Structured Test Tables:** Simple column-based format specifies pin IDs, expected values, tolerances, and test actions
- **Connector Mapping:** Excel-based pin-to-address mapping makes it easy to update hardware configurations
- **Version Control:** Test definitions can be tracked, reviewed, and shared like any other document
- **Rapid Iteration:** Change test parameters, add new test cases, or adjust thresholds without touching source code

#### 📝 **Automated Report Generation**
Professional documentation with zero manual effort:
- **Word Document Output:** Automatically generate formatted test reports in DOCX format with company branding
- **Comprehensive Results:** Detailed tables showing pin-by-pin results, measured vs. expected values, pass/fail status
- **Timestamps and Metadata:** Complete traceability with test date, operator, hardware configuration, and software version
- **Embedded Visualizations:** Include test flow diagrams and measurement graphs directly in reports
- **Batch Processing:** Generate reports for multiple test runs, compare results across different hardware units

#### 🏗️ **Modular Architecture**
Built for maintainability and extensibility:
- **Hardware Abstraction Layer:** Swap between different board types (Controllino Mega, Arduino Mega, Arduino Uno) without changing test code
- **Plugin-Ready Design:** Factory pattern for hardware initialization, making it simple to add support for new boards or communication protocols
- **Separation of Concerns:** Clean boundaries between hardware control, business logic, and user interface layers
- **Configuration-Driven:** Almost everything is configurable via YAML/JSON files—timeouts, thresholds, pin mappings, test types
- **Extensible Test Framework:** Add custom test types by inheriting from base test classes

#### 🔒 **Thread-Safe Operations**
Reliable concurrent execution:
- **Thread-Safe Communication:** Lockless UDP sender/receiver pairs ensure reliable packet transmission
- **Synchronized Hardware Access:** Serial port operations protected by threading locks to prevent race conditions
- **Safe UI Updates:** Cross-thread communication patterns ensure UI remains responsive during long test runs
- **Event-Driven Control:** Pause, resume, and stop operations handled through thread-safe event mechanisms

#### 🛡️ **Robust Error Handling**
Graceful degradation and clear diagnostics:
- **Connection Resilience:** Automatic retry logic for serial and UDP connections with configurable timeouts
- **Detailed Error Messages:** User-friendly error descriptions identify exactly what went wrong and how to fix it
- **Graceful Failures:** Tests continue when individual pins fail, collecting all results for comprehensive reports
- **Validation Guards:** Settings and configurations validated on load with clear feedback about invalid values
- **Debug Logging:** Hierarchical logging system captures trace, debug, info, warning, and error messages with timestamps

### Use Cases

The IO Tester excels in these scenarios:

- **Production Testing:** Automated go/no-go testing of manufactured units on the production line
- **Quality Assurance:** Periodic validation of existing systems to catch degradation or component failures
- **Development Validation:** Verify new hardware designs before committing to production
- **Troubleshooting:** Quickly identify failing pins, shorts, or connection issues in malfunctioning systems
- **Documentation:** Generate comprehensive test reports for regulatory compliance or customer delivery
- **Training:** Simulation mode allows training operators without risk to physical hardware
- **Regression Testing:** Verify that hardware modifications don't break existing functionality

By combining automation, flexibility, and comprehensive reporting, the IO Tester transforms hardware validation from a tedious, error-prone manual process into a fast, reliable, and well-documented automated workflow.

---

## System Requirements

### Preconditions for Running the Application

#### Hardware Requirements
- **Development/Testing:**
  - Arduino Uno/Mega or Controllino Mega board
  - USB connection to PC
  - Optional: IO cards for real hardware testing
  
- **Production:**
  - Controllino Mega with ControllinoSerialInterface.ino firmware
  - IO cards connected via UDP/Ethernet (up to 7 cards)
  - Test harness with pin connectors

#### Software Requirements
- **Operating System:** Windows (primary), Linux/Mac (untested)
- **Python:** Version 3.8 or higher
- **Serial Port:** Available COM port for Controllino/Arduino connection
- **Network:** UDP communication capability (for real hardware mode)
- **Optional:** Web browser (for trace visualization)
- **Optional:** Graphviz (for generating flow diagrams from Excel)

#### Python Dependencies
```txt
pyserial          # Serial communication
pymata4           # Firmata protocol
pyyaml            # YAML configuration parsing
ruamel.yaml       # YAML with comment preservation
pandas            # Excel data handling
openpyxl          # Excel file I/O
python-docx       # Word document generation
pytest            # Testing framework (development)
```

---

## Installation & Setup

### Step 1: Clone or Download Project
```powershell
cd C:\ArduinoProject
git clone <repository-url> IO_Tester
cd IO_Tester
```

### Step 2: Create Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 3: Install Dependencies
```powershell
# Install in editable mode
pip install -e .

# Or install from requirements
pip install -r requirements.txt
```

### Step 4: Upload Arduino Firmware (Hardware Mode Only)

---

## Qt User Interface Guide

The Qt UI is the recommended, modern interface for the IO Tester. It is designed for clarity, efficiency, and real-time feedback. Below is an overview of the main components and controls:

### Main Window Layout

- **Pin Table (Top Panel):**
  - Displays all pins and their test data in a scrollable, sortable table.
  - Columns include: ID, Connect, Discrete Name, Signal Name, Plug, Type, Pin, Power/Pullup/Logic test results, and more.
  - Color coding highlights pass/fail and current test status.

- **Control Panels (Middle Row):**
  - **Connector/File Group:**
    - *Connector Field*: Enter or select the connector to test.
    - *Load*: Load the selected connector's test profile.
    - *Report*: Generate a test report.
    - *DOC*: Export results as a Word document.
  - **Run Controls Group:**
    - *Test*: Run the test for the selected pin(s).
    - *Test_All*: Run all tests for the loaded connector.
    - *Stop*: Stop the current test sequence.
    - *Status Labels*: Show which pin is being tested and the latest Power, Pullup, and Logic results.
  - **Log Group:**
    - *Log Level Checkboxes*: Filter log messages by type (INF, SUC, WRN, ERR, DBG).
    - *Clear*: Clear the log display.
  - **Test/Debug Group:**
    - *Keepalive*: Send a keepalive signal to hardware/simulator.
    - *IBIT*: Start a full system integrity (I-bit) test.
    - *Stop IBIT*: Stop the I-bit test.
    - *Simulation*: Toggle simulation mode (on/off).
    - *LocalHost*: Switch to localhost simulation.
    - *Next*: Step to the next test in sequence.
    - *Debug*: Toggle debug mode.
    - *Debug Option*: Select and view HTML flowcharts of test logic.

- **Operational Log (Bottom Panel):**
  - Shows real-time logs with timestamps and color-coded levels.
  - Supports filtering and clearing.

### Button/Component Functions

| Button/Component | Function |
|------------------|----------|
| **Connector**    | Enter/select connector to test |
| **Load**         | Load test profile for connector |
| **Report**       | Generate a test report (table format) |
| **DOC**          | Export results as Word document |
| **Test**         | Run test for selected pin(s) |
| **Test_All**     | Run all tests for loaded connector |
| **Stop**         | Stop current test sequence |
| **Keepalive**    | Send keepalive to hardware/simulator |
| **IBIT**         | Start full system integrity test |
| **Stop IBIT**    | Stop I-bit test |
| **Simulation**   | Toggle simulation mode (on/off) |
| **LocalHost**    | Switch to localhost simulation |
| **Next**         | Step to next test in sequence |
| **Debug**        | Toggle debug mode |
| **Debug Option** | Select HTML flowchart to view |
| **Log Level Checkboxes** | Filter log messages by type |
| **Clear**        | Clear the log display |

### Status Indicators

- **Testing Pin**: Shows the pin currently under test.
- **Power/Pullup/Logic**: Show the latest result for each test type.

### Tips

- Use the **Simulation** and **LocalHost** buttons for development without hardware.
- The **Debug Option** dropdown lets you view test logic flowcharts generated from your Excel test definitions.
- All actions and errors are logged in the Operational Log for traceability.

---
1. Open Arduino IDE
2. Load `ControllinoSerialInterface/ControllinoSerialInterface.ino`
3. Select correct board: Tools → Board → Controllino Mega
4. Select correct COM port: Tools → Port → COMx
5. Upload sketch to board

### Step 5: Verify Installation
```powershell
# Test that package is installed
python -m hw_tester.app --help

# Or use console script
hw-tester --help
```

---

## Configuration

### Main Configuration File: `settings.yaml`

Location: `src/hw_tester/config/settings.yaml`

#### Key Configuration Sections

```yaml
# Application metadata
IO_Tester:
  Name: HW Tester
  Version: 1.0.0
  Description: Hardware pin testing tool

# Debug mode (enables trace visualization)
Debug:
  mode: true

# UI Selection
UI:
  UI_Type: Qt          # Options: "Qt" or "Tkinter"

# IO Box Type (determines test database)
IO_Box:
  Type: MTC_AFT        # Options: Demo, MTC_FWD, MTC_AFT
  AvailableTypes:
    - Demo
    - MTC_FWD
    - MTC_AFT

# Board Configuration
Board:
  Type: ControllinoMega
  AvailableTypes:
    - ControllinoMega
    - ArduinoMega
    - ArduinoUno
    - none
  Port: COM5           # Serial port
  BaudRate: 115200     # Serial baud rate
  simulation: true     # true = localhost mode, false = hardware mode

# Timing Configuration
Timeouts:
  duration: 0.5              # Default measurement duration (seconds)
  sample_interval: 0.1       # Sampling interval (seconds)
  TestStep: 2.5              # Time per test step (seconds)
  Connection: 5.0            # Connection timeout (seconds)
  pins_to_stabilize: 0.1     # Pin stabilization delay (seconds)

# Voltage Thresholds
scale:
  voltage: 6.14                      # Voltage scale factor
  voltage_degredation: 1.5           # Acceptable voltage drop
  voltage_tolerance: 1.5             # Measurement tolerance
  zero_voltage_threshold: 0.5        # Zero detection threshold (V)
  Analog_voltage_threshold: 11.0     # Analog pin threshold (V)
  logic_voltage_threshold: 4.0       # Logic high threshold (V)

# File Paths
Paths:
  Path_1: C:/ArduinoProject/IO_Tester
  Path_2: src/hw_tester/config/pin_map.json
  reports: C:\ArduinoProject\IO_Tester\tests\Results
  ConnectorAddressMap: src/hw_tester/config/connector_Address_map.xlsx
  powerup_MTC_FWD: tests/DB/MTC_FWD/powerup_MTC_FWD.json
  powerup_MTC_AFT: tests/DB/MTC_AFT/powerup_MTC_AFT.json
```

### Pin Mapping: `pin_map.json`

Location: `src/hw_tester/config/pin_map.json`

Defines mapping between logical pin names and physical pins.

```json
{
  "analog": {
    "A0": 0,
    "A1": 1
  },
  "digital": {
    "D2": 2,
    "D3": 3
  }
}
```

### Board Pin Configuration: `board_pin_config.json`

Location: `src/hw_tester/config/board_pin_config.json`

Defines board-specific capabilities and pin functions.

---

## Operating Modes

### 1. Hardware Mode (Real Hardware)

**Use Case:** Testing with physical Controllino/Arduino and IO cards

**Configuration:**
```yaml
Board:
  simulation: false    # Disable simulation
  Port: COM5          # Actual COM port
  BaudRate: 115200
```

**Preconditions:**
- Controllino/Arduino connected via USB
- ControllinoSerialInterface.ino firmware uploaded
- IO cards connected via Ethernet (if using UDP)
- Correct COM port in settings.yaml

**To Switch to Hardware Mode:**
```powershell
.\switch_to_hardware.bat
```

### 2. Localhost Simulation Mode

**Use Case:** Development and testing without physical hardware

**Configuration:**
```yaml
Board:
  simulation: true     # Enable simulation

UDP_Settings:
  localhost_mode: true
  Cards_localhost:    # All cards use 127.0.0.1
    - card_id: 1
      ip: 127.0.0.1
```

**Preconditions:**
- No hardware required
- Localhost simulator running (optional - for UDP testing)

**To Switch to Localhost Mode:**
```powershell
.\switch_to_localhost.bat
```

**Running Localhost Simulator (for UDP testing):**
```powershell
# Terminal 1: Start simulator
python src/hw_tester/core/localhost_simulator.py

# Terminal 2: Run application
python src/hw_tester/app.py
```

### 3. Web Visualization Mode

**Use Case:** View test execution flow in real-time

**Preconditions:**
- Debug mode enabled in settings.yaml: `Debug: mode: true`
- Test trace files generated (HTML in `src/hw_tester/web/`)

**Running Web Server:**
```powershell
# Serve test visualizations
python src/hw_tester/web/serve_nocache.py

# Open browser to: http://localhost:8000
```

---

## Running the Application

### Method 1: Direct Python Execution
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run application
python src/hw_tester/app.py
```

### Method 2: Console Script (After Installation)
```powershell
hw-tester
```

### Method 3: Module Execution
```powershell
python -m hw_tester.app
```

### Selecting UI Type

Edit `settings.yaml`:
```yaml
UI:
  UI_Type: Qt         # Modern Qt interface
  # UI_Type: Tkinter  # Legacy Tkinter interface
```

### Application Startup

1. Application reads `settings.yaml` to determine UI type and configuration
2. Loads pin mappings from `pin_map.json` and `board_pin_config.json`
3. Initializes hardware connection (or simulation mode)
4. Launches selected UI (Qt or Tkinter)
5. Displays connection status and available tests

---

## API Reference

### Core APIs

#### 1. Hardware API (`hardware/controllino_io.py`)

**ControllinoIO Class**

Direct serial communication with Controllino/Arduino boards.

```python
from hw_tester.hardware.controllino_io import ControllinoIO

# Initialize connection
hardware = ControllinoIO(
    port="COM5",
    baud_rate=115200,
    allow_no_connection=False,  # Raise error if connection fails
    log_callback=None           # Optional logging function
)

# Check connection
if hardware.connected:
    print("Hardware connected")

# Read analog pin (returns voltage)
voltage = hardware.analog_read(pin=0)  # Read A0

# Digital write
hardware.digital_write(pin=13, state=True)  # Set D13 HIGH

# Digital read
state = hardware.digital_read(pin=2)  # Read D2

# Set pin mode
hardware.pin_mode(pin=13, mode="OUTPUT")  # Modes: INPUT, OUTPUT, INPUT_PULLUP

# Send raw command
hardware.send_command("PING")

# Close connection
hardware.disconnect()
```

**Key Methods:**
- `analog_read(pin: int) -> float` - Read analog pin voltage
- `digital_write(pin: int, state: bool)` - Write digital pin state
- `digital_read(pin: int) -> bool` - Read digital pin state
- `pin_mode(pin: int, mode: str)` - Set pin mode (INPUT/OUTPUT/INPUT_PULLUP)
- `send_command(cmd: str) -> str` - Send raw command to board
- `disconnect()` - Close serial connection

---

#### 2. Measurement API (`core/measurer.py`)

**Measurer Class**

Handles voltage measurements with simulation support.

```python
from hw_tester.core.measurer import Measurer

# Initialize measurer
measurer = Measurer(
    hardware_io=hardware,    # ControllinoIO instance
    settings=settings_dict   # Settings from settings.yaml
)

# Measure voltage on analog pin
voltage = measurer.measure_voltage(
    analog_port=0,           # A0
    duration=1.0,            # Measurement duration (seconds)
    sample_interval=0.1,     # Sample every 0.1 seconds
    idx=0                    # Index for simulation variation
)

# Continuous measurement
voltages = []
for i in range(10):
    v = measurer.measure_voltage(analog_port=0)
    voltages.append(v)
```

**Key Methods:**
- `measure_voltage(analog_port: int, duration: float = None, sample_interval: float = None, idx: int = 0) -> float`
  - Returns: Average voltage over measurement period
  - In simulation mode: Returns simulated value based on idx

---

#### 3. Test Handler API (`core/test_handle.py`)

**TestHandle Class**

Core test execution engine.

```python
from hw_tester.core.test_handle import TestHandle

# Initialize test handler
test_handler = TestHandle(
    hardware=hardware,
    settings=settings_dict,
    pin_map=pin_map_dict,
    board_config=board_config,
    measurer=measurer,
    card_manager=udp_card_manager,
    log_callback=log_function
)

# Run power test on a pin
voltage, passed, message = test_handler.run_power_test(pin_object)

# Run pullup test
voltage, passed, message = test_handler.run_pullup_test(pin_object)

# Run logic test
voltage, passed, message = test_handler.run_logic_test(
    pin=pin_object,
    pin_table_rows=test_rows
)

# Run I-bit test (full system test)
test_handler.run_i_bit_test()

# Run short circuit test
results = test_handler.short_circuit_test()

# Run relay/fuse test
result, passed = test_handler.relay_fuse_test(
    first_relay="R1",
    second_relay="R2",
    pullup_pin="P1",
    voltage_measure_pin1="V1",
    voltage_measure_pin2="V2"
)

# Control test execution
test_handler.running = True   # Start test
test_handler.running = False  # Stop test
```

**Key Test Methods:**

| Method | Purpose | Returns |
|--------|---------|---------|
| `run_power_test(pin)` | Test pin can deliver power | `(voltage, passed, message)` |
| `run_pullup_test(pin)` | Test pin pullup/pulldown | `(voltage, passed, message)` |
| `run_logic_test(pin, rows)` | Test pin logic levels | `(voltage, passed, message)` |
| `run_i_bit_test()` | Full system integrity test | None (uses log callback) |
| `short_circuit_test()` | Detect short circuits | `[(voltages, passed, details)]` |
| `relay_fuse_test(...)` | Test relays and fuses | `(result_str, passed)` |

---

#### 4. UDP Communication API (`core/udp_sender.py`)

**UDPSender Class**

Bidirectional UDP communication with IO cards at 20 Hz.

```python
from hw_tester.core.udp_sender import UDPSender

# Initialize UDP sender
udp_sender = UDPSender(
    remote_ip="192.168.1.100",
    send_port=12345,
    receive_port=12346,
    frequency=20.0,  # Hz
    timeout=1.0,     # seconds
    log_callback=log_function
)

# Start communication
udp_sender.start()

# Set digital output
udp_sender.set_digital_output(do_number=1, state=True)

# Set multiple digital outputs
udp_sender.set_digital_outputs(do_list=[1, 2, 5])

# Get digital output state
state = udp_sender.get_digital_output(do_number=1)

# Set TTL output
udp_sender.set_ttl_output(ttl_number=1, state=True)

# Set multiple TTL outputs
udp_sender.set_ttl_outputs(ttl_list=[1, 3, 4])

# Get TTL output state
state = udp_sender.get_ttl_output(ttl_number=1)

# Configure matrix dimensions (for routing)
udp_sender.set_matrix_dimensions(rows=8, columns=8)

# Get received data
received_data = udp_sender.receive_data

# Access received values
if received_data:
    digital_inputs = received_data.digital_inputs
    analog_inputs = received_data.analog_inputs
    ttl_states = received_data.ttl_states

# Stop communication
udp_sender.stop()
```

**Key Methods:**
- `start()` - Begin UDP communication loop
- `stop()` - Stop UDP communication
- `set_digital_output(do_number: int, state: bool)` - Control digital output
- `set_digital_outputs(do_list: List[int])` - Set multiple digital outputs
- `get_digital_output(do_number: int) -> bool` - Get digital output state
- `set_ttl_output(ttl_number: int, state: bool)` - Control TTL output
- `set_ttl_outputs(ttl_list: List[int])` - Set multiple TTL outputs
- `get_ttl_output(ttl_number: int) -> bool` - Get TTL output state
- `set_matrix_dimensions(rows: int, columns: int)` - Configure routing matrix

**Data Structures:**
- **SendData** (32 bytes): Digital outputs, TTL outputs, matrix configuration
- **ReceiveData** (64 bytes): Digital inputs, analog inputs, TTL states

---

#### 5. UDP Card Manager API (`core/udp_card_manager.py`)

**UDPCardManager Class**

Manages multiple UDP cards (up to 7 cards).

```python
from hw_tester.core.udp_card_manager import UDPCardManager

# Initialize card manager (loads from settings.yaml)
card_manager = UDPCardManager.from_settings()

# Or initialize manually
card_manager = UDPCardManager(
    card_configs=[
        {"card_id": 1, "ip": "192.168.1.101", "send_port": 12345, "receive_port": 12346},
        {"card_id": 2, "ip": "192.168.1.102", "send_port": 12345, "receive_port": 12346}
    ],
    frequency=20.0
)

# Start all cards
card_manager.start_all()

# Get specific card
card1 = card_manager.get_card(card_id=1)

# Control outputs on specific card
card_manager.set_digital_output(card_id=1, do_number=5, state=True)

# Stop all cards
card_manager.stop_all()
```

---

#### 6. Localhost Simulator API (`core/localhost_simulator.py`)

**LocalhostSimulatorManager Class**

Simulates multiple IO cards on localhost for testing.

```python
from hw_tester.core.localhost_simulator import LocalhostSimulatorManager

# Initialize simulator manager (loads response data from tests/DB/simulator_responses/)
simulator = LocalhostSimulatorManager(
    response_data_dir=Path("tests/DB/simulator_responses")
)

# Start all simulators
simulator.start_all()

# Start specific card
simulator.start_card(card_id=1)

# Get statistics
stats = simulator.get_all_statistics()
simulator.print_statistics()

# Stop all simulators
simulator.stop_all()
```

**Running Standalone:**
```powershell
python src/hw_tester/core/localhost_simulator.py
```

---

#### 7. Configuration API (`utils/config_loader.py`)

**Configuration Loading Functions**

```python
from hw_tester.utils.config_loader import (
    load_settings,
    load_pin_map,
    get_board_config_and_pins,
    get_project_root
)

# Load settings.yaml
settings = load_settings()

# Load pin_map.json
pin_map = load_pin_map()

# Load both settings and pin map
settings, pin_map = get_board_config_and_pins(
    settings_path="src/hw_tester/config/settings.yaml",
    pin_map_path="src/hw_tester/config/pin_map.json"
)

# Get project root directory
project_root = get_project_root()
```

---

#### 8. Document Generation API (`core/doc_handle.py`)

**Document Handler for Test Reports**

```python
from hw_tester.core.doc_handle import DocHandle

# Initialize document handler
doc_handler = DocHandle(
    output_dir="tests/Results",
    template_path="template.docx"  # Optional
)

# Create new test report
doc_handler.create_report(
    title="Power Test Results",
    test_results=results_list
)

# Add test result to document
doc_handler.add_test_result(
    pin_id="J1-1",
    test_type="Power Test",
    result="PASS",
    voltage=12.5,
    expected=12.0,
    tolerance=1.0
)

# Save document
doc_handler.save("test_report_20260413.docx")
```

---

#### 9. Pin Pulser API (`core/pin_pulser.py`)

**Pin Pulsing for Dynamic Tests**

```python
from hw_tester.core.pin_pulser import PinPulser

# Initialize pin pulser
pulser = PinPulser(hardware=hardware)

# Pulse a pin (toggle on/off)
pulser.pulse_pin(
    pin_number=13,
    duration_ms=100,    # Pulse duration
    count=5             # Number of pulses
)

# Generate PWM signal
pulser.pwm(
    pin_number=9,
    duty_cycle=0.5,     # 50% duty cycle
    frequency=1000      # 1 kHz
)
```

---

### UI APIs

#### Qt UI (Primary)

Main window: `src/hw_tester/ui/qt/app.py`

**Features:**
- Modern interface with tabs
- Real-time test visualization
- Expandable test tree view
- Integrated log viewer
- Status indicators

#### Tkinter UI (Legacy)

Main window: `src/hw_tester/ui/main_window.py`

**Features:**
- Traditional desktop interface
- Test table view
- Log panel
- Control buttons

---

## Test Types

### 1. Power Test
**Purpose:** Verify pin can deliver expected voltage

**Steps:**
1. Configure pin as power output
2. Measure voltage on target pin
3. Compare with expected voltage ± tolerance

**Pass Criteria:** Measured voltage within tolerance

---

### 2. Pullup Test
**Purpose:** Verify pullup/pulldown resistor functionality

**Steps:**
1. Configure pin with pullup/pulldown enabled
2. Leave pin floating (no external connection)
3. Measure voltage
4. Expect HIGH for pullup, LOW for pulldown

**Pass Criteria:** Voltage matches pullup/pulldown state

---

### 3. Logic Test
**Purpose:** Verify pin can detect logic levels

**Steps:**
1. Apply known voltage to pin
2. Read pin state (HIGH/LOW)
3. Verify state matches expected

**Pass Criteria:** Detected state matches expected

---

### 4. I-bit Test
**Purpose:** Full system integrity test

**Steps:**
1. Systematically test all pins
2. Verify communication with all cards
3. Check for any anomalies

**Pass Criteria:** All components respond correctly

---

### 5. Relay/Fuse Test
**Purpose:** Verify relay switching and fuse integrity

**Steps:**
1. Activate first relay
2. Measure voltage through circuit
3. Activate second relay
4. Measure voltage through second circuit
5. Verify both paths conduct

**Pass Criteria:** Both paths show expected voltage

---

### 6. Short Circuit Test
**Purpose:** Detect short circuits between pins

**Steps:**
1. Apply voltage to test pin
2. Measure voltage on all other pins
3. Check for unexpected voltage (indicates short)

**Pass Criteria:** No unexpected voltages detected

---

## Troubleshooting

### Issue: Cannot Connect to COM Port

**Symptoms:**
- "Failed to open COM port" error
- Application exits immediately

**Solutions:**
1. Verify COM port in settings.yaml matches Device Manager
2. Close Arduino IDE or other programs using the port
3. Check USB cable connection
4. Try different COM port
5. Enable simulation mode for development

```yaml
Board:
  Port: COM5        # Change to correct port
  simulation: true  # Or enable simulation
```

---

### Issue: UDP Cards Not Responding

**Symptoms:**
- Card timeout errors
- No data received from cards

**Solutions:**
1. Verify IP addresses in settings.yaml
2. Check network connectivity (ping cards)
3. Verify firewall allows UDP traffic on specified ports
4. Use localhost mode for development

```yaml
UDP_Settings:
  localhost_mode: true  # Enable for testing
```

---

### Issue: Test Results Always FAIL

**Symptoms:**
- All tests fail regardless of hardware state

**Solutions:**
1. Check voltage thresholds in settings.yaml
2. Verify pin mapping is correct
3. Check connector address mapping Excel file
4. Review test definitions in DB folder
5. Enable debug mode and check trace

```yaml
scale:
  voltage_tolerance: 2.0  # Increase tolerance
  
Debug:
  mode: true  # Enable debug traces
```

---

### Issue: Web Visualization Not Working

**Symptoms:**
- Browser shows 404 or empty page
- Trace not updating during test

**Solutions:**
1. Verify debug mode is enabled
2. Check that HTML files exist in `src/hw_tester/web/`
3. Ensure web server is running

```powershell
# Run web server
python src/hw_tester/web/serve_nocache.py
```

---

### Issue: UI Not Launching

**Symptoms:**
- Application starts but no window appears
- "Unknown UI_Type" error

**Solutions:**
1. Check UI_Type in settings.yaml
2. Install UI dependencies (Qt or Tkinter)
3. Try alternative UI

```yaml
UI:
  UI_Type: Tkinter  # Switch to Tkinter if Qt fails
```

For Qt:
```powershell
pip install PyQt5
```

---

### Issue: Excel Files Not Loading

**Symptoms:**
- "Failed to load Excel file" error
- Test definitions not found

**Solutions:**
1. Verify Excel files exist in `tests/DB/` directories
2. Check file paths in settings.yaml
3. Install openpyxl

```powershell
pip install openpyxl
```

---

### Issue: Simulation Mode Not Working

**Symptoms:**
- Simulation mode enabled but getting hardware errors

**Solutions:**
1. Verify simulation flag in settings.yaml
2. Check hardware initialization allows no connection

```yaml
Board:
  simulation: true  # Must be true for simulation
```

---

## Advanced Topics

### Creating Custom Test Profiles

1. Create Excel file in `tests/DB/<IO_Box_Type>/`
2. Define test sequence with columns:
   - Pin ID
   - Test Type
   - Expected Value
   - Tolerance
3. Update settings.yaml with path to new test file

### Adding New IO Box Types

1. Create directory: `tests/DB/<new_type>/`
2. Add test definition files
3. Update settings.yaml:

```yaml
IO_Box:
  AvailableTypes:
    - Demo
    - MTC_FWD
    - MTC_AFT
    - YourNewType  # Add here
```

### Extending Hardware Support

1. Create new hardware class in `hardware/`
2. Inherit from base interface or ControllinoIO
3. Update hardware_factory.py to recognize new board type

---

## Additional Resources

### Project Files
- `Arch.txt` - Project architecture overview
- `System_Flows.txt` - System flow documentation
- `LOGIC_TREE_VIEW_PROCEDURE.md` - Logic tree view guide
- `RUNTIME_UPDATE_FIX.md` - Runtime update procedures
- `TRACE_UPDATE_FIX.md` - Trace update procedures

### Test Databases
- `tests/DB/Demo/` - Demo test cases
- `tests/DB/MTC_AFT/` - AFT test cases
- `tests/DB/MTC_FWD/` - FWD test cases
- `tests/DB/simulator_responses/` - Simulated card responses

### Arduino Sketches
- `ControllinoSerialInterface/` - Main firmware for Controllino
- `ControllPinMapper/` - Pin mapping utility
- `sketch_keepalive/` - Keepalive test sketch

---

## Support & Contact

For issues, feature requests, or questions:
1. Check this manual for troubleshooting steps
2. Review `.github/copilot-instructions.md` for development guidance
3. Check test results in `tests/Results/` folder
4. Enable debug mode for detailed logs

---

**End of User Manual**
