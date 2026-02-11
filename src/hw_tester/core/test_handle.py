"""
Test Handler - Core test execution functions for HW Tester.
Contains all test procedures: power, pullup, logic, I-bit, relay/fuse, and short circuit tests.
"""
import time
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hw_tester.hardware.pin import Pin

from hw_tester.hardware.pin import TestResult
from hw_tester.hardware.controllino_io import connector_pin_to_bits
from hw_tester.utils.general import (
    parse_event_string,
    get_pin_pair_info_controlino,
    set_mux_bits,
    verify_card_output,
    enable_cards,
    clear_mux_bits,
    clear_bits,
)


class TestHandle:
    """
    Test handler class that encapsulates all test execution logic.
    Separates test business logic from UI layer for better organization.
    """
    
    def __init__(self, hardware, settings, pin_map, board_config, measurer, card_manager, log_callback):
        """
        Initialize test handler with required dependencies.
        
        Args:
            hardware: Hardware IO instance (Controllino/Mock)
            settings: Settings dictionary from settings.yaml
            pin_map: Pin mapping dictionary
            board_config: Board-specific pin configuration
            measurer: Measurer instance for voltage readings
            card_manager: UDPCardManager for controlling IO cards
            log_callback: Function to call for logging (signature: log_callback(message, level))
        """
        self.hardware = hardware
        self.settings = settings
        self.pin_map = pin_map
        self.board_config = board_config
        self.measurer = measurer
        self.card_manager = card_manager
        self.log = log_callback
        
        # Control flags for stopping tests
        self.running = False
        self.running_ibit = False
        
        # Threading event for debug control
        self.next_event = threading.Event()
    
    def wait_debug(self, ID: int = 0, status: str = "active") -> None:
        """
        Pause execution for debugging purposes.
        Waits for user to press next button.
        
        Args:
            ID: Debug checkpoint ID
            status: Status of checkpoint ("active" or "done")
        """
        from hw_tester.web.trace_writer import trace_step
        
        trace_step(ID, status)
        
        # Small delay to ensure trace.json is written and visible to browser
        time.sleep(0.05)  # 50ms - enough for file system sync

        self.log(f"in node {ID} Waiting for Next button press to continue...", "INFO")
        self.next_event.wait()  # Wait for Next button press
        self.next_event.clear()  # Reset event for next pause
        # self.log("Continuing test execution...", "INFO")
    
    def measure_voltage(self, pin_id: str, analog_port: int, idx: int = 0) -> None:
        """
        Measure voltage on a pin.
        Delegates to Measurer which handles simulation mode internally.
        
        Args:
            pin_id: Pin ID to measure
            analog_port: Analog port number (e.g., 0 for A0)
            idx: Index for simulation variation (default: 0)
        """
        # Get voltage scale factor from settings
        scale_factor = self.settings.get('Measure_value', {}).get('Scale_1', 1.0)
        
        # Measurer handles simulation mode internally
        try:
            measured_voltage = self.measurer.measure_voltage(analog_port)
        except Exception as e:
            self.log(f"Measurement error on {pin_id}: {str(e)}", "ERROR")
            measured_voltage = 0.0
        
        # Scale the measurement
        scaled_voltage = measured_voltage * scale_factor
        
        self.log(f"Measured {pin_id} (A{analog_port}): {scaled_voltage:.3f}V", "INFO")
        
        return scaled_voltage
    
    def run_power_test(self, pin: "Pin") -> tuple[float, bool, str]:
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
        
        
        is_simulation = self.settings.get('Board', {}).get('simulation', True)
        
        if is_simulation:
            # Simulation mode - return fixed value based on expected
            time.sleep(0.2)  # Simulate measurement delay
            import random
            variation = random.uniform(-0.1, 0.1)
  
        if self.settings.get('Debug', {}).get('mode', False):
            self.wait_debug(100, "active")

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
        
        if self.settings.get('Debug', {}).get('mode', False):
            #self.wait_debug(100, "done")
            self.wait_debug(110, "active")

        if not success:
            self.log(f"in Power test -Failed to set mux bits for pin {pin_number}", "ERROR")
            if self.settings.get('Debug', {}).get('mode', False):
                #self.wait_debug(110, "done")
                self.wait_debug(120, "active")
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
            self.log(f"Initial measurement: {measured_voltage:.3f}V", "DEBUG")
            if self.settings.get('Debug', {}).get('mode', False):
                #self.wait_debug(110, "done")
                self.wait_debug(121, "active")
        except Exception as e:
            self.log(f"in Power test - Measurement error: {str(e)}", "ERROR")
            if self.settings.get('Debug', {}).get('mode', False):
                #self.wait_debug(110, "done")
                self.wait_debug(122, "active")
            return (0.0, False, f"Error: Measurement failed - {str(e)}")
        
        # Step 2: Check if Power_Input is "none" or empty
        # in case it is in simulation mode the mesured volateg will be as the expected voltage or zero ....
        if self.settings.get('Debug', {}).get('mode', False):
            self.wait_debug(123, "active")
        if not pin.Power_Input or pin.Power_Input.strip().lower() == "none" or pin.Power_Input.strip() == "P" or pin.Power_Input.strip() == "Power":
            if is_simulation:
                measured_voltage = pin.Power_Expected + variation
                self.log(f"the measure_Voltage is simulated (pin.Power_Expected + variation) + samll variation = {variation} ", "DEBUG")

            # No external control needed - just verify measurement
            voltage_diff = abs(measured_voltage* voltage_scale - pin.Power_Expected)
            if voltage_diff <= tolerance:
                self.log(f"Measurement {measured_voltage* voltage_scale:.3f}V is within tolerance of {pin.Power_Expected:.3f}V", "SUCCESS")
                if self.settings.get('Debug', {}).get('mode', False):
                    self.wait_debug(124, "active")
                return (measured_voltage* voltage_scale, True, "Measurement is in tolerance")
            else:
                self.log(f"Measurement {measured_voltage* voltage_scale:.3f}V is NOT within tolerance of {pin.Power_Expected:.3f}V (diff: {voltage_diff:.3f}V)", "WARNING")
                if self.settings.get('Debug', {}).get('mode', False):
                    self.wait_debug(124, "active")
                return (measured_voltage* voltage_scale, False, f"Measurement not in tolerance (diff: {voltage_diff:.3f}V)")
        
        # Step 3: Power_Input is provided - need to activate external card
        # First verify initial measurement is ~0V

        if is_simulation:
            measured_voltage = 0 + variation
            self.log(f"the measure_Voltage is simulated {pin.Power_Expected + variation} + samll variation = {variation} ", "DEBUG")
            
        if abs(measured_voltage* voltage_scale) > tolerance:
            self.log(f"Initial voltage {measured_voltage* voltage_scale:.3f}V is not ~0V (tolerance: {tolerance}V) - test failed", "WARNING")
            if self.settings.get('Debug', {}).get('mode', False):
                    self.wait_debug(124, "active")
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
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(130, "active")
        elif event_type == "DO":
            success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=bool(event_value))
            self.log(f"active: Set Card {card} DO{event_num} to {event_value}: {'Success' if success else 'Failed'}", "INFO")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(130, "active")
        else:
            self.log(f"in Power test - Unknown event type: {event_type}", "ERROR")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(131, "active")
            return (measured_voltage, False, f"Unknown event type: {event_type}")
        
        if not success:
            self.log(f"in Power test - Failed to activate card {card}", "ERROR")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(131, "active")
            return (measured_voltage, False, f"Failed to activate card {card}")
        
        # Wait for signal to stabilize
        stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
        time.sleep(stabilize_delay)
        # Verify the output was set correctly
        verify_success, verify_msg = verify_card_output(
            self.card_manager, card, event_type, event_num, event_value, 
            tolerance, self.log
        )
        if self.settings.get('Debug', {}).get('mode', False):
            self.wait_debug(140, "active")
        if not verify_success:
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(141, "active")
            return (measured_voltage, False, verify_msg)
        
        # Wait for signal to stabilize
        stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
        time.sleep(stabilize_delay)

        # Measure voltage again after activation
        try:
            measured_voltage = self.measurer.measure_voltage(analog_port)
            self.log(f"Measurement after activation: {measured_voltage* voltage_scale:.3f}V", "DEBUG")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(150, "active")

        except Exception as e:
            self.log(f"in Power test - Measurement error after activation: {str(e)}", "ERROR")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(151, "active")
            return (0.0, False, f"Error: Measurement failed after activation - {str(e)}")
        if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(160, "active")
        # Set analog or digital output  buck to zero 
        if event_type == "AO":
            success = self.card_manager.set_analog_output(card_id=card, ao_number=event_num, voltage=0)
            event_value = 0
            self.log(f"DeActive: Set Card {card} AO{event_num} to {0}V: {'Success' if success else 'Failed'}", "INFO")
        elif event_type == "DO":
            success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
            event_value = False
            self.log(f"DeActive: Set Card {card} DO{event_num} to False: {'Success' if success else 'Failed'}", "INFO")
        else:
            self.log(f"in Power test - Unknown event type: {event_type}", "ERROR")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(161, "active")
            return (measured_voltage, False, f"Unknown event type: {event_type}")
        
        if not success:
            self.log(f"in Power test - Failed to activate card {card}", "ERROR")
            return (measured_voltage, False, f"Failed to activate card {card}")
        
        # Verify the output was set correctly
        verify_success, verify_msg = verify_card_output(
            self.card_manager, card, event_type, event_num, event_value, 
            tolerance, self.log
        )
        if self.settings.get('Debug', {}).get('mode', False):
            self.wait_debug(170, "active")
        if not verify_success:
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(180, "active")
            return (measured_voltage, False, verify_msg)
        
        if is_simulation:
            measured_voltage = pin.Power_Expected + variation
            self.log(f"the measure_Voltage is simulated (pin.Power_Expected + variation) + samll variation = {variation} ", "DEBUG")
        # Compare to expected value

        voltage_diff = abs(measured_voltage* voltage_scale - pin.Power_Expected)
        if voltage_diff <= tolerance:
            self.log(f"Measurement {measured_voltage* voltage_scale:.3f}V is within tolerance of {pin.Power_Expected:.3f}V", "SUCCESS")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(180, "active")
            return (measured_voltage* voltage_scale* voltage_scale, True, "Measurement is in tolerance")
        else:
            self.log(f"Measurement {measured_voltage* voltage_scale:.3f}V is NOT within tolerance of {pin.Power_Expected:.3f}V (diff: {voltage_diff:.3f}V)", "WARNING")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(180, "active")
            return (measured_voltage* voltage_scale, False, f"Measurement not in tolerance (diff: {voltage_diff:.3f}V)")
    
    def run_pullup_test(self, pin: "Pin") -> tuple[float, bool, str]:
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
        
        
        
        is_simulation = self.settings.get('Board', {}).get('simulation', True)

        
        if is_simulation:
            # Simulation mode - return fixed value based on expected
            time.sleep(0.2)  # Simulate measurement delay
            import random
            variation = random.uniform(-0.1, 0.1)
            
        if self.settings.get('Debug', {}).get('mode', False):
            self.wait_debug(200, "active")
        # Real hardware mode
        # Get tolerance from settings (default 0.5V)
        tolerance = self.settings.get('scale', {}).get('voltage_tolerance', 0.5)

        # Get pair number and associated pins
        pin_number = int(''.join(filter(str.isdigit, pin.Id)))
        pair_num, voltage_pin_key, voltage_pin_b_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(pin_number)

        # Get actual pin names from board config
        voltage_pin_name = self.board_config.get(voltage_pin_key, 'A0')
        pullup_pin_name = self.board_config.get(pullup_pin_key, 'D20')
        
        # Convert connector pin to bit representation and set mux matrix
        bits = connector_pin_to_bits(pin_number, "a")
        success = set_mux_bits(bits, pin_number, self.pin_map, self.hardware, self.settings, self.log)
        
        if self.settings.get('Debug', {}).get('mode', False):
            self.wait_debug(210, "active")

        if not success:
            self.log(f"in pullup test - Failed to set mux bits for pin {pin_number}", "ERROR")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(220, "active")
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
            self.log(f"Initial measurement: {measured_voltage:.3f}V", "DEBUG")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(221, "active")
        except Exception as e:
            self.log(f"in pullup test - Measurement error: {str(e)}", "ERROR")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(222, "active")
            return (0.0, False, f"Error: Measurement failed - {str(e)}")
        
        if is_simulation:
            measured_voltage = 0 + variation
            self.log(f"the measure_Voltage is simulated {pin.PullUp_Expected + variation} + samll variation = {variation} ", "DEBUG")
        
        if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(223, "active")
        # Step 2: Verify initial measurement is ~0V
        if abs(measured_voltage * voltage_scale) > tolerance:
            self.log(f"Initial voltage {measured_voltage * voltage_scale:.3f}V is not ~0V (tolerance: {tolerance}V) - test failed", "WARNING")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(224, "active")
            return (measured_voltage * voltage_scale, False, f"Initial voltage {measured_voltage:.3f}V is not ~0V")
        
        self.log(f"Initial voltage {measured_voltage * voltage_scale:.3f}V is ~0V - proceeding to activate hardware pullup", "DEBUG")
        
        # Step 4: Activate pullup pin (set HIGH)
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
        if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(230, "active")
        # Step 5: Measure voltage after pullup activation
        try:
            measured_voltage = self.measurer.measure_voltage(analog_port)
            self.log(f"Measurement after pullup activation: {measured_voltage * voltage_scale:.3f}V", "DEBUG")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(231, "active")
        except Exception as e:
            self.log(f"in pullup test - Measurement error after pullup activation: {str(e)}", "ERROR")
            # Ensure pullup pin is deactivated even on error
            self.hardware.digital_write(pullup_physical_pin, False)
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(240, "active")
            return (0.0, False, f"Error: Measurement failed after pullup activation - {str(e)}")
        
        # Step 6: Check that measured voltage matches PullUp_Expected
        if is_simulation:
            measured_voltage = pin.PullUp_Expected + variation
            self.log(f"the measure_Voltage is simulated {pin.PullUp_Expected + variation} + samll variation = {variation} ", "DEBUG")
        voltage_diff = abs(measured_voltage * voltage_scale - pin.PullUp_Expected)
        if self.settings.get('Debug', {}).get('mode', False):
            self.wait_debug(250, "active")
        if voltage_diff > tolerance:
            self.log(f"Pullup voltage {measured_voltage * voltage_scale:.3f}V does NOT match expected {pin.PullUp_Expected:.3f}V (diff: {voltage_diff:.3f}V)", "WARNING")
            # Deactivate pullup and return with warning
            self.hardware.digital_write(pullup_physical_pin, False)
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(251, "active")
            return (measured_voltage * voltage_scale, False, f"Pullup voltage not in tolerance (diff: {voltage_diff:.3f}V)")
        
        self.log(f"Pullup voltage {measured_voltage * voltage_scale:.3f}V matches expected {pin.PullUp_Expected:.3f}V", "SUCCESS")
        
        # Step 7: Parse PullUp_Input data
        pullup_input_value = pin.PullUp_Input.strip() if pin.PullUp_Input else "G"
        
        # Step 8: Check if PullUp_Input == "G" (ground test only)
        if pullup_input_value.upper() == "G":
            self.log(f"PullUp_Input is 'G' - deactivating pullup and completing test", "INFO")
            # Deactivate pullup pin (set LOW)
            self.hardware.digital_write(pullup_physical_pin, False)
            self.log(f"Deactivating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) LOW", "INFO")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(252, "active")
            return (measured_voltage * voltage_scale, True, "Pullup test passed (ground test)")
        
        # Step 9: PullUp_Input is not "G" - parse and activate DO
        self.log(f"PullUp_Input is '{pullup_input_value}' - activating DO output", "DEBUG")
        
        # Parse PullUp_Input for DO control (format: "C2_DO13V1" or similar)
        card, event_type, event_num, event_value = parse_event_string(pin.PullUp_Input)
        if self.settings.get('Debug', {}).get('mode', False):
            self.wait_debug(260, "active")
        if card is None or event_type is None or event_type != "DO":
            self.log(f"in pullup test - Failed to parse PullUp_Input or not DO type: {pullup_input_value}", "ERROR")
            # Deactivate pullup and return with error
            self.hardware.digital_write(pullup_physical_pin, False)
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(261, "active")
            return (measured_voltage, False, f"Failed to parse PullUp_Input: {pullup_input_value}")
        
        # Step 10: Activate the DO
        do_state = bool(event_value)
        success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=do_state)
        self.log(f"Active: Set Card {card} DO{event_num} to {do_state}: {'Success' if success else 'Failed'}", "INFO")
        if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(270, "active")
       
        if not success:
            self.log(f"Failed to activate DO on card {card}", "WARNING")
            # Deactivate pullup and return with warning
            self.hardware.digital_write(pullup_physical_pin, False)

            return (measured_voltage * voltage_scale, False, f"Failed to activate DO on card {card}")
        
        # Wait for DO to stabilize
        time.sleep(stabilize_delay)
        
        # Step 11: Read DO status to verify it was set
        actual_do_state = self.card_manager.get_digital_output(card_id=card, do_number=event_num)
        if is_simulation:
            actual_do_state = do_state  # Simulate correct setting in simulation mode
            self.log(f"the DO state is simulated to be {actual_do_state} ", "DEBUG")
        if self.settings.get('Debug', {}).get('mode', False):
            self.wait_debug(280, "active")
        if actual_do_state != do_state:
            self.log(f"DO verification failed: Expected {do_state}, got {actual_do_state}", "WARNING")
            # Deactivate pullup and DO, then return with warning
            self.hardware.digital_write(pullup_physical_pin, False)
            self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(281, "active")
            return (measured_voltage * voltage_scale, False, f"DO not set correctly: expected {do_state}, got {actual_do_state}")
        
        self.log(f"DO status verified: {actual_do_state}", "DEBUG")
        

        
        # Step 12: Measure voltage again after DO activation
        try:
            measured_voltage_after_do = self.measurer.measure_voltage(analog_port)
            self.log(f"Measurement after DO activation: {measured_voltage_after_do * voltage_scale:.3f}V", "DEBUG")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(290, "active")
        except Exception as e:
            self.log(f"in pullup test - Measurement error after DO activation: {str(e)}", "ERROR")
            # Ensure cleanup
            self.hardware.digital_write(pullup_physical_pin, False)
            self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(291, "active")
            return (0.0, False, f"Error: Measurement failed after DO activation - {str(e)}")
        
        # Step 13: Check that voltage is now ~0V (within tolerance)
        if is_simulation:
            measured_voltage_after_do = 0 + variation
            self.log(f"the measure_Voltage is simulated to be ~0V + samll variation = {variation} ", "DEBUG")
        if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(300, "active")
        if abs(measured_voltage_after_do * voltage_scale) > tolerance:
            self.log(f"Voltage after DO activation {measured_voltage_after_do * voltage_scale:.3f}V is not ~0V (tolerance: {tolerance}V)", "WARNING")
            # Cleanup and return with warning
            self.hardware.digital_write(pullup_physical_pin, False)
            self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(301, "active")
            return (measured_voltage_after_do * voltage_scale, False, f"Voltage after DO not ~0V: {measured_voltage_after_do * voltage_scale:.3f}V")
        
        self.log(f"Voltage after DO activation is ~0V as expected", "SUCCESS")
        
        # Step 14: Deactivate pullup pin (set LOW)
        self.hardware.digital_write(pullup_physical_pin, False)
        self.log(f"Deactivating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) LOW", "INFO")
        if self.settings.get('Debug', {}).get('mode', False):
            self.wait_debug(310, "active")
        # Step 15: Deactivate the DO (set to False)
        success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
        self.log(f"DeActive: Set Card {card} DO{event_num} to False: {'Success' if success else 'Failed'}", "INFO")
        
        if not success:
            self.log(f"Failed to deactivate DO on card {card}", "WARNING")
            return (measured_voltage * voltage_scale, False, f"Failed to deactivate DO on card {card}")
        
        # Wait for DO to stabilize
        time.sleep(stabilize_delay)
        
        # Step 16: Read DO status to verify it was deactivated
        actual_do_state_after = self.card_manager.get_digital_output(card_id=card, do_number=event_num)
        if self.settings.get('Debug', {}).get('mode', False):
            self.wait_debug(320, "active")
        
        if is_simulation:
            actual_do_state_after = False  # Simulate correct deactivation in simulation mode
            self.log(f"the DO state after deactivation is simulated to be {actual_do_state_after} ", "DEBUG")
        if actual_do_state_after != False:
            self.log(f"DO deactivation verification failed: Expected False, got {actual_do_state_after}", "WARNING")
            if self.settings.get('Debug', {}).get('mode', False):
                self.wait_debug(321, "active")
            return (measured_voltage * voltage_scale, False, f"DO not deactivated correctly: got {actual_do_state_after}")
        
        self.log(f"DO deactivation verified: {actual_do_state_after}", "DEBUG")
        

        if self.settings.get('Debug', {}).get('mode', False):
            self.wait_debug(330, "active")
        # All steps completed successfully
        return (measured_voltage * voltage_scale, True, "Pullup test passed")
    
    def run_logic_test(self, pin: "Pin", pin_table_rows: list) -> tuple[float, bool, str]:
        """
        Run logic test on a pin.
        
        Test Procedure:
        1. Get pair info (voltage_measure_pin, card enables, etc.) for connector pin
        2. Convert connector pin number to bit pattern and set mux matrix (D0-D15) - system A
        3. Read the pin number from the "Logic_Pin_Input" = will be defined as "second Pin"
        4. Create "second Pin" according to the pin table and the second pin number
        5. Check if "second Pin" power_result != pass or Power_Measured != "0" with tolerance, report wrong logic pin input data and return
        6. Convert "second Pin" pin number to bit pattern and set mux matrix (D0-D15) - system B
        7. Activate the two proper relays for pin and "second Pin"
        8. Parse "Logic_Expected" data
        9. Read the DI status (get_digital_input)
        10. Check the read status as defined in the Logic_Expected, if not return with warning
        11. Deactivate the Relay cards
        12. Return result (status)
        
        Args:
            pin: Pin object containing test parameters (Id, Logic_Pin_Input, Logic_Expected, etc.)
            pin_table_rows: All rows from pin table (for looking up second pin data)
            
        Returns:
            Tuple of (measured_voltage, success, message):
                - success: True if status matches expected, False otherwise
                - message: Descriptive message about test result or error
        """
        
        
        Overallsuccess = False 
        is_simulation = self.settings.get('Board', {}).get('simulation', True)
        text = ""

        
        if is_simulation:
            # Simulation mode - return fixed value based on expected
            time.sleep(0.2)  # Simulate measurement delay
            import random
            variation = random.uniform(-0.1, 0.1)
            
        # Real hardware mode
        # Get tolerance from settings (default 0.5V)
        tolerance = self.settings.get('scale', {}).get('voltage_tolerance', 0.5)
        
        # Step 1: Get pair number and associated pins for first pin
        pin_number = int(''.join(filter(str.isdigit, pin.Id)))
        pair_num, voltage_pin_key, voltage_pin_b_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(pin_number)
        
        # Step 2: Convert connector pin to bit representation and set mux matrix (system A)
        bits = connector_pin_to_bits(pin_number, "a")
        success = set_mux_bits(bits, pin_number, self.pin_map, self.hardware, self.settings, self.log)
        
        if not success:
            text = f"Failed to set mux bits for pin {pin_number}"
            self.log(text, "ERROR")
            return (0.0, False, text)
        
        # Step 3: Read the pin number from Logic_Pin_Input (second pin)
        if not hasattr(pin, 'Logic_Pin_Input') or not pin.Logic_Pin_Input or pin.Logic_Pin_Input.strip().lower() == "none":
            text = f"No Logic_Pin_Input specified for pin {pin_number} - skipping logic test"
            self.log(text, "INFO")
            return (0.0, True, text)
        
        #this for loop is run on all the data in the Logic_Pin_Input field for each one of them make the test 
        for i in range(len(pin.Logic_Pin_Input.split(","))):
            try:
                second_pin_number = int(pin.Logic_Pin_Input.split(",")[i].strip())
                self.log(f"Second pin number from Logic_Pin_Input: {second_pin_number}", "DEBUG")
            except ValueError:
                text = f"Invalid Logic_Pin_Input '{pin.Logic_Pin_Input}': Must be a pin number"
                self.log(text, "ERROR")
                return (0.0, False, text)
            
            # Step 4: Create "second Pin" object from pin table
            second_pin_row = None
            for row in pin_table_rows:
                if row["ID"] == str(second_pin_number) or row["ID"] == f"J1-{second_pin_number:02d}":
                    second_pin_row = row
                    break
            
            if not second_pin_row:
                text = f"Second pin {second_pin_number} not found in pin table"
                self.log(text, "ERROR")
                return (0.0, False, text)
            
            # Step 5: Check if second pin Power_Result is Pass and Power_Measured is <4V
            second_pin_power_result = second_pin_row.get("Power_Result", "No Result")
            second_pin_power_measured_str = second_pin_row.get("Power_Measured", "")
            
            try:
                second_pin_power_measured = float(second_pin_power_measured_str) if second_pin_power_measured_str else 0.0
            except ValueError:
                second_pin_power_measured = 0.0

            
            if second_pin_power_result != "Pass" :
                text = f"Second pin {second_pin_number} Power_Result is '{second_pin_power_result}' (expected 'Pass')"
                self.log(text, "WARNING")
                return (0.0, False, text)
            
            zero_voltage_threshold = self.settings.get('scale', {}).get('zero_voltage_threshold', 0.5)
            logic_voltage_threshold = self.settings.get('scale', {}).get('logic_voltage_threshold', 4.0)
            Analog_voltage_threshold = self.settings.get('scale', {}).get('Analog_voltage_threshold', 11.0)
            # check we connected Digital Input to retrun line  
            if "DI" in pin.Logic_Expected:
                self.log(f"we are connecting Digital input, the connection should be to RTN line ~0V")
                if pin.Power_Measured > logic_voltage_threshold or second_pin_power_measured > logic_voltage_threshold :
                    text = f"invalid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}V"
                    self.log(text, "WARNING")
                    return (0.0, False, text)
                    
                elif pin.Power_Measured > zero_voltage_threshold and second_pin_power_measured < zero_voltage_threshold :
                    text = f"valid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}'V"
                    self.log(text, "info")
                    
                elif second_pin_power_measured > zero_voltage_threshold and pin.Power_Measured < zero_voltage_threshold :
                    text = f"valid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}'V"
                    self.log(text, "info")
                    
                else:
                    text = f"invalid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}V"
                    self.log(text, "WARNING")
                    return (0.0, False, text)
            # check we connected Analog Input to return line  
            elif "AI" in pin.Logic_Expected:
                self.log(f"we are connecting Analog input, the connection should be to RTN line ~10V")
                if pin.Power_Measured > Analog_voltage_threshold or second_pin_power_measured > Analog_voltage_threshold :
                    text = f"invalid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}'V"
                    self.log(text, "WARNING")
                    return (0.0, False, text)
                
                elif pin.Power_Measured > zero_voltage_threshold and second_pin_power_measured < zero_voltage_threshold :
                    text = f"valid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}'V"
                    self.log(text, "info")
                    
                elif second_pin_power_measured > zero_voltage_threshold and pin.Power_Measured < zero_voltage_threshold :
                    text = f"valid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}'V"
                    self.log(text, "info")
                    
                else:
                    text = f"invalid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}V"
                    self.log(text, "WARNING")
                    return (0.0, False, text)
            else :
                text=f"Logic_Expected is {pin.Logic_Expected} which is not contain AI or DI - wrong logic pin input data"
                self.log(text, "WARNING")
                return (0.0, False, text)

            
            # Step 6: Convert second pin to bit pattern and set mux matrix (system B)
            second_pair_num, second_voltage_pin_key, second_voltage_pin_b_key, second_pullup_pin_key, second_card_enable_a_key, second_card_enable_b_key, second_relay_enable_a_key, second_relay_enable_b_key = get_pin_pair_info_controlino(second_pin_number)
            
            try:
                second_bits = connector_pin_to_bits(second_pin_number, "b")
                success = set_mux_bits(second_bits, second_pin_number, self.pin_map, self.hardware, self.settings, self.log)
                
                if not success:
                    text = f"Failed to set mux bits for second pin {second_pin_number}"
                    self.log(text, "ERROR")
                    return (0.0, False, text)
                
            except Exception as e:
                text = f"Error in Logic test setting mux for second pin {second_pin_number}: {str(e)}"  
                self.log(text, "ERROR")
                return (0.0, False, text)
            
            # Step 7: Activate the two proper relays for pin and second pin
            relay_ports = self.pin_map.get('R', {})
            
            relay_a_name = self.board_config.get(relay_enable_a_key, 'R0')
            relay_a_pin = relay_ports.get(relay_a_name)
            
            relay_b_name = self.board_config.get(second_relay_enable_b_key, 'R1')
            relay_b_pin = relay_ports.get(relay_b_name)
            
            if relay_a_pin is None:
                text = f"Relay A pin {relay_a_name} not found in pin map"
                self.log(text, "ERROR")
                return (0.0, False, f"Error: {text}")
            
            if relay_b_pin is None:
                text = f"Relay B pin {relay_b_name} not found in pin map"
                self.log(text, "ERROR")
                return (0.0, False, f"Error: {text}")
            
            self.log(f"Activating relay A {relay_a_name} (pin {relay_a_pin}) for pin {pin_number}", "INFO")
            self.hardware.digital_write(relay_a_pin, True)
            
            self.log(f"Activating relay B {relay_b_name} (pin {relay_b_pin}) for second pin {second_pin_number}", "INFO")
            self.hardware.digital_write(relay_b_pin, True)
            
            # Wait for relays to stabilize
            stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
            time.sleep(stabilize_delay)
            
            # Step 8: Parse Logic_Expected data (format: "C2_DI13_1" -> Card=2, DI=13, ExpectedState=1)
            if not hasattr(pin, 'Logic_Expected') or not pin.Logic_Expected or pin.Logic_Expected.strip().lower() == "none":
                text = f"No Logic_Expected specified for pin {pin_number} - skipping verification"
                self.log(text, "WARNING")
                # Deactivate relays
                self.hardware.digital_write(relay_a_pin, False)
                self.hardware.digital_write(relay_b_pin, False)
                clear_mux_bits(self.pin_map, self.hardware, self.log)
                return (0.0, False, text)
            

            # Parse Logic_cpmmand  for DO if exsit and operate  (format: "C2_DO13_1" or similar)
            if "_DO" in pin.Logic_Command:
                card, event_type, event_num, event_value = parse_event_string(pin.Logic_Command.split(",")[i])
                success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=bool(event_value))
                self.log(f"active: Set Card {card} DO{event_num} to {event_value}: {'Success' if success else 'Failed'}", "INFO")
                # Wait for signal to stabilize
                stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
                time.sleep(stabilize_delay)
                # Verify the output was set correctly
                verify_success, verify_msg = verify_card_output(
                    self.card_manager, card, event_type, event_num, event_value, 
                    tolerance, self.log
                )
                if not verify_success:
                                    # Deactivate relays
                    self.hardware.digital_write(relay_a_pin, False)
                    self.hardware.digital_write(relay_b_pin, False)
                    clear_mux_bits(self.pin_map, self.hardware, self.log)
                    text = f"Error: Invalid Logic_command operate - the output card {card} DO{event_num}  value{event_value} not set correctly: {verify_msg}"
                    self.log(text, "ERROR")
                    return (0.0, False, text)

            # Parse Logic_Expected for DI control (format: "C2_DI13_1" or similar)
            card, event_type, event_num, event_value = parse_event_string(pin.Logic_Expected.split(",")[i])            

            if card is None or event_type is None :
                text = f"Failed to parse Logic_Expected '{pin.Logic_Expected}': Expected format 'C#_DI##_#' or 'C#_AI##_#'"
                self.log(text, "ERROR")
                # Deactivate relays
                self.hardware.digital_write(relay_a_pin, False)
                self.hardware.digital_write(relay_b_pin, False)
                clear_mux_bits(self.pin_map, self.hardware, self.log)
                return (0.0, False, text)
            
            
            
            # Step 9: Read  status from card
            try:
                if "DI" in pin.Logic_Expected:
                    expected_state_bool = bool(event_value)
                    self.log(f"Parsed Logic_Expected: Card={card}, DI={event_num}, Expected={'HIGH' if expected_state_bool else 'LOW'}", "INFO")
                    di_status = self.card_manager.get_digital_input(card_id=card, di_number=event_num)
                    status_str = "HIGH" if di_status else "LOW"
                    self.log(f"measured -> Card {card} DI{event_num} status: {status_str}", "INFO")
                    
                elif  "AI" in pin.Logic_Expected:
                    self.log(f"Parsed Logic_Expected: Card={card}, AI={event_num}, Expected={event_value}", "INFO")
                    ai_status = self.card_manager.get_analog_input(card_id=card, ai_number=event_num)
                    self.log(f"measured -> Card {card} AI{event_num} Voltage : {ai_status}", "INFO")
                else:
                    text = f"Logic_Expected '{pin.Logic_Expected}' does not specify DI or AI type"
                    self.log(text, "ERROR")
                    # Deactivate relays
                    self.hardware.digital_write(relay_a_pin, False)
                    self.hardware.digital_write(relay_b_pin, False)
                    clear_mux_bits(self.pin_map, self.hardware, self.log)
                    return (0.0, False, text)
                
            except Exception as e:
                text = f"Error in Logic test reading DI{event_num} from card {card}: {str(e)}"
                self.log(text, "ERROR")
                # Deactivate relays before returning
                self.hardware.digital_write(relay_a_pin, False)
                self.hardware.digital_write(relay_b_pin, False)
                clear_mux_bits(self.pin_map, self.hardware, self.log)
                return (0.0, False, text)
            
            if is_simulation:
                self.log(f"workingin in simulation mode the tatus against Logic_Expected are good", "DEBUG")


            # Step 10: Check the read status against Logic_Expected
            if "DI" in pin.Logic_Expected:
                if is_simulation:
                    di_status = expected_state_bool
               
                status_match = (di_status == expected_state_bool)
            elif  "AI" in pin.Logic_Expected:    
                if is_simulation:
                    ai_status = event_value
                
                status_match = (abs(ai_status - event_value)<tolerance)
            

            # Step 11: Deactivate relay cards
            self.hardware.digital_write(relay_a_pin, False)
            self.hardware.digital_write(relay_b_pin, False)
            self.log(f"Deactivated relays {relay_a_name} and {relay_b_name}", "DEBUG")
            
            # Clear mux bits
            clear_mux_bits(self.pin_map, self.hardware, self.log)
            
            # Parse Logic_cpmmand  for DO if exsit and Deactivate it   (format: "C2_DO13_1" or similar)
            if pin.Logic_Command is not "" and pin.Logic_Command is not None:
                card, event_type, event_num, event_value = parse_event_string(pin.Logic_Command.split(",")[i])
                success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
                event_value = False
                self.log(f"active: Set Card {card} DO{event_num} to False: {'Success' if success else 'Failed'}", "INFO")
                # Wait for signal to stabilize
                stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
                time.sleep(stabilize_delay)
                # Verify the output was set correctly
                verify_success, verify_msg = verify_card_output(
                    self.card_manager, card, event_type, event_num, event_value, 
                    tolerance, self.log
                )
                if not verify_success:
                                    # Deactivate relays
                    self.hardware.digital_write(relay_a_pin, False)
                    self.hardware.digital_write(relay_b_pin, False)
                    clear_mux_bits(self.pin_map, self.hardware, self.log)
                    text = f"Error: Invalid Logic_command deactivate - the output card {card} DO{event_num} value {event_value} not deactivated correctly: {verify_msg}"
                    self.log(text, "ERROR")
                    return (0.0, False, text)



            # Step 12: Return result based on status match
            if "DI" in pin.Logic_Expected:
                if status_match:
                    self.log(f"Logic test PASSED: DI{event_num} is {status_str}, expected {'HIGH' if expected_state_bool else 'LOW'}", "SUCCESS")
                    Overallsuccess = True
                else:
                    self.log(f"Logic test FAILED: DI{event_num} is {status_str}, expected {'HIGH' if expected_state_bool else 'LOW'}", "WARNING")
                    Overallsuccess = False
            elif "AI" in pin.Logic_Expected:
                if status_match:
                    self.log(f"Logic test PASSED: AI{event_num} is {ai_status}, expected {event_value}", "SUCCESS")
                    Overallsuccess = True
                else:
                    self.log(f"Logic test FAILED: DI{event_num} is {ai_status}, expected {event_value}", "WARNING")
                    Overallsuccess = False

                
        if Overallsuccess:
            return (0.0, True, "Logic test PASSED")
        else:
            return (0.0, False, "Logic test FAILED")
    
    def relay_fuse_test(self, first_relay: str, second_relay: str, pullup_pin: str, voltage_measure_pin1: str, voltage_measure_pin2: str) -> tuple[str, bool]:
        """
        Relay fuse test.
        
        Test Procedure:
        1. Disable all cards - use the enable_cards() with no input
        2. Activate first_relay and second_relay
        3. Activate pullup_pin
        4. Wait for signal stabilization
        5. Measure voltage on voltage_measure_pin1, voltage_measure_pin2
        6. Status check that the voltage_measure_pin1, voltage_measure_pin2 are the same
        7. Deactivate pullup_pin (set LOW) and deactivate first_relay, second_relay
        8. Clear mux bits
        9. Return status of the compare
        
        Args:
            first_relay: Name of first relay pin (e.g., 'enable_Relay_pin_1_A')
            second_relay: Name of second relay pin (e.g., 'enable_Relay_pin_1_B')
            pullup_pin: Name of pullup pin (e.g., 'pullup_pins_pin_pair1')
            voltage_measure_pin1: Name of first voltage measurement pin (e.g., 'voltage_measure_pin_pair1')
            voltage_measure_pin2: Name of second voltage measurement pin (e.g., 'voltage_measure_pin_pair2')
            
        Returns:
            Tuple of (message, status):
                - message: Result message string
                - status: True if test passed, False otherwise
        """
        
        
        self.log("Starting Relay Fuse Test...", "INFO")
        
        # Get tolerance from settings (default 0.5V)
        tolerance = self.settings.get('Test', {}).get('voltage_tolerance', 0.5)
        
        try:
            # Step 1: Disable all cards
            enable_cards([], self.board_config, self.pin_map, self.hardware, self.log)
            self.log("All cards disabled", "DEBUG")
            
            # Step 2: Activate relay pins
            digital_ports = self.pin_map.get('D', {})
            relay_ports = self.pin_map.get('R', {})

            relay_1a_name = self.board_config.get(first_relay, None)
            relay_1b_name = self.board_config.get(second_relay, None)
            
            if not relay_1a_name or not relay_1b_name:
                error_msg = f"Relay pins not found in board configuration: {first_relay}, {second_relay}"
                self.log(error_msg, "ERROR")
                return (f"FAIL: {error_msg}", False)
            
            relay_1a_pin = relay_ports.get(relay_1a_name)
            relay_1b_pin = relay_ports.get(relay_1b_name)
            
            if relay_1a_pin is None or relay_1b_pin is None:
                error_msg = f"Relay pins not found in pin map: {relay_1a_name}, {relay_1b_name}"
                self.log(error_msg, "ERROR")
                return (f"FAIL: {error_msg}", False)
            
            self.log(f"Activating relay pins: {relay_1a_name} (pin {relay_1a_pin}), {relay_1b_name} (pin {relay_1b_pin})", "DEBUG")
            self.hardware.digital_write(relay_1a_pin, True)
            self.hardware.digital_write(relay_1b_pin, True)
            
            # Step 3: Activate pullup pin
            pullup_pin_name = self.board_config.get(pullup_pin, None)
            
            if not pullup_pin_name:
                error_msg = f"Pullup pin not found in board configuration: {pullup_pin}"
                self.log(error_msg, "ERROR")
                # Cleanup
                self.hardware.digital_write(relay_1a_pin, False)
                self.hardware.digital_write(relay_1b_pin, False)
                return (f"FAIL: {error_msg}", False)
            
            pullup_pin_physical = digital_ports.get(pullup_pin_name)
            
            if pullup_pin_physical is None:
                error_msg = f"Pullup pin not found in pin map: {pullup_pin_name}"
                self.log(error_msg, "ERROR")
                # Cleanup
                self.hardware.digital_write(relay_1a_pin, False)
                self.hardware.digital_write(relay_1b_pin, False)
                return (f"FAIL: {error_msg}", False)
            
            self.log(f"Activating pullup pin: {pullup_pin_name} (pin {pullup_pin_physical})", "DEBUG")
            self.hardware.digital_write(pullup_pin_physical, True)
            
            # Step 4: Wait for signal stabilization
            stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
            time.sleep(stabilize_delay)
            
            # Step 5: Measure voltages on both pairs
            analog_ports = self.pin_map.get('A', {})
            
            voltage_pin_1_name = self.board_config.get(voltage_measure_pin1, None)
            voltage_pin_2_name = self.board_config.get(voltage_measure_pin2, None)
            
            if not voltage_pin_1_name or not voltage_pin_2_name:
                error_msg = f"Voltage measurement pins not found in board configuration: {voltage_measure_pin1}, {voltage_measure_pin2}"
                self.log(error_msg, "ERROR")
                # Cleanup
                self.hardware.digital_write(pullup_pin_physical, False)
                self.hardware.digital_write(relay_1a_pin, False)
                self.hardware.digital_write(relay_1b_pin, False)
                return (f"FAIL: {error_msg}", False)
            
            voltage_pin_1 = analog_ports.get(voltage_pin_1_name)
            voltage_pin_2 = analog_ports.get(voltage_pin_2_name)
            
            if voltage_pin_1 is None or voltage_pin_2 is None:
                error_msg = f"Voltage pins not found in pin map: {voltage_pin_1_name}, {voltage_pin_2_name}"
                self.log(error_msg, "ERROR")
                # Cleanup
                self.hardware.digital_write(pullup_pin_physical, False)
                self.hardware.digital_write(relay_1a_pin, False)
                self.hardware.digital_write(relay_1b_pin, False)
                return (f"FAIL: {error_msg}", False)
            
            self.log(f"Measuring voltage on {voltage_pin_1_name} (pin {voltage_pin_1})", "DEBUG")
            voltage_1 = self.measurer.measure_voltage(voltage_pin_1)
            
            self.log(f"Measuring voltage on {voltage_pin_2_name} (pin {voltage_pin_2})", "DEBUG")
            voltage_2 = self.measurer.measure_voltage(voltage_pin_2)
            
            self.log(f"Measured voltages: {voltage_pin_1_name}={voltage_1:.3f}V, {voltage_pin_2_name}={voltage_2:.3f}V", "INFO")
            
            # Step 6: Compare voltages
            voltage_diff = abs(voltage_1 - voltage_2)
            voltages_match = voltage_diff <= tolerance
            
            status_msg = f"Voltage difference: {voltage_diff:.3f}V (tolerance: {tolerance}V)"
            self.log(status_msg, "INFO")
            
            # Step 7: Deactivate all pins
            self.log("Deactivating pullup and relay pins", "DEBUG")
            self.hardware.digital_write(pullup_pin_physical, False)
            self.hardware.digital_write(relay_1a_pin, False)
            self.hardware.digital_write(relay_1b_pin, False)
            time.sleep(stabilize_delay)
            
            # Step 8: Clear mux bits
            clear_mux_bits(self.pin_map, self.hardware, self.log)
            
            # Step 9: Return status
            if voltages_match:
                result = f"PASS: Relay fuse test successful.fuse is intact,relays  {relay_1a_name} and {relay_1a_name} are operational, analogs {voltage_pin_1_name}, {voltage_pin_2_name} are operational, pullup {pullup_pin_name} is operational."
                self.log(result, "SUCCESS")
                status = True
            else:
                result = f"FAIL: Relay fuse test failed. {status_msg} some thing in the configuration of {relay_1a_pin, relay_1b_pin, voltage_pin_1_name, voltage_pin_2_name, pullup_pin_name} is not operational."
                self.log(result, "WARNING")
                status = False
            
            return (result, status)
            
        except Exception as e:
            error_msg = f"Error during relay fuse test: {str(e)}"
            self.log(error_msg, "ERROR")
            # Attempt cleanup
            try:
                clear_mux_bits(self.pin_map, self.hardware, self.log)
            except:
                pass
            return (f"FAIL: {error_msg}", False)
    
    def run_i_bit_test(self) -> None:
        """
        Run I_Bit test (relay fuse tests + short circuit test).
        This function is intended to be run in a separate thread.
        """
        try:
            pair1_test_results, pair1_test_status = self.relay_fuse_test(
                "enable_Relay_pin_1_A", "enable_Relay_pin_1_B", 
                "pullup_pins_pin_pair1", "voltage_measure_pin_pair1", "voltage_measure_pin_pair1_B"
            )
            pair2_test_results, pair2_test_status = self.relay_fuse_test(
                "enable_Relay_pin_2_A", "enable_Relay_pin_2_B", 
                "pullup_pins_pin_pair2", "voltage_measure_pin_pair2", "voltage_measure_pin_pair2_B"
            )
            pair3_test_results, pair3_test_status = self.relay_fuse_test(
                "enable_Relay_pin_3_A", "enable_Relay_pin_3_B", 
                "pullup_pins_pin_pair3", "voltage_measure_pin_pair3", "voltage_measure_pin_pair3_B"
            )
            pair4_test_results, pair4_test_status = self.relay_fuse_test(
                "enable_Relay_pin_4_A", "enable_Relay_pin_4_B", 
                "pullup_pins_pin_pair4", "voltage_measure_pin_pair4", "voltage_measure_pin_pair4_B"
            )

            if pair1_test_status and pair2_test_status and pair3_test_status and pair4_test_status:
                self.log(f"I_Bit test complete: All relay pairs PASSED", "SUCCESS")
            else:
                self.log(f"I_Bit test complete: Some relay pairs FAILED", "WARNING")
            
            test_results = self.short_circuit_test()
            passed_count = sum(1 for _, passed, _ in test_results if passed)
            total_count = len(test_results)
            self.log(
                f"I_Bit test complete: {passed_count}/{total_count} pins PASSED",
                "SUCCESS" if passed_count == total_count else "WARNING"
            )
        except Exception as e:
            error_msg = f"Error during I_Bit test: {str(e)}"
            self.log(error_msg, "ERROR")
    
    def short_circuit_test(self) -> list[tuple[list[float], bool, list[dict]]]:
        """
        Short circuit test for all pins.
        
        Test Procedure:
        1. For each pin 1-50: Get pair info (voltage_measure_pin, pullup_pin, card enables, etc.) for connector pin
        2. Convert connector pin number to bit pattern and set mux matrix (D0-D15) - system A
        3. Activate pullup_pin_key (set HIGH)
        4. Wait for signal stabilization
        5. Measure voltage
        6. Run measure_all_pins_system_b(pin_number, measured_voltage) to verify routing
        7. Deactivate pullup_pin_key (set LOW)
        8. Clear mux bits
        9. Return result (array of test results from measure_all_pins_system_b)
        
        Returns:
            list[tuple[list[float], bool, list[dict]]]: Array of 50 test results, each containing:
                - list[float]: Voltage measurements for all 50 pins
                - bool: Pass/fail status for that test iteration
                - list[dict]: Failed pins with details {'pin': N, 'measured': V, 'expected': V}
        """
        
        
        
        test_results = []
        voltage_scale = 1
        
        self.log("Starting Short Circuit Test for all pins (1-50)...", "INFO")
        
        for pin_number in range(1, 51):
            if not self.running_ibit:
                self.log("I_Bit test stopped by user", "WARNING")
                break
            
            try:
                self.log(f"Testing pin {pin_number} for short circuits...", "INFO")
                
                # Step 1: Get pair info
                pair_num, voltage_pin_key, voltage_pin_b_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(pin_number)
                
                # Get actual pin names from board config
                voltage_pin_name = self.board_config.get(voltage_pin_key, 'A0')
                pullup_pin_name = self.board_config.get(pullup_pin_key, 'D20')
                
                # Step 2: Convert connector pin to bit representation using system A and set mux matrix
                bits = connector_pin_to_bits(pin_number, "a")
                success = set_mux_bits(bits, pin_number, self.pin_map, self.hardware, self.settings, self.log)
                
                if not success:
                    self.log(f"on short circut test  - Failed to set mux bits for pin {pin_number}", "ERROR")
                    test_results.append(([], False, []))
                    continue
                
                # Step 3: Activate pullup pin (set HIGH)
                digital_ports = self.pin_map.get('D', {})
                pullup_physical_pin = digital_ports.get(pullup_pin_name)
                
                if pullup_physical_pin is None:
                    self.log(f"on short circut test - Pullup pin {pullup_pin_name} not found in pin map for pin {pin_number}", "ERROR")
                    test_results.append(([], False, []))
                    continue
                
                self.log(f"Activating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) HIGH", "DEBUG")
                self.hardware.digital_write(pullup_physical_pin, True)
                
                # Step 4: Wait for signal stabilization
                stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
                time.sleep(stabilize_delay)
                
                # Step 5: Measure voltage
                analog_ports = self.pin_map.get('A', {})
                analog_port = analog_ports.get(voltage_pin_name)
                
                if analog_port is None:
                    self.log(f"in short circuit test - Analog pin {voltage_pin_name} not found in pin map for pin {pin_number}", "ERROR")
                    self.hardware.digital_write(pullup_physical_pin, False)
                    test_results.append(([], False, []))
                    continue
                
                try:
                    voltage_degredation = self.settings.get('scale', {}).get('voltage_degredation', 3.0)
                    measured_voltage = self.measurer.measure_voltage(analog_port) * voltage_scale - voltage_degredation
                    self.log(f"in card  A at Pin {pin_number} voltage with pullup: {measured_voltage:.3f}V", "DEBUG")
                except Exception as e:
                    self.log(f"in short circut test  - Measurement error on pin {pin_number}: {str(e)}", "ERROR")
                    self.hardware.digital_write(pullup_physical_pin, False)
                    test_results.append(([], False, []))
                    continue
                
                # Step 6: Run measure_all_pins_system_b to verify routing

                voltage_measurements, test_passed, failed_pins = self.measure_all_pins_system_b(pin_number, measured_voltage)
                test_results.append((voltage_measurements, test_passed, failed_pins))
                
                # Step 7: Deactivate pullup pin (set LOW)
                self.hardware.digital_write(pullup_physical_pin, False)
                self.log(f"Deactivating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) LOW", "DEBUG")
                
                # Step 8: Clear mux bits before next pin
                clear_mux_bits(self.pin_map, self.hardware, self.log)
                
            except Exception as e:
                self.log(f"Error in short circuit test processing pin {pin_number}: {str(e)}", "ERROR")
                test_results.append(([], False, []))
        
        # Summary
        passed_count = sum(1 for _, passed, _ in test_results if passed)
        total_count = len(test_results)
        self.log(f"Short Circuit Test complete: {passed_count}/{total_count} pins PASSED", "SUCCESS" if passed_count == total_count else "WARNING")
        
        return test_results
    
    def measure_all_pins_system_b(self, pin_number: int, voltage: float) -> tuple[list[float], bool, list[dict]]:
        """
        System B measurement for loop run with validation.
        
        Test Procedure:
        1. For each pin 1-50: Get pair info (voltage_measure_pin, pullup_pin, card enables, etc.) for connector pin
        2. Convert connector pin number to bit pattern and set mux matrix (D0-D15) - system B
        3. Measure voltage on pair-specific analog pin
        4. Validate measurements:
           - Pin matching pin_number should measure ~voltage (within tolerance)
           - All other pins should measure ~0V (within tolerance)
        5. Return result (array of 50 voltage measurement values + pass/fail status + failed pins list)
        
        Args:
            pin_number: The pin number that should show the voltage (1-50)
            voltage: Expected voltage value on the specified pin
            
        Returns:
            tuple[list[float], bool, list[dict]]: 
                - Array of 50 final voltage readings in volts
                - True if all measurements pass validation, False otherwise
                - List of failed pins with format: [{'pin': int, 'measured': float, 'expected': float}, ...]
        """
        
        
        
        voltage_measurements = []
        failed_pins = []  # Track failed pins with their measurements
        voltage_scale = 1
        tolerance = self.settings.get('Test', {}).get('voltage_degredation', 3.0)
        all_tests_passed = True
        
        self.log(f"Starting System B measurement for all pins (1-50)... Expected: Pin {pin_number} = {voltage}V, Others = ~0V", "INFO")
        
        for current_pin in range(1, 51):
            try:
                # Step 1: Get pair info
                pair_num, voltage_pin_key, voltage_pin_b_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(current_pin)
                
                # Get actual pin names from board config
                voltage_pin_name = self.board_config.get(voltage_pin_b_key, 'A1')
                
                # Step 2: Convert connector pin to bit representation using system B and set mux matrix
                bits = connector_pin_to_bits(current_pin, "b")
                success = set_mux_bits(bits, current_pin, self.pin_map, self.hardware, self.settings, self.log)
                
                if not success:
                    self.log(f"Failed to set mux bits for pin {current_pin}", "WARNING")
                    voltage_measurements.append(0.0)
                    failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': voltage if current_pin == pin_number else 0.0})
                    all_tests_passed = False
                    continue
                
                # Get physical analog port from pin map
                analog_ports = self.pin_map.get('A', {})
                analog_port = analog_ports.get(voltage_pin_name)
                
                self.log(f"Pin {current_pin}: Looking for {voltage_pin_name} in analog ports", "DEBUG")
                
                if analog_port is None:
                    self.log(f"Analog pin {voltage_pin_name} not found in pin map for pin {current_pin}", "WARNING")
                    voltage_measurements.append(0.0)
                    failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': voltage if current_pin == pin_number else 0.0})
                    all_tests_passed = False
                    continue
                
                self.log(f"Pin {current_pin}: Using analog port {analog_port} ({voltage_pin_name})", "INFO")
                
                # Step 3: Measure voltage
                try:
                    measured_voltage = self.measurer.measure_voltage(analog_port) * voltage_scale 
                    voltage_measurements.append(measured_voltage)
                    
                    # Step 4: Validate measurement
                    if current_pin == pin_number:
                        # This pin should measure ~voltage
                        voltage_diff = abs(measured_voltage - voltage)
                        if voltage_diff <= tolerance:
                            self.log(f"in measure all pins sys B -  Pin {pin_number} check Pin {current_pin}: {measured_voltage:.3f}V (PASS - expected {voltage}V)", "SUCCESS")
                        else:
                            self.log(f"in measure all pins sys B  - Pin {pin_number} check Pin {current_pin}: {measured_voltage:.3f}V (FAIL - expected {voltage}V, diff: {voltage_diff:.3f}V)", "WARNING")
                            failed_pins.append({'pin': current_pin, 'measured': measured_voltage, 'expected': voltage})
                            all_tests_passed = False
                    else:
                        # This pin should measure ~0V
                        if abs(measured_voltage) <= tolerance:
                            self.log(f"for Pin {pin_number} check Pin {current_pin}: {measured_voltage:.3f}V (PASS - expected ~0V)", "DEBUG")
                        else:
                            self.log(f"in measure all pins sys B - for Pin {pin_number} check Pin {current_pin}: {measured_voltage:.3f}V (FAIL - expected ~0V)", "WARNING")
                            failed_pins.append({'pin': current_pin, 'measured': measured_voltage, 'expected': 0.0})
                            all_tests_passed = False
                            
                except Exception as e:
                    self.log(f"in measure all pins sys B -Measurement error on pin {current_pin}: {str(e)}", "ERROR")
                    voltage_measurements.append(0.0)
                    failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': voltage if current_pin == pin_number else 0.0})
                    all_tests_passed = False
                
                # Clear mux bits before next pin
                clear_bits(bits, self.pin_map, self.hardware, self.log)
                
            except Exception as e:
                self.log(f"in measure all pins sys B -Error processing pin {current_pin}: {str(e)}", "ERROR")
                voltage_measurements.append(0.0)
                failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': voltage if current_pin == pin_number else 0.0})
                all_tests_passed = False
        
        result_msg = "SUCCESS" if all_tests_passed else "FAILED"
        if failed_pins:
            self.log(f"System B measurement complete: {len(voltage_measurements)} pins measured - {result_msg} - {len(failed_pins)} failures", "SUCCESS" if all_tests_passed else "WARNING")
        else:
            self.log(f"System B measurement complete: {len(voltage_measurements)} pins measured - {result_msg}", "SUCCESS" if all_tests_passed else "WARNING")
        return voltage_measurements, all_tests_passed, failed_pins

    def run_tests(self, selected_ids, all_rows, root, pin_table, on_test_complete):
        """
        Execute test sequence on selected pins.
        
        Args:
            selected_ids: List of selected pin IDs to test
            all_rows: All pin table rows
            root: Tkinter root for after() calls
            pin_table: Pin table view for updating results
            on_test_complete: Callback function when tests complete
        """
        from hw_tester.hardware.pin import Pin
        
        
        if self.settings.get('Debug', {}).get('mode', False):
            self.wait_debug(10, "active")
        
        for idx, pin_id in enumerate(selected_ids):
            if not self.running:
                break
            
            try:
                # Step 1: Get row data for this pin
                pin_row = None
                for row in all_rows:
                    if row["ID"] == pin_id:
                        pin_row = row
                        break
                
                if not pin_row:
                    self.log(f"running test - Pin {pin_id} not found in table", "ERROR")
                    continue
                
                # Step 2: Create Pin object from row data
                # Handle empty strings properly - don't convert to 0.0
                power_exp_str = pin_row.get("Power_Expected", "").strip()
                pullup_exp_str = pin_row.get("PullUp_Expected", "").strip()
                
                power_exp_val = float(power_exp_str) if power_exp_str else 0.0
                pullup_exp_val = float(pullup_exp_str) if pullup_exp_str else 0.0
                
                pin = Pin(
                    Id=pin_row["ID"],
                    Connect=pin_row.get("Connect", ""),
                    Discrete_Name=pin_row.get("Discrete_Name", ""),
                    Signal_Name=pin_row.get("Signal_Name", ""),
                    Plug=pin_row.get("Plug", ""),
                    Pin=pin_row.get("Pin", ""),
                    Power_Expected=power_exp_val,
                    Power_Measured=0.0,
                    Power_Result=TestResult.NO_RESULT,
                    PullUp_Expected=pullup_exp_val,
                    PullUp_Measured=0.0,
                    PullUp_Result=TestResult.NO_RESULT,
                    Power_Input=pin_row.get("Power_Input", ""),
                    PullUp_Input=pin_row.get("PullUp_Input", ""),
                    Logic_Pin_Input=pin_row.get("Logic_Pin_Input", ""),
                    Logic_Command=pin_row.get("Logic_Command", ""),
                    Logic_Expected=pin_row.get("Logic_Expected", ""),
                    Logic_DI_Result=TestResult.NO_RESULT
                )
                
                self.log(f"Processing pin number {pin.Id} - Type: {pin.Discrete_Name}", "INFO")
                
                # Step 3: Determine which tests to run based on whether values are provided (not empty)
                # Empty values in Excel mean the test should be skipped
                # 0.0 is a valid measurement, so we check if Power_Expected/PullUp_Expected were actually set
                power_expected_str = pin_row.get("Power_Expected", "").strip()
                pullup_expected_str = pin_row.get("PullUp_Input", "").strip()
                logic_Expected_str = pin_row.get("Logic_Expected", "").strip()
                logic_Command_str = pin_row.get("Logic_Command", "").strip()

                run_power_test = (power_expected_str != "" and power_expected_str != "-")
                run_pullup_test = (pullup_expected_str != "" and pullup_expected_str != "-")
                run_logic_test = (logic_Expected_str != "" and logic_Expected_str != "-")
                
                # Run tests
                # Clear mux bits before setting new ones
                clear_mux_bits(self.pin_map, self.hardware, self.log)
                if run_power_test:
                    
                    self.log(f"Running Power Test for pin {pin.Id}", "INFO")
                    power_voltage, power_success, power_message = self.run_power_test(pin)
                    # Clear mux bits before setting new ones
                    clear_mux_bits(self.pin_map, self.hardware, self.log)
                    pin.Power_Measured = power_voltage
                    pin.Power_Result = power_success
                    self.log(
                        f"Power Test: Expected={pin.Power_Expected}V, Measured={pin.Power_Measured}V, Result={'PASS' if pin.Power_Result else 'FAIL'} - {power_message}",
                        "SUCCESS" if pin.Power_Result else "WARNING"
                    )
                    # Update table immediately after power test
                    # Capture values to avoid lambda closure issues
                    pin_id_local = pin.Id
                    power_measured = f"{pin.Power_Measured:.2f}"
                    power_result = "Pass" if pin.Power_Result else "Fail"
                    power_reason = power_message
                    root.after(0, lambda pid=pin_id_local, pm=power_measured, pr=power_result, r=power_reason: 
                        pin_table.update_row(pid, {
                            "Power_Measured": pm,
                            "Power_Result": pr,
                            "Power_Result_Reason": r
                        }))
                
                if run_pullup_test:
                    if pin.Power_Result == True and pin.Power_Expected == 0.0: # the basic condition to run pullup test is that power test passed and expected power is 0V
                        self.log(f"Running PullUp Test for {pin.Id}", "INFO")
                        pullup_voltage, pullup_success, pullup_message = self.run_pullup_test(pin)
                        # Clear mux bits before setting new ones
                        clear_mux_bits(self.pin_map, self.hardware, self.log)
                        pin.PullUp_Measured = pullup_voltage
                        pin.PullUp_Result = pullup_success
                        self.log(
                            f"PullUp Test: Expected={pin.PullUp_Expected}V, Measured={pin.PullUp_Measured}V, Result={'PASS' if pin.PullUp_Result else 'FAIL'} - {pullup_message}",
                            "SUCCESS" if pin.PullUp_Result else "WARNING"
                        )
                        # Update table immediately after pullup test
                        # Capture values to avoid lambda closure issues
                        pin_id_local = pin.Id
                        pullup_measured = f"{pin.PullUp_Measured:.2f}"
                        pullup_result = "Pass" if pin.PullUp_Result else "Fail"
                        pullup_reason = pullup_message
                        root.after(0, lambda pid=pin_id_local, pum=pullup_measured, pur=pullup_result, r=pullup_reason:
                            pin_table.update_row(pid, {
                                "PullUp_Measured": pum,
                                "PullUp_Result": pur,
                                "PullUp_Result_Reason": r
                            }))
                    elif pin.Power_Result == True and pin.Power_Expected != 0.0:
                        self.log(
                            f"PullUp Test: in Pin ID {pin.Id} the define pullup_expected ={pin.PullUp_Expected}V, not meet the pull up bascic condition  V= 0.0 V, so skip pullup test","WARNING"
                        )
                    elif pin.Power_Result == False:
                        self.log(
                            f"PullUp Test: in Pin ID {pin.Id} Power test failed, so skip pullup test","WARNING"
                        )
                
                if run_logic_test:
                    logic_result = self.run_logic_test(pin, all_rows)
                    Logic_test_voltage,Logic_test_result,logic_test_message = logic_result
                    pin.Logic_DI_Result = Logic_test_result
                    self.log(
                            f"Logic Test: Result={'PASS' if pin.Logic_DI_Result else 'FAIL'} - {logic_test_message}",
                            "SUCCESS" if pin.Logic_DI_Result else "WARNING"
                        )
                        # Update table immediately after logic test
                        # Capture values to avoid lambda closure issues
                    pin_id_local = pin.Id
                    logic_result_str = "Pass" if pin.Logic_DI_Result else "Fail"
                    logic_reason = logic_test_message
                    root.after(0, lambda pid=pin_id_local, lr=logic_result_str, r=logic_reason:
                            pin_table.update_row(pid, {
                                "Logic_DI_Result": lr,
                                "Logic_DI_Result_Reason": r
                            }))
            except ValueError as e:
                error_msg = f"running test - Pin data error for {pin_id}: {str(e)}"
                self.log(error_msg, "ERROR")
            except Exception as e:
                error_msg = f"running test - Unexpected error processing {pin_id}: {str(e)}"
                self.log(error_msg, "ERROR")
        
        root.after(0, on_test_complete)
 