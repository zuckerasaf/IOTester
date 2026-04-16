# IO Tester - Hardware Testing Framework

A comprehensive hardware I/O testing application for Controllino Mega and Arduino-based systems with automated test execution, UDP communication, and real-time visualization.

## 🚀 Quick Start

```powershell
# 1. Create virtual environment and activate
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install application
pip install -e .

# 3. Configure settings
# Edit src/hw_tester/config/settings.yaml

# 4. Run application
python src/hw_tester/app.py
```

## 📚 Documentation

- **[USER_MANUAL.md](USER_MANUAL.md)** - Complete user guide with setup, configuration, and troubleshooting
- **[API_REFERENCE.md](API_REFERENCE.md)** - Detailed API documentation for developers
- **[Arch.txt](Arch.txt)** - Project architecture overview
- **[System_Flows.txt](System_Flows.txt)** - System flow documentation

## ✨ Features

- ✅ **Multiple Test Types:** Power, Pullup, Logic, I-bit, Relay/Fuse, Short Circuit
- ✅ **Dual UI:** Modern Qt or legacy Tkinter interface
- ✅ **Simulation Mode:** Develop and test without hardware using localhost simulator
- ✅ **UDP Multi-Card Support:** Control up to 7 IO cards simultaneously
- ✅ **Web Visualization:** Real-time test trace visualization in browser
- ✅ **Excel Integration:** Test definitions from XLSM files
- ✅ **Automated Reporting:** Generate Word documents for test results
- ✅ **Thread-Safe Operations:** Concurrent test execution

## 🔧 System Requirements

### Hardware
- Controllino Mega / Arduino Mega / Arduino Uno
- USB connection to PC
- Optional: IO cards for real hardware testing

### Software
- Python 3.8 or higher
- Windows (primary), Linux/Mac (untested)
- Available COM port for board connection
- Web browser (for trace visualization)

### Dependencies
- pyserial - Serial communication
- pyyaml - Configuration parsing
- pandas - Excel data handling
- openpyxl - Excel file I/O
- python-docx - Report generation

## 🎯 Operating Modes

### 1. Hardware Mode
Test with physical Controllino/Arduino and IO cards.

```yaml
# settings.yaml
Board:
  simulation: false
  Port: COM5
```

### 2. Localhost Simulation Mode
Develop and test without physical hardware.

```yaml
# settings.yaml
Board:
  simulation: true
```

```powershell
# Run simulator (separate terminal)
python src/hw_tester/core/localhost_simulator.py

# Run application
python src/hw_tester/app.py
```

### 3. Web Visualization Mode
View test execution flow in browser.

```powershell
# Start web server
python src/hw_tester/web/serve_nocache.py

# Open browser: http://localhost:8000
```

## 📖 Quick API Examples

### Basic Voltage Measurement
```python
from hw_tester.hardware.controllino_io import ControllinoIO
from hw_tester.core.measurer import Measurer
from hw_tester.utils.config_loader import load_settings

settings = load_settings()
hardware = ControllinoIO(port="COM5", baud_rate=115200)
measurer = Measurer(hardware, settings)

voltage = measurer.measure_voltage(analog_port=0)
print(f"Voltage: {voltage:.2f}V")
```

### Running Power Test
```python
from hw_tester.core.test_handle import TestHandle
from hw_tester.hardware.pin import Pin

pin = Pin(pin_id="J1-1", connector="J1", pin_type="POWER", 
          expected_voltage=12.0, tolerance=1.0)

voltage, passed, message = test_handler.run_power_test(pin)
print(f"Result: {'PASS' if passed else 'FAIL'} - {message}")
```

### UDP Multi-Card Control
```python
from hw_tester.core.udp_card_manager import UDPCardManager

card_manager = UDPCardManager.from_settings()
card_manager.start_all()

# Control card 1, digital output 5
card_manager.set_digital_output(card_id=1, do_number=5, state=True)

card_manager.stop_all()
```

## 🏗️ Project Structure

```
IO_Tester/
├── src/hw_tester/
│   ├── app.py                    # Main entry point
│   ├── config/                   # Configuration files
│   │   ├── settings.yaml         # Main settings
│   │   ├── pin_map.json          # Pin mappings
│   │   └── board_pin_config.json # Board configuration
│   ├── hardware/                 # Hardware abstraction
│   │   ├── controllino_io.py     # Serial communication
│   │   ├── hardware_factory.py   # Hardware factory
│   │   └── pin.py                # Pin abstraction
│   ├── core/                     # Business logic
│   │   ├── test_handle.py        # Test execution
│   │   ├── measurer.py           # Voltage measurements
│   │   ├── udp_sender.py         # UDP communication
│   │   ├── udp_card_manager.py   # Multi-card management
│   │   └── localhost_simulator.py # Localhost simulation
│   ├── ui/                       # User interfaces
│   │   ├── main_window.py        # Tkinter UI
│   │   └── qt/                   # Qt UI
│   ├── web/                      # Web visualization
│   │   ├── Web_Presentation.py   # Test flow generation
│   │   └── serve_nocache.py      # Development server
│   └── utils/                    # Utilities
│       ├── config_loader.py      # Configuration loading
│       └── general.py            # General utilities
├── tests/                        # Test definitions & results
│   ├── DB/                       # Test databases
│   │   ├── Demo/                 # Demo tests
│   │   ├── MTC_AFT/              # AFT test cases
│   │   ├── MTC_FWD/              # FWD test cases
│   │   └── simulator_responses/  # Simulator data
│   └── Results/                  # Test reports
├── ControllinoSerialInterface/   # Arduino firmware
├── requirements.txt              # Python dependencies
├── setup.py                      # Package setup
└── pyproject.toml               # Project configuration
```

