"""
Basic Test - Debug environment for testing basic hardware commands.
Run this script directly (not part of the main UI application).
Uses the application's abstraction layers for hardware control.
"""
import sys
from pathlib import Path
import time

# Add src to path to import hw_tester modules
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from hw_tester.utils.config_loader import load_settings, get_board_pin_map
from hw_tester.hardware.hardware_factory import initialize_hardware


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
    input("\n[Basic_Test] Press ENTER to continue to next step...")
    # Test 1: Set multiple digital pins using helper function
    print(f"\n[Basic_Test] pin 15 is up")
    set_digital_pins(hardware, digital_pin_map, {
        "D0": True,   # LOW
        "D1": True,  # LOW
        "D2": True,   # LOW
        "D3": True,  # LOW 
        "D8": True,   # HIGH

    })

    #print_digital_pin_status(hardware, digital_pin_map, ["D0", "D1", "D2", "D3", "D8"])
    measure_analog_pins(hardware, analog_pin_map, ["A0"])

    # Wait for user confirmation before proceeding
    input("\n[Basic_Test] change the value in the SE Press ENTER to continue to next step...")

     #print_digital_pin_status(hardware, digital_pin_map, ["D0", "D1", "D2", "D3", "D8"])
    measure_analog_pins(hardware, analog_pin_map, ["A0"])

    # Wait for user confirmation before proceeding
    input("\n[Basic_Test] Press ENTER to continue to next step...")
    
    print(f"\n[Basic_Test] pin 20 is up")
    set_digital_pins(hardware, digital_pin_map, {
        "D20": True,   # HIGh
    })
    
    #print_digital_pin_status(hardware, digital_pin_map, ["D0", "D1", "D2", "D3", "D9"])
    measure_analog_pins(hardware, analog_pin_map, ["A0"])

     # Wait for user confirmation before proceeding
    input("\n[Basic_Test] change the value in the SE Press ENTER to continue to next step...")

     #print_digital_pin_status(hardware, digital_pin_map, ["D0", "D1", "D2", "D3", "D8"])
    measure_analog_pins(hardware, analog_pin_map, ["A0"])

    # Wait for user confirmation before proceeding
    input("\n[Basic_Test] Press ENTER to continue...")
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
    hardware.close()
    print("[Basic_Test] Hardware closed")


if __name__ == "__main__":
    main()
