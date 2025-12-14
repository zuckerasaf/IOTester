"""
UDP Data Mapper - Translates between logical I/O parameters and UDP byte positions.

Provides two separate data structures:
1. SendData - For data transmitted to cards (32 bytes)
2. ReceiveData - For data received from cards (64 bytes)
"""
from typing import Dict, List, Optional, Union
import struct


class SendData:
    """
    Maps logical parameters to send data structure (32 bytes).
    
    SEND DATA STRUCTURE (32 bytes):
    - Byte 0: Header (0x55)
    - Byte 1: Reserved
    - Bytes 2-5: Digital Outputs (DO 1-32, bit-mapped)
    - Bytes 6-7: TTL Outputs (TTL 1-16, bit-mapped)
    - Bytes 8-9: Matrix Dimensions (Row: byte 8, Column: byte 9)
    - Bytes 10-11: Reserved
    - Bytes 12-27: Analog Outputs (AO 0-7, 16-bit each, little-endian)
    - Bytes 28-31: Reserved
    """
    
    def __init__(self):
        """Initialize send data structure."""
        self.data = bytearray(32)
        self.data[0] = 0x55  # Header byte
        
        # Logical parameter storage
        self.digital_outputs: Dict[int, bool] = {}  # DO number -> state
        self.analog_outputs: Dict[int, float] = {}  # AO number -> voltage
        self.ttl_outputs: Dict[int, bool] = {}  # TTL number -> state
        self.matrix_row_dimension: int = 0  # 0-8 rows (0 = no matrix)
        self.matrix_column_dimension: int = 0  # 0-8 columns (0 = no matrix)
    
    def set_digital_output(self, do_number: int, state: bool) -> None:
        """
        Set digital output state.
        
        Args:
            do_number: Digital output number (1-32)
            state: True for ON, False for OFF
        
        Mapping:
            DO 1-8   -> data[2], bits 0-7
            DO 9-16  -> data[3], bits 0-7
            DO 17-24 -> data[4], bits 0-7
            DO 25-32 -> data[5], bits 0-7
        """
        if not (1 <= do_number <= 32):
            raise ValueError(f"Digital output {do_number} out of range (1-32)")
        
        # Store logical state
        self.digital_outputs[do_number] = state
        
        # Calculate byte and bit position
        byte_index = 2 + (do_number - 1) // 8
        bit_position = (do_number - 1) % 8
        
        if state:
            # Set bit to 1
            self.data[byte_index] |= (1 << bit_position)
        else:
            # Clear bit to 0
            self.data[byte_index] &= ~(1 << bit_position)
    
    def get_digital_output(self, do_number: int) -> bool:
        """
        Get digital output state.
        
        Args:
            do_number: Digital output number (1-32)
        
        Returns:
            True if ON, False if OFF
        """
        if not (1 <= do_number <= 32):
            raise ValueError(f"Digital output {do_number} out of range (1-32)")
        
        return self.digital_outputs.get(do_number, False)
    
    def set_digital_outputs(self, do_list: List[int]) -> None:
        """
        Set multiple digital outputs to ON, all others to OFF.
        
        Args:
            do_list: List of digital output numbers (1-32) to set to ON
        """
        # Clear all digital outputs
        self.digital_outputs.clear()
        self.data[2] = 0
        self.data[3] = 0
        self.data[4] = 0
        self.data[5] = 0
        
        # Set specified outputs to ON
        for do in do_list:
            self.set_digital_output(do, True)
    
    def set_ttl_output(self, ttl_number: int, state: bool) -> None:
        """
        Set TTL output state.
        
        Args:
            ttl_number: TTL output number (1-16)
            state: True for ON, False for OFF
        
        Mapping:
            TTL 1-8  -> data[6], bits 0-7
            TTL 9-16 -> data[7], bits 0-7
        """
        if not (1 <= ttl_number <= 16):
            raise ValueError(f"TTL output {ttl_number} out of range (1-16)")
        
        # Store logical state
        self.ttl_outputs[ttl_number] = state
        
        # Calculate byte and bit position
        byte_index = 6 + (ttl_number - 1) // 8
        bit_position = (ttl_number - 1) % 8
        
        if state:
            # Set bit to 1
            self.data[byte_index] |= (1 << bit_position)
        else:
            # Clear bit to 0
            self.data[byte_index] &= ~(1 << bit_position)
    
    def get_ttl_output(self, ttl_number: int) -> bool:
        """
        Get TTL output state.
        
        Args:
            ttl_number: TTL output number (1-16)
        
        Returns:
            True if ON, False if OFF
        """
        if not (1 <= ttl_number <= 16):
            raise ValueError(f"TTL output {ttl_number} out of range (1-16)")
        
        return self.ttl_outputs.get(ttl_number, False)
    
    def set_ttl_outputs(self, ttl_list: List[int]) -> None:
        """
        Set multiple TTL outputs to ON, all others to OFF.
        
        Args:
            ttl_list: List of TTL output numbers (1-16) to set to ON
        """
        # Clear all TTL outputs
        self.ttl_outputs.clear()
        self.data[6] = 0
        self.data[7] = 0
        
        # Set specified outputs to ON
        for ttl in ttl_list:
            self.set_ttl_output(ttl, True)
    
    def set_matrix_dimensions(self, rows: int, columns: int) -> None:
        """
        Set matrix dimensions.
        
        Args:
            rows: Number of rows (0-8, 0 = no matrix, Dout works normally)
            columns: Number of columns (0-8, 0 = no matrix, Din works normally)
        
        Mapping:
            Byte 8: Row dimension (0-8)
            Byte 9: Column dimension (0-8)
        """
        if not (0 <= rows <= 8):
            raise ValueError(f"Matrix rows {rows} out of range (0-8)")
        
        if not (0 <= columns <= 8):
            raise ValueError(f"Matrix columns {columns} out of range (0-8)")
        
        # Store logical values
        self.matrix_row_dimension = rows
        self.matrix_column_dimension = columns
        
        # Store in data bytes
        self.data[8] = rows
        self.data[9] = columns
    
    def get_matrix_dimensions(self) -> tuple:
        """
        Get matrix dimensions.
        
        Returns:
            Tuple of (rows, columns)
        """
        return (self.matrix_row_dimension, self.matrix_column_dimension)
    
    def set_analog_output(self, ao_number: int, voltage: float) -> None:
        """
        Set analog output voltage.
        
        Args:
            ao_number: Analog output number (0-7)
            voltage: Voltage value (-13.5 to +13.5)
        
        Mapping (16-bit, 2's complement, little-endian):
            AO 0 -> data[12:14]  (bytes 12, 13)
            AO 1 -> data[14:16]  (bytes 14, 15)
            AO 2 -> data[16:18]  (bytes 16, 17)
            AO 3 -> data[18:20]  (bytes 18, 19)
            AO 4 -> data[20:22]  (bytes 20, 21)
            AO 5 -> data[22:24]  (bytes 22, 23)
            AO 6 -> data[24:26]  (bytes 24, 25)
            AO 7 -> data[26:28]  (bytes 26, 27)
        
        Resolution: 27V / 65536 = 0.000412V per bit
        """
        if not (0 <= ao_number <= 7):
            raise ValueError(f"Analog output {ao_number} out of range (0-7)")
        
        if not (-13.5 <= voltage <= 13.5):
            raise ValueError(f"Analog voltage {voltage} out of range (-13.5 to +13.5)")
        
        # Store logical value
        self.analog_outputs[ao_number] = voltage
        
        # Convert to 16-bit signed integer
        raw_value = int(voltage * 65536 / 27.0)
        raw_value = max(-32768, min(32767, raw_value))
        
        # Convert to unsigned (2's complement)
        if raw_value < 0:
            unsigned_value = (1 << 16) + raw_value
        else:
            unsigned_value = raw_value
        
        # Calculate byte position
        byte_index = 12 + ao_number * 2
        
        # Store in little-endian format
        self.data[byte_index] = unsigned_value & 0xFF  # Low byte
        self.data[byte_index + 1] = (unsigned_value >> 8) & 0xFF  # High byte
    
    def get_analog_output(self, ao_number: int) -> Optional[float]:
        """
        Get analog output voltage.
        
        Args:
            ao_number: Analog output number (0-7)
        
        Returns:
            Voltage value or None if not set
        """
        if not (0 <= ao_number <= 7):
            raise ValueError(f"Analog output {ao_number} out of range (0-7)")
        
        return self.analog_outputs.get(ao_number)
    
    def set_multiple_analog_outputs(self, analog_values: Dict[int, float]) -> None:
        """
        Set multiple analog outputs at once.
        
        Args:
            analog_values: Dictionary mapping AO number -> voltage
        
        Example:
            set_multiple_analog_outputs({0: 5.0, 1: -3.2, 7: 10.5})
        """
        for ao_number, voltage in analog_values.items():
            self.set_analog_output(ao_number, voltage)
    
    def clear_all(self) -> None:
        """Clear all data (reset to defaults)."""
        self.data = bytearray(32)
        self.data[0] = 0x55  # Restore header
        self.digital_outputs.clear()
        self.analog_outputs.clear()
        self.ttl_outputs.clear()
        self.matrix_row_dimension = 0
        self.matrix_column_dimension = 0
    
    def get_bytes(self) -> bytes:
        """
        Get the complete send data as bytes.
        
        Returns:
            32-byte data ready to send
        """
        return bytes(self.data)
    
    def to_dict(self) -> Dict:
        """
        Export logical parameters as dictionary.
        
        Returns:
            Dictionary with digital_outputs, analog_outputs, ttl_outputs, and matrix dimensions
        """
        return {
            "digital_outputs": self.digital_outputs.copy(),
            "analog_outputs": self.analog_outputs.copy(),
            "ttl_outputs": self.ttl_outputs.copy(),
            "matrix_dimensions": {
                "rows": self.matrix_row_dimension,
                "columns": self.matrix_column_dimension
            }
        }
    
    def __repr__(self) -> str:
        di_count = len([v for v in self.digital_outputs.values() if v])
        ai_count = len(self.analog_outputs)
        ttl_count = len([v for v in self.ttl_outputs.values() if v])
        matrix = f"{self.matrix_row_dimension}x{self.matrix_column_dimension}"
        return f"SendData(DO: {di_count} active, AO: {ai_count} set, TTL: {ttl_count} active, Matrix: {matrix})"


