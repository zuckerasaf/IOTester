"""
Controllino/Arduino Hardware I/O - Direct serial communication.
"""
import serial
import time
import threading
import pandas as pd
from pathlib import Path

# Shared connector address mapping (loaded once and reused)
_connector_mapping_cache = None


def _load_connector_mapping(type = "a"):
    """Load connector address map from path specified in settings.yaml (cached)"""
    global _connector_mapping_cache
    
    # # Return cached version if already loaded
    # if _connector_mapping_cache is not None:
    #     return _connector_mapping_cache
    
    try:
        from hw_tester.utils.config_loader import load_settings, get_project_root
        settings = load_settings()
        
        # Get board type from settings
        board_type = settings.get('Board', {}).get('Type', 'ControllinoMega')
        
        # Try to get board-specific mapping path first
        board_specific_key = f'ConnectorAddressMap_{board_type}'
        map_path = settings.get('Paths', {}).get(board_specific_key)
        
        # Fallback to default if board-specific path not found
        #if map_path is None:
        if type == "a":
            map_path = settings.get('Paths', {}).get('ConnectorAddressMap_A', 'src/hw_tester/config/connector_Address_map_A.xlsx')
        elif type == "b":
            map_path = settings.get('Paths', {}).get('ConnectorAddressMap_B', 'src/hw_tester/config/connector_Address_map_B.xlsx')
        else:
            map_path = settings.get('Paths', {}).get('ConnectorAddressMap', 'src/hw_tester/config/connector_Address_map.xlsx')
            print(f"[ControllinoIO] No board-specific mapping for {board_type}, using default")
        #else:
        #print(f"[ControllinoIO] Using board-specific mapping for {board_type}")
        
        # Resolve relative to project root (same as pin_map.json)
        full_path = get_project_root() / map_path
        
        if not full_path.exists():
            print(f"[ControllinoIO WARNING] Connector mapping file not found: {full_path}")
            return None
        
        _connector_mapping_cache = pd.read_excel(full_path)
        print(f"[ControllinoIO] Loaded connector mapping from: {full_path}")
        return _connector_mapping_cache
    except Exception as e:
        print(f"[ControllinoIO WARNING] Failed to load connector mapping: {e}")
        return None


class ControllinoIO:
    """
    Hardware I/O implementation for Controllino boards using direct serial commands.
    Requires ControllinoSerialInterface.ino sketch uploaded to the board.
    """
    
    def __init__(self, port: str = "COM5", baud_rate: int = 115200, allow_no_connection: bool = False):
        """
        Initialize connection to Controllino board.
        
        Args:
            port: Serial port (e.g., 'COM5' on Windows)
            baud_rate: Serial baud rate (115200)
            allow_no_connection: If True, don't raise error on connection failure (simulation mode)
        
        Raises:
            RuntimeError: If connection fails and allow_no_connection is False
        """
        self.port = port
        self.baud_rate = baud_rate
        self.serial = None
        self.connected = False
        self._lock = threading.Lock()  # Thread-safe serial access
        
        # Load connector mapping (cached after first load)
        self.connector_mapping = _load_connector_mapping()
        
        try:
            print(f"[ControllinoIO] Connecting to board on {port} @ {baud_rate} baud...")
            self.serial = serial.Serial(
                port=port,
                baudrate=baud_rate,
                timeout=2,
                write_timeout=2
            )
            
            # Wait for Arduino to reset
            time.sleep(2)
            
            # Clear any startup messages
            self.serial.reset_input_buffer()
            
            # Send ping to verify connection
            self.serial.write(b'?\n')
            response = self.serial.readline().decode('utf-8').strip()
            
            if response == "OK":
                print(f"[ControllinoIO] Successfully connected to board on {port}")
                self.connected = True
            else:
                raise RuntimeError(f"Board not responding correctly. Got: {response}")
            
        except Exception as e:
            if allow_no_connection:
                print(f"[ControllinoIO WARNING] Failed to connect to {port}: {str(e)}")
                print(f"[ControllinoIO] Running in no-connection mode (operations will be no-ops)")
                self.connected = False
            else:
                raise RuntimeError(f"Failed to connect to board on {port}: {str(e)}")
    
    def digital_write(self, port: int, value: bool) -> None:
        """
        Write digital value to a pin.
        
        Args:
            port: Digital pin number
            value: True for HIGH (5V), False for LOW (0V)
        """
        if not self.connected:
            # No-op if not connected
            return
            
        with self._lock:  # Ensure thread-safe access
            try:
                # Clear any pending data
                self.serial.reset_input_buffer()
                
                cmd = f"W,{port},{1 if value else 0}\n"
                self.serial.write(cmd.encode('utf-8'))
                
                # Read response with timeout
                response = self.serial.readline().decode('utf-8').strip()
                
                if response.startswith("OK:W"):
                    state = "HIGH" if value else "LOW"
                    print(f"[ControllinoIO] Digital Write: Pin D{port} -> {state}")
                else:
                    print(f"[ControllinoIO ERROR] Failed to write to D{port}: {response}")
                
                # Small delay to prevent buffer overflow
                time.sleep(0.01)
                    
            except Exception as e:
                print(f"[ControllinoIO ERROR] Failed to write to D{port}: {str(e)}")
    
    def analog_read(self, port: int) -> float:
        """
        Read analog value from a pin.
        
        Args:
            port: Analog pin number (54-69 for A0-A15)
        
        Returns:
            Voltage reading (0.0 - 5.0V)
        """
        if not self.connected:
            # Return 0.0 if not connected
            return 0.0
            
        with self._lock:  # Ensure thread-safe access
            try:
                # Clear any pending data
                self.serial.reset_input_buffer()
                
                cmd = f"R,{port}\n"
                self.serial.write(cmd.encode('utf-8'))
                
                # Read response: OK:R,pin,voltage
                response = self.serial.readline().decode('utf-8').strip()
                
                if response.startswith("OK:R"):
                    parts = response.split(',')
                    if len(parts) == 3:
                        voltage = float(parts[2])
                        # print(f"[ControllinoIO] Analog Read: Pin A{port} -> {voltage:.2f}V")
                        return voltage
                    else:
                        print(f"[ControllinoIO ERROR] Invalid response format: {response}")
                        return 0.0
                else:
                    print(f"[ControllinoIO ERROR] Failed to read from A{port}: {response}")
                    return 0.0
                
            except Exception as e:
                print(f"[ControllinoIO ERROR] Failed to read from A{port}: {str(e)}")
                return 0.0
    
    def close(self) -> None:
        """Close connection to the board."""
        try:
            if self.serial and self.serial.is_open:
                self.serial.close()
                print(f"[ControllinoIO] Connection closed")
            self.connected = False
        except Exception as e:
            print(f"[ControllinoIO ERROR] Error closing connection: {str(e)}")
    
    def __repr__(self) -> str:
        return f"ControllinoIO(port={self.port}, baud_rate={self.baud_rate}, connected={self.connected})"
    
    def __del__(self):
        """Cleanup on object destruction."""
        self.close()


