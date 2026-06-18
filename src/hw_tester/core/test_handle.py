"""
Test Handler - Core test execution functions for HW Tester.
Contains all test procedures: power, pullup, logic, I-bit, relay/fuse, and short circuit tests.
"""
import time
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hw_tester.hardware.pin import Pin

from hw_tester.core.test_power import power_test
from hw_tester.core.test_pullUp import pullup_test
from hw_tester.core.test_logic import logic_test
from hw_tester.hardware.pin import TestResult
from hw_tester.hardware.controllino_io import connector_pin_to_bits
from hw_tester.utils.general import (
    parse_event_string,
    get_debug_setting,
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
    
    
    
    # def run_logic_test(self, pin: "Pin", pin_table_rows: list) -> tuple[float, bool, str]:
    #     return logic_test(self, pin, pin_table_rows)

    def relay_general_operate(self, operate:bool) -> bool:
         
        relay_ports = self.pin_map.get('R', {})
        Relay_general = self.board_config.get("enable_Relay_general", None)
        pin_Relay_general = relay_ports.get(Relay_general)

        if pin_Relay_general is None:
            error_msg = f"Relay pins not found in pin map: {pin_Relay_general}"
            self.log(error_msg, "ERROR")
            return (False)

        self.log(f"Activating relay pins: {pin_Relay_general} to {operate} ", "DEBUG")
        self.hardware.digital_write(pin_Relay_general, operate)

        # Step 4: Wait for relay stabilization
        stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
        time.sleep(stabilize_delay)
        return (True)

    
   
    def run_i_bit_test(self) -> None:
        """
        Run I_Bit test (relay fuse tests + short circuit test).
        This function is intended to be run in a separate thread.
        """
        is_simulation = self.settings.get('Board', {}).get('simulation', True)
        debug = get_debug_setting(self.settings, "Power_Test")

        ibit_A = self.measure_all_pins_system("a",4.0, is_simulation)
        ibit_B = self.measure_all_pins_system("b",4.0, is_simulation)
        passed_count = len(ibit_A[0]) + len(ibit_B[0])
        total_count = 100
        self.log(f"Ibit  Circuit Test complete: {passed_count}/{total_count} pins PASSED", "SUCCESS" if passed_count == total_count else "WARNING")
        
    
    def measure_all_pins_system(self, system: str, voltage: float, isSimulate: bool) -> tuple[list[float], bool, list[dict]]:
        """
        System measurement - loop run with validation.
        Test Procedure:
        1. For each pin 1-50 in system "System": Get pair info (voltage_measure_pin, pullup_pin, card enables, etc.) for connector pin
        2. Convert connector pin number to bit pattern and set mux matrix (D0-D15) - select the pin
        3. Measure voltage on pair-specific analog pin
        4. Validate measurements - pins should measure ~0V (within tolerance)
        5. Write result to log: "Pin (number) on system 'System' (mux address) Volt measurement (voltage) - pass/fail"
        6. Pullup activate
        7. Wait 1 sec
        8. Validate measurements - pins should measure input "Expected voltage" (within tolerance)
        9. Write result to log: "Pin (number) on system 'System' (mux address) Volt measurement (voltage) - pass/fail"
        10. Wait 1 sec - pullup deactivate, deselect the pin
        11. Return result (array of 50 voltage measurement values + pass/fail status + failed pins list)
        Args:
            system: "A" or "B"
            voltage: Expected voltage value on the specified pin
            isSimulate: If True, simulate measurements
        Returns:
            tuple[list[float], bool, list[dict]]: 
                - Array of 50 final voltage readings in volts
                - True if all measurements pass validation, False otherwise
                - List of failed pins with format: [{'pin': int, 'measured': float, 'expected': float}, ...]
        """
        voltage_measurements = []
        failed_pins = []
        voltage_scale = 1
        tolerance = self.settings.get('Test', {}).get('voltage_degredation', 3.0)
        pins_to_stabilize = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.5)
        all_tests_passed = True
        for current_pin in range(1, 51):
            if not self.running_ibit:
                self.log("I_Bit test stopped by user", "WARNING")
                break
            
            try:
                # Step 0: Clear mux bits before next pin
                clear_max= clear_mux_bits(self.pin_map, self.hardware, self.log)
                if not clear_max:
                    self.log(f"Failed to clear mux bits before testing pin {current_pin} on system {system}", "WARNING")
                    break

                # Step 1: Get pair info
                pair_num, voltage_pin_key, voltage_pin_b_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(current_pin)
                voltage_pin_name = self.board_config.get(voltage_pin_key if system.upper() == "A" else voltage_pin_b_key, 'A0')
                pullup_pin_name = self.board_config.get(pullup_pin_key, 'D23')
                # Step 2: Set mux for this system
                bits = connector_pin_to_bits(current_pin, system.lower())
                success = set_mux_bits(bits, current_pin, self.pin_map, self.hardware, self.settings, self.log)
                if not success:
                    self.log(f"Failed to set mux bits for pin {current_pin}", "WARNING")
                    voltage_measurements.append(0.0)
                    failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': 0.0})
                    all_tests_passed = False
                    continue
                analog_ports = self.pin_map.get('A', {})
                analog_port = analog_ports.get(voltage_pin_name)
                mux_addr = f"{system.upper()}:{current_pin}"  # Example mux address
                if analog_port is None:
                    self.log(f"Analog pin {voltage_pin_name} not found in pin map for pin {current_pin}", "WARNING")
                    voltage_measurements.append(0.0)
                    failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': 0.0})
                    all_tests_passed = False
                    continue
                # Step 3: Measure voltage (before pullup)
                if isSimulate:
                    import random, time
                    time.sleep(0.1)
                    measured_voltage = random.uniform(-0.05, 0.05)
                else:
                    measured_voltage = self.measurer.measure_voltage(analog_port) * voltage_scale
                # Step 4: Validate ~0V
                if abs(measured_voltage) <= tolerance:
                    self.log(f"Pin {current_pin} on system {system} ({bits}) Volt measurement {measured_voltage:.3f}V - PASS (expected ~0V)", "SUCCESS")
                else:
                    self.log(f"Pin {current_pin} on system {system} ({bits}) Volt measurement {measured_voltage:.3f}V - FAIL (expected ~0V)", "WARNING")
                    failed_pins.append({'pin': current_pin, 'measured': measured_voltage, 'expected': 0.0})
                    all_tests_passed = False
                voltage_measurements.append(measured_voltage)
                # Step 6: Pullup activate
                digital_ports = self.pin_map.get('D', {})
                pullup_physical_pin = digital_ports.get(pullup_pin_name)
                if pullup_physical_pin is None:
                    self.log(f"Pullup pin {pullup_pin_name} not found in pin map for pin {current_pin}", "WARNING")
                    all_tests_passed = False
                    continue
                self.hardware.digital_write(pullup_physical_pin, True)
                # Step 7: Wait 1 sec
                import time
                time.sleep(pins_to_stabilize)
                # Step 8: Measure voltage (after pullup)
                if isSimulate:
                    measured_voltage_pullup = voltage + random.uniform(-0.1, 0.1)
                else:
                    measured_voltage_pullup = self.measurer.measure_voltage(analog_port) * voltage_scale
                # Step 9: Validate expected voltage
                voltage_diff = abs(measured_voltage_pullup - voltage)
                if voltage_diff <= tolerance:
                    self.log(f"Pin {current_pin} on system {system} ({mux_addr}) Volt measurement {measured_voltage_pullup:.3f}V - PASS (expected {voltage}V)", "SUCCESS")
                else:
                    self.log(f"Pin {current_pin} on system {system} ({mux_addr}) Volt measurement {measured_voltage_pullup:.3f}V - FAIL (expected {voltage}V, diff: {voltage_diff:.3f}V)", "WARNING")
                    failed_pins.append({'pin': current_pin, 'measured': measured_voltage_pullup, 'expected': voltage})
                    all_tests_passed = False
                # Step 10: Wait 1 sec, pullup deactivate, deselect pin
                time.sleep(pins_to_stabilize)
                self.hardware.digital_write(pullup_physical_pin, False)
                time.sleep(pins_to_stabilize)
                #clear_bits(bits, self.pin_map, self.hardware, self.log)
            except Exception as e:
                self.log(f"Error processing pin {current_pin} on system {system}: {str(e)}", "ERROR")
                voltage_measurements.append(0.0)
                failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': 0.0})
                all_tests_passed = False

        result_msg = "SUCCESS" if all_tests_passed else "FAILED"
        clear_bits(bits, self.pin_map, self.hardware, self.log)
        self.log(f"System {system} measurement complete: {len(voltage_measurements)} pins measured - {result_msg} - {len(failed_pins)} failures", "SUCCESS" if all_tests_passed else "WARNING")
        return voltage_measurements, all_tests_passed, failed_pins
    
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
        
        debug = get_debug_setting(self.settings, "Test_Sequence")
        if debug:
            self.log(f"Starting test sequence for selected pins: {selected_ids}", "INFO")
            self.wait_debug(10, "active")
        
        for idx, pin_id in enumerate(selected_ids):
            if not self.running:
                self.log("running test stopped by user", "WARNING")
                # Clear mux bits before setting new ones
                clear_mux_bits(self.pin_map, self.hardware, self.log)
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
                
                print(f"★★★ DEBUG: Pin object created for ID={pin.Id}, Type={pin.Discrete_Name}")
                self.log(f"Processing pin number {pin.Id} - Type: {pin.Discrete_Name}", "INFO")
                print(f"★★★ DEBUG: About to check hasattr for set_testing_pin")
                
                # Highlight the row being tested (orange background)
                if hasattr(pin_table, 'set_testing_pin'):
                    self.log(f"Setting testing indicator for pin {pin.Id}", "DEBUG")
                    pin_table.set_testing_pin(pin.Id)
                    # Small delay to ensure orange is visible
                    time.sleep(0.1)
                else:
                    self.log("pin_table does not have set_testing_pin method", "WARNING")
                
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
                print(f"★★★ DEBUG: About to run tests - power={run_power_test}, pullup={run_pullup_test}, logic={run_logic_test}")
                if run_power_test:
                    print(f"★★★ DEBUG: Starting power test for pin {pin.Id}")
                    self.log(f"Running Power Test for pin {pin.Id}", "INFO")
                    #power_voltage, power_success, power_message = self.run_power_test(pin)
                    power_voltage, power_success, power_message = power_test(self, pin)
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
                    pin_row["Power_Measured"] = power_measured
                    pin_row["Power_Result"] = power_result
                    pin_row["Power_Result_Reason"] = power_reason
                    root.after(0, lambda pid=pin_id_local, pm=power_measured, pr=power_result, r=power_reason: 
                        pin_table.update_row(pid, {
                            "Power_Measured": pm,
                            "Power_Result": pr,
                            "Power_Result_Reason": r
                        }))
                
                if run_pullup_test:
                    if pin.Power_Result == True and pin.Power_Expected == 0.0: # the basic condition to run pullup test is that power test passed and expected power is 0V
                        self.log(f"Running PullUp Test for {pin.Id}", "INFO")
                        pullup_voltage, pullup_success, pullup_message = pullup_test(self, pin)
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
                        pin_row["PullUp_Measured"] = pullup_measured
                        pin_row["PullUp_Result"] = pullup_result
                        pin_row["PullUp_Result_Reason"] = pullup_reason
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
                    logic_result = logic_test(self, pin, all_rows)
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
                    pin_row["Logic_DI_Result"] = logic_result_str
                    pin_row["Logic_DI_Result_Reason"] = logic_reason
                    root.after(0, lambda pid=pin_id_local, lr=logic_result_str, r=logic_reason:
                            pin_table.update_row(pid, {
                                "Logic_DI_Result": lr,
                                "Logic_DI_Result_Reason": r
                            }))
                
                # Keep indicator visible for a moment so user can see it
                time.sleep(0.3)
                
                # Clear testing indicator after all tests for this pin complete
                if hasattr(pin_table, 'set_testing_pin'):
                    self.log(f"Clearing testing indicator for pin {pin.Id}", "DEBUG")
                    pin_table.set_testing_pin(None)
                    
            except ValueError as e:
                error_msg = f"running test - Pin data error for {pin_id}: {str(e)}"
                self.log(error_msg, "ERROR")
                # Clear testing indicator on error
                if hasattr(pin_table, 'set_testing_pin'):
                    pin_table.set_testing_pin(None)
            except Exception as e:
                error_msg = f"running test - Unexpected error processing {pin_id}: {str(e)}"
                self.log(error_msg, "ERROR")
                # Clear testing indicator on error
                if hasattr(pin_table, 'set_testing_pin'):
                    pin_table.set_testing_pin(None)
        
        root.after(0, on_test_complete)
 