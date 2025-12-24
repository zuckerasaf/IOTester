"""
Basic Test - Debug environment for testing basic hardware commands.
Run this script directly (not part of the main UI application).
Uses the application's abstraction layers for hardware control.
"""
import sys
from pathlib import Path
import time

from hw_tester.hardware.controllino_io import connector_pin_to_bits
from hw_tester.utils.general import clear_mux_bits, set_mux_bits

# Add src to path to import hw_tester modules
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from hw_tester.ui.views import log_view
from hw_tester.utils.config_loader import load_settings, get_board_pin_map
from hw_tester.hardware.hardware_factory import initialize_hardware
from hw_tester.core.udp_card_manager import UDPCardManager

def set_digital_pins(hardware, pin_map: dict, pin_states: dict):
    """
    Set multiple digital pins to specified states.
    
    Args:
        hardware: Hardware I/O object
        pin_map: Digital pin mapping dictionary (D pins)
        pin_states: Dictionary of logical pin -> state (True/False or 1/0)
                   Example: {"D1": True, "D2": False, "D5": 1, "D10": 0}
    
    Example:
        set_digital_pins(hardware, digital_pin_map, {
            "D1": True,
            "D2": False,
            "D5": True,
            "D10": False
        })
    """
    for logical_pin, state in pin_states.items():
        physical_pin = pin_map.get(logical_pin)
        if physical_pin is None:
            print(f"[WARNING] Pin {logical_pin} not found in pin map, skipping...")
            continue
        
        state_bool = bool(state)
        state_str = "HIGH" if state_bool else "LOW"
        print(f"[set_digital_pins] Setting {logical_pin} (pin {physical_pin}) -> {state_str}")
        hardware.digital_write(physical_pin, state_bool)


def measure_analog_pins(hardware, pin_map: dict, analog_pins: list) -> dict:
    """
    Measure voltage on multiple analog pins.
    
    Args:
        hardware: Hardware I/O object
        pin_map: Analog pin mapping dictionary (A pins)
        analog_pins: List of logical pin names to measure
                    Example: ["A0", "A1", "A5", "A10"]
    
    Returns:
        Dictionary of logical pin -> voltage reading
        Example: {"A0": 3.25, "A1": 0.0, "A5": 5.0, "A10": 2.47}
    
    Example:
        voltages = measure_analog_pins(hardware, analog_pin_map, ["A0", "A1", "A5"])
        print(f"A0 voltage: {voltages['A0']}V")
    """
    results = {}
    
    for logical_pin in analog_pins:
        physical_pin = pin_map.get(logical_pin)
        if physical_pin is None:
            print(f"[WARNING] Pin {logical_pin} not found in pin map, skipping...")
            continue
        
        print(f"[measure_analog_pins] Reading {logical_pin} (pin {physical_pin})...")
        voltage = hardware.analog_read(physical_pin)
        results[logical_pin] = voltage
        print(f"[measure_analog_pins] {logical_pin} -> {voltage}V")
    
    return results


def print_digital_pin_status(hardware, pin_map: dict, pins: list):
    """
    Read and print the current status of digital pins.
    
    Args:
        hardware: Hardware I/O object
        pin_map: Digital pin mapping dictionary (D pins)
        pins: List of logical pin names to read
              Example: ["D0", "D1", "D2", "D8"]
    
    Example:
        print_digital_pin_status(hardware, digital_pin_map, ["D0", "D1", "D8"])
    """
    print("[print_digital_pin_status] Current digital pin states:")
    for logical_pin in pins:
        physical_pin = pin_map.get(logical_pin)
        if physical_pin is None:
            print(f"[WARNING] Pin {logical_pin} not found in pin map, skipping...")
            continue
        
        state = hardware.digital_read(physical_pin)
        state_str = "HIGH" if state else "LOW"
        print(f"[print_digital_pin_status] {logical_pin} (pin {physical_pin}) -> {state_str}")


