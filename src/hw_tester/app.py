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
from hw_tester.utils.config_loader import load_settings


# -----------------------------------------------------
#  Main logic
# -----------------------------------------------------
def main():
    """
    Main entry point for HW Tester application.
    Launches the Qt UI.
    """
    # Load settings for logging only.
    settings = load_settings()
    ui_type = settings.get('UI', {}).get('UI_Type', 'Qt')
    
    print(f"UI Type (configured): {ui_type}")
    print(f"Project root: {PROJECT_ROOT}")

    if ui_type != "Qt":
        print(f"UI_Type '{ui_type}' is deprecated. Forcing Qt mode for EXE compatibility.")

    print("Launching Qt UI...")
    from hw_tester.ui.qt.app import main as qt_main
    return qt_main()


# -----------------------------------------------------
#  Run
# -----------------------------------------------------
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user.")
        sys.exit(0)