## 🧪 Test Types

| Test Type | Purpose | Pass Criteria |
|-----------|---------|---------------|
| Power Test | Verify pin can deliver voltage | Voltage within tolerance |
| Pullup Test | Verify pullup/pulldown resistor | Voltage matches configuration |
| Logic Test | Verify logic level detection | State matches expected |
| I-bit Test | Full system integrity check | All components respond |
| Relay/Fuse Test | Test relay switching | Both paths conduct |
| Short Circuit Test | Detect shorts between pins | No unexpected voltages |

## 🔌 API Overview

### Hardware Layer
- **ControllinoIO** - Serial communication with board
- **Pin** - Pin abstraction and test result tracking
- **hardware_factory** - Hardware instantiation

### Core Testing
- **TestHandle** - Test execution engine
- **Measurer** - Voltage measurement with simulation
- **UDPSender** - Single card UDP communication (32B send / 64B receive)
- **UDPCardManager** - Multi-card management (up to 7 cards)
- **LocalhostSimulatorManager** - Localhost simulation for development

### Configuration
- **config_loader** - Load settings.yaml and pin_map.json
- **general** - Utility functions

See [API_REFERENCE.md](API_REFERENCE.md) for complete API documentation.

## 🛠️ Configuration

### Main Settings: `settings.yaml`

```yaml
UI:
  UI_Type: Qt          # Qt or Tkinter

IO_Box:
  Type: MTC_AFT        # Demo, MTC_FWD, MTC_AFT

Board:
  Type: ControllinoMega
  Port: COM5
  BaudRate: 115200
  simulation: true     # true = localhost, false = hardware

Timeouts:
  duration: 0.5
  sample_interval: 0.1
  TestStep: 2.5

scale:
  voltage: 6.14
  voltage_tolerance: 1.5
  zero_voltage_threshold: 0.5
```

## 🚨 Troubleshooting

### Cannot Connect to COM Port
1. Verify COM port in settings.yaml matches Device Manager
2. Close Arduino IDE or other programs using the port
3. Enable simulation mode: `Board: simulation: true`

### UDP Cards Not Responding
1. Verify IP addresses in settings.yaml
2. Check network connectivity (ping cards)
3. Use localhost mode: `UDP_Settings: localhost_mode: true`

### Test Results Always Fail
1. Check voltage thresholds in settings.yaml
2. Verify pin mapping is correct
3. Enable debug mode: `Debug: mode: true`

See [USER_MANUAL.md](USER_MANUAL.md) for complete troubleshooting guide.

## 📦 Installation Details

### Install from Source
```powershell
git clone <repository-url>
cd IO_Tester
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### Upload Arduino Firmware
1. Open Arduino IDE
2. Load `ControllinoSerialInterface/ControllinoSerialInterface.ino`
3. Select board: Tools → Board → Controllino Mega
4. Select port: Tools → Port → COMx
5. Upload

## 🎨 UI Options

### Qt UI (Recommended)
Modern interface with tabbed layout and real-time visualization.

```yaml
UI:
  UI_Type: Qt
```

### Tkinter UI (Legacy)
Traditional desktop interface.

```yaml
UI:
  UI_Type: Tkinter
```

## 📊 Test Database Structure

Test definitions stored in `tests/DB/<IO_Box_Type>/`:
- Excel files (XLSM) with test sequences
- JSON files for powerup/powerdown procedures
- Connector mapping files

Example: `tests/DB/MTC_AFT/powerup_MTC_AFT.json`

## 🌐 Web Visualization

Real-time test execution flow visualization:
1. Enable debug mode in settings.yaml
2. Run tests (generates HTML/DOT files in `web/`)
3. Start web server: `python src/hw_tester/web/serve_nocache.py`
4. Open browser: http://localhost:8000

## 🤝 Contributing

1. Follow project structure in [Arch.txt](Arch.txt)
2. Maintain separation of concerns (hardware/core/ui layers)
3. Add tests in `tests/` directory
4. Update documentation when adding features

## 📄 License

[Specify your license here]

## 📞 Support

For detailed documentation:
- User guide: [USER_MANUAL.md](USER_MANUAL.md)
- API reference: [API_REFERENCE.md](API_REFERENCE.md)
- Architecture: [Arch.txt](Arch.txt)

---

**Version:** 1.0.0  
**Last Updated:** April 2026
