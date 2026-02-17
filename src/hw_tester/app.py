import sys
from pathlib import Path
import yaml

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
from hw_tester.utils.config_loader import get_board_config_and_pins, load_settings


# -----------------------------------------------------
#  Main logic
# -----------------------------------------------------
def main():
    """
    Main entry point for HW Tester application.
    Reads UI_Type from settings and launches appropriate UI (Qt or Tkinter).
    """
    # Load settings to determine which UI to launch
    settings = load_settings()
    ui_type = settings.get('UI', {}).get('UI_Type', 'Tkinter')
    
    print(f"UI Type: {ui_type}")
    print(f"Project root: {PROJECT_ROOT}")
    
    if ui_type == "Qt":
        # Launch Qt UI
        print("Launching Qt UI...")
        from hw_tester.ui.qt.app import main as qt_main
        return qt_main()
    
    elif ui_type == "Tkinter":
        # Launch Tkinter UI
        print("Launching Tkinter UI...")
        from hw_tester.ui.main_window import MainWindow
        
        # Load settings for display
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
        print(f"Using board: {board_type}")
        print(f"Port: {port}, Baud: {baud}")
        print(f"Simulation mode: {simulation}")
        print(f"Pin map groups: {list(pin_map.keys())}")
        print("\nStarting HW Tester GUI...\n")
        
        try:
            app.run()
        except KeyboardInterrupt:
            print("\nApplication closed by user.")
    
    else:
        print(f"ERROR: Unknown UI_Type '{ui_type}'. Please set UI_Type to 'Qt' or 'Tkinter' in settings.yaml")
        return 1


# -----------------------------------------------------
#  Run
# -----------------------------------------------------
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user.")
        sys.exit(0)
