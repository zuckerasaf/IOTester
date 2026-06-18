import time
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


def pullup_test(test_handle, pin: "Pin") -> tuple[float, bool, str]:
    """
    Run pullup test on a pin.
    
    Test Procedure:
    1. Get pair info (voltage_measure_pin, pullup_pin, card enables, etc.) for connector pin
    2. Convert connector pin number to bit pattern and set mux matrix (D0-D15)
    3. Measure initial voltage on pair-specific analog pin
    4. Verify initial measurement is ~0V (within tolerance)
    5. Activate pullup_pin_key (set HIGH)
    6. Wait for signal stabilization
    7. Measure voltage again
    8. Check that measured voltage matches PullUp_Expected (within tolerance), if not return with warning
    9. Parse PullUp_Input data
    10. If PullUp_Input == "G": deactivate pullup_pin_key (set LOW) and return
    11. Else:
        - Activate the DO (set_digital_output) according to data in PullUp_Input (card_id, do_number, state)
        - Read the DO status (get_digital_output)
        - Check DO was changed as requested, if not return with warning
        - Measure voltage again
        - Check that measured voltage is ~0V (within tolerance), if not return with warning
        - Deactivate pullup_pin_key (set LOW)
        - Deactivate the DO (set_digital_output)
        - Read the DO status (get_digital_output)
        - Check DO was changed as requested, if not return with warning
    
    Args:
        pin: Pin object containing test parameters (Id, PullUp_Expected, PullUp_Input, etc.)
        
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
        import random
        variation = random.uniform(-0.1, 0.1)

    # Real hardware mode
    # Get tolerance from settings (default 0.5V)
    tolerance = self.settings.get('scale', {}).get('voltage_tolerance', 0.5)

    # Get pair number and associated pins
    pin_number = int(''.join(filter(str.isdigit, pin.Id)))
    pin_PullUp_Expected =  pin.PullUp_Expected

    pair_num, voltage_pin_key, voltage_pin_b_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(pin_number)
    
    if get_debug_setting(self.settings, "PullUp_Test"):
        self.log(f"start PullUp test for pin {pin_number}", "INFO")
        self.wait_debug(200, "active")

    # Get actual pin names from board config
    voltage_pin_name = self.board_config.get(voltage_pin_key, 'A0')
    pullup_pin_name = self.board_config.get(pullup_pin_key, 'D20')
    
    # Convert connector pin to bit representation and set mux matrix
    bits = connector_pin_to_bits(pin_number, "a")
    success = set_mux_bits(bits, pin_number, self.pin_map, self.hardware, self.settings, self.log)
    

    # Step 0: Activate pullup pin (set HIGH)
    digital_ports = self.pin_map.get('D', {})
    pullup_physical_pin = digital_ports.get(pullup_pin_name)
    
    if pullup_physical_pin is None:
        self.log(f"in pullup test - Pullup pin {pullup_pin_name} not found in pin map", "ERROR")
        return (0.0, False, f"Error: Pullup pin {pullup_pin_name} not found")
    
    self.log(f"Activating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) HIGH", "INFO")
    self.hardware.digital_write(pullup_physical_pin, True)
    
    # Wait for signal to stabilize
    stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
    time.sleep(stabilize_delay)

    if not success:
        self.log(f"in pullup test - Failed to set mux bits for pin {pin_number}", "ERROR")
        return (0.0, False, "Error: Failed to set mux matrix")
    
    # Get physical analog port from pin map
    analog_ports = self.pin_map.get('A', {})
    analog_port = analog_ports.get(voltage_pin_name)
    
    if analog_port is None:
        self.log(f"in pullup test - Analog pin {voltage_pin_name} not found in pin map", "ERROR")
        return (0.0, False, "Error: Analog pin not found in pin map")
    
    # Apply voltage scaling factor from settings
    voltage_scale = 1
    
    # Step 1: Measure initial voltage
    self.log(f"Measuring voltage on {voltage_pin_name} (pin {analog_port})", "DEBUG")
    try:
        measured_voltage = self.measurer.measure_voltage(analog_port) * voltage_scale
        if is_simulation:
            measured_voltage = 0 + variation
            self.log(f"the measure_Voltage is simulated {pin_PullUp_Expected + variation} + samll variation = {variation} ", "DEBUG")
        self.log(f"Initial measurement: {measured_voltage:.3f}V for pin {pin_number}", "INFO")
        if get_debug_setting(self.settings, "PullUp_Test"):
            self.wait_debug(221, "active")
    except Exception as e:
        self.log(f"in pullup test - Measurement error: {str(e)}", "ERROR")
        return (0.0, False, f"Error: Measurement failed - {str(e)}")
    

    

    # Step 2: Verify initial measurement is ~0V
    if abs(measured_voltage * voltage_scale) > tolerance:
        self.log(f"Initial voltage {measured_voltage * voltage_scale:.3f}V is not ~0V (tolerance: {tolerance}V) - test failed", "WARNING")
        return (measured_voltage * voltage_scale, False, f"Initial voltage {measured_voltage:.3f}V is not ~0V")
    
    self.log(f"Initial voltage {measured_voltage * voltage_scale:.3f}V is ~0V - proceeding to activate hardware pullup", "DEBUG")

    # Step 4: close Relay 15
    relay_connect = self.relay_general_operate(True)
    if relay_connect == False:
        return (0, False, f"the relay logic didnt operate")
        

    # Step 5: Measure voltage after pullup activation
    # Step 5.1: Parse PullUp_Input data
    pullup_input_value = pin.PullUp_Input.strip() if pin.PullUp_Input else "G"


    try:
        measured_voltage = self.measurer.measure_voltage(analog_port)
        if is_simulation:
            if pullup_input_value == "G":
                measured_voltage = 0 + variation
                self.log(f"the measure_Voltage is simulated ~0V + samll variation = {variation} ", "DEBUG")
            else:
                measured_voltage = pin_PullUp_Expected + variation
                self.log(f"the measure_Voltage is simulated {pin_PullUp_Expected + variation} + samll variation = {variation} ", "DEBUG")

    except Exception as e:
        self.log(f"in pullup test - Measurement error after pullup activation: {str(e)}", "ERROR")
        # Ensure pullup pin is deactivated even on error
        self.hardware.digital_write(pullup_physical_pin, False)
        relay_connect = self.relay_general_operate(False)
        return (0.0, False, f"Error: Measurement failed after pullup activation - {str(e)}")
    
    # Step 6: Check that measured voltage matches PullUp_Expected

    voltage_diff = abs(measured_voltage * voltage_scale - pin_PullUp_Expected)

    if voltage_diff > tolerance:
        self.log(f"Pullup voltage {measured_voltage * voltage_scale:.3f}V does NOT match expected {pin_PullUp_Expected:.2f}V (diff: {voltage_diff:.3f}V)", "WARNING")
        # Deactivate pullup and return with warning
        self.hardware.digital_write(pullup_physical_pin, False)
        relay_connect = self.relay_general_operate(False)

        return (measured_voltage * voltage_scale, False, f"Pullup voltage not in tolerance (diff: {voltage_diff:.2f}V)")
    
    self.log(f"Pullup voltage {measured_voltage * voltage_scale:.3f}V matches expected {pin_PullUp_Expected:.2f}V", "SUCCESS")
    if get_debug_setting(self.settings, "PullUp_Test"):
        self.wait_debug(231, "active")

 
    
    # Step 8: Check if PullUp_Input == "G" (ground test only)
    if pullup_input_value.upper() == "G":
        self.log(f"PullUp_Input is 'G' - deactivating pullup and completing test", "INFO")
        # Deactivate pullup pin (set LOW)
        self.hardware.digital_write(pullup_physical_pin, False)
        relay_connect = self.relay_general_operate(False)
        self.log(f"Deactivating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) LOW", "INFO")
        return (measured_voltage * voltage_scale, True, "Pullup test passed (ground test)")
    
    # Step 9: PullUp_Input is not "G" - parse and activate DO
    self.log(f"PullUp_Input is '{pullup_input_value}' - activating DO output", "DEBUG")
    
    # Parse PullUp_Input for DO control (format: "C2_DO13V1" or similar)
    card, event_type, event_num, event_value = parse_event_string(pin.PullUp_Input)

    if card is None or event_type is None or event_type != "DO":
        self.log(f"in pullup test - Failed to parse PullUp_Input or not DO type: {pullup_input_value}", "ERROR")
        # Deactivate pullup and return with error
        self.hardware.digital_write(pullup_physical_pin, False)
        relay_connect = self.relay_general_operate(False)
        return (measured_voltage, False, f"Failed to parse PullUp_Input: {pullup_input_value}")
    
    # Step 10: Activate the DO
    do_state = bool(event_value)
    success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=do_state)
    self.log(f"Active: Set Card {card} DO{event_num} to {do_state}: {'Success' if success else 'Failed'}", "INFO")
    if get_debug_setting(self.settings, "PullUp_Test"):
        self.wait_debug(270, "active")
   
    if not success:
        self.log(f"Failed to activate DO on card {card}", "WARNING")
        # Deactivate pullup and return with warning
        self.hardware.digital_write(pullup_physical_pin, False)
        relay_connect = self.relay_general_operate(False)
        return (measured_voltage * voltage_scale, False, f"Failed to activate DO on card {card}")
    
    # Wait for DO to stabilize
    time.sleep(stabilize_delay)
    
    # Step 11: Read DO status to verify it was set
    actual_do_state = self.card_manager.get_digital_output(card_id=card, do_number=event_num)
    if is_simulation:
        actual_do_state = do_state  # Simulate correct setting in simulation mode
        self.log(f"the DO state is simulated to be {actual_do_state} ", "DEBUG")

    if actual_do_state != do_state:
        self.log(f"DO verification failed: Expected {do_state}, got {actual_do_state}", "WARNING")
        # Deactivate pullup and DO, then return with warning
        self.hardware.digital_write(pullup_physical_pin, False)
        relay_connect = self.relay_general_operate(False)
        self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
        return (measured_voltage * voltage_scale, False, f"DO not set correctly: expected {do_state}, got {actual_do_state}")
    
    self.log(f"DO status verified: {actual_do_state}", "DEBUG")
    
    
        
    # Step 12: Measure voltage again after DO activation
    try:
        measured_voltage_after_do = self.measurer.measure_voltage(analog_port)
        if is_simulation:
            measured_voltage_after_do = 0 + variation
        self.log(f"the measure_Voltage is simulated to be ~0V + samll variation = {variation} ", "DEBUG")
        self.log(f"Measurement after DO activation: {measured_voltage_after_do * voltage_scale:.3f}V", "INFO")
        if get_debug_setting(self.settings, "PullUp_Test"):
            self.wait_debug(290, "active")
    except Exception as e:
        self.log(f"in pullup test - Measurement error after DO activation: {str(e)}", "ERROR")
        # Ensure cleanup
        self.hardware.digital_write(pullup_physical_pin, False)
        relay_connect = self.relay_general_operate(False)
        self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
        return (0.0, False, f"Error: Measurement failed after DO activation - {str(e)}")
    
    # Step 13: Check that voltage is now ~0V (within tolerance)

    if abs(measured_voltage_after_do * voltage_scale) > tolerance:
        self.log(f"Voltage after DO activation {measured_voltage_after_do * voltage_scale:.3f}V is not ~0V (tolerance: {tolerance}V)", "WARNING")
        # Cleanup and return with warning
        self.hardware.digital_write(pullup_physical_pin, False)
        relay_connect = self.relay_general_operate(False)
        self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)

        return (measured_voltage_after_do * voltage_scale, False, f"Voltage after DO not ~0V: {measured_voltage_after_do * voltage_scale:.3f}V")
    
    self.log(f"Voltage after DO activation is ~0V as expected", "SUCCESS")
    
    # Step 14: Deactivate pullup pin (set LOW)
    self.hardware.digital_write(pullup_physical_pin, False)
    relay_connect = self.relay_general_operate(False)
    self.log(f"Deactivating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) LOW", "INFO")

    # Step 15: Deactivate the DO (set to False)
    success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
    self.log(f"DeActive: Set Card {card} DO{event_num} to False: {'Success' if success else 'Failed'}", "INFO")
    if get_debug_setting(self.settings, "PullUp_Test"):
        self.wait_debug(310, "active")

    if not success:
        self.log(f"Failed to deactivate DO on card {card}", "WARNING")
        return (measured_voltage * voltage_scale, False, f"Failed to deactivate DO on card {card}")
    
    # Wait for DO to stabilize
    time.sleep(stabilize_delay)
    
    # Step 16: Read DO status to verify it was deactivated
    actual_do_state_after = self.card_manager.get_digital_output(card_id=card, do_number=event_num)

    
    if is_simulation:
        actual_do_state_after = False  # Simulate correct deactivation in simulation mode
        self.log(f"the DO state after deactivation is simulated to be {actual_do_state_after} ", "DEBUG")
    if actual_do_state_after != False:
        self.log(f"DO deactivation verification failed: Expected False, got {actual_do_state_after}", "WARNING")
        return (measured_voltage * voltage_scale, False, f"DO not deactivated correctly: got {actual_do_state_after}")
    
    self.log(f"DO deactivation verified: {actual_do_state_after}", "DEBUG")

    # All steps completed successfully
    return (measured_voltage * voltage_scale, True, "Pullup test passed")