class ReceiveData:
    """
    Maps received data structure to logical parameters (64 bytes).
    
    RECEIVE DATA STRUCTURE (64 bytes):
    - Bytes 0-1: Header
    - Bytes 2-9: Digital Inputs (DI 1-64, bit-mapped)
    - Bytes 10-11: TTL/Status
    - Bytes 12-15: Matrix row
    - Bytes 16-47: Analog Inputs (AI 1-16, 16-bit each, little-endian)
    - Bytes 48-51: Matrix data
    - Bytes 52-59: Encoder
    - Bytes 60-63: Absolute encoder
    """
    
    def __init__(self, data: bytes = None):
        """
        Initialize receive data structure.
        
        Args:
            data: 64-byte received data (optional)
        """
        self.data = bytearray(64) if data is None else bytearray(data)
        
        # Parsed logical parameters
        self.header: int = 0
        self.digital_inputs: Dict[int, bool] = {}  # DI number -> state
        self.analog_inputs: Dict[int, float] = {}  # AI number -> voltage
        self.ttl_status: int = 0
        self.matrix_row: bytes = b''
        self.matrix_data: bytes = b''
        self.encoder: bytes = b''
        self.abs_encoder: bytes = b''
        
        # Parse data if provided
        if data is not None:
            self.parse()
    
    def update(self, data: bytes) -> None:
        """
        Update with new received data and parse.
        
        Args:
            data: 64-byte received data
        """
        if len(data) != 64:
            raise ValueError(f"Expected 64 bytes, got {len(data)}")
        
        self.data = bytearray(data)
        self.parse()
    
    def parse(self) -> None:
        """Parse raw data into logical parameters."""
        # Parse header (bytes 0-1)
        self.header = (self.data[1] << 8) | self.data[0]
        
        # Parse digital inputs (bytes 2-9, DI 1-64)
        self.digital_inputs.clear()
        for byte_idx in range(2, 10):  # Bytes 2-9
            byte_value = self.data[byte_idx]
            for bit_idx in range(8):
                di_number = (byte_idx - 2) * 8 + bit_idx + 1  # DI 1-64
                self.digital_inputs[di_number] = bool(byte_value & (1 << bit_idx))
        
        # Parse TTL/Status (bytes 10-11)
        self.ttl_status = (self.data[11] << 8) | self.data[10]
        
        # Parse matrix row (bytes 12-15)
        self.matrix_row = bytes(self.data[12:16])
        
        # Parse analog inputs (bytes 16-47, AI 1-16)
        self.analog_inputs.clear()
        for ai_idx in range(16):
            byte_idx = 16 + ai_idx * 2
            # Read little-endian 16-bit value
            low_byte = self.data[byte_idx]
            high_byte = self.data[byte_idx + 1]
            unsigned_value = (high_byte << 8) | low_byte
            
            # Convert from 2's complement to signed
            if unsigned_value >= 32768:
                signed_value = unsigned_value - 65536
            else:
                signed_value = unsigned_value
            
            # Convert to voltage (-13.5 to +13.5)
            voltage = signed_value * 27.0 / 65536
            self.analog_inputs[ai_idx + 1] = voltage
        
        # Parse matrix data (bytes 48-51)
        self.matrix_data = bytes(self.data[48:52])
        
        # Parse encoder (bytes 52-59)
        self.encoder = bytes(self.data[52:60])
        
        # Parse absolute encoder (bytes 60-63)
        self.abs_encoder = bytes(self.data[60:64])
    
    def get_digital_input(self, di_number: int) -> bool:
        """
        Get digital input state.
        
        Args:
            di_number: Digital input number (1-64)
        
        Returns:
            True if ON, False if OFF
        """
        if not (1 <= di_number <= 64):
            raise ValueError(f"Digital input {di_number} out of range (1-64)")
        
        return self.digital_inputs.get(di_number, False)
    
    def get_digital_inputs_active(self) -> List[int]:
        """
        Get list of active (ON) digital inputs.
        
        Returns:
            List of DI numbers that are ON
        """
        return [di_num for di_num, state in self.digital_inputs.items() if state]
    
    def get_analog_input(self, ai_number: int) -> Optional[float]:
        """
        Get analog input voltage.
        
        Args:
            ai_number: Analog input number (1-16)
        
        Returns:
            Voltage value or None if not available
        """
        if not (1 <= ai_number <= 16):
            raise ValueError(f"Analog input {ai_number} out of range (1-16)")
        
        return self.analog_inputs.get(ai_number)
    
    def to_dict(self) -> Dict:
        """
        Export all parsed data as dictionary.
        
        Returns:
            Dictionary with all parsed parameters
        """
        return {
            "header": self.header,
            "digital_inputs": self.digital_inputs.copy(),
            "digital_inputs_active": self.get_digital_inputs_active(),
            "analog_inputs": self.analog_inputs.copy(),
            "ttl_status": self.ttl_status,
            "matrix_row": self.matrix_row.hex(),
            "matrix_data": self.matrix_data.hex(),
            "encoder": self.encoder.hex(),
            "abs_encoder": self.abs_encoder.hex()
        }
    
    def __repr__(self) -> str:
        di_active = len(self.get_digital_inputs_active())
        ai_count = len(self.analog_inputs)
        return f"ReceiveData(Header: 0x{self.header:04X}, DI: {di_active}/64 active, AI: {ai_count} channels)"


