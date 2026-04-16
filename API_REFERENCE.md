# IO Tester - API Quick Reference

**Version:** 1.0.0  
**Last Updated:** April 2026

---

## Quick Start

```python
from hw_tester.hardware.controllino_io import ControllinoIO
from hw_tester.core.measurer import Measurer
from hw_tester.core.test_handle import TestHandle
from hw_tester.utils.config_loader import load_settings, get_board_config_and_pins

# Load configuration
settings, pin_map = get_board_config_and_pins()

# Initialize hardware
hardware = ControllinoIO(port="COM5", baud_rate=115200)

# Initialize measurer
measurer = Measurer(hardware_io=hardware, settings=settings)

# Run tests
test_handler = TestHandle(
    hardware=hardware,
    settings=settings,
    pin_map=pin_map,
    board_config={},
    measurer=measurer,
    card_manager=None,
    log_callback=print
)
```

---

## API Summary by Module

### 1. Hardware Layer (`hardware/`)

#### ControllinoIO
**Purpose:** Direct serial communication with Controllino/Arduino board

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__` | `port, baud_rate, allow_no_connection, log_callback` | Instance | Initialize connection |
| `analog_read` | `pin: int` | `float` | Read analog pin voltage (0-5V) |
| `digital_read` | `pin: int` | `bool` | Read digital pin state |
| `digital_write` | `pin: int, state: bool` | None | Write digital pin state |
| `pin_mode` | `pin: int, mode: str` | None | Set pin mode (INPUT/OUTPUT/INPUT_PULLUP) |
| `send_command` | `cmd: str` | `str` | Send raw command, get response |
| `disconnect` | - | None | Close serial connection |

**Properties:**
- `connected: bool` - Connection status
- `port: str` - Serial port name
- `baud_rate: int` - Communication speed

---

#### Pin
**Purpose:** Pin abstraction with test result tracking

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__` | `pin_id, connector, pin_type, expected_voltage, ...` | Instance | Create pin object |
| `set_result` | `voltage: float, passed: bool, message: str` | None | Store test result |
| `get_result` | - | `TestResult` | Get test result |

**Properties:**
- `pin_id: str` - Unique pin identifier
- `connector: str` - Connector name (e.g., "J1")
- `pin_type: str` - Type (e.g., "POWER", "GND", "DIGITAL")
- `expected_voltage: float` - Expected voltage value
- `test_result: TestResult` - Test outcome

---

### 2. Core Testing (`core/`)

#### TestHandle
**Purpose:** Test execution engine

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__` | `hardware, settings, pin_map, board_config, measurer, card_manager, log_callback` | Instance | Initialize test handler |
| `run_power_test` | `pin: Pin` | `(float, bool, str)` | Test power delivery |
| `run_pullup_test` | `pin: Pin` | `(float, bool, str)` | Test pullup/pulldown |
| `run_logic_test` | `pin: Pin, pin_table_rows: list` | `(float, bool, str)` | Test logic levels |
| `run_i_bit_test` | - | None | Full system test |
| `short_circuit_test` | - | `list[tuple]` | Detect short circuits |
| `relay_fuse_test` | `first_relay, second_relay, pullup_pin, voltage_measure_pin1, voltage_measure_pin2` | `(str, bool)` | Test relays/fuses |
| `measure_voltage` | `pin_id: str, analog_port: int, idx: int` | None | Measure and store voltage |
| `wait_debug` | `ID: int, status: str` | None | Debug pause point |

**Properties:**
- `running: bool` - Test execution flag
- `running_ibit: bool` - I-bit test flag
- `next_event: threading.Event` - Debug control event

---

#### Measurer
**Purpose:** Voltage measurement with simulation support

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__` | `hardware_io, settings: dict` | Instance | Initialize measurer |
| `measure_voltage` | `analog_port: int, duration: float, sample_interval: float, idx: int` | `float` | Measure voltage (average) |

**Default Values:**
- `duration`: From settings (default: 0.5s)
- `sample_interval`: From settings (default: 0.1s)
- `idx`: 0 (for simulation variation)

---

