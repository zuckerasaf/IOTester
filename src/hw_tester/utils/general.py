"""
General utility functions for HW Tester application.
"""
import re
import time
from typing import Tuple, Optional, Dict, Callable, Any


def parse_event_string(event_str: str) -> Tuple[Optional[int], Optional[str], Optional[int], Optional[int]]:
    """
    Parse event string format and extract components.
    
    Expected format: C{Card}_{EventType}{EventNum}V{EventValue}
    Example: "C2_AO2V10" -> Card=2, EventType="AO", EventNum=2, EventValue=10
    
    Args:
        event_str: Event string to parse (e.g., "C2_AO2V10")
        
    Returns:
        Tuple of (Card, EventType, EventNum, EventValue)
        Returns (None, None, None, None) if parsing fails
        
    Examples:
        >>> parse_event_string("C2_AO2V10")
        (2, 'AO', 2, 10)
        
        >>> parse_event_string("C1_DI5V1")
        (1, 'DI', 5, 1)
        
        >>> parse_event_string("C3_DO12V0")
        (3, 'DO', 12, 0)
    """
    try:
        # Pattern: C{digit(s)}_{letters}{digit(s)}V{digit(s)}
        # Example: C2_AO2V10
        pattern = r'^C(\d+)_([A-Z]+)(\d+)V(\d+)$'
        
        match = re.match(pattern, event_str.strip())
        
        if not match:
            return (None, None, None, None)
        
        card = int(match.group(1))
        event_type = match.group(2)
        event_num = int(match.group(3))
        event_value = int(match.group(4))
        
        return (card, event_type, event_num, event_value)
        
    except Exception as e:
        # If any error occurs during parsing, return None values
        return (None, None, None, None)


