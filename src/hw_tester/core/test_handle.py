"""
Test Handler - Core test execution functions for HW Tester.
Contains all test procedures: power, pullup, logic, I-bit, relay/fuse, and short circuit tests.
"""
import time
import random
import threading
import traceback
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hw_tester.hardware.pin import Pin

from hw_tester.core.test_power import power_test
from hw_tester.core.test_pullUp import pullup_test
from hw_tester.core.test_logic import logic_test
from hw_tester.core.test_cable_one_box import Cable_test
from hw_tester.hardware.pin import TestResult
from hw_tester.hardware.controllino_io import connector_pin_to_bits
from hw_tester.utils.general import (
    get_debug_setting,
    get_pin_pair_info_controlino,
    set_mux_bits,
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
        self.last_sequence_failures = []
        
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

    
   
    def run_tests(self, selected_ids, all_rows, root, pin_table, on_test_complete):
        """
        Execute the configured test sequence for the selected connector pins.

        Test Procedure:
        1. Check the running flag and stop cleanly if the user requests a stop.
        2. Find each selected pin row and create a Pin object from its values.
        3. Select tests from the row data:
           - Power test when Power_Expected is populated.
           - PullUp test when PullUp_Input is populated.
           - Logic test when Logic_Expected is populated.
           - Cable test when Type or Card is "Cable".
        4. If a Cable test is selected, skip Power, PullUp, and Logic tests for
           that row.
        5. Clear the mux matrix before running the selected test functions.
        6. Run power_test(), pullup_test(), logic_test(), or Cable_test() and
           update the corresponding row results after each test.
        7. Clear the testing indicator and schedule the completion callback.

        Args:
            selected_ids: List of selected pin IDs to test.
            all_rows: All pin table rows used to create Pin objects and select
                the configured tests.
            root: UI root object providing after() for thread-safe updates.
            pin_table: Pin table view used for testing indicators and results.
            on_test_complete: Callback invoked after all selected pins finish.

        Returns:
            None. Test results are written into the pin table and operational
            log, then on_test_complete is scheduled on the UI thread.
        """
        from hw_tester.hardware.pin import Pin

        self.last_sequence_failures = []
        
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
                    self.last_sequence_failures.append(f"{pin_id}: pin row not found")
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
                
                # Highlight the row being tested (thread-safe via postEvent internally)
                if hasattr(pin_table, 'set_testing_pin'):
                    self.log(f"Setting testing indicator for pin {pin.Id}", "DEBUG")
                    pin_table.set_testing_pin(pin.Id)
                    # Give the main thread time to render the yellow before the test runs
                    time.sleep(0.15)
                else:
                    self.log("pin_table does not have set_testing_pin method", "WARNING")
                
                # Step 3: Determine which tests to run based on whether values are provided (not empty)
                # Empty values in Excel mean the test should be skipped
                # 0.0 is a valid measurement, so we check if Power_Expected/PullUp_Expected were actually set
                power_expected_str = pin_row.get("Power_Expected", "").strip()
                pullup_expected_str = pin_row.get("PullUp_Input", "").strip()
                logic_Expected_str = pin_row.get("Logic_Expected", "").strip()
                logic_Command_str = pin_row.get("Logic_Command", "").strip()
                cable_test_Type_str = pin_row.get("Type", "").strip()
                cable_test_Card_str = pin_row.get("Card", "").strip()

                run_power_test = (power_expected_str != "" and power_expected_str != "-")
                run_pullup_test = (pullup_expected_str != "" and pullup_expected_str != "-")
                run_logic_test = (logic_Expected_str != "" and logic_Expected_str != "-")
                run_cable_test = (cable_test_Type_str == "Cable" or cable_test_Card_str == "Cable")
                if run_cable_test:
                    self.log(f"Running Cable Test for pin {pin.Id}", "INFO")
                    run_power_test = False
                    run_pullup_test = False
                    run_logic_test = False
                
                # Run tests
                # Clear mux bits before setting new ones
                clear_mux_bits(self.pin_map, self.hardware, self.log)
                print(f"★★★ DEBUG: About to run tests - power={run_power_test}, pullup={run_pullup_test}, logic={run_logic_test}, cable={run_cable_test}")
                if run_power_test:
                    print(f"★★★ DEBUG: Starting power test for pin {pin.Id}")
                    self.log(f"Running Power Test for pin {pin.Id}", "INFO")
                    #power_voltage, power_success, power_message = self.run_power_test(pin)
                    power_voltage, power_success, power_message = power_test(self, pin)
                    # Clear mux bits before setting new ones
                    clear_mux_bits(self.pin_map, self.hardware, self.log)
                    pin.Power_Measured = power_voltage
                    pin.Power_Result = power_success
                    if not power_success:
                        self.last_sequence_failures.append(f"{pin.Id}: Power")
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
                        if not pullup_success:
                            self.last_sequence_failures.append(f"{pin.Id}: PullUp")
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
                    if not Logic_test_result:
                        self.last_sequence_failures.append(f"{pin.Id}: Logic")
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

                if run_cable_test:
                    logic_result = Cable_test(self, pin, all_rows)
                    Logic_test_voltage,Logic_test_result,logic_test_message = logic_result
                    pin.Logic_DI_Result = Logic_test_result
                    if not Logic_test_result:
                        self.last_sequence_failures.append(f"{pin.Id}: Cable")
                    self.log(
                            f"Cable Test: Result={'PASS' if pin.Logic_DI_Result else 'FAIL'} - {logic_test_message}",
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
                self.last_sequence_failures.append(f"{pin_id}: {error_msg}")
                if hasattr(pin_table, 'set_testing_pin'):
                    pin_table.set_testing_pin(None)
            except Exception as e:
                error_msg = f"running test - Unexpected error processing {pin_id}: {str(e)}"
                self.log(error_msg, "ERROR")
                self.last_sequence_failures.append(f"{pin_id}: {error_msg}")
                if hasattr(pin_table, 'set_testing_pin'):
                    pin_table.set_testing_pin(None)
        
        root.after(0, on_test_complete)
 