#### UDPSender
**Purpose:** Bidirectional UDP communication (32 bytes send, 64 bytes receive)

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__` | `remote_ip, send_port, receive_port, frequency, timeout, log_callback` | Instance | Initialize UDP sender |
| `start` | - | None | Start communication loop |
| `stop` | - | None | Stop communication |
| `set_digital_output` | `do_number: int, state: bool` | None | Set single DO |
| `set_digital_outputs` | `do_list: List[int]` | None | Set multiple DOs |
| `get_digital_output` | `do_number: int` | `bool` | Get DO state |
| `set_ttl_output` | `ttl_number: int, state: bool` | None | Set single TTL |
| `set_ttl_outputs` | `ttl_list: List[int]` | None | Set multiple TTLs |
| `get_ttl_output` | `ttl_number: int` | `bool` | Get TTL state |
| `set_matrix_dimensions` | `rows: int, columns: int` | None | Configure routing matrix |

**Class Methods:**
- `load_settings(settings_path)` → `dict`
- `get_card_configs_from_settings(settings_path)` → `List[dict]`
- `get_frequency_from_settings(settings_path)` → `float`
- `get_timeout_from_settings(settings_path)` → `float`

**Properties:**
- `send_data: SendData` - Data to send (32 bytes)
- `receive_data: ReceiveData` - Received data (64 bytes)
- `running: bool` - Communication status
- `last_send_time: float` - Last send timestamp
- `last_receive_time: float` - Last receive timestamp

---

#### UDPCardManager
**Purpose:** Manage multiple UDP cards (up to 7)

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__` | `card_configs: List[dict], frequency: float` | Instance | Initialize card manager |
| `from_settings` | `settings_path: str` (class method) | Instance | Load from settings.yaml |
| `start_all` | - | None | Start all cards |
| `stop_all` | - | None | Stop all cards |
| `start_card` | `card_id: int` | `bool` | Start specific card |
| `stop_card` | `card_id: int` | `bool` | Stop specific card |
| `get_card` | `card_id: int` | `UDPSender` | Get card instance |
| `set_digital_output` | `card_id: int, do_number: int, state: bool` | None | Set DO on card |
| `get_statistics` | - | `Dict` | Get all card statistics |

---

#### LocalhostSimulatorManager
**Purpose:** Simulate IO cards on localhost

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__` | `response_data_dir: Path` | Instance | Initialize simulator manager |
| `start_all` | - | None | Start all simulators |
| `stop_all` | - | None | Stop all simulators |
| `start_card` | `card_id: int` | `bool` | Start specific card |
| `stop_card` | `card_id: int` | `bool` | Stop specific card |
| `get_simulator` | `card_id: int` | `LocalhostCardSimulator` | Get simulator instance |
| `get_all_statistics` | - | `Dict[int, Dict]` | Get all statistics |
| `print_statistics` | - | None | Print statistics to console |

**Standalone Execution:**
```powershell
python src/hw_tester/core/localhost_simulator.py
```

---

#### PinPulser
**Purpose:** Generate pulse sequences on pins

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `__init__` | `hardware` | Instance | Initialize pulser |
| `pulse_pin` | `pin_number: int, duration_ms: int, count: int` | None | Pulse pin multiple times |
| `pwm` | `pin_number: int, duty_cycle: float, frequency: int` | None | Generate PWM signal |

---

### 3. Configuration (`utils/`)

#### config_loader Module

| Function | Parameters | Returns | Description |
|----------|-----------|---------|-------------|
| `load_settings` | `settings_path: str = None` | `dict` | Load settings.yaml |
| `load_pin_map` | `pin_map_path: str = None` | `dict` | Load pin_map.json |
| `get_board_config_and_pins` | `settings_path: str, pin_map_path: str` | `(dict, dict)` | Load both configs |
| `get_project_root` | - | `Path` | Get project root directory |

**Auto-detection:**
All functions auto-detect file paths if not provided.

---

### 4. Data Structures

#### SendData (UDP 32 bytes)
```python
from hw_tester.core.udp_data_mapper import SendData

send_data = SendData()
send_data.digital_outputs = [1, 2, 5]  # List of active DOs
send_data.ttl_outputs = [3, 7]          # List of active TTLs
send_data.matrix_rows = 8               # Matrix dimensions
send_data.matrix_columns = 8

# Convert to bytes for sending
data_bytes = send_data.to_bytes()
```

#### ReceiveData (UDP 64 bytes)
```python
from hw_tester.core.udp_data_mapper import ReceiveData

# Parse received bytes
receive_data = ReceiveData.from_bytes(received_bytes)