def main():
    """Main test function"""
    print("[Basic_Test] Starting basic hardware test...")
    
    # Load settings
    settings = load_settings()
    print(f"[Basic_Test] Board Type: {settings['Board']['Type']}")
    print(f"[Basic_Test] Port: {settings['Board']['Port']}")
    print(f"[Basic_Test] BaudRate: {settings['Board']['BaudRate']}")
    
    # Load pin map for the configured board
    board_pin_map = get_board_pin_map(settings)
    digital_pin_map = board_pin_map.get('D', {})
    analog_pin_map = board_pin_map.get('A', {})
    relay_pin_map = board_pin_map.get('R', {})
    
    # Initialize hardware
    print("[Basic_Test] Initializing hardware...")
    hardware = initialize_hardware(settings)
    
    if hardware is None:
        print("[Basic_Test ERROR] Failed to initialize hardware (board type is 'none')")
        return
    
    print("[Basic_Test] Hardware initialized successfully")

    # Initialize UDP card manager
    print("[Basic_Test] Initializing UDP card manager...")
    card_manager = UDPCardManager(create_all=False)  # Only create enabled cards
    card_manager.start_all()
    time.sleep(0.5)  # Give threads time to initialize

    
    # Check which cards are enabled
    enabled_cards = card_manager.get_enabled_cards()
    print(f"[Basic_Test] Enabled cards: {[card.card_id for card in enabled_cards]}")
    
    # Check if card 2 exists
    card_2 = card_manager.get_card(2)
    if card_2:
        print(f"[Basic_Test] Card 2 found - Send to: {card_2.send_ip}:{card_2.send_port}, Receive from: {card_2.receive_ip}:{card_2.receive_port}, Enabled: {card_2.enabled}")
    else:
        print("[Basic_Test] WARNING: Card 2 not found in card manager!")
    
    print("[Basic_Test] UDP card manager initialized successfully")
    
    # Give cards a moment to initialize communication
    print("[Basic_Test] Waiting for card communication to initialize...")
    time.sleep(0.5)

    clear_mux_bits(board_pin_map, hardware)
    #input("\n[Basic_Test] Press ENTER to continue to next step...")
    pin_number = 17
    pullup_pin_number = "D21"
    mesure_pin_number = "A1"
    # Step 2: Convert connector pin to bit representation using system A and set mux matrix
    bits = connector_pin_to_bits(pin_number, "a")
    success = set_mux_bits(bits, pin_number, board_pin_map, hardware, settings)
    print(f"\n[Basic_Test] pin {pin_number} is up")

    #state = hardware.digital_read(digital_pin_map.get(pullup_pin_number))
    set_digital_pins(hardware, digital_pin_map, {
        pullup_pin_number: True,})  # HIG
    #state = hardware.digital_read(digital_pin_map.get(pullup_pin_number))
    
    print(f"\n[Basic_Test] pin {pin_number} is up")
    measure_analog_pins(hardware, analog_pin_map, [mesure_pin_number])

    print("\n[Basic_Test] Sending UDP commands to card 2...")
    success = card_manager.set_digital_output(card_id=2, do_number=13, state=bool(1))
    print(f"[Basic_Test] Card 2 DO13 set to 1: {'Success' if success else 'FAILED'}")
    
    success2 = card_manager.set_analog_output(card_id=2, ao_number=1, voltage=10)
    print(f"[Basic_Test] Card 2 AO1 set to 10V: {'Success' if success2 else 'FAILED'}")
    
    # Wait for outputs to stabilize
    print("[Basic_Test] Waiting for outputs to stabilize...")
    time.sleep(0.2)

    measure_analog_pins(hardware, analog_pin_map, [mesure_pin_number])

    # Step 2: Convert connector pin to bit representation using system A and set mux matrix
    bits = connector_pin_to_bits(pin_number, "b")
    success = set_mux_bits(bits, pin_number, board_pin_map, hardware, settings)
    print(f"\n[Basic_Test] pin {pin_number} is up")
    # set_digital_pins(hardware, digital_pin_map, {
    #     pullup_pin_number: True,})  # HIG
    # print(f"\n[Basic_Test] pin {pin_number} is up")
    measure_analog_pins(hardware, analog_pin_map, [mesure_pin_number])

   
    set_digital_pins(hardware, relay_pin_map, {
        "R6": True,})  # HIG
    set_digital_pins(hardware, relay_pin_map, {
        "R7": True,})  # HIG
    
    mesure_pin_number = "A3"
    measure_analog_pins(hardware, analog_pin_map, [mesure_pin_number])

    mesure_pin_number = "A7"
    measure_analog_pins(hardware, analog_pin_map, [mesure_pin_number])


    # Wait for user confirmation before proceeding
    #input("\n[Basic_Test] Press ENTER to continue...")
    print(f"\n[Basic_Test] pin 20 is up")
    set_digital_pins(hardware, digital_pin_map, {
        "D20": False,   # HIGh
    })
    # print(f"\n[Basic_Test]   set relay pin to high")
    # set_digital_pins(hardware, relay_pin_map, {
    #     "R0": True,   # HIGH
    # })

    # # Wait for user confirmation before proceeding
    # input("\n[Basic_Test] set relay pin to high")
    # set_digital_pins(hardware, relay_pin_map, {
    #     "R0": False,   # LOW
    # })


    if(False):
        # Test 2: Original single pin pulse test
        digital_logical_pin = "D1"
        digital_physical_pin = digital_pin_map.get(digital_logical_pin, 1)
        wait_time = 7.0  # 7000ms
        
        print(f"\n[Basic_Test] Test 2: Digital Pin Pulse")
        print(f"[Basic_Test] Pin mapping: {digital_logical_pin} -> physical pin {digital_physical_pin}")
        print(f"[Basic_Test] Setting {digital_logical_pin} (pin {digital_physical_pin}) HIGH...")
        hardware.digital_write(digital_physical_pin, True)
        
        print(f"[Basic_Test] Waiting {wait_time*1000}ms...")
        time.sleep(wait_time)
        
        print(f"[Basic_Test] Setting {digital_logical_pin} (pin {digital_physical_pin}) LOW...")
        hardware.digital_write(digital_physical_pin, False)
    
    # # Test 2: Read analog voltage
    # analog_logical_pin = "A0"
    # analog_physical_pin = analog_pin_map.get(analog_logical_pin, 0)
    
    # print(f"\n[Basic_Test] Test 2: Analog Voltage Reading")
    # print(f"[Basic_Test] Pin mapping: {analog_logical_pin} -> physical pin {analog_physical_pin}")
    # print(f"[Basic_Test] Reading voltage from {analog_logical_pin} (pin {analog_physical_pin})...")
    # voltage = hardware.analog_read(analog_physical_pin)
    # print(f"[Basic_Test] Voltage: {voltage}V")
    
    # print("[Basic_Test] Test complete")
    
    # Cleanup
    card_manager.stop_all()
    print("[Basic_Test] UDP card manager stopped")
    hardware.close()
    print("[Basic_Test] Hardware closed")


if __name__ == "__main__":
    main()