def connector_pin_to_bits(pin_number, type="a", mapping_df=None):
    """
    Returns the binary bits (D0–D15) for a given connector pin number (1–50)
    based on the mapping table in connector_Address_map.xlsx
    
    Args:
        pin_number: Connector pin number (1-50)
        type: Mapping type - "a" or "b" (default: "a")
        mapping_df: Optional DataFrame with mapping. If None, loads from cache.
    
    Returns:
        List of 16 integers (0 or 1) representing the bit pattern
    """
    # Use provided mapping or load from cache
    df = mapping_df if mapping_df is not None else _load_connector_mapping(type)
    
    if df is None:
        raise RuntimeError("Connector mapping not loaded. Cannot convert pin to bits.")
    
    # The connector pin column is the last one (W)
    row = df[df.iloc[:, -1] == pin_number]

    if row.empty:
        raise ValueError(f"Pin number {pin_number} not found in mapping table")

    # Bit columns are columns G–V → in your file they are columns 6 to 21 (0-indexed)
    bit_cols = df.columns[6:22]

    # Return the bits as a list of ints
    bits = row[bit_cols].iloc[0].astype(int).tolist()
    return bits


if __name__ == "__main__":
    """
    Test/debug mode - run this file directly to test connector_pin_to_bits function.
    Usage: python -m hw_tester.hardware.controllino_io
    """
    import sys
    from pathlib import Path
    
    # Add project root to path for imports
    project_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(project_root / "src"))
    
    # Reload the mapping with correct path
    from hw_tester.utils.config_loader import load_settings, get_project_root
    settings = load_settings()
    map_path = settings.get('Paths', {}).get('ConnectorAddressMap', 'src/hw_tester/config/connector_Address_map.xlsx')
    full_path = get_project_root() / map_path
    
    if full_path.exists():
        df = pd.read_excel(full_path)
        print(f"[ControllinoIO Test] Loaded mapping from: {full_path}")
    else:
        print(f"[ControllinoIO Test] ERROR: Mapping file not found at {full_path}")
        sys.exit(1)
    
    print("[ControllinoIO Test] Testing connector_pin_to_bits function...")
    print("=" * 60)
    
    # Test with some example pin numbers
    test_pins = [1, 4, 16, 25, 50]
    
    for pin_num in test_pins:
        try:
            bits = connector_pin_to_bits(pin_num, type="a", mapping_df=df)
            bits_str = ''.join(str(b) for b in bits)
            print(f"Pin {pin_num:2d} -> Bits: {bits_str} -> {bits}")
        except ValueError as e:
            print(f"Pin {pin_num:2d} -> ERROR: {e}")
        except Exception as e:
            print(f"Pin {pin_num:2d} -> UNEXPECTED ERROR: {e}")
    
    print("=" * 60)
    print("[ControllinoIO Test] Test complete")