# Access values
digital_inputs = receive_data.digital_inputs  # List[int]
analog_inputs = receive_data.analog_inputs    # List[float]
ttl_states = receive_data.ttl_states          # List[bool]
```

#### TestResult
```python
from hw_tester.hardware.pin import TestResult

result = TestResult(
    voltage=12.5,
    passed=True,
    message="Test passed"
)

# Properties
print(result.voltage)  # float
print(result.passed)   # bool
print(result.message)  # str
```

---

## Configuration Reference

### settings.yaml Structure

```yaml
# Application Info
IO_Tester:
  Name: str
  Version: str
  Description: str

# Debug Mode
Debug:
  mode: bool  # Enable trace visualization

# UI Selection
UI:
  UI_Type: str  # "Qt" or "Tkinter"

# Test Type
IO_Box:
  Type: str  # Demo, MTC_FWD, MTC_AFT
  AvailableTypes: List[str]

# Hardware
Board:
  Type: str  # ControllinoMega, ArduinoMega, ArduinoUno, none
  AvailableTypes: List[str]
  Port: str  # COM5, /dev/ttyUSB0, etc.
  BaudRate: int  # 115200, 57600, etc.
  simulation: bool  # true = localhost, false = hardware

# Timing
Timeouts:
  duration: float  # Measurement duration (s)
  sample_interval: float  # Sample interval (s)
  TestStep: float  # Time per test step (s)
  Connection: float  # Connection timeout (s)
  pins_to_stabilize: float  # Stabilization delay (s)

# Voltage Thresholds
scale:
  voltage: float  # Scale factor
  voltage_degredation: float  # Acceptable drop
  voltage_tolerance: float  # Measurement tolerance
  zero_voltage_threshold: float  # Zero detection (V)
  Analog_voltage_threshold: float  # Analog threshold (V)
  logic_voltage_threshold: float  # Logic high threshold (V)

# File Paths
Paths:
  Path_1: str  # Project root
  Path_2: str  # Pin map path
  reports: str  # Reports directory
  ConnectorAddressMap: str  # Connector mapping Excel
  powerup_MTC_FWD: str  # Test definition
  powerup_MTC_AFT: str  # Test definition

# UDP Configuration (optional)
UDP_Settings:
  localhost_mode: bool
  frequency: float  # Hz
  timeout: float  # seconds
  Cards:  # Real hardware
    - card_id: int
      ip: str
      send_port: int
      receive_port: int
  Cards_localhost:  # Localhost simulation
    - card_id: int
      ip: "127.0.0.1"
      send_port: int
      receive_port: int
```

---

## Common Usage Patterns

### Pattern 1: Basic Voltage Measurement
```python
from hw_tester.hardware.controllino_io import ControllinoIO
from hw_tester.core.measurer import Measurer
from hw_tester.utils.config_loader import load_settings

settings = load_settings()
hardware = ControllinoIO(port="COM5", baud_rate=115200)
measurer = Measurer(hardware, settings)

voltage = measurer.measure_voltage(analog_port=0)
print(f"Measured voltage: {voltage:.2f}V")
```

### Pattern 2: Running Full Test Suite
```python
from hw_tester.core.test_handle import TestHandle
from hw_tester.hardware.pin import Pin

# Initialize test handler (see Quick Start)
test_handler = TestHandle(...)

# Create pin object
pin = Pin(
    pin_id="J1-1",
    connector="J1",
    pin_type="POWER",
    expected_voltage=12.0,
    tolerance=1.0
)

# Run test
voltage, passed, message = test_handler.run_power_test(pin)
print(f"Pin: {pin.pin_id}, Result: {'PASS' if passed else 'FAIL'}")
print(f"Voltage: {voltage:.2f}V, Message: {message}")
```

### Pattern 3: UDP Multi-Card Control
```python
from hw_tester.core.udp_card_manager import UDPCardManager

# Load from settings.yaml
card_manager = UDPCardManager.from_settings()
card_manager.start_all()

# Control card 1, DO 5
card_manager.set_digital_output(card_id=1, do_number=5, state=True)

# Get card 2
card2 = card_manager.get_card(card_id=2)
card2.set_ttl_output(ttl_number=3, state=True)

# Cleanup
card_manager.stop_all()
```

### Pattern 4: Localhost Simulation
```python
from hw_tester.core.localhost_simulator import LocalhostSimulatorManager
from pathlib import Path

