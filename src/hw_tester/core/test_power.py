import time
import random
from typing import TYPE_CHECKING

from hw_tester.hardware.controllino_io import connector_pin_to_bits
from hw_tester.utils.general import (
    parse_event_string,
    get_debug_setting,
    get_pin_pair_info_controlino,
    set_mux_bits,
    verify_card_output,
)

if TYPE_CHECKING:
    from hw_tester.hardware.pin import Pin


def power_test(test_handle, pin: "Pin") -> tuple[float, bool, str]:
    """
    Run power test on a pin.
    
    Test Procedure:
    1. Get pair info (voltage_measure_pin, card enables, etc.) for connector pin
    2. Convert connector pin number to bit pattern and set mux matrix (D0-D15)
    3. Measure initial voltage on pair-specific analog pin
    4. If Power_Input == "none" or empty:
       - Compare initial measurement to Power_Expected
       - Return result (pass/fail based on voltage tolerance)
    5. If Power_Input is specified (e.g., "C2_AO2V10"):
       - Verify initial measurement is ~0V (within tolerance)
       - Parse Power_Input string to get card, event type (AO/DO), number, and value
       - Activate card output (set AO voltage or DO state)
       - Wait for signal stabilization
       - Measure voltage again
       - Deactivate card output (set to 0V or False)
       - Compare measurement to Power_Expected
       - Return result (pass/fail based on voltage tolerance)
    
    Args:
        pin: Pin object containing test parameters (Id, Power_Expected, Power_Input, etc.)
        
    Returns:
        Tuple of (measured_voltage, success, message):
            - measured_voltage: Final voltage reading in volts
            - success: True if measurement within tolerance, False otherwise
            - message: Descriptive message about test result or error
    """

    self = test_handle

    is_simulation = self.settings.get('Board', {}).get('simulation', True)
    

    if is_simulation:
        # Simulation mode - return fixed value based on expected
        time.sleep(0.2)  # Simulate measurement delay
        variation = random.uniform(-0.1, 0.1)

    # Real hardware mode
    # Get tolerance from settings (default 0.5V)
    tolerance = self.settings.get('scale', {}).get('voltage_tolerance', 0.5)

    # Get pair number and associated pins
    pin_number = int(''.join(filter(str.isdigit, pin.Id)))
    pair_num, voltage_pin_key, voltage_pin_b_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(pin_number)

    # Get actual pin names from board config
    voltage_pin_name = self.board_config.get(voltage_pin_key, 'A0')

       
    # Convert connector pin to bit representation and set mux matrix
    bits = connector_pin_to_bits(pin_number, "a")
    success = set_mux_bits(bits, pin_number, self.pin_map, self.hardware, self.settings, self.log)
        
    if get_debug_setting(self.settings, "Power_Test"):
        self.log(f"start Power test for pin {pin_number}", "INFO")
        self.wait_debug(100, "active")


    if not success:
        self.log(f"in Power test -Failed to set mux bits for pin {pin_number}", "ERROR")
        return (0.0, False, "Error: Failed to set mux matrix")
        
    # Get physical analog port from pin map
    analog_ports = self.pin_map.get('A', {})
    analog_port = analog_ports.get(voltage_pin_name)
        
    if analog_port is None:
        self.log(f"in Power test - Analog pin {voltage_pin_name} not found in pin map", "ERROR")
        return (0.0, False, "Error: Analog pin not found in pin map")
        
    # Apply voltage scaling factor from settings
    voltage_scale = 1
    
    # Step 1: Measure initial voltage
    self.log(f"Measuring voltage on {voltage_pin_name} (pin {analog_port})", "DEBUG")
    try:
        measured_voltage = self.measurer.measure_voltage(analog_port) * voltage_scale
        if is_simulation:
            measured_voltage = 0 + variation
            self.log(f"the measure_Voltage is simulated {pin.Power_Expected + variation} + samll variation = {variation} ", "DEBUG")

        self.log(f"Initial measurement: {measured_voltage:.3f}V for pin {pin_number}", "INFO")
        if get_debug_setting(self.settings, "Power_Test"):
            self.wait_debug(121, "active")

    except Exception as e:
        self.log(f"in Power test - Measurement error: {str(e)}", "ERROR")
        return (0.0, False, f"Error: Measurement failed - {str(e)}")
        
    # Step 2: Check if Power_Input is "none" or empty or Power - if so, just verify measurement against expected value

    if not pin.Power_Input or pin.Power_Input.strip().lower() == "none" or pin.Power_Input.strip() == "P" or pin.Power_Input.strip() == "p" or pin.Power_Input.strip() == "Power":
        if is_simulation:
            measured_voltage = pin.Power_Expected + variation
            self.log(f"the measure_Voltage is simulated (pin.Power_Expected + variation) + samll variation = {variation} ", "DEBUG")

        # No external control needed - just verify measurement
        voltage_diff = abs(measured_voltage* voltage_scale - pin.Power_Expected)
        if voltage_diff <= tolerance:
            self.log(f"Measurement {measured_voltage* voltage_scale:.3f}V is within tolerance of {pin.Power_Expected:.3f}V", "SUCCESS")
            return (measured_voltage* voltage_scale, True, "Measurement is in tolerance")
        else:
            self.log(f"Measurement {measured_voltage* voltage_scale:.3f}V is NOT within tolerance of {pin.Power_Expected:.3f}V (diff: {voltage_diff:.3f}V)", "WARNING")
            return (measured_voltage* voltage_scale, False, f"Measurement not in tolerance (diff: {voltage_diff:.3f}V)")
        
    # Step 3: Power_Input is provided - need to activate external card
    # First verify initial measurement is ~0V


            
    if abs(measured_voltage* voltage_scale) > tolerance:
        self.log(f"Initial voltage {measured_voltage* voltage_scale:.3f}V is not ~0V (tolerance: {tolerance}V) - test failed", "WARNING")

        return (measured_voltage* voltage_scale, False, f"Initial voltage {measured_voltage:.3f}V is not ~0V")
        
    self.log(f"Initial voltage {measured_voltage* voltage_scale:.3f}V is ~0V - proceeding to activate card", "DEBUG")
        
    # Parse Power_Input and activate card
    card, event_type, event_num, event_value = parse_event_string(pin.Power_Input)
    if card is None or event_type is None:
        self.log(f"in Power test - Failed to parse Power_Input: {pin.Power_Input}", "ERROR")
        return (measured_voltage, False, f"Failed to parse Power_Input or not needed: {pin.Power_Input}")
        
    # Set analog or digital output
    if event_type == "AO":
        success = self.card_manager.set_analog_output(card_id=card, ao_number=event_num, voltage=event_value)
        self.log(f"active: Set Card {card} AO{event_num} to {event_value}V: {'Success' if success else 'Failed'}", "INFO")
    elif event_type == "DO":
        success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=bool(event_value))
        self.log(f"active: Set Card {card} DO{event_num} to {event_value}: {'Success' if success else 'Failed'}", "INFO")
    else:
        self.log(f"in Power test - Unknown event type: {event_type}", "ERROR")
        return (measured_voltage, False, f"Unknown event type: {event_type}")

    if get_debug_setting(self.settings, "Power_Test"):
        self.wait_debug(130, "active")


    if not success:
        self.log(f"in Power test - Failed to activate card {card}", "ERROR")
        return (measured_voltage, False, f"Failed to activate card {card}")
        
    # Wait for signal to stabilize
    stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
    time.sleep(stabilize_delay)
    # Verify the output was set correctly
    verify_success, verify_msg = verify_card_output(
        self.card_manager, card, event_type, event_num, event_value, 
        tolerance, self.log
    )

    if not verify_success:
        self.log(f"in Power test - Card output verification failed: {verify_msg} ", "ERROR")
        return (measured_voltage, False, verify_msg)
        

    # Measure voltage again after activation
    try:
        measured_voltage = self.measurer.measure_voltage(analog_port)
        if is_simulation:
            measured_voltage = pin.Power_Expected + variation
            self.log(f"the measure_Voltage is simulated (pin.Power_Expected + variation) + samll variation = {variation} ", "DEBUG")
        self.log(f"Measurement after activation: {measured_voltage* voltage_scale:.3f}V", "DEBUG")
        if get_debug_setting(self.settings, "Power_Test"):
            self.log(f"Measurement after spider activation: {measured_voltage:.3f}V for pin {pin_number}", "INFO")
            self.wait_debug(150, "active")

    except Exception as e:
        self.log(f"in Power test - Measurement error after activation: {str(e)}", "ERROR")
        return (0.0, False, f"Error: Measurement failed after activation - {str(e)}")

    # Set analog or digital output  buck to zero 
    if event_type == "AO":
        success = self.card_manager.set_analog_output(card_id=card, ao_number=event_num, voltage=0)
        event_value = 0
        self.log(f"Deactive: Set Card {card} AO{event_num} to {0}V: {'Success' if success else 'Failed'}", "INFO")
    elif event_type == "DO":
        success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
        event_value = False
        self.log(f"Deactive: Set Card {card} DO{event_num} to False: {'Success' if success else 'Failed'}", "INFO")
    else:
        self.log(f"in Power test - Unknown event type: {event_type}", "ERROR")
        return (measured_voltage, False, f"Unknown event type: {event_type}")

    if get_debug_setting(self.settings, "Power_Test"):
        self.wait_debug(160, "active")

    if not success:
        self.log(f"in Power test - Failed to deactivate card {card}", "ERROR")
        return (measured_voltage, False, f"Failed to deactivate card {card}")
        
    # Verify the output was set correctly
    verify_success, verify_msg = verify_card_output(
        self.card_manager, card, event_type, event_num, event_value, 
        tolerance, self.log
    )

    if not verify_success:
        self.log(f"in Power test - Failed to deactivate card {card}", "ERROR")
        return (measured_voltage, False, verify_msg)
        

    # Compare to expected value

    voltage_diff = abs(measured_voltage* voltage_scale - pin.Power_Expected)
    if voltage_diff <= tolerance:
        self.log(f"Measurement {measured_voltage* voltage_scale:.3f}V is within tolerance of {pin.Power_Expected:.3f}V", "SUCCESS")
        return (measured_voltage* voltage_scale* voltage_scale, True, "Measurement is in tolerance")
    else:
        self.log(f"Measurement {measured_voltage* voltage_scale:.3f}V is NOT within tolerance of {pin.Power_Expected:.3f}V (diff: {voltage_diff:.3f}V)", "WARNING")
        return (measured_voltage* voltage_scale, False, f"Measurement not in tolerance (diff: {voltage_diff:.3f}V)")    # Real hardware mode
   