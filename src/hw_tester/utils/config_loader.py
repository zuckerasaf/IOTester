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
    """
    return Path(__file__).resolve().parents[3]  # 3 levels up from utils/


def load_settings(path: str = "src/hw_tester/config/settings.yaml") -> dict:
    """
    Load YAML configuration into a dictionary, using a path relative to project root.
    Uses ruamel.yaml if available to preserve comments for later saving.
    """
    full_path = get_project_root() / path
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


def save_settings(settings: dict, path: str = "src/hw_tester/config/settings.yaml") -> None:
    """
    Save settings dictionary back to YAML file while preserving comments.
    Uses ruamel.yaml if available to preserve comments, otherwise falls back to yaml.safe_dump.
    
    Note: The settings dict must be the same object loaded by load_settings() to preserve comments.
    
    Args:
        settings: Settings dictionary to save (must be loaded with ruamel.yaml)
        path: Relative path to settings file from project root
    """
    full_path = get_project_root() / path
    
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


def load_pin_map(path: str = "src/hw_tester/config/pin_map.json") -> dict:
    """
    Load the full pin map JSON (relative path).
    """
    full_path = get_project_root() / path
    if not full_path.exists():
        raise FileNotFoundError(f"Pin map file not found: {full_path}")

    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f) or {}

    if "Boards" not in data:
        raise KeyError("pin_map.json must contain a 'Boards' key")
    return data["Boards"]


def get_board_pin_map(settings: dict, pin_map_path="src/hw_tester/config/pin_map.json") -> dict:
    """
    Return pin map for the board specified in settings.yaml.
    """
    boards = load_pin_map(pin_map_path)
    board_type = settings.get("Board", {}).get("Type")
    if not board_type or board_type not in boards:
        raise KeyError(f"Board '{board_type}' not found in pin_map.json.")
    return boards[board_type]


def get_board_config_and_pins(
    settings_path="src/hw_tester/config/settings.yaml",
    pin_map_path="src/hw_tester/config/pin_map.json",
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
    
    config_path = get_project_root() / "src/hw_tester/config/board_pin_config.json"
    
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