# Start simulator (in separate terminal or thread)
simulator = LocalhostSimulatorManager(
    response_data_dir=Path("tests/DB/simulator_responses")
)
simulator.start_all()

# Now run your application - it will communicate with simulator
# ... your application code ...

# Stop simulator
simulator.stop_all()
```

### Pattern 5: Custom Test Logic
```python
from hw_tester.core.test_handle import TestHandle
from hw_tester.hardware.pin import Pin

class CustomTestHandle(TestHandle):
    def run_custom_test(self, pin: Pin) -> tuple[float, bool, str]:
        """Custom test implementation."""
        # Configure hardware
        self.hardware.pin_mode(pin.analog_port, "INPUT")
        
        # Measure voltage
        voltage = self.measurer.measure_voltage(pin.analog_port)
        
        # Custom logic
        passed = (voltage >= pin.expected_voltage * 0.9 and 
                  voltage <= pin.expected_voltage * 1.1)
        
        message = "Custom test passed" if passed else "Custom test failed"
        
        return voltage, passed, message
```

---

## Error Handling

### Connection Errors
```python
from hw_tester.hardware.controllino_io import ControllinoIO

try:
    hardware = ControllinoIO(port="COM5", baud_rate=115200)
    if not hardware.connected:
        print("Failed to connect to hardware")
except RuntimeError as e:
    print(f"Connection error: {e}")
    # Fallback to simulation mode
    hardware = ControllinoIO(
        port="COM5",
        baud_rate=115200,
        allow_no_connection=True
    )
```

### UDP Timeout Handling
```python
from hw_tester.core.udp_sender import UDPSender

udp = UDPSender(
    remote_ip="192.168.1.100",
    send_port=12345,
    receive_port=12346,
    timeout=2.0  # 2 second timeout
)
udp.start()

# Check if receiving data
if udp.receive_data is None:
    print("No data received - check network connection")
```

### Test Failure Handling
```python
voltage, passed, message = test_handler.run_power_test(pin)

if not passed:
    # Log failure
    print(f"Test FAILED: {message}")
    print(f"Expected: {pin.expected_voltage}V ± {pin.tolerance}V")
    print(f"Measured: {voltage:.2f}V")
    
    # Store result
    pin.set_result(voltage, passed, message)
    
    # Generate report
    # doc_handler.add_test_result(...)
```

---

## Thread Safety

### Thread-Safe Operations
- `ControllinoIO` uses `threading.Lock` for serial access
- `UDPSender` runs communication in separate thread
- `TestHandle.next_event` for inter-thread signaling

### Thread-Safe Example
```python
import threading

def run_test_thread(test_handler, pin):
    """Run test in separate thread."""
    result = test_handler.run_power_test(pin)
    print(f"Test result: {result}")

# Create thread
thread = threading.Thread(
    target=run_test_thread,
    args=(test_handler, pin)
)
thread.start()
thread.join()  # Wait for completion
```

---

## Performance Optimization

### Batch Operations
```python
# Bad: Multiple individual calls
for do in [1, 2, 3, 4, 5]:
    udp_sender.set_digital_output(do, True)

# Good: Single batch call
udp_sender.set_digital_outputs([1, 2, 3, 4, 5])
```

### Measurement Optimization
```python
# Fast measurement (fewer samples)
voltage = measurer.measure_voltage(
    analog_port=0,
    duration=0.1,        # 100ms
    sample_interval=0.05 # 50ms intervals
)

# Accurate measurement (more samples)
voltage = measurer.measure_voltage(
    analog_port=0,
    duration=2.0,        # 2 seconds
    sample_interval=0.01 # 10ms intervals
)
```

---

## Testing & Debugging

### Enable Debug Mode
```yaml
# settings.yaml
Debug:
  mode: true
```

### View Test Traces
```powershell
# Start web server
python src/hw_tester/web/serve_nocache.py

# Open browser to:
# http://localhost:8000/IO_Tester_logic_Power_test.html
```

### Manual Testing
```powershell
# Test UDP communication
python -c "from hw_tester.core.udp_sender import UDPSender; ..."

# Test hardware connection
python -c "from hw_tester.hardware.controllino_io import ControllinoIO; ..."

# Test measurer
python -c "from hw_tester.core.measurer import Measurer; ..."
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | April 2026 | Initial comprehensive API documentation |

---

**End of API Quick Reference**