# Demo/Test code
if __name__ == "__main__":
    """Test data mapper functionality."""
    print("=" * 60)
    print("UDP Data Mapper Test")
    print("=" * 60)
    
    # Test SendData
    print("\n--- SEND DATA TEST ---")
    send = SendData()
    
    # Set digital inputs
    send.set_digital_outputs([1, 5, 9, 17, 32])
    print(f"Set DO: 1, 5, 9, 17, 32")
    print(f"DO bytes: {send.data[2:6].hex()}")
    print(f"DO 1: {send.get_digital_output(1)}")
    print(f"DO 2: {send.get_digital_output(2)}")
    
    # Set analog outputs
    send.set_analog_output(0, 5.0)
    send.set_analog_output(1, -3.2)
    send.set_multiple_analog_outputs({2: 0.0, 7: 13.5})
    print(f"\nSet AO: 0=5.0V, 1=-3.2V, 2=0.0V, 7=13.5V")
    print(f"AO 0 bytes: {send.data[12:14].hex()}")
    print(f"AO 0 value: {send.get_analog_output(0)}V")
    
    # Set TTL outputs
    send.set_ttl_outputs([1, 5, 10, 16])
    print(f"\nSet TTL: 1, 5, 10, 16")
    print(f"TTL bytes: {send.data[6:8].hex()}")
    print(f"TTL 1: {send.get_ttl_output(1)}")
    print(f"TTL 2: {send.get_ttl_output(2)}")
    
    # Set matrix dimensions
    send.set_matrix_dimensions(4, 6)
    print(f"\nSet Matrix: 4 rows x 6 columns")
    print(f"Matrix bytes: {send.data[8:10].hex()}")
    print(f"Matrix dimensions: {send.get_matrix_dimensions()}")
    
    # Export
    print(f"\n{send}")
    print(f"Logical parameters: {send.to_dict()}")
    print(f"Send bytes (first 16): {send.get_bytes()[:16].hex()}")
    
    # # Test ReceiveData
    # print("\n--- RECEIVE DATA TEST ---")
    
    # # Create test receive data
    # test_data = bytearray(64)
    # test_data[0] = 0xAA  # Header low
    # test_data[1] = 0x55  # Header high
    # test_data[2] = 0b00010001  # DO 1 and 5 active
    # test_data[3] = 0b10000000  # DO 16 active
    
    # # Set analog output 1 to 5.0V (as example)
    # ao1_raw = int(5.0 * 65536 / 27.0)
    # test_data[16] = ao1_raw & 0xFF  # Low byte
    # test_data[17] = (ao1_raw >> 8) & 0xFF  # High byte
    
    # receive = ReceiveData(bytes(test_data))
    
    # print(f"{receive}")
    # print(f"Header: 0x{receive.header:04X}")
    # print(f"DI active: {receive.get_digital_inputs_active()}")
    # print(f"DI 1: {receive.get_digital_input(1)}")
    # print(f"DI 2: {receive.get_digital_input(2)}")
    # print(f"AI 1: {receive.get_analog_input(1):.3f}V")
    # print(f"TTL Status: 0x{receive.ttl_status:04X}")
    
    # # Update with new data
    # print("\n--- UPDATE TEST ---")
    # new_data = bytearray(64)
    # new_data[0] = 0xFF
    # new_data[2] = 0xFF  # All DI 1-8 active
    # receive.update(bytes(new_data))
    # print(f"Updated: {receive}")
    # print(f"DI active: {receive.get_digital_inputs_active()[:10]}... (showing first 10)")
    
    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)