def parse_logic_input_string(logic_input: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Parse logic input string format and extract components.
    
    Expected format: C{Card}_DI{DINum}_{ConnectPin}
    Example: "C4_DI29_3" -> Card=4, DINum=29, ConnectPin=3
    
    Args:
        logic_input: Logic input string to parse (e.g., "C4_DI29_3")
        
    Returns:
        Tuple of (Card, DINumber, ConnectPinNumber)
        Returns (None, None, None) if parsing fails
        
    Examples:
        >>> parse_logic_input_string("C4_DI29_3")
        (4, 29, 3)
        
        >>> parse_logic_input_string("C1_DI5_12")
        (1, 5, 12)
        
        >>> parse_logic_input_string("C2_DI15_25")
        (2, 15, 25)
    """
    try:
        # Pattern: C{digit(s)}_DI{digit(s)}_{digit(s)}
        # Example: C4_DI29_3
        pattern = r'^C(\d+)_DI(\d+)_(\d+)$'
        
        match = re.match(pattern, logic_input.strip())
        
        if not match:
            return (None, None, None)
        
        card = int(match.group(1))
        di_number = int(match.group(2))
        connect_pin = int(match.group(3))
        
        return (card, di_number, connect_pin)
        
    except Exception as e:
        # If any error occurs during parsing, return None values
        return (None, None, None)


def get_pin_pair_info_controlino(pin_number: int) -> Tuple[int, str, str, str, str, str, str, str]:
    """
    Determine the pair number and associated pins based on connector pin number.
    
    Pin ranges:
    - Pins 1-16: Pair 1, Card 1_A and Card 1_B
    - Pins 17-32: Pair 2, Card 2_A and Card 2_B
    - Pins 33-48: Pair 3, Card 3_A and Card 3_B
    - Pins 49+: Pair 4, Card 4_A and Card 4_B
    
    Args:
        pin_number: Connector pin number (e.g., 5, 25, 40)
        
    Returns:
        Tuple of (pair_num, voltage_measure_pin, pullup_pin, card_enable_A, card_enable_B)
        
    Examples:
        >>> get_pin_pair_info_controlino(5)
        (1, 'voltage_measure_pin_pair1', 'pullup_pins_pin_pair1', 'enable_card_1_A_pin', 'enable_card_1_B_pin', 'enable_Relay_pin_1_A', 'enable_Relay_pin_1_B')
        
        >>> get_pin_pair_info_controlino(25)
        (2, 'voltage_measure_pin_pair2', 'pullup_pins_pin_pair2', 'enable_card_2_A_pin', 'enable_card_2_B_pin', 'enable_Relay_pin_2_A', 'enable_Relay_pin_2_B')
        
        >>> get_pin_pair_info_controlino(40)
        (3, 'voltage_measure_pin_pair3', 'pullup_pins_pin_pair3', 'enable_card_3_A_pin', 'enable_card_3_B_pin', 'enable_Relay_pin_3_A', 'enable_Relay_pin_3_B')
        
        >>> get_pin_pair_info_controlino(50)
        (4, 'voltage_measure_pin_pair4', 'pullup_pins_pin_pair4', 'enable_card_4_A_pin', 'enable_card_4_B_pin', 'enable_Relay_pin_4_A', 'enable_Relay_pin_4_B')
    """
    if 1 <= pin_number <= 16:
        return (1, "voltage_measure_pin_pair1","voltage_measure_pin_pair1_B", "pullup_pins_pin_pair1", "enable_card_1_A_pin", "enable_card_1_B_pin", "enable_Relay_pin_1_A", "enable_Relay_pin_1_B")
    elif 17 <= pin_number <= 32:
        return (2, "voltage_measure_pin_pair2","voltage_measure_pin_pair2_B", "pullup_pins_pin_pair2", "enable_card_2_A_pin", "enable_card_2_B_pin", "enable_Relay_pin_2_A", "enable_Relay_pin_2_B")
    elif 33 <= pin_number <= 48:
        return (3, "voltage_measure_pin_pair3","voltage_measure_pin_pair3_B", "pullup_pins_pin_pair3", "enable_card_3_A_pin", "enable_card_3_B_pin", "enable_Relay_pin_3_A", "enable_Relay_pin_3_B")
    else:
        return (4, "voltage_measure_pin_pair4","voltage_measure_pin_pair4_B", "pullup_pins_pin_pair4", "enable_card_4_A_pin", "enable_card_4_B_pin", "enable_Relay_pin_4_A", "enable_Relay_pin_4_B")


def enable_cards(
    cards_to_enable: list[str],
    board_config: Dict,
    pin_map: Dict,
    hardware: Any,
    log_callback: Optional[Callable] = None
) -> None:
    """
    Enable specific card pins and disable all others.
    
    Args:
        cards_to_enable: List of card pin keys to enable (e.g., ['enable_card_1_A_pin', 'enable_card_1_B_pin'])
        board_config: Board configuration dictionary
        pin_map: Pin mapping dictionary
        hardware: Hardware interface object
        log_callback: Optional logging function(message, level)
        
    Example:
        >>> enable_cards(['enable_card_1_A_pin'], board_config, pin_map, hardware)
        # Enables card 1_A, disables all other cards
    """
    def log(message: str, level: str = "INFO"):
        """Helper to log messages if callback provided."""
        if log_callback:
            log_callback(message, level)
    
    # All possible card enable pins
    all_card_pins = [
        "enable_card_1_A_pin", "enable_card_1_B_pin",
        "enable_card_2_A_pin", "enable_card_2_B_pin",
        "enable_card_3_A_pin", "enable_card_3_B_pin",
        "enable_card_4_A_pin", "enable_card_4_B_pin"
    ]
    
    # Get digital ports from pin map
    digital_ports = pin_map.get('D', {})
    
    # Enable/disable card pins
    for card_pin_key in all_card_pins:
        card_pin_name = board_config.get(card_pin_key)
        if card_pin_name:
            card_physical_pin = digital_ports.get(card_pin_name)
            if card_physical_pin is not None:
                # Set HIGH only for the cards in cards_to_enable, LOW for all others
                state = (card_pin_key in cards_to_enable)
                hardware.digital_write(card_physical_pin, state)
                if state:
                    log(f"Enabling card pin {card_pin_name} (pin {card_physical_pin}) HIGH", "DEBUG")
                else:
                    log(f"Disabling card pin {card_pin_name} (pin {card_physical_pin}) LOW", "DEBUG")


def clear_mux_bits(
    pin_map: Dict,
    hardware: Any,
    log_callback: Optional[Callable] = None
) -> bool:
    """
    Clear all mux matrix bits by setting D0-D15 to LOW.
    Should be called before setting a new bit pattern.
    
    Args:
        pin_map: Pin mapping dictionary
        hardware: Hardware interface object
        log_callback: Optional logging function(message, level)
        
    Returns:
        True if successful, False otherwise
    """
    def log(message: str, level: str = "INFO"):
        """Helper to log messages if callback provided."""
        if log_callback:
            log_callback(message, level)
    
    try:
        # Get digital ports from pin map
        digital_ports = pin_map.get('D', {})
        
        if not digital_ports:
            log("No digital ports found in pin map", "ERROR")
            return False
        
        # Set all D0-D15 pins to LOW
        for bit_idx in range(16):
            digital_pin_name = f"D{bit_idx}"
            if digital_pin_name in digital_ports:
                physical_pin = digital_ports.get(digital_pin_name)
                if physical_pin is not None:
                    hardware.digital_write(physical_pin, False)
        
        log("All mux bits (D0-D15) cleared to LOW", "DEBUG")
        return True
        
    except Exception as e:
        log(f"Error clearing mux bits: {str(e)}", "ERROR")
        return False


def clear_analog_bits(
    pin_map: Dict,
    hardware: Any,
    log_callback: Optional[Callable] = None
) -> bool:
    """
    Clear all Analog bits by setting A0-A7 to LOW.
    Should be called before setting a new bit pattern.
    
    Args:
        pin_map: Pin mapping dictionary
        hardware: Hardware interface object
        log_callback: Optional logging function(message, level)
        
    Returns:
        True if successful, False otherwise
    """
    def log(message: str, level: str = "INFO"):
        """Helper to log messages if callback provided."""
        if log_callback:
            log_callback(message, level)
    
    try:
        # Get analog ports from pin map
        analog_ports = pin_map.get('A', {})
        
        if not analog_ports:
            log("No analog ports found in pin map", "ERROR")
            return False
        
        # Set all A0-A7 pins to LOW
        for bit_idx in range(8):
            analog_pin_name = f"A{bit_idx}"
            if analog_pin_name in analog_ports:
                physical_pin = analog_ports.get(analog_pin_name)
                if physical_pin is not None:
                    hardware.digital_write(physical_pin, False)
        
        log("All analog bits (A0-A7) cleared to LOW", "DEBUG")
        return True
        
    except Exception as e:
        log(f"Error clearing analog bits: {str(e)}", "ERROR")
        return False


def set_mux_bits(
    bits: list,
    pin_number: int,
    pin_map: Dict,
    hardware: Any,
    settings: Dict,
    log_callback: Optional[Callable] = None
) -> bool:
    """
    Set digital pins D0-D15 based on bit pattern for mux matrix routing.
    
    Args:
        bits: List of 16 integers (0 or 1) representing the bit pattern for D0-D15
        pin_number: Connector pin number (for logging purposes)
        pin_map: Pin mapping dictionary
        hardware: Hardware interface object
        settings: Settings dictionary (for stabilization delay)
        log_callback: Optional logging function(message, level)
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> bits = [1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        >>> set_mux_bits(bits, 5, pin_map, hardware, settings)
        True
    """
    def log(message: str, level: str = "INFO"):
        """Helper to log messages if callback provided."""
        if log_callback:
            log_callback(message, level)
    
    try:
        # Get digital ports from pin map
        digital_ports = pin_map.get('D', {})
        
        if not digital_ports:
            log("No digital ports found in pin map", "ERROR")
            return False
        
        # Build pin states dictionary (D0-D15)
        pin_states = {}
        for bit_idx, bit_value in enumerate(bits):
            digital_pin_name = f"D{bit_idx}"
            if digital_pin_name in digital_ports:
                pin_states[digital_pin_name] = bool(bit_value)
        
        if not pin_states:
            log("No valid digital pins found for bit pattern", "WARNING")
            return False
        
        # Log which pins will be set HIGH
        # high_pins = [name for name, state in pin_states.items() if state]
        # if high_pins:
        #     log(f"Setting HIGH pins for connector pin {pin_number}: {', '.join(high_pins)}", "INFO")
        # else:
        #     log(f"All mux bits LOW for connector pin {pin_number}", "DEBUG")
        
        # Apply the digital pin states
        for logical_pin, state in pin_states.items():
            physical_pin = digital_ports.get(logical_pin)
            if physical_pin is not None:
                if state == True: # only write HIGH pins to reduce I/O operations and to enable working with 2 pin in paralle 
                    hardware.digital_write(physical_pin, state)
        
        # Small delay to allow pins to stabilize
        stabilize_delay = settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
        time.sleep(stabilize_delay)
        
        log(f"Mux bits set successfully for pin {pin_number}", "DEBUG")
        return True
        
    except Exception as e:
        log(f"Error setting mux bits: {str(e)}", "ERROR")
        return False


def setup_pin_hardware_for_test(
    pin_id: str,
    board_config: Dict,
    pin_map: Dict,
    hardware: Any,
    settings: Dict,
    test_type: str,
    log_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Configure hardware for testing a specific pin.
    
    This function handles:
    - Getting pair info and pin mappings
    - Enabling correct card pins based on test type
    - Setting up mux matrix (bit pattern)
    - Waiting for stabilization
    
    Args:
        pin_id: Pin ID (e.g., "J1-05")
        board_config: Board configuration dictionary
        pin_map: Pin mapping dictionary
        hardware: Hardware interface object
        settings: Settings dictionary
        test_type: Type of test ('power', 'pullup', 'logic')
        log_callback: Optional logging function(message, level)
        
    Returns:
        Dictionary with:
            - voltage_pin_name: Voltage measurement pin name
            - pullup_pin_name: Pullup pin name
            - pair_num: Pair number
            - card_enable_a: Card A enable pin key
            - card_enable_b: Card B enable pin key
            
    Test type card enabling:
        - 'power': Enable both card A and B
        - 'pullup': Enable both card A and B (pullup needs full circuit)
        - 'logic': Enable both card A and B (logic test needs full circuit)
    """
    from hw_tester.hardware.controllino_io import connector_pin_to_bits
    
    def log(message: str, level: str = "INFO"):
        """Helper to log messages if callback provided."""
        if log_callback:
            log_callback(message, level)
    
    # Step 4: Get pair number and associated pins
    pin_number = int(''.join(filter(str.isdigit, pin_id)))
    pair_num, voltage_pin_key, voltage_pin_b_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(pin_number)
    
    # Get actual pin names from board config
    voltage_pin_name = board_config.get(voltage_pin_key, 'A0')
    pullup_pin_name = board_config.get(pullup_pin_key, 'D20')
    
    log(f"Pin {pin_id} belongs to Pair {pair_num}, Cards: {card_enable_a_key}, {card_enable_b_key}", "INFO")
    
    # Step 5: Determine which cards to enable based on test type
    if test_type == 'power':
        active_cards = [card_enable_a_key]
    elif test_type == 'pullup':
        active_cards = [card_enable_a_key]
    elif test_type == 'logic':
        active_cards = [card_enable_a_key, card_enable_b_key]
    else:
        active_cards = [card_enable_a_key, card_enable_b_key]  # Default: enable both
    
    # Enable specified cards and disable all others
    enable_cards(active_cards, board_config, pin_map, hardware, log_callback)
    
    # Step 6: Small delay to allow pins to stabilize
    stabilize_delay = settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
    time.sleep(stabilize_delay)
    
    # Return configuration info
    return {
        'voltage_pin_name': voltage_pin_name,
        'pullup_pin_name': pullup_pin_name,
        'pair_num': pair_num,
        'card_enable_a': card_enable_a_key,
        'card_enable_b': card_enable_b_key
    }


if __name__ == "__main__":
    # Test cases for parse_event_string
    test_cases = [
        "C2_AO2V10",
        "C1_DI5V1",
        "C3_DO12V0",
        "C4_AI3V255",
        "invalid_format",
        "C2_AO2",
        ""
    ]
    
    print("Testing parse_event_string():")
    print("-" * 60)
    for test in test_cases:
        card, event_type, event_num, event_value = parse_event_string(test)
        print(f"Input: '{test}'")
        print(f"  Card={card}, EventType={event_type}, EventNum={event_num}, EventValue={event_value}")
        print()
    
    # Test cases for get_pin_pair_info_controlino
    print("\nTesting get_pin_pair_info_controlino():")
    print("-" * 60)
    pin_tests = [1, 5, 16, 17, 25, 32, 33, 40, 48, 49, 50, 64]
    for pin_num in pin_tests:
        pair_num, voltage_pin, voltage_pin_b, pullup_pin, card_a, card_b, relay_a, relay_b = get_pin_pair_info_controlino(pin_num)
        print(f"Pin {pin_num:2d}: Pair {pair_num}, Voltage: {voltage_pin}, Voltage_B: {voltage_pin_b}, Pullup: {pullup_pin}")
        print(f"         Cards: {card_a}, {card_b}")
        print(f"         Relays: {relay_a}, {relay_b}")
    print()
