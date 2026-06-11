import sys
import yaml
import json
from pathlib import Path

try:
    from ruamel.yaml import YAML
    HAS_RUAMEL = True
except ImportError:
    HAS_RUAMEL = False


def get_project_root() -> Path:
    """
    Return the absolute path to the project root (where 'src' folder lives).

    When running under PyInstaller in onefile mode, use the internal extracted path.
    When running normally, use the repo root above src/hw_tester/utils.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[3]  # 3 levels up from utils/


def get_config_root() -> Path:
    """
    Return the folder containing the deployed config files.

    Prefer an external `config` folder located next to the running executable/script.
    Fall back to the PyInstaller `_MEIPASS/config` folder if present.
    Otherwise return the normal source config folder.
    """
    exe_dir = Path(sys.argv[0]).resolve().parent
    external_config = exe_dir / "config"
    if external_config.exists():
        return external_config

    if getattr(sys, '_MEIPASS', None):
        internal_config = Path(sys._MEIPASS) / "config"
        if internal_config.exists():
            return internal_config

    if getattr(sys, 'frozen', False):
        return exe_dir

    return get_project_root() / "src" / "hw_tester" / "config"


def resolve_config_path(path: str) -> Path:
    """
    Resolve a relative config asset path to the actual filesystem location.

    This supports:
    - normal source mode: src/hw_tester/config/...
    - PyInstaller frozen mode with external config/ next to EXE
    - PyInstaller internal bundled config under _MEIPASS/config
    """
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate

    if getattr(sys, 'frozen', False):
        config_root = get_config_root()

        # Most deployed config files are in a flat config folder next to the EXE.
        flat_path = config_root / candidate.name
        if flat_path.exists():
            return flat_path

        # If the internal bundle keeps relative folders, preserve the nested path.
        nested_path = config_root / candidate
        if nested_path.exists():
            return nested_path

        # If the path was provided as src/hw_tester/config/..., try the filename alone.
        if candidate.parts[-1]:
            return config_root / candidate.name

        return nested_path

    if candidate.parts[:4] == ('src', 'hw_tester', 'config'):
        return get_project_root() / candidate
    if candidate.parts[0] == 'config':
        return get_project_root() / "src" / "hw_tester" / Path(*candidate.parts[1:])
    return get_project_root() / "src" / "hw_tester" / "config" / candidate


def load_settings(path: str = "settings.yaml") -> dict:
    """
    Load YAML configuration into a dictionary, using a path relative to the config directory.
    Uses ruamel.yaml if available to preserve comments for later saving.
    """
    full_path = resolve_config_path(path)
    if not full_path.exists():
        raise FileNotFoundError(f"Settings file not found: {full_path}")

    if HAS_RUAMEL:
        # Use ruamel.yaml to load and preserve comments
        yaml_handler = YAML()
        with open(full_path, "r", encoding="utf-8") as f:
            return yaml_handler.load(f)
    else:
        # Fallback to standard yaml (loses comments)
        with open(full_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}


def save_settings(settings: dict, path: str = "settings.yaml") -> None:
    """
    Save settings dictionary back to YAML file while preserving comments.
    Uses ruamel.yaml if available to preserve comments, otherwise falls back to yaml.safe_dump.
    
    Note: The settings dict must be the same object loaded by load_settings() to preserve comments.
    
    Args:
        settings: Settings dictionary to save (must be loaded with ruamel.yaml)
        path: Relative path to settings file from project root
    """
    full_path = resolve_config_path(path)
    
    if HAS_RUAMEL:
        # Use ruamel.yaml to preserve comments and formatting
        yaml_handler = YAML()
        yaml_handler.preserve_quotes = True
        yaml_handler.default_flow_style = False
        
        # Write back with preserved comments (settings dict already has comment metadata)
        with open(full_path, "w", encoding="utf-8") as f:
            yaml_handler.dump(settings, f)
    else:
        # Fallback to standard yaml (loses comments)
        with open(full_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(settings, f, default_flow_style=False, sort_keys=False)


def load_pin_map(path: str = "pin_map.json") -> dict:
    """
    Load the full pin map JSON (relative path).
    """
    full_path = resolve_config_path(path)
    if not full_path.exists():
        raise FileNotFoundError(f"Pin map file not found: {full_path}")

    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f) or {}

    if "Boards" not in data:
        raise KeyError("pin_map.json must contain a 'Boards' key")
    return data["Boards"]


def get_board_pin_map(settings: dict, pin_map_path="pin_map.json") -> dict:
    """
    Return pin map for the board specified in settings.yaml.
    """
    boards = load_pin_map(pin_map_path)
    board_type = settings.get("Board", {}).get("Type")
    if not board_type or board_type not in boards:
        raise KeyError(f"Board '{board_type}' not found in pin_map.json.")
    return boards[board_type]


def get_board_config_and_pins(
    settings_path="settings.yaml",
    pin_map_path="pin_map.json",
) -> tuple[dict, dict]:
    """
    Convenience helper: loads both settings and board pin map.
    """
    settings = load_settings(settings_path)
    pins = get_board_pin_map(settings, pin_map_path)
    return settings, pins


def get_board_pin_config(settings: dict) -> dict:
    """
    Get board-specific pin configuration (voltage measurement pin, control pins, etc.).
    
    Args:
        settings: Settings dictionary containing board type
    
    Returns:
        Dictionary with board-specific pin configuration
    """
    board_type = settings.get('Board', {}).get('Type', 'ArduinoUno')
    
    config_path = resolve_config_path("board_pin_config.json")
    
    try:
        with open(config_path, 'r') as f:
            all_configs = json.load(f)
        
        if board_type not in all_configs:
            print(f"[ConfigLoader WARNING] Board type '{board_type}' not found in board_pin_config.json, using ArduinoUno")
            board_type = 'ArduinoUno'
        
        config = all_configs[board_type]
        print(f"[ConfigLoader] Loaded pin config for {board_type}: voltage_measure_pin={config.get('voltage_measure_pin')}")
        return config
    
    except FileNotFoundError:
        print(f"[ConfigLoader ERROR] Board pin config file not found: {config_path}")
        return {'voltage_measure_pin': 'A0', 'digital_control_pins': {}, 'analog_pins': {}}
    except json.JSONDecodeError as e:
        print(f"[ConfigLoader ERROR] Invalid JSON in board pin config file: {e}")
        return {'voltage_measure_pin': 'A0', 'digital_control_pins': {}, 'analog_pins': {}}
    except Exception as e:
        print(f"[ConfigLoader ERROR] Unexpected error loading board pin config: {e}")
        return {'voltage_measure_pin': 'A0', 'digital_control_pins': {}, 'analog_pins': {}}
