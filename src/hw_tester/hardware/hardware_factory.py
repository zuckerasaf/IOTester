"""
Hardware Factory - Initializes hardware I/O based on board type from settings.
"""
from typing import Optional


def initialize_hardware(settings: dict):
    """
    Initialize hardware I/O based on Board Type from settings.
    
    Args:
        settings: Settings dictionary containing Board configuration
    
    Returns:
        Hardware I/O object or None for simulation mode or unsupported boards
        
    Example:
        settings = {'Board': {'Type': 'ControllinoMega', 'simulation': False, 'Port': 'COM5', 'BaudRate': 115200}}
        hardware = initialize_hardware(settings)
    """
    board_config = settings.get('Board', {})
    board_type = board_config.get('Type', 'none')
    is_simulation = board_config.get('simulation', True)
    port = board_config.get('Port', 'COM5')
    
    # Return None for 'none' board type
    if board_type == 'none':
        return None
    
    # NOTE: Simulation mode does NOT skip hardware initialization
    # simulation=True means: Use predefined/fake measurement data instead of real sensor readings
    # simulation=False means: Use actual measurement data from the board
    # In both cases, the board hardware is initialized and can be controlled
    
    # Initialize real hardware based on board type
    if board_type in ["ControllinoMega", "ControllinoMini", "ArduinoUno", "ArduinoMega"]:
        from hw_tester.hardware.controllino_io import ControllinoIO
        baud = board_config.get('BaudRate', 115200)
        
        try:
            # Allow no connection in simulation mode
            return ControllinoIO(port=port, baud_rate=baud, allow_no_connection=is_simulation)
        except Exception as e:
            print(f"[HardwareFactory ERROR] Failed to initialize {board_type}: {str(e)}")
            print(f"[HardwareFactory] Make sure:")
            print(f"  1. Board is connected to {port}")
            print(f"  2. ControllinoSerialInterface.ino is uploaded to the board")
            print(f"  3. pyserial is installed: pip install pyserial")
            
            # Automatically enable simulation mode and save settings
            if not is_simulation:
                print(f"[HardwareFactory] Automatically enabling simulation mode...")
                settings['Board']['simulation'] = True
                
                # Save updated settings
                try:
                    from hw_tester.utils.config_loader import save_settings
                    save_settings(settings)
                    print(f"[HardwareFactory] Simulation mode enabled in settings.yaml")
                except Exception as save_error:
                    print(f"[HardwareFactory WARNING] Failed to save settings: {save_error}")
                
                # Try again with simulation mode enabled
                try:
                    return ControllinoIO(port=port, baud_rate=baud, allow_no_connection=True)
                except Exception as retry_error:
                    print(f"[HardwareFactory ERROR] Failed to initialize even in simulation mode: {retry_error}")
                    return None
            else:
                # Already in simulation mode, just return None
                return None
    
    # Return None only when board type is 'none'
    return None
