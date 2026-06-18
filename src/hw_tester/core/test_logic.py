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
    clear_mux_bits,
)

if TYPE_CHECKING:
    from hw_tester.hardware.pin import Pin


def logic_test(test_handle, pin: "Pin", pin_table_rows: list) -> tuple[float, bool, str]:
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

    self = test_handle

    Overallsuccess = False
    is_simulation = self.settings.get('Board', {}).get('simulation', True)
    text = ""

    if is_simulation:
        # Simulation mode - return fixed value based on expected
        time.sleep(0.2)  # Simulate measurement delay
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

    if get_debug_setting(self.settings, "logic_test"):
        self.log(f"start Logic test for pin {pin_number}", "INFO")
        self.wait_debug(400, "active")
    if not success:
        text = f"Failed to set mux bits for pin {pin_number}"
        self.log(text, "ERROR")
        return (0.0, False, text)

    # Step 3: Read the pin number from Logic_Pin_Input (second pin)
    if not hasattr(pin, 'Logic_Pin_Input') or not pin.Logic_Pin_Input or pin.Logic_Pin_Input.strip().lower() == "none":
        text = f"No Logic_Pin_Input specified for pin {pin_number} - skipping logic test"
        self.log(text, "INFO")
        return (0.0, True, text)

    # this for loop is run on all the data in the Logic_Pin_Input field for each one of them make the test
    # this for loop is incase we will need to connect more than one pin as a second pin in the logic test, for example if we want to connect 2 DI pins to the same RTN line and check that both of them are LOW
    # for the 17 of june 26 we dont use more than one as the second pin 
    for i in range(len(pin.Logic_Pin_Input.split(","))):
        try:
            second_pin_number = int(pin.Logic_Pin_Input.split(",")[i].strip())
            self.log(f"Second pin number from Logic_Pin_Input: {second_pin_number}", "INFO")
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

        if get_debug_setting(self.settings, "logic_test"):
            self.wait_debug(420, "active")    
        # Step 5: Check if second pin Power_Result is Pass and Power_Measured is <4V
        second_pin_power_result = second_pin_row.get("Power_Result", "No Result")
        second_pin_power_measured_str = second_pin_row.get("Power_Measured", "")

        try:
            second_pin_power_measured = float(second_pin_power_measured_str) if second_pin_power_measured_str else 0.0
        except ValueError:
            second_pin_power_measured = 0.0

        if second_pin_power_result != "Pass":
            text = f"Second pin {second_pin_number} Power_Result is '{second_pin_power_result}' (expected 'Pass')"
            self.log(text, "WARNING")
            return (0.0, False, text)
        


        zero_voltage_threshold = self.settings.get('scale', {}).get('zero_voltage_threshold', 0.5)
        logic_voltage_threshold = self.settings.get('scale', {}).get('logic_voltage_threshold', 4.0)
        Analog_voltage_threshold = self.settings.get('scale', {}).get('Analog_voltage_threshold', 13.0)

        if "DI" in pin.Logic_Expected or "IE" in pin.Logic_Expected:
            self.log("we are connecting Digital input, the connection should be to RTN line ~0V")
            if pin.Power_Measured > logic_voltage_threshold or second_pin_power_measured > logic_voltage_threshold:
                text = f"invalid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}V"
                self.log(text, "WARNING")
                return (0.0, False, text)
            elif pin.Power_Measured > zero_voltage_threshold and second_pin_power_measured < zero_voltage_threshold:
                text = f"valid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}'V"
                self.log(text, "info")
            elif second_pin_power_measured > zero_voltage_threshold and pin.Power_Measured < zero_voltage_threshold:
                text = f"valid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}'V"
                self.log(text, "info")
            else:
                text = f"invalid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}V"
                self.log(text, "WARNING")
                return (0.0, False, text)
        elif "AI" in pin.Logic_Expected:
            self.log("we are connecting Analog input, the connection should be to  line ~10V")
            if pin.Power_Measured > Analog_voltage_threshold or second_pin_power_measured > Analog_voltage_threshold:
                text = f"invalid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}'V"
                self.log(text, "WARNING")
                return (0.0, False, text)
            elif pin.Power_Measured > 0 and second_pin_power_measured < Analog_voltage_threshold:
                text = f"valid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}'V"
                self.log(text, "info")
            elif second_pin_power_measured > 0 and pin.Power_Measured < Analog_voltage_threshold:
                text = f"valid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}'V"
                self.log(text, "info")
            else:
                text = f"invalid combination :Pin {pin_number} Power_Measured is '{pin.Power_Measured}'V  Second pin {second_pin_number} Power_Measured is '{second_pin_power_measured}'V"
                self.log(text, "WARNING")
                return (0.0, False, text)
        else:
            text = f"Logic_Expected is {pin.Logic_Expected} which is not contain AI or DI - wrong logic pin input data"
            self.log(text, "WARNING")
            return (0.0, False, text)

        # Step 6: Convert second pin to bit pattern and set mux matrix (system B)
        second_pair_num, second_voltage_pin_key, second_voltage_pin_b_key, second_pullup_pin_key, second_card_enable_a_key, second_card_enable_b_key, second_relay_enable_a_key, second_relay_enable_b_key = get_pin_pair_info_controlino(second_pin_number)

        try:
            second_bits = connector_pin_to_bits(second_pin_number, "b")
            success = set_mux_bits(second_bits, second_pin_number, self.pin_map, self.hardware, self.settings, self.log)

            if get_debug_setting(self.settings, "logic_test"):
                self.log(f"start Logic test for second pin {second_pin_number}", "INFO")
                self.wait_debug(450, "active")  
            if not success:
                text = f"Failed to set mux bits for second pin {second_pin_number}"
                self.log(text, "ERROR")
                return (0.0, False, text)
        except Exception as e:
            text = f"Error in Logic test setting mux for second pin {second_pin_number}: {str(e)}"
            self.log(text, "ERROR")
            return (0.0, False, text)

        # Step 8: Parse Logic_Expected data (format: "C2_DI13_1" -> Card=2, DI=13, ExpectedState=1)
        if not hasattr(pin, 'Logic_Expected') or not pin.Logic_Expected or pin.Logic_Expected.strip().lower() == "none":
            text = f"No Logic_Expected specified for pin {pin_number} - skipping verification"
            self.log(text, "WARNING")
            clear_mux_bits(self.pin_map, self.hardware, self.log)
            return (0.0, False, text)

        if "_DO" in pin.Logic_Command:
            card, event_type, event_num, event_value = parse_event_string(pin.Logic_Command.split(",")[i])
            success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=bool(event_value))
            self.log(f"active: Set Card {card} DO{event_num} to {event_value}: {'Success' if success else 'Failed'}", "INFO")
            stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
            time.sleep(stabilize_delay)
            verify_success, verify_msg = verify_card_output(
                self.card_manager, card, event_type, event_num, event_value,
                tolerance, self.log
            )
            if not verify_success:
                clear_mux_bits(self.pin_map, self.hardware, self.log)
                text = f"Error: Invalid Logic_command operate - the output card {card} DO{event_num}  value{event_value} not set correctly: {verify_msg}"
                self.log(text, "ERROR")
                return (0.0, False, text)

        card, event_type, event_num, event_value = parse_event_string(pin.Logic_Expected.split(",")[i])

        if card is None or event_type is None:
            text = f"Failed to parse Logic_Expected '{pin.Logic_Expected}': Expected format 'C#_DI##_#' or 'C#_AI##_#'"
            self.log(text, "ERROR")
            clear_mux_bits(self.pin_map, self.hardware, self.log)
            return (0.0, False, text)

        temp = self.card_manager.get_encoder_word(card_id=3, encoder_id=1, word_index=1)
        try:
            if "DI" in pin.Logic_Expected:
                expected_state_bool = bool(event_value)
                self.log(f"Parsed Logic_Expected: Card={card}, DI={event_num}, Expected={'HIGH' if expected_state_bool else 'LOW'}", "INFO")
                di_status = self.card_manager.get_digital_input(card_id=card, di_number=event_num)
                status_str = "HIGH" if di_status else "LOW"
                self.log(f"measured -> Card {card} DI{event_num} status: {status_str}", "INFO")
            elif "AI" in pin.Logic_Expected:
                self.log(f"Parsed Logic_Expected: Card={card}, AI={event_num}, Expected={event_value}", "INFO")
                ai_status = self.card_manager.get_analog_input(card_id=card, ai_number=event_num)
                self.log(f"measured -> Card {card} AI{event_num} Voltage : {ai_status}", "INFO")
            elif "IE" in pin.Logic_Expected:
                self.log(f"Parsed Logic_Expected: Card={card}, IE={event_num}, Expected={event_value}", "INFO")
                ie_status = self.card_manager.get_encoder_word(card_id=card, encoder_id=event_num, word_index=1)
                self.log(f"measured -> Card {card} IE{event_num} Value : {ie_status}", "INFO")
            else:
                text = f"Logic_Expected '{pin.Logic_Expected}' does not specify DI or AI type"
                self.log(text, "ERROR")
                clear_mux_bits(self.pin_map, self.hardware, self.log)
                return (0.0, False, text)
        except Exception as e:
            text = f"Error in Logic test reading DI{event_num} from card {card}: {str(e)}"
            self.log(text, "ERROR")
            clear_mux_bits(self.pin_map, self.hardware, self.log)
            return (0.0, False, text)

        if is_simulation:
            self.log(f"workingin in simulation mode the tatus against Logic_Expected are good", "DEBUG")

        if "DI" in pin.Logic_Expected:
            if is_simulation:
                di_status = expected_state_bool
            status_match = (di_status == expected_state_bool)
        elif "AI" in pin.Logic_Expected:
            if is_simulation:
                ai_status = event_value
            status_match = (abs(ai_status - event_value) < tolerance)
        else:
            if is_simulation:
                ie_status = event_value
            status_match = (ie_status == event_value)

        clear_mux_bits(self.pin_map, self.hardware, self.log)

        if pin.Logic_Command:
            card, event_type, event_num, event_value = parse_event_string(pin.Logic_Command.split(",")[i])
            success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
            event_value = False
            self.log(f"active: Set Card {card} DO{event_num} to False: {'Success' if success else 'Failed'}", "INFO")
            stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
            time.sleep(stabilize_delay)
            verify_success, verify_msg = verify_card_output(
                self.card_manager, card, event_type, event_num, event_value,
                tolerance, self.log
            )
            if not verify_success:
                clear_mux_bits(self.pin_map, self.hardware, self.log)
                text = f"Error: Invalid Logic_command deactivate - the output card {card} DO{event_num} value {event_value} not deactivated correctly: {verify_msg}"
                self.log(text, "ERROR")
                return (0.0, False, text)

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
                self.log(f"Logic test FAILED: AI{event_num} is {ai_status}, expected {event_value}", "WARNING")
                Overallsuccess = False
        else:
            if status_match:
                self.log(f"Logic test PASSED: IE{event_num} is {ie_status}, expected {event_value}", "SUCCESS")
                Overallsuccess = True
            else:
                self.log(f"Logic test FAILED: IE{event_num} is {ie_status}, expected {event_value}", "WARNING")
                Overallsuccess = False

    if Overallsuccess:
        return (0.0, True, "Logic test PASSED")
    return (0.0, False, "Logic test FAILED")
