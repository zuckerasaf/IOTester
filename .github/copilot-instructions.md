# IO Tester Project - AI Coding Agent Instructions

## Project Overview
Hardware I/O testing framework for Controllino Mega (development on Arduino Uno). Python-based application using Firmata protocol to control a mux matrix for automated circuit testing - measuring voltages between pins and closing circuits between connector pins.

## Architecture

### Package Structure (`src/hw_tester/`)
- **`app.py`** - Main entry point for the application
- **`hardware/`** - Hardware abstraction layer
  - `base_io.py` - Abstract interface for hardware operations
  - `controllino_io.py` - Real Controllino/Arduino implementation (pyFirmata/serial)
  - `mock_io.py` - Fake hardware for offline development and testing
- **`core/`** - Business logic of the tester
  - `matrix_router.py` - Mux matrix control: "connect pin A to pin B" logic
  - `measurer.py` - Voltage reading and continuity checks
  - `sequencer.py` - Test sequence orchestration and execution
  - `results.py` - Pass/fail logic, logging, result export
- **`ui/`** - Tkinter GUI layer (future: web interface)
  - `main_window.py` - Main GUI window and application loop
  - `views/` - Dialogs, widgets, custom UI components
- **`config/`** - Configuration files (YAML/JSON)
  - `settings.yaml` - Global settings (COM ports, timeouts, thresholds)
  - `pin_map.json` - Controllino pin mapping
  - `test_profiles/` - Test definitions (sequences, expected values)
- **`utils/`** - Shared utilities
  - `config_loader.py` - Load settings.yaml and pin maps
  - `logging_setup.py` - Standardized logging configuration

### Key Design Principles
- **Hardware Abstraction**: `base_io.py` defines interface, `controllino_io.py` implements real hardware, `mock_io.py` enables offline dev/testing
- **Separation of Concerns**: Hardware layer (`hardware/`) isolated from business logic (`core/`) and UI (`ui/`)
- **Configuration-Driven**: Test definitions, pin mappings, and settings in `config/` (YAML/JSON) for easy modification
- **Python Package**: Install with `pip install -e .` for development (use `src/` layout pattern)
- **Board Abstraction**: Support both Arduino Uno (dev) and Controllino Mega (production) with same codebase

## Development Workflow

### Environment Setup
```powershell
# Create and activate virtual environment (already exists as .venv)
.\.venv\Scripts\Activate.ps1

# Install in editable mode with dependencies
pip install -e .
```

### Dependencies to Add
When implementing, likely dependencies include:
- `pyserial` - Serial communication
- `pyFirmata` or `pymata4` - Firmata protocol implementation for Python
- `pytest` - Testing framework
- `pyyaml` or `toml` - Configuration file parsing
- Tkinter (built-in with Python) - Primary GUI framework
- Future: `flask` or `fastapi` + web framework for web interface phase

### Running Tests
```powershell
pytest tests/ -v
```

## Implementation Guidance

### Hardware Communication Pattern
- Use Firmata protocol via `pyFirmata` or `pymata4` library
- Arduino/Controllino must run StandardFirmata or custom Firmata firmware
- Implement device auto-detection (scan COM ports on Windows)
- Create abstraction layer in `hardware/` that works with both Arduino Uno and Controllino Mega
- Handle timeouts and disconnections gracefully

### Mux Matrix Control
- Design mux matrix configuration schema for routing connections between connector pins
- Implement mux control logic in `hardware/controllino_io.py` to switch circuit paths
- `core/matrix_router.py` handles high-level routing: "connect pin A to pin B" logic
- Support two primary operations:
  1. **Voltage measurement**: Connect analog inputs to measure voltage between two pins
  2. **Circuit closing**: Close circuits between specified connector pins for continuity testing

### Test Sequencing
- `core/sequencer.py` orchestrates test execution: load test profiles, execute sequences, coordinate with matrix_router and measurer
- `core/measurer.py` performs actual voltage readings and continuity checks via hardware layer
- `core/results.py` handles pass/fail determination, logging, and exporting results

### Configuration Files
- Store test definitions as YAML/JSON in `config/test_profiles/`
- `config/settings.yaml` - Global settings (COM ports, timeouts, voltage thresholds)
- `config/pin_map.json` - Pin mapping for Arduino Uno (development) and Controllino Mega (production)
- Mux matrix routing tables: define which control pins activate which circuit paths
- Example test profile structure: test name, connector pins, expected voltage ranges, pass/fail criteria

### Core Testing Engine
- Test runner loads config via `utils/config_loader.py`, initializes Firmata connection, configures mux matrix
- `core/sequencer.py` executes test sequences from `config/test_profiles/`
- `core/measurer.py` performs voltage measurements and continuity checks
- `core/results.py` generates pass/fail status based on thresholds, timing data, measured values

## Project Conventions

### Module Organization
- Each subdirectory should have descriptive modules (not just `__init__.py`)
- Example: `hardware/firmata_board.py`, `hardware/mux_controller.py`, `core/test_runner.py`, `core/result_collector.py`
- UI modules: `ui/main_window.py`, `ui/test_panel.py`, `ui/results_viewer.py`

### Entry Point
- Create GUI entry point in `src/hw_tester/__main__.py` or console script in `setup.py`/`pyproject.toml`
- Tkinter app should be modular to allow future web interface integration (keep UI logic separate from core)

### Error Handling
- Hardware operations must handle serial port errors, device not found, timeout conditions
- Provide clear error messages for common issues (wrong COM port, Arduino not responding, etc.)

## Next Steps for New Features
1. Define `pyproject.toml` or `setup.py` with project metadata and dependencies
2. Implement Firmata abstraction layer in `hardware/base_io.py` (interface) and `hardware/controllino_io.py` (implementation)
3. Create `hardware/mock_io.py` for offline development and testing
4. Implement mux matrix control logic in `core/matrix_router.py`
5. Create test definition schema and example configs in `config/test_profiles/`
6. Build test orchestration in `core/sequencer.py`, voltage/continuity logic in `core/measurer.py`
7. Add Tkinter GUI in `ui/main_window.py` for executing tests and viewing results
8. Keep UI decoupled from core logic to enable future web interface migration
