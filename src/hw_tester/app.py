import sys
from pathlib import Path

# -----------------------------------------------------
# Make project imports work no matter where app runs
# -----------------------------------------------------
# Get the project root (the folder containing "src")
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[2]  # -> C:\ArduinoProject\IO_Tester
SRC_PATH = PROJECT_ROOT / "src"

# Add src to sys.path so Python can import hw_tester.*
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# -----------------------------------------------------
#  Import project modules
# -----------------------------------------------------
from hw_tester.utils.config_loader import get_board_config_and_pins
from hw_tester.utils.read_excell import load_connector_from_excel
from hw_tester.ui.main_window import MainWindow
# In future:
# from hw_tester.hardware.controllino_io import ControllinoIO
# from hw_tester.hardware.arduino_uno_io import ArduinoUnoIO
# from hw_tester.core.sequencer import Sequencer


# -----------------------------------------------------
#  Main logic
# -----------------------------------------------------
def main():
    """
    Main entry point for HW Tester application.
    Launches the Tkinter GUI.
    """
    # Load settings to check configuration
    settings_path = "src/hw_tester/config/settings.yaml"
    pin_map_path = "src/hw_tester/config/pin_map.json"

    settings, pin_map = get_board_config_and_pins(settings_path, pin_map_path)

    board_cfg = settings["Board"]
    board_type = board_cfg["Type"]
    port = board_cfg.get("Port", "COM5")
    baud = board_cfg.get("BaudRate", 57600)
    simulation = board_cfg.get("simulation", True)

    # Launch the main window
    app = MainWindow(title=f"HW Tester - {board_type}")
    
    # Log startup info to the application log
    app.log_view.append("=== HW Tester Startup Info ===", "INFO")
    app.log_view.append(f"Project root: {PROJECT_ROOT}", "INFO")
    app.log_view.append(f"Using board: {board_type}", "INFO")
    app.log_view.append(f"Port: {port}, Baud: {baud}", "INFO")
    app.log_view.append(f"Simulation mode: {simulation}", "SUCCESS" if simulation else "WARNING")
    app.log_view.append(f"Pin map groups: {list(pin_map.keys())}", "INFO")
    app.log_view.append("==============================", "INFO")
    
    # Also print to console
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Using board: {board_type}")
    print(f"Port: {port}, Baud: {baud}")
    print(f"Simulation mode: {simulation}")
    print(f"Pin map groups: {list(pin_map.keys())}")
    print("\nStarting HW Tester GUI...\n")
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nApplication closed by user.")
    
    # Example: later instantiate the hardware class based on board_type
    # hw = ControllinoIO(port, baud, pin_map) if board_type == "ControllinoMega" else ArduinoUnoIO(port, baud, pin_map)
    # sequencer = Sequencer(hw, settings)
    # app = MainWindow(sequencer, settings)


# -----------------------------------------------------
#  Run
# -----------------------------------------------------
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user.")
        sys.exit(0)
