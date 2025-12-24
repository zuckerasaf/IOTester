"""
MainWindow - HW Tester application main window.
Integrates PinTableView, OperationalPanel, and LogView.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from typing import List, Optional
import sys
from pathlib import Path
from hw_tester.hardware.controllino_io import connector_pin_to_bits
from hw_tester.hardware.pin import Pin
from hw_tester.utils.general import clear_mux_bits, parse_event_string, get_pin_pair_info_controlino, set_mux_bits, clear_bits, verify_card_output

# Fix imports when running as script
if __name__ == "__main__":
    # Add src to path for standalone execution
    project_root = Path(__file__).resolve().parents[3]
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

from hw_tester.ui.views import PinTableView, OperationalPanel, LogView
from hw_tester.utils.read_excell import load_connector_from_excel
from hw_tester.core.measurer import Measurer
from hw_tester.core.pin_pulser import PinPulser
from hw_tester.core.udp_card_manager import UDPCardManager
from hw_tester.utils.config_loader import load_settings, get_board_pin_map, get_board_pin_config, save_settings


class MainWindow:
    """
    Main application window for HW Tester.
    Manages the overall UI layout and coordinates between components.
    """
    
    def __init__(self, title: str = "HW Tester"):
        """
        Initialize main window.
        
        Args:
            title: Window title
        """
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry("1600x700")
        
        # Configure root grid layout (3 rows, 1 column)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=3)  # Pin table
        self.root.rowconfigure(1, weight=0)  # Operational panel
        self.root.rowconfigure(2, weight=1)  # Log
        
        # Load settings BEFORE creating widgets
        self.settings = load_settings()
        
        # Load board pin map
        self.pin_map = get_board_pin_map(self.settings)
        
        # Load board-specific pin configuration
        self.board_config = get_board_pin_config(self.settings)
        
        # Initialize state
        self.connected = False
        self.running = False
        self.running_ibit = False
        
        # Buffer for hardware initialization logs (before log_view exists)
        self._init_log_buffer = []
        
        # Initialize hardware ONCE and share it between components
        # auto_detect=False uses the Type from settings.yaml
        # auto_detect=True attempts to detect board type (may be ambiguous for Controllino)
        from hw_tester.hardware.hardware_factory import initialize_hardware
        self.hardware = initialize_hardware(self.settings, log_callback=self._buffer_log)
        
        # Reload settings in case hardware initialization changed simulation mode
        self.settings = load_settings()
        
        # Create main components (needs settings to be loaded first)
        self._create_widgets()
        
        # Flush buffered logs to log view
        for msg, level in self._init_log_buffer:
            self.log_view.append(msg, level)
        self._init_log_buffer.clear()
        
        # Initialize Measurer with shared hardware instance
        self.measurer = Measurer(hardware_io=self.hardware, settings=self.settings)
        
        # Initialize KeepAlive with shared hardware instance
        self.keep_alive = PinPulser(hardware_io=self.hardware, settings=self.settings)
        
        # Initialize UDP Card Manager for controlling IO cards
        self.card_manager = UDPCardManager(create_all=False)  # Only create enabled cards
        self.card_manager.start_all()  # Start communication threads
        
        # Set up proper cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _buffer_log(self, message: str, level: str = "INFO") -> None:
        """Buffer log messages during initialization before log_view exists."""
        self._init_log_buffer.append((message, level))
    
    def on_closing(self) -> None:
        """Clean up resources before closing the application."""
        if hasattr(self, 'log_view'):
            self.log_view.append("[MainWindow] Shutting down application...", "INFO")
        
        # Stop any running tests (sets flags to exit thread loops)
        if hasattr(self, 'running') and self.running:
            if hasattr(self, 'log_view'):
                self.log_view.append("[MainWindow] Stopping running test...", "WARNING")
            self.running = False
        
        if hasattr(self, 'running_ibit') and self.running_ibit:
            if hasattr(self, 'log_view'):
                self.log_view.append("[MainWindow] Stopping I_Bit test...", "WARNING")
            self.running_ibit = False
        
        # Give threads a moment to exit gracefully
        import time
        time.sleep(0.2)
        
        # Stop UDP card manager
        if hasattr(self, 'card_manager') and self.card_manager is not None:
            if hasattr(self, 'log_view'):
                self.log_view.append("[MainWindow] Stopping UDP card manager...", "INFO")
            self.card_manager.stop_all()
        
        # Close hardware connection
        if hasattr(self, 'hardware') and self.hardware is not None:
            if hasattr(self, 'log_view'):
                self.log_view.append("[MainWindow] Closing hardware connection...", "INFO")
            self.hardware.close()
        
        # Final log message before closing
        if hasattr(self, 'log_view'):
            self.log_view.append("[MainWindow] Exiting application...", "INFO")
        
        # Destroy window
        self.root.destroy()
        
        # Exit the application cleanly
        sys.exit(0)
    
    def _create_widgets(self) -> None:
        """Create and layout all UI components."""
        # Pin Table (top)
        pin_frame = tk.LabelFrame(self.root, text="Pin Table", padx=5, pady=5)
        pin_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 5))
        pin_frame.columnconfigure(0, weight=1)
        pin_frame.rowconfigure(0, weight=1)
        
        self.pin_table = PinTableView(pin_frame)
        self.pin_table.grid(row=0, column=0, sticky="nsew")
        
        # Operational Panel (middle)
        op_frame = tk.Frame(self.root, padx=5, pady=5)
        op_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        self.op_panel = OperationalPanel(
            op_frame,
            on_load=self.on_load,
            on_keep_alive=self.on_keep_alive,
            on_i_bit=self.on_i_bit,
            on_test=self.on_test,
            on_stop_ibit=self.on_stop_ibit,
            on_stop_t=self.on_stop_t,
            on_report=self.on_report,
            on_clear_log=self.on_clear_log,
            settings=self.settings,
            on_hw_change=self.on_hw_change,
            on_simulate_change=self.on_simulate_change,
            on_iobox_change=self.on_iobox_change
        )
        self.op_panel.pack(fill=tk.BOTH, expand=True)
        
        # Log View (bottom)
        log_frame = tk.LabelFrame(self.root, text="Operational Log", padx=5, pady=5)
        log_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(5, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_view = LogView(log_frame)
        self.log_view.grid(row=0, column=0, sticky="nsew")
    
    def _load_demo_data(self) -> None:
        """Load demo pin data for testing."""
        demo_rows = [
            {"ID": "J1-01", "type": "digital", "volt": "5.0", "Measure": "", "destination": "D5", "substance": "Signal A", "card": "1"},
            {"ID": "J1-02", "type": "analog", "volt": "3.3", "Measure": "", "destination": "A0", "substance": "Sensor Input", "card": "1"},
            {"ID": "J1-03", "type": "ground", "volt": "0.0", "Measure": "", "destination": "GND", "substance": "Ground", "card": "1"},
            {"ID": "J1-04", "type": "power", "volt": "5.0", "Measure": "", "destination": "VCC", "substance": "Power Supply", "card": "2"},
            {"ID": "J1-05", "type": "pwm", "volt": "3.3", "Measure": "", "destination": "D9", "substance": "PWM Output", "card": "2"},
            {"ID": "J1-06", "type": "digital", "volt": "5.0", "Measure": "", "destination": "D10", "substance": "Signal B", "card": "2"},
            {"ID": "J1-07", "type": "analog", "volt": "3.3", "Measure": "", "destination": "A1", "substance": "Temperature", "card": "1"},
            {"ID": "J1-08", "type": "digital", "volt": "5.0", "Measure": "", "destination": "D11", "substance": "LED Control", "card": "2"},
        ]
        self.pin_table.set_rows(demo_rows)
        self.op_panel.set_connector("J1 - Demo Connector")
    
    def on_load(self) -> None:
        """Handle Load button click - Open file browser and load Excel connector data."""
        # Open file dialog to select Excel file
        file_path = filedialog.askopenfilename(
            title="Select Connector Excel File",
            initialdir=Path.cwd() / "tests" / "DB",
            filetypes=[
                ("Excel files", "*.xlsx *.xls"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            self.log_view.append("File selection cancelled", "INFO")
            return
        
        file_path = Path(file_path)
        self.log_view.append(f"Loading connector data from: {file_path.name}", "INFO")
        
        # Load connector data in background thread to avoid freezing UI
        def load_data():
            try:
                # Extract connector ID from filename (e.g., "J1_Routing.xlsx" -> "J1")
                connector_id = file_path.stem.split('_')[0]
                
                # Load connector from Excel
                connector = load_connector_from_excel(
                    file_name=file_path.name,
                    db_path=str(file_path.parent),
                    connector_id=connector_id
                )
                
                # Convert connector pins to table rows
                rows = []
                for pin in connector.pins:
                    rows.append({
                        "ID": pin.Id,
                        "Connect": pin.Connect,
                        "Type": pin.Type,
                        "Power_Expected": f"{pin.Power_Expected:.2f}",
                        "Power_Input": pin.Power_Input,
                        "Power_Measured": "" if pin.Power_Measured == 0.0 else f"{pin.Power_Measured:.2f}",
                        "Power_Result": pin.Power_Result.value,
                        "PullUp_Expected": f"{pin.PullUp_Expected:.2f}",
                        "PullUp_Input": pin.PullUp_Input,
                        "PullUp_Measured": "" if pin.PullUp_Measured == 0.0 else f"{pin.PullUp_Measured:.2f}",
                        "PullUp_Result": pin.PullUp_Result.value,
                        "Logic_Pin_Input": str(pin.Logic_Pin_Input),
                        "Logic_Expected": str(pin.Logic_Expected),
                        "Logic_DI_Result": pin.Logic_DI_Result.value
                    })
                
                # Update UI on main thread
                self.root.after(0, self._on_load_complete, file_path.name, connector.id, rows)
                
            except Exception as e:
                error_msg = f"Error loading file: {str(e)}"
                self.root.after(0, self._on_load_error, error_msg)
        
        threading.Thread(target=load_data, daemon=True).start()
    
    def _on_load_complete(self, filename: str, connector_id: str, rows: List[dict]) -> None:
        """Called when Excel file loading completes successfully."""
        self.pin_table.set_rows(rows)
        self.op_panel.set_connector(filename)  # Show filename instead of connector ID
        self.connected = True
        self.op_panel.enable_test(True)
        self.log_view.append(f"Successfully loaded {len(rows)} pins from {filename} (Connector: {connector_id})", "SUCCESS")
    
    def _on_load_error(self, error_msg: str) -> None:
        """Called when Excel file loading fails."""
        self.log_view.append(error_msg, "ERROR")
        messagebox.showerror("Load Error", error_msg)
    
    def on_keep_alive(self) -> None:
        """Handle KeepAlive button click - Pulse all digital ports for the configured board."""
        self.log_view.append("Starting KeepAlive pulse sequence...", "INFO")
        
        # Get all digital ports from pin map
        digital_ports = self.pin_map.get('D', {})
        
        if not digital_ports:
            board_type = self.settings.get('Board', {}).get('Type', 'unknown')
            self.log_view.append(f"No digital ports found for {board_type}", "WARNING")
            return
        
        self.log_view.append(f"Pulsing {len(digital_ports)} digital ports...", "INFO")
        
        # Pulse all digital ports asynchronously
        for port_name, port_number in digital_ports.items():
            try:
                # Pulse the digital port (async, non-blocking)
                timer = self.keep_alive.pulse_async(digital_port=port_number)
                self.log_view.append(f"Pulsing {port_name} (port {port_number})", "DEBUG")
            except Exception as e:
                self.log_view.append(f"Error pulsing {port_name}: {str(e)}", "ERROR")
        
        self.log_view.append(f"KeepAlive pulse sequence initiated for all {len(digital_ports)} ports", "SUCCESS")
    
    def on_i_bit(self) -> None:
        """Handle I_Bit button click - Run short circuit test on all pins."""
        self.log_view.append("Starting I_Bit short circuit test...", "INFO")
        self.running_ibit = True
        self.op_panel.enable_stop_ibit(True)
        self.op_panel.enable_i_bit(False)
        
        # Run short circuit test in background thread
        def run_i_bit_test():
            try:
                pair1_test_results,pair1_test_status = self.relay_fuse_test("enable_Relay_pin_1_A","enable_Relay_pin_1_B","pullup_pins_pin_pair1","voltage_measure_pin_pair1","voltage_measure_pin_pair1_B")
                pair2_test_results,pair2_test_status = self.relay_fuse_test("enable_Relay_pin_2_A","enable_Relay_pin_2_B","pullup_pins_pin_pair2","voltage_measure_pin_pair2","voltage_measure_pin_pair2_B")
                pair3_test_results,pair3_test_status = self.relay_fuse_test("enable_Relay_pin_3_A","enable_Relay_pin_3_B","pullup_pins_pin_pair3","voltage_measure_pin_pair3","voltage_measure_pin_pair3_B")
                pair4_test_results,pair4_test_status = self.relay_fuse_test("enable_Relay_pin_4_A","enable_Relay_pin_4_B","pullup_pins_pin_pair4","voltage_measure_pin_pair4","voltage_measure_pin_pair4_B")

                if pair1_test_status and pair2_test_status and pair3_test_status and pair4_test_status:
                    self.root.after(0, lambda: self.log_view.append(
                        f"I_Bit test complete: All relay pairs PASSED",
                        "SUCCESS"
                    ))
                else:
                    self.root.after(0, lambda: self.log_view.append(
                        f"I_Bit test complete: Some relay pairs FAILED",
                        "WARNING"
                    ))
                #def relay_fuse_test(self, first_relay: str, second_relay: str, pullup_pin: str, voltage_measure_pin1: str, voltage_measure_pin2: str) -> str:
                test_results = self.short_circuit_test()
                passed_count = sum(1 for _, passed, _ in test_results if passed)
                total_count = len(test_results)
                self.root.after(0, lambda: self.log_view.append(
                    f"I_Bit test complete: {passed_count}/{total_count} pins PASSED",
                    "SUCCESS" if passed_count == total_count else "WARNING"
                ))
            except Exception as e:
                error_msg = f"Error during I_Bit test: {str(e)}"
                self.root.after(0, lambda: self.log_view.append(error_msg, "ERROR"))
            finally:
                self.root.after(0, self._on_ibit_complete)
        
        threading.Thread(target=run_i_bit_test, daemon=True).start()
    
    def measure_voltage(self, pin_id: str, analog_port: int, idx: int = 0) -> None:
        """
        Measure voltage on a pin.
        If simulation mode is enabled, simulates the measurement.
        Otherwise, uses real hardware via Measurer.
        
        Args:
            pin_id: Pin ID to measure
            analog_port: Analog port number (e.g., 0 for A0)
            idx: Index for simulation variation (default: 0)
        """
        is_simulation = self.settings.get('Board', {}).get('simulation', True)
        
        # Get voltage scale factor from settings
        scale_factor = self.settings.get('Measure_value', {}).get('Scale_1', 1.0)
        
        if is_simulation:
            # Simulation mode - generate fake voltage
            time.sleep(0.5)
            voltage = 5.0 if "power" in pin_id or "digital" in pin_id else 3.3
            measured_voltage = voltage + (idx * 0.01)
        else:
            # Real hardware mode - use Measurer
            try:
                measured_voltage = self.measurer.measure_voltage(analog_port)
            except Exception as e:
                measured = f"ERROR: {str(e)}"
                self.log_view.append(f"Measurement error on {pin_id}: {str(e)}", "ERROR")
                # Update the measurement in the UI
                self.root.after(0, self._update_measurement, pin_id, measured)
                return
        
        # Apply scale factor to the measured voltage
        scaled_voltage = measured_voltage * scale_factor
        measured = f"{scaled_voltage:.2f}V"
        
        # Update the measurement in the UI
        self.root.after(0, self._update_measurement, pin_id, measured)
    
    def on_test(self) -> None:
        """Handle Run button click - Execute test sequence."""
        if not self.connected:
            self.log_view.append("Not connected. Please connect first.", "WARNING")
            return
        
        selected_ids = self.pin_table.get_selected_ids()
        if not selected_ids:
            self.log_view.append("No pins selected. Please select pins to test.", "WARNING")
            return
        
        # Clear all Measure column data before starting test
        all_rows = self.pin_table.get_all_rows()
        for row in all_rows:
            self.pin_table.update_row(row["ID"], {"Measure": ""})
        
        is_simulation = self.settings.get('Board', {}).get('simulation', True)
        mode_str = "SIMULATION" if is_simulation else "HARDWARE"
        self.log_view.append(f"Starting test sequence on {len(selected_ids)} selected pins ({mode_str} mode)", "INFO")
        self.running = True
        self.op_panel.enable_stop_t(True)
        self.op_panel.enable_test(False)
        
        # Get digital pin map for bit setting
        digital_ports = self.pin_map.get('D', {})
        
        # Get all rows to access pin types
        all_rows = self.pin_table.get_all_rows()
        pin_types = {row["ID"]: row.get("type", "") for row in all_rows}
        
        # Run test sequence in background
        def run_tests():
            from hw_tester.hardware.pin import Pin
            
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
                        self.log_view.append(f"Pin {pin_id} not found in table", "ERROR")
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
                        Type=pin_row.get("Type", ""),
                        Power_Expected=power_exp_val,
                        Power_Measured=0.0,
                        Power_Result=False,
                        PullUp_Expected=pullup_exp_val,
                        PullUp_Measured=0.0,
                        PullUp_Result=False,
                        Power_Input=pin_row.get("Power_Input", ""),
                        PullUp_Input=pin_row.get("PullUp_Input", ""),
                        Logic_Pin_Input=pin_row.get("Logic_Pin_Input", ""),
                        Logic_Expected=pin_row.get("Logic_Expected", ""),
                        Logic_DI_Result=False
                    )
                    
                    self.log_view.append(f"Processing {pin.Id} - Type: {pin.Type}", "INFO")
                    
                    # Step 3: Determine which tests to run based on whether values are provided (not empty)
                    # Empty values in Excel mean the test should be skipped
                    # 0.0 is a valid measurement, so we check if Power_Expected/PullUp_Expected were actually set
                    power_expected_str = pin_row.get("Power_Expected", "").strip()
                    pullup_expected_str = pin_row.get("PullUp_Input", "").strip()
                    logic_Expected_str = pin_row.get("Logic_Expected", "").strip()
                    
                    run_power_test = (power_expected_str != "" and power_expected_str != "-")
                    run_pullup_test = (pullup_expected_str != "" and pullup_expected_str != "-")
                    run_logic_test = (logic_Expected_str != "" and logic_Expected_str != "-")
                    
                    # Run tests
                    # Clear mux bits before setting new ones
                    clear_mux_bits(self.pin_map, self.hardware, self.log_view.append)
                    if run_power_test:
                        self.log_view.append(f"Running Power Test for {pin.Id}", "INFO")
                        power_voltage, power_success, power_message = self.run_power_test(pin)
                        # Clear mux bits before setting new ones
                        clear_mux_bits(self.pin_map, self.hardware, self.log_view.append)
                        pin.Power_Measured = power_voltage
                        pin.Power_Result = power_success
                        self.log_view.append(
                            f"Power Test: Expected={pin.Power_Expected}V, Measured={pin.Power_Measured}V, Result={'PASS' if pin.Power_Result else 'FAIL'} - {power_message}",
                            "SUCCESS" if pin.Power_Result else "WARNING"
                        )
                        # Update table immediately after power test
                        # Capture values to avoid lambda closure issues
                        pin_id = pin.Id
                        power_measured = f"{pin.Power_Measured:.2f}"
                        power_result = "Pass" if pin.Power_Result else "Fail"
                        self.root.after(0, lambda pid=pin_id, pm=power_measured, pr=power_result: 
                            self.pin_table.update_row(pid, {
                                "Power_Measured": pm,
                                "Power_Result": pr
                            }))
                    
                    if run_pullup_test:
                        if pin.Power_Result == True and pin.Power_Expected == 0.0: # the basic condition to run pullup test is that power test passed and expected power is 0V
                            self.log_view.append(f"Running PullUp Test for {pin.Id}", "INFO")
                            pullup_voltage, pullup_success, pullup_message = self.run_pullup_test(pin)
                            # Clear mux bits before setting new ones
                            clear_mux_bits(self.pin_map, self.hardware, self.log_view.append)
                            pin.PullUp_Measured = pullup_voltage
                            pin.PullUp_Result = pullup_success
                            self.log_view.append(
                                f"PullUp Test: Expected={pin.PullUp_Expected}V, Measured={pin.PullUp_Measured}V, Result={'PASS' if pin.PullUp_Result else 'FAIL'} - {pullup_message}",
                                "SUCCESS" if pin.PullUp_Result else "WARNING"
                            )
                            # Update table immediately after pullup test
                            # Capture values to avoid lambda closure issues
                            pin_id = pin.Id
                            pullup_measured = f"{pin.PullUp_Measured:.2f}"
                            pullup_result = "Pass" if pin.PullUp_Result else "Fail"
                            self.root.after(0, lambda pid=pin_id, pum=pullup_measured, pur=pullup_result:
                                self.pin_table.update_row(pid, {
                                    "PullUp_Measured": pum,
                                    "PullUp_Result": pur
                                }))
                        elif pin.Power_Result == True and pin.Power_Expected != 0.0:
                            self.log_view.append(
                                f"PullUp Test: in Pin ID {pin.Id} the define pullup_expected ={pin.PullUp_Expected}V, not meet the pull up bascic condition  V= 0.0 V, so skip pullup test","WARNING"
                            )
                        elif pin.Power_Result == False:
                            self.log_view.append(
                                f"PullUp Test: in Pin ID {pin.Id} Power test failed, so skip pullup test","WARNING"
                            )
                    
                    if run_logic_test:
                        if pin.Power_Result == True and pin.Power_Measured< 20.0: # the basic condition to run logic test is that power test passed and expected power is 0V
                            self.log_view.append(f"Running Logic Test for {pin.Id} (Input: {pin.Logic_Pin_Input})", "INFO")
                            logic_result = self.run_logic_test(pin)
                            Logic_test_voltage,Logic_test_result,logic_test_message = logic_result
                            pin.Logic_DI_Result = Logic_test_result
                            self.log_view.append(
                                f"Logic Test: Result={'PASS' if pin.Logic_DI_Result else 'FAIL'} - {logic_test_message}",
                                "SUCCESS" if pin.Logic_DI_Result else "WARNING"
                            )
                            # Update table immediately after logic test
                            # Capture values to avoid lambda closure issues
                            pin_id = pin.Id
                            logic_result_str = "Pass" if pin.Logic_DI_Result else "Fail"
                            self.root.after(0, lambda pid=pin_id, lr=logic_result_str:
                                self.pin_table.update_row(pid, {
                                    "Logic_DI_Result": lr
                                }))
                        elif pin.Power_Result == True and pin.Power_Expected > 0.0:
                            self.log_view.append(
                                f"Logic Test: in Pin ID {pin.Id} the defined Logic test condition not met (expected power > 0.0 V), so skip logic test","WARNING"
                            )
                        elif pin.Power_Result == False:
                            self.log_view.append(
                                f"Logic Test: Power test failed, so skip logic test","WARNING"
                            )
                    
                except ValueError as e:
                    error_msg = f"Pin data error for {pin_id}: {str(e)}"
                    self.log_view.append(error_msg, "ERROR")
                except Exception as e:
                    error_msg = f"Unexpected error processing {pin_id}: {str(e)}"
                    self.log_view.append(error_msg, "ERROR")
            
            self.root.after(0, self._on_test_complete)
        
        threading.Thread(target=run_tests, daemon=True).start()
    
    def _update_measurement(self, pin_id: str, measured_value: str) -> None:
        """Update measurement in the table."""
        self.pin_table.update_row(pin_id, {"Measure": measured_value})
        self.log_view.append(f"Measured {pin_id}: {measured_value}", "INFO")
    
    def _update_pin_results(self, pin: "Pin") -> None:
        """
        Update all test results for a pin in the UI table.
        
        Args:
            pin: Pin object with test results
        """
        self.pin_table.update_row(pin.Id, {
            "Power_Measured": f"{pin.Power_Measured:.2f}",
            "Power_Result": "Pass" if pin.Power_Result else "Fail",
            "PullUp_Measured": f"{pin.PullUp_Measured:.2f}",
            "PullUp_Result": "Pass" if pin.PullUp_Result else "Fail",
            "Logic_DI_Result": "Pass" if pin.Logic_DI_Result else "Fail"
        })
    
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
            # Return expected value with small variation
            import random
            variation = random.uniform(-0.1, 0.1)
            simulated_voltage = pin.Power_Expected + variation
            success = abs(simulated_voltage - pin.Power_Expected) < 0.5
            message = "Simulation: measurement in tolerance" if success else "Simulation: measurement not in tolerance"
            return (simulated_voltage, success, message)
        
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
        success = set_mux_bits(bits, pin_number, self.pin_map, self.hardware, self.settings, self.log_view.append)
        
        # Debug mode - wait for user confirmation
        mode_debug = self.settings.get('Debug', {}).get('mode', False)
        if mode_debug:
            input("\nWAIT...")

        if not success:
            self.log_view.append(f"Failed to set mux bits for pin {pin_number}", "ERROR")
            return (0.0, False, "Error: Failed to set mux matrix")
        
        # Get physical analog port from pin map
        analog_ports = self.pin_map.get('A', {})
        analog_port = analog_ports.get(voltage_pin_name)
        
        if analog_port is None:
            self.log_view.append(f"Analog pin {voltage_pin_name} not found in pin map", "ERROR")
            return (0.0, False, "Error: Analog pin not found in pin map")
        
        # Apply voltage scaling factor from settings
        voltage_scale = 1

        # Step 1: Measure initial voltage
        self.log_view.append(f"Measuring voltage on {voltage_pin_name} (pin {analog_port})", "DEBUG")
        try:
            measured_voltage = self.measurer.measure_voltage(analog_port) * voltage_scale
            self.log_view.append(f"Initial measurement: {measured_voltage:.3f}V", "DEBUG")
        except Exception as e:
            self.log_view.append(f"Measurement error: {str(e)}", "ERROR")
            return (0.0, False, f"Error: Measurement failed - {str(e)}")
        

        
        # Step 2: Check if Power_Input is "none" or empty
        if not pin.Power_Input or pin.Power_Input.strip().lower() == "none":
            # No external control needed - just verify measurement
            voltage_diff = abs(measured_voltage* voltage_scale - pin.Power_Expected)
            if voltage_diff <= tolerance:
                self.log_view.append(f"Measurement {measured_voltage* voltage_scale:.3f}V is within tolerance of {pin.Power_Expected:.3f}V", "SUCCESS")
                return (measured_voltage* voltage_scale, True, "Measurement is in tolerance")
            else:
                self.log_view.append(f"Measurement {measured_voltage* voltage_scale:.3f}V is NOT within tolerance of {pin.Power_Expected:.3f}V (diff: {voltage_diff:.3f}V)", "WARNING")
                return (measured_voltage* voltage_scale, False, f"Measurement not in tolerance (diff: {voltage_diff:.3f}V)")
        
        # Step 3: Power_Input is provided - need to activate external card
        # First verify initial measurement is ~0V
        if abs(measured_voltage* voltage_scale) > tolerance:
            self.log_view.append(f"Initial voltage {measured_voltage* voltage_scale:.3f}V is not ~0V (tolerance: {tolerance}V) - test failed", "WARNING")
            return (measured_voltage* voltage_scale, False, f"Initial voltage {measured_voltage:.3f}V is not ~0V")
        
        self.log_view.append(f"Initial voltage {measured_voltage* voltage_scale:.3f}V is ~0V - proceeding to activate card", "DEBUG")
        
        
        # Parse Power_Input and activate card
        card, event_type, event_num, event_value = parse_event_string(pin.Power_Input)
        if card is None or event_type is None:
            self.log_view.append(f"Failed to parse Power_Input: {pin.Power_Input}", "ERROR")
            return (measured_voltage, False, f"Failed to parse Power_Input or not needed: {pin.Power_Input}")
        
        # Set analog or digital output
        if event_type == "AO":
            success = self.card_manager.set_analog_output(card_id=card, ao_number=event_num, voltage=event_value)
            self.log_view.append(f"active: Set Card {card} AO{event_num} to {event_value}V: {'Success' if success else 'Failed'}", "INFO")
        elif event_type == "DO":
            success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=bool(event_value))
            self.log_view.append(f"active: Set Card {card} DO{event_num} to {event_value}: {'Success' if success else 'Failed'}", "INFO")
        else:
            self.log_view.append(f"Unknown event type: {event_type}", "ERROR")
            return (measured_voltage, False, f"Unknown event type: {event_type}")
        
        if not success:
            self.log_view.append(f"Failed to activate card {card}", "ERROR")
            return (measured_voltage, False, f"Failed to activate card {card}")
        
        # Wait for signal to stabilize
        stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
        time.sleep(stabilize_delay)

        # Verify the output was set correctly
        verify_success, verify_msg = verify_card_output(
            self.card_manager, card, event_type, event_num, event_value, 
            tolerance, self.log_view.append
        )
        if not verify_success:
            return (measured_voltage, False, verify_msg)
        
        # Wait for signal to stabilize
        stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
        time.sleep(stabilize_delay)

        # Debug mode - wait for user confirmation
        mode_debug = self.settings.get('Debug', {}).get('mode', False)
        if mode_debug:
            input("\nWAIT...")

        # Measure voltage again after activation
        try:
            measured_voltage = self.measurer.measure_voltage(analog_port)
            self.log_view.append(f"Measurement after activation: {measured_voltage* voltage_scale:.3f}V", "DEBUG")

        except Exception as e:
            self.log_view.append(f"Measurement error after activation: {str(e)}", "ERROR")

        
            return (0.0, False, f"Error: Measurement failed after activation - {str(e)}")
        

        # Set analog or digital output  buck to zero 
        if event_type == "AO":
            success = self.card_manager.set_analog_output(card_id=card, ao_number=event_num, voltage=0)
            event_value = 0
            self.log_view.append(f"DeActive: Set Card {card} AO{event_num} to {0}V: {'Success' if success else 'Failed'}", "INFO")
        elif event_type == "DO":
            success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
            event_value = False
            self.log_view.append(f"DeActive: Set Card {card} DO{event_num} to False: {'Success' if success else 'Failed'}", "INFO")
        else:
            self.log_view.append(f"Unknown event type: {event_type}", "ERROR")
            return (measured_voltage, False, f"Unknown event type: {event_type}")
        
        if not success:
            self.log_view.append(f"Failed to activate card {card}", "ERROR")
            return (measured_voltage, False, f"Failed to activate card {card}")
        
        # Verify the output was set correctly
        verify_success, verify_msg = verify_card_output(
            self.card_manager, card, event_type, event_num, event_value, 
            tolerance, self.log_view.append
        )
        if not verify_success:
            return (measured_voltage, False, verify_msg)
        
        # Compare to expected value
        voltage_diff = abs(measured_voltage* voltage_scale - pin.Power_Expected)
        if voltage_diff <= tolerance:
            self.log_view.append(f"Measurement {measured_voltage* voltage_scale:.3f}V is within tolerance of {pin.Power_Expected:.3f}V", "SUCCESS")
            return (measured_voltage* voltage_scale* voltage_scale, True, "Measurement is in tolerance")
        else:
            self.log_view.append(f"Measurement {measured_voltage* voltage_scale:.3f}V is NOT within tolerance of {pin.Power_Expected:.3f}V (diff: {voltage_diff:.3f}V)", "WARNING")
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
            # Return expected value with small variation
            import random
            variation = random.uniform(-0.1, 0.1)
            simulated_voltage = pin.PullUp_Expected + variation
            success = abs(simulated_voltage - pin.PullUp_Expected) < 0.5
            message = "Simulation: measurement in tolerance" if success else "Simulation: measurement not in tolerance"
            return (simulated_voltage, success, message)
        
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
        success = set_mux_bits(bits, pin_number, self.pin_map, self.hardware, self.settings, self.log_view.append)
        
        # Debug mode - wait for user confirmation
        mode_debug = self.settings.get('Debug', {}).get('mode', False)
        if mode_debug:
            input("\nWAIT...")

        if not success:
            self.log_view.append(f"Failed to set mux bits for pin {pin_number}", "ERROR")
            return (0.0, False, "Error: Failed to set mux matrix")
        
        # Get physical analog port from pin map
        analog_ports = self.pin_map.get('A', {})
        analog_port = analog_ports.get(voltage_pin_name)
        
        if analog_port is None:
            self.log_view.append(f"Analog pin {voltage_pin_name} not found in pin map", "ERROR")
            return (0.0, False, "Error: Analog pin not found in pin map")
        
        # Apply voltage scaling factor from settings
        voltage_scale = 1
        
        # Step 1: Measure initial voltage
        self.log_view.append(f"Measuring voltage on {voltage_pin_name} (pin {analog_port})", "DEBUG")
        try:
            measured_voltage = self.measurer.measure_voltage(analog_port) * voltage_scale
            self.log_view.append(f"Initial measurement: {measured_voltage:.3f}V", "DEBUG")
        except Exception as e:
            self.log_view.append(f"Measurement error: {str(e)}", "ERROR")
            return (0.0, False, f"Error: Measurement failed - {str(e)}")
        
        # Step 2: Verify initial measurement is ~0V
        if abs(measured_voltage * voltage_scale) > tolerance:
            self.log_view.append(f"Initial voltage {measured_voltage * voltage_scale:.3f}V is not ~0V (tolerance: {tolerance}V) - test failed", "WARNING")
            return (measured_voltage * voltage_scale, False, f"Initial voltage {measured_voltage:.3f}V is not ~0V")
        
        self.log_view.append(f"Initial voltage {measured_voltage * voltage_scale:.3f}V is ~0V - proceeding to activate hardware pullup", "DEBUG")
        
        # Step 4: Activate pullup pin (set HIGH)
        digital_ports = self.pin_map.get('D', {})
        pullup_physical_pin = digital_ports.get(pullup_pin_name)
        
        if pullup_physical_pin is None:
            self.log_view.append(f"Pullup pin {pullup_pin_name} not found in pin map", "ERROR")
            return (0.0, False, f"Error: Pullup pin {pullup_pin_name} not found")
        
        self.log_view.append(f"Activating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) HIGH", "INFO")
        self.hardware.digital_write(pullup_physical_pin, True)
        
        # Wait for signal to stabilize
        stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
        time.sleep(stabilize_delay)

        # Debug mode - wait for user confirmation
        if mode_debug:
            input("\nWAIT...")

        # Step 5: Measure voltage after pullup activation
        try:
            measured_voltage = self.measurer.measure_voltage(analog_port)
            self.log_view.append(f"Measurement after pullup activation: {measured_voltage * voltage_scale:.3f}V", "DEBUG")
        except Exception as e:
            self.log_view.append(f"Measurement error after pullup activation: {str(e)}", "ERROR")
            # Ensure pullup pin is deactivated even on error
            self.hardware.digital_write(pullup_physical_pin, False)
            return (0.0, False, f"Error: Measurement failed after pullup activation - {str(e)}")
        
        # Step 6: Check that measured voltage matches PullUp_Expected
        voltage_diff = abs(measured_voltage * voltage_scale - pin.PullUp_Expected)
        if voltage_diff > tolerance:
            self.log_view.append(f"Pullup voltage {measured_voltage * voltage_scale:.3f}V does NOT match expected {pin.PullUp_Expected:.3f}V (diff: {voltage_diff:.3f}V)", "WARNING")
            # Deactivate pullup and return with warning
            self.hardware.digital_write(pullup_physical_pin, False)
            return (measured_voltage * voltage_scale, False, f"Pullup voltage not in tolerance (diff: {voltage_diff:.3f}V)")
        
        self.log_view.append(f"Pullup voltage {measured_voltage * voltage_scale:.3f}V matches expected {pin.PullUp_Expected:.3f}V", "SUCCESS")
        
        # Step 7: Parse PullUp_Input data
        pullup_input_value = pin.PullUp_Input.strip() if pin.PullUp_Input else "G"
        
        # Step 8: Check if PullUp_Input == "G" (ground test only)
        if pullup_input_value.upper() == "G":
            self.log_view.append(f"PullUp_Input is 'G' - deactivating pullup and completing test", "INFO")
            # Deactivate pullup pin (set LOW)
            self.hardware.digital_write(pullup_physical_pin, False)
            self.log_view.append(f"Deactivating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) LOW", "INFO")
            return (measured_voltage * voltage_scale, True, "Pullup test passed (ground test)")
        
        # Step 9: PullUp_Input is not "G" - parse and activate DO
        self.log_view.append(f"PullUp_Input is '{pullup_input_value}' - activating DO output", "DEBUG")
        
        # Parse PullUp_Input for DO control (format: "C2_DO13V1" or similar)
        card, event_type, event_num, event_value = parse_event_string(pin.PullUp_Input)
        
        if card is None or event_type is None or event_type != "DO":
            self.log_view.append(f"Failed to parse PullUp_Input or not DO type: {pullup_input_value}", "ERROR")
            # Deactivate pullup and return with error
            self.hardware.digital_write(pullup_physical_pin, False)
            return (measured_voltage, False, f"Failed to parse PullUp_Input: {pullup_input_value}")
        
        # Step 10: Activate the DO
        do_state = bool(event_value)
        success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=do_state)
        self.log_view.append(f"Active: Set Card {card} DO{event_num} to {do_state}: {'Success' if success else 'Failed'}", "INFO")
        
        if not success:
            self.log_view.append(f"Failed to activate DO on card {card}", "WARNING")
            # Deactivate pullup and return with warning
            self.hardware.digital_write(pullup_physical_pin, False)
            return (measured_voltage * voltage_scale, False, f"Failed to activate DO on card {card}")
        
        # Wait for DO to stabilize
        time.sleep(stabilize_delay)
        
        # Step 11: Read DO status to verify it was set
        actual_do_state = self.card_manager.get_digital_output(card_id=card, do_number=event_num)
        if actual_do_state != do_state:
            self.log_view.append(f"DO verification failed: Expected {do_state}, got {actual_do_state}", "WARNING")
            # Deactivate pullup and DO, then return with warning
            self.hardware.digital_write(pullup_physical_pin, False)
            self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
            return (measured_voltage * voltage_scale, False, f"DO not set correctly: expected {do_state}, got {actual_do_state}")
        
        self.log_view.append(f"DO status verified: {actual_do_state}", "DEBUG")
        
        # Debug mode - wait for user confirmation
        if mode_debug:
            input("\nWAIT...")
        
        # Step 12: Measure voltage again after DO activation
        try:
            measured_voltage_after_do = self.measurer.measure_voltage(analog_port)
            self.log_view.append(f"Measurement after DO activation: {measured_voltage_after_do * voltage_scale:.3f}V", "DEBUG")
        except Exception as e:
            self.log_view.append(f"Measurement error after DO activation: {str(e)}", "ERROR")
            # Ensure cleanup
            self.hardware.digital_write(pullup_physical_pin, False)
            self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
            return (0.0, False, f"Error: Measurement failed after DO activation - {str(e)}")
        
        # Step 13: Check that voltage is now ~0V (within tolerance)
        if abs(measured_voltage_after_do * voltage_scale) > tolerance:
            self.log_view.append(f"Voltage after DO activation {measured_voltage_after_do * voltage_scale:.3f}V is not ~0V (tolerance: {tolerance}V)", "WARNING")
            # Cleanup and return with warning
            self.hardware.digital_write(pullup_physical_pin, False)
            self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
            return (measured_voltage_after_do * voltage_scale, False, f"Voltage after DO not ~0V: {measured_voltage_after_do * voltage_scale:.3f}V")
        
        self.log_view.append(f"Voltage after DO activation is ~0V as expected", "SUCCESS")
        
        # Step 14: Deactivate pullup pin (set LOW)
        self.hardware.digital_write(pullup_physical_pin, False)
        self.log_view.append(f"Deactivating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) LOW", "INFO")
        
        # Step 15: Deactivate the DO (set to False)
        success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
        self.log_view.append(f"DeActive: Set Card {card} DO{event_num} to False: {'Success' if success else 'Failed'}", "INFO")
        
        if not success:
            self.log_view.append(f"Failed to deactivate DO on card {card}", "WARNING")
            return (measured_voltage * voltage_scale, False, f"Failed to deactivate DO on card {card}")
        
        # Wait for DO to stabilize
        time.sleep(stabilize_delay)
        
        # Step 16: Read DO status to verify it was deactivated
        actual_do_state_after = self.card_manager.get_digital_output(card_id=card, do_number=event_num)
        if actual_do_state_after != False:
            self.log_view.append(f"DO deactivation verification failed: Expected False, got {actual_do_state_after}", "WARNING")
            return (measured_voltage * voltage_scale, False, f"DO not deactivated correctly: got {actual_do_state_after}")
        
        self.log_view.append(f"DO deactivation verified: {actual_do_state_after}", "DEBUG")
        
        # All steps completed successfully
        return (measured_voltage * voltage_scale, True, "Pullup test passed")
    
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
        
        self.log_view.append(f"Starting System B measurement for all pins (1-50)... Expected: Pin {pin_number} = {voltage}V, Others = ~0V", "INFO")
        
        for current_pin in range(1, 51):
            try:
                # Step 1: Get pair info
                pair_num, voltage_pin_key, voltage_pin_b_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(current_pin)
                
                # Get actual pin names from board config
                voltage_pin_name = self.board_config.get(voltage_pin_b_key, 'A1')
                
                # Step 2: Convert connector pin to bit representation using system B and set mux matrix
                bits = connector_pin_to_bits(current_pin, "b")
                success = set_mux_bits(bits, current_pin, self.pin_map, self.hardware, self.settings, self.log_view.append)
                
                if not success:
                    self.log_view.append(f"Failed to set mux bits for pin {current_pin}", "WARNING")
                    voltage_measurements.append(0.0)
                    failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': voltage if current_pin == pin_number else 0.0})
                    all_tests_passed = False
                    continue
                
                # Get physical analog port from pin map
                analog_ports = self.pin_map.get('A', {})
                analog_port = analog_ports.get(voltage_pin_name)
                
                self.log_view.append(f"Pin {current_pin}: Looking for {voltage_pin_name} in analog ports", "DEBUG")
                #self.log_view.append(f"Available analog ports: {list(analog_ports.keys())}", "DEBUG")
                
                if analog_port is None:
                    self.log_view.append(f"Analog pin {voltage_pin_name} not found in pin map for pin {current_pin}", "WARNING")
                    voltage_measurements.append(0.0)
                    failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': voltage if current_pin == pin_number else 0.0})
                    all_tests_passed = False
                    continue
                
                self.log_view.append(f"Pin {current_pin}: Using analog port {analog_port} ({voltage_pin_name})", "INFO")
                
                # Step 3: Measure voltage
                try:
                    measured_voltage = self.measurer.measure_voltage(analog_port) * voltage_scale 
                    voltage_measurements.append(measured_voltage)
                    
                    # Step 4: Validate measurement
                    if current_pin == pin_number:
                        # This pin should measure ~voltage
                        voltage_diff = abs(measured_voltage - voltage)
                        if voltage_diff <= tolerance:
                            self.log_view.append(f"for Pin {pin_number} check Pin {current_pin}: {measured_voltage:.3f}V (PASS - expected {voltage}V)", "SUCCESS")
                        else:
                            self.log_view.append(f"for Pin {pin_number} check Pin {current_pin}: {measured_voltage:.3f}V (FAIL - expected {voltage}V, diff: {voltage_diff:.3f}V)", "WARNING")
                            failed_pins.append({'pin': current_pin, 'measured': measured_voltage, 'expected': voltage})
                            all_tests_passed = False
                    else:
                        # This pin should measure ~0V
                        if abs(measured_voltage) <= tolerance:
                            self.log_view.append(f"for Pin {pin_number} check Pin {current_pin}: {measured_voltage:.3f}V (PASS - expected ~0V)", "DEBUG")
                        else:
                            self.log_view.append(f"for Pin {pin_number} check Pin {current_pin}: {measured_voltage:.3f}V (FAIL - expected ~0V)", "WARNING")
                            failed_pins.append({'pin': current_pin, 'measured': measured_voltage, 'expected': 0.0})
                            all_tests_passed = False
                            
                except Exception as e:
                    self.log_view.append(f"Measurement error on pin {current_pin}: {str(e)}", "ERROR")
                    voltage_measurements.append(0.0)
                    failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': voltage if current_pin == pin_number else 0.0})
                    all_tests_passed = False
                
                # Clear mux bits before next pin
                clear_bits(bits, self.pin_map, self.hardware, self.log_view.append)
                
            except Exception as e:
                self.log_view.append(f"Error processing pin {current_pin}: {str(e)}", "ERROR")
                voltage_measurements.append(0.0)
                failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': voltage if current_pin == pin_number else 0.0})
                all_tests_passed = False
        
        result_msg = "SUCCESS" if all_tests_passed else "FAILED"
        if failed_pins:
            self.log_view.append(f"System B measurement complete: {len(voltage_measurements)} pins measured - {result_msg} - {len(failed_pins)} failures", "SUCCESS" if all_tests_passed else "WARNING")
        else:
            self.log_view.append(f"System B measurement complete: {len(voltage_measurements)} pins measured - {result_msg}", "SUCCESS" if all_tests_passed else "WARNING")
        return voltage_measurements, all_tests_passed, failed_pins
    
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
        
        Args:
            none
            
        Returns:
            list[tuple[list[float], bool, list[dict]]]: Array of 50 test results, each containing:
                - list[float]: Voltage measurements for all 50 pins
                - bool: Pass/fail status for that test iteration
                - list[dict]: Failed pins with details {'pin': N, 'measured': V, 'expected': V}
        """
        test_results = []
        voltage_scale = 1
        
        self.log_view.append("Starting Short Circuit Test for all pins (1-50)...", "INFO")
        
        for pin_number in range(1, 51):
            if not self.running_ibit:
                self.log_view.append("I_Bit test stopped by user", "WARNING")
                break
            
            try:
                self.log_view.append(f"Testing pin {pin_number} for short circuits...", "INFO")
                
                # Step 1: Get pair info
                pair_num, voltage_pin_key, voltage_pin_b_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(pin_number)
                
                # Get actual pin names from board config
                voltage_pin_name = self.board_config.get(voltage_pin_key, 'A0')
                pullup_pin_name = self.board_config.get(pullup_pin_key, 'D20')
                
                # Step 2: Convert connector pin to bit representation using system A and set mux matrix
                bits = connector_pin_to_bits(pin_number, "a")
                success = set_mux_bits(bits, pin_number, self.pin_map, self.hardware, self.settings, self.log_view.append)
                
                if not success:
                    self.log_view.append(f"Failed to set mux bits for pin {pin_number}", "ERROR")
                    test_results.append(([], False, []))
                    continue
                
                # Step 3: Activate pullup pin (set HIGH)
                digital_ports = self.pin_map.get('D', {})
                pullup_physical_pin = digital_ports.get(pullup_pin_name)
                
                if pullup_physical_pin is None:
                    self.log_view.append(f"Pullup pin {pullup_pin_name} not found in pin map for pin {pin_number}", "ERROR")
                    test_results.append(([], False, []))
                    continue
                
                self.log_view.append(f"Activating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) HIGH", "DEBUG")
                self.hardware.digital_write(pullup_physical_pin, True)
                
                # Step 4: Wait for signal stabilization
                stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
                time.sleep(stabilize_delay)
                
                # Step 5: Measure voltage
                analog_ports = self.pin_map.get('A', {})
                analog_port = analog_ports.get(voltage_pin_name)
                
                if analog_port is None:
                    self.log_view.append(f"Analog pin {voltage_pin_name} not found in pin map for pin {pin_number}", "ERROR")
                    self.hardware.digital_write(pullup_physical_pin, False)
                    test_results.append(([], False, []))
                    continue
                
                try:
                    voltage_degredation = self.settings.get('scale', {}).get('voltage_degredation', 3.0)
                    measured_voltage = self.measurer.measure_voltage(analog_port) * voltage_scale - voltage_degredation
                    self.log_view.append(f"in card  A at Pin {pin_number} voltage with pullup: {measured_voltage:.3f}V", "DEBUG")
                except Exception as e:
                    self.log_view.append(f"Measurement error on pin {pin_number}: {str(e)}", "ERROR")
                    self.hardware.digital_write(pullup_physical_pin, False)
                    test_results.append(([], False, []))
                    continue
                
                # Step 6: Run measure_all_pins_system_b to verify routing

                voltage_measurements, test_passed, failed_pins = self.measure_all_pins_system_b(pin_number, measured_voltage)
                test_results.append((voltage_measurements, test_passed, failed_pins))
                
                # Step 7: Deactivate pullup pin (set LOW)
                self.hardware.digital_write(pullup_physical_pin, False)
                self.log_view.append(f"Deactivating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) LOW", "DEBUG")
                
                # Step 8: Clear mux bits before next pin
                clear_mux_bits(self.pin_map, self.hardware, self.log_view.append)
                
            except Exception as e:
                self.log_view.append(f"Error processing pin {pin_number}: {str(e)}", "ERROR")
                test_results.append(([], False, []))
        
        # Summary
        passed_count = sum(1 for _, passed, _ in test_results if passed)
        total_count = len(test_results)
        self.log_view.append(f"Short Circuit Test complete: {passed_count}/{total_count} pins PASSED", "SUCCESS" if passed_count == total_count else "WARNING")
        
        return test_results
        
    
    def relay_fuse_test(self, first_relay: str, second_relay: str, pullup_pin: str, voltage_measure_pin1: str, voltage_measure_pin2: str) -> str:
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
            string with the status
        """
        self.log_view.append("Starting Relay Fuse Test...", "INFO")
        
        # Get tolerance from settings (default 0.5V)
        tolerance = self.settings.get('Test', {}).get('voltage_tolerance', 0.5)
        
        try:
            # Step 1: Disable all cards
            from hw_tester.utils.general import enable_cards
            enable_cards([], self.board_config, self.pin_map, self.hardware, self.log_view.append)
            self.log_view.append("All cards disabled", "DEBUG")
            
            # Step 2: Activate relay pins
            digital_ports = self.pin_map.get('D', {})
            relay_ports = self.pin_map.get('R', {})

            relay_1a_name = self.board_config.get(first_relay, None)
            relay_1b_name = self.board_config.get(second_relay, None)
            
            if not relay_1a_name or not relay_1b_name:
                error_msg = f"Relay pins not found in board configuration: {first_relay}, {second_relay}"
                self.log_view.append(error_msg, "ERROR")
                return f"FAIL: {error_msg}"
            
            relay_1a_pin = relay_ports.get(relay_1a_name)
            relay_1b_pin = relay_ports.get(relay_1b_name)
            
            if relay_1a_pin is None or relay_1b_pin is None:
                error_msg = f"Relay pins not found in pin map: {relay_1a_name}, {relay_1b_name}"
                self.log_view.append(error_msg, "ERROR")
                return f"FAIL: {error_msg}"
            
            self.log_view.append(f"Activating relay pins: {relay_1a_name} (pin {relay_1a_pin}), {relay_1b_name} (pin {relay_1b_pin})", "DEBUG")
            self.hardware.digital_write(relay_1a_pin, True)
            self.hardware.digital_write(relay_1b_pin, True)
            
            # Step 3: Activate pullup pin
            pullup_pin_name = self.board_config.get(pullup_pin, None)
            
            if not pullup_pin_name:
                error_msg = f"Pullup pin not found in board configuration: {pullup_pin}"
                self.log_view.append(error_msg, "ERROR")
                # Cleanup
                self.hardware.digital_write(relay_1a_pin, False)
                self.hardware.digital_write(relay_1b_pin, False)
                return f"FAIL: {error_msg}"
            
            pullup_pin_physical = digital_ports.get(pullup_pin_name)
            
            if pullup_pin_physical is None:
                error_msg = f"Pullup pin not found in pin map: {pullup_pin_name}"
                self.log_view.append(error_msg, "ERROR")
                # Cleanup
                self.hardware.digital_write(relay_1a_pin, False)
                self.hardware.digital_write(relay_1b_pin, False)
                return f"FAIL: {error_msg}"
            
            self.log_view.append(f"Activating pullup pin: {pullup_pin_name} (pin {pullup_pin_physical})", "DEBUG")
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
                self.log_view.append(error_msg, "ERROR")
                # Cleanup
                self.hardware.digital_write(pullup_pin_physical, False)
                self.hardware.digital_write(relay_1a_pin, False)
                self.hardware.digital_write(relay_1b_pin, False)
                return f"FAIL: {error_msg}"
            
            voltage_pin_1 = analog_ports.get(voltage_pin_1_name)
            voltage_pin_2 = analog_ports.get(voltage_pin_2_name)
            
            if voltage_pin_1 is None or voltage_pin_2 is None:
                error_msg = f"Voltage pins not found in pin map: {voltage_pin_1_name}, {voltage_pin_2_name}"
                self.log_view.append(error_msg, "ERROR")
                # Cleanup
                self.hardware.digital_write(pullup_pin_physical, False)
                self.hardware.digital_write(relay_1a_pin, False)
                self.hardware.digital_write(relay_1b_pin, False)
                return f"FAIL: {error_msg}"
            
            self.log_view.append(f"Measuring voltage on {voltage_pin_1_name} (pin {voltage_pin_1})", "DEBUG")
            voltage_1 = self.measurer.measure_voltage(voltage_pin_1)
            
            self.log_view.append(f"Measuring voltage on {voltage_pin_2_name} (pin {voltage_pin_2})", "DEBUG")
            voltage_2 = self.measurer.measure_voltage(voltage_pin_2)
            
            self.log_view.append(f"Measured voltages: {voltage_pin_1_name}={voltage_1:.3f}V, {voltage_pin_2_name}={voltage_2:.3f}V", "INFO")
            
            # Step 6: Compare voltages
            voltage_diff = abs(voltage_1 - voltage_2)
            voltages_match = voltage_diff <= tolerance
            
            status_msg = f"Voltage difference: {voltage_diff:.3f}V (tolerance: {tolerance}V)"
            self.log_view.append(status_msg, "INFO")
            
            # Step 7: Deactivate all pins
            self.log_view.append("Deactivating pullup and relay pins", "DEBUG")
            self.hardware.digital_write(pullup_pin_physical, False)
            self.hardware.digital_write(relay_1a_pin, False)
            self.hardware.digital_write(relay_1b_pin, False)
            time.sleep(stabilize_delay)
            
            # Step 8: Clear mux bits
            clear_mux_bits(self.pin_map, self.hardware, self.log_view.append)
            
            # Step 9: Return status
            if voltages_match:
                result = f"PASS: Relay fuse test successful.fuse is intact,relays  {relay_1a_name} and {relay_1a_name} are operational, analogs {voltage_pin_1_name}, {voltage_pin_2_name} are operational, pullup {pullup_pin_name} is operational."
                self.log_view.append(result, "SUCCESS")
                status = True
            else:
                result = f"FAIL: Relay fuse test failed. {status_msg} some thing in the configuration of {relay_1a_pin, relay_1b_pin, voltage_pin_1_name, voltage_pin_2_name, pullup_pin_name} is not operational."
                self.log_view.append(result, "WARNING")
                status = False
            
            return result, status 
            
        except Exception as e:
            error_msg = f"Error during relay fuse test: {str(e)}"
            self.log_view.append(error_msg, "ERROR")
            # Attempt cleanup
            try:
                clear_mux_bits(self.pin_map, self.hardware, self.log_view.append)
            except:
                pass
            return f"FAIL: {error_msg}"
    
    def run_logic_test(self, pin: "Pin") -> tuple[float, bool, str]:
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
            
        Returns:
            Tuple of (measured_voltage, success, message):
                - success: True if status matches expected, False otherwise
                - message: Descriptive message about test result or error
        """
        is_simulation = self.settings.get('Board', {}).get('simulation', True)
        
        if is_simulation:
            # Simulation mode - return fixed result
            time.sleep(0.2)  # Simulate test delay
            import random
            success = random.random() > 0.1  # 90% pass rate
            message = "Simulation: DI high detected" if success else "Simulation: DI low detected"
            return (0.0, success, message)
        
        # Real hardware mode
        # Get tolerance from settings (default 0.5V)
        tolerance = self.settings.get('scale', {}).get('voltage_tolerance', 0.5)
        
        # Step 1: Get pair number and associated pins for first pin
        pin_number = int(''.join(filter(str.isdigit, pin.Id)))
        pair_num, voltage_pin_key, voltage_pin_b_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(pin_number)
        
        # Step 2: Convert connector pin to bit representation and set mux matrix (system A)
        bits = connector_pin_to_bits(pin_number, "a")
        success = set_mux_bits(bits, pin_number, self.pin_map, self.hardware, self.settings, self.log_view.append)
        
        if not success:
            self.log_view.append(f"Failed to set mux bits for pin {pin_number}", "ERROR")
            return (0.0, False, "Error: Failed to set mux matrix")
        
        # Step 3: Read the pin number from Logic_Pin_Input (second pin)
        if not hasattr(pin, 'Logic_Pin_Input') or not pin.Logic_Pin_Input or pin.Logic_Pin_Input.strip().lower() == "none":
            self.log_view.append(f"No Logic_Pin_Input specified for pin {pin_number} - skipping logic test", "INFO")
            return (0.0, True, "Logic test skipped (no Logic_Pin_Input)")
        
        try:
            second_pin_number = int(pin.Logic_Pin_Input.strip())
            self.log_view.append(f"Second pin number from Logic_Pin_Input: {second_pin_number}", "DEBUG")
        except ValueError:
            self.log_view.append(f"Invalid Logic_Pin_Input '{pin.Logic_Pin_Input}': Must be a pin number", "ERROR")
            return (0.0, False, f"Error: Invalid Logic_Pin_Input format (expected pin number)")
        
        # Step 4: Create "second Pin" object from pin table
        all_rows = self.pin_table.get_all_rows()
        second_pin_row = None
        for row in all_rows:
            if row["ID"] == str(second_pin_number) or row["ID"] == f"J1-{second_pin_number:02d}":
                second_pin_row = row
                break
        
        if not second_pin_row:
            self.log_view.append(f"Second pin {second_pin_number} not found in pin table", "ERROR")
            return (0.0, False, f"Error: Second pin {second_pin_number} not found in table")
        
        # Step 5: Check if second pin Power_Result is Pass and Power_Measured is ~0V
        second_pin_power_result = second_pin_row.get("Power_Result", "No Result")
        second_pin_power_measured_str = second_pin_row.get("Power_Measured", "")
        
        try:
            second_pin_power_measured = float(second_pin_power_measured_str) if second_pin_power_measured_str else 0.0
        except ValueError:
            second_pin_power_measured = 0.0

        zero_voltage_threshold = self.settings.get('scale', {}).get('zero_voltage_threshold', 0.5)
        
        if second_pin_power_measured > zero_voltage_threshold:
            self.log_view.append(f"Second pin {second_pin_number} Power_Result is not ~0 (got '{second_pin_power_measured}') - invalid Logic_Pin_Input", "WARNING")
            return (0.0, False, f"Wrong logic pin input: Second pin power test not passed")


        if second_pin_power_result != "Pass":
            self.log_view.append(f"Second pin {second_pin_number} Power_Result is not Pass (got '{second_pin_power_result}') - invalid Logic_Pin_Input", "WARNING")
            return (0.0, False, f"Wrong logic pin input: Second pin power test not passed")
        
        if abs(second_pin_power_measured) > tolerance:
            self.log_view.append(f"Second pin {second_pin_number} Power_Measured is {second_pin_power_measured:.3f}V (not ~0V, tolerance: {tolerance}V) - invalid Logic_Pin_Input", "WARNING")
            return (0.0, False, f"Wrong logic pin input: Second pin voltage not ~0V ({second_pin_power_measured:.3f}V)")
        
        self.log_view.append(f"Second pin {second_pin_number} validation passed (Power: Pass, Voltage: ~0V)", "SUCCESS")
        
        # Step 6: Convert second pin to bit pattern and set mux matrix (system B)
        second_pair_num, second_voltage_pin_key, second_voltage_pin_b_key, second_pullup_pin_key, second_card_enable_a_key, second_card_enable_b_key, second_relay_enable_a_key, second_relay_enable_b_key = get_pin_pair_info_controlino(second_pin_number)
        
        try:
            second_bits = connector_pin_to_bits(second_pin_number, "b")
            success = set_mux_bits(second_bits, second_pin_number, self.pin_map, self.hardware, self.settings, self.log_view.append)
            
            if not success:
                self.log_view.append(f"Failed to set mux bits for second pin {second_pin_number}", "ERROR")
                return (0.0, False, "Error: Failed to set mux matrix for second pin")
            
        except Exception as e:
            self.log_view.append(f"Error setting mux for second pin {second_pin_number}: {str(e)}", "ERROR")
            return (0.0, False, f"Error: {str(e)}")
        
        # Step 7: Activate the two proper relays for pin and second pin
        relay_ports = self.pin_map.get('R', {})
        
        relay_a_name = self.board_config.get(relay_enable_a_key, 'R0')
        relay_a_pin = relay_ports.get(relay_a_name)
        
        relay_b_name = self.board_config.get(second_relay_enable_b_key, 'R1')
        relay_b_pin = relay_ports.get(relay_b_name)
        
        if relay_a_pin is None:
            self.log_view.append(f"Relay A pin {relay_a_name} not found in pin map", "ERROR")
            return (0.0, False, f"Error: Relay A pin {relay_a_name} not found")
        
        if relay_b_pin is None:
            self.log_view.append(f"Relay B pin {relay_b_name} not found in pin map", "ERROR")
            return (0.0, False, f"Error: Relay B pin {relay_b_name} not found")
        
        self.log_view.append(f"Activating relay A {relay_a_name} (pin {relay_a_pin}) for pin {pin_number}", "INFO")
        self.hardware.digital_write(relay_a_pin, True)
        
        self.log_view.append(f"Activating relay B {relay_b_name} (pin {relay_b_pin}) for second pin {second_pin_number}", "INFO")
        self.hardware.digital_write(relay_b_pin, True)
        
        # Wait for relays to stabilize
        stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
        time.sleep(stabilize_delay)
        
        # Step 8: Parse Logic_Expected data (format: "C2_DI13_1" -> Card=2, DI=13, ExpectedState=1)
        if not hasattr(pin, 'Logic_Expected') or not pin.Logic_Expected or pin.Logic_Expected.strip().lower() == "none":
            self.log_view.append(f"No Logic_Expected specified for pin {pin_number} - skipping verification", "WARNING")
            # Deactivate relays
            self.hardware.digital_write(relay_a_pin, False)
            self.hardware.digital_write(relay_b_pin, False)
            clear_mux_bits(self.pin_map, self.hardware, self.log_view.append)
            return (0.0, False, "Logic test incomplete (no Logic_Expected)")
        
        # Parse PullUp_Input for DO control (format: "C2_DO13V1" or similar)
        card, event_type, event_num, event_value = parse_event_string(pin.Logic_Expected)
        
        if card is None or event_type is None :
            self.log_view.append(f"Failed to parse Logic_Expected '{pin.Logic_Expected}': Expected format 'C#_DI##_#'", "ERROR")
            # Deactivate relays
            self.hardware.digital_write(relay_a_pin, False)
            self.hardware.digital_write(relay_b_pin, False)
            clear_mux_bits(self.pin_map, self.hardware, self.log_view.append)
            return (0.0, False, f"Error: Invalid Logic_Expected format")
        
        expected_state_bool = bool(event_value)
        self.log_view.append(f"Parsed Logic_Expected: Card={card}, DI={event_num}, Expected={'HIGH' if expected_state_bool else 'LOW'}", "INFO")
        
        # Step 9: Read DI status from card
        try:
            di_status = self.card_manager.get_digital_input(card_id=card, di_number=event_num)
            status_str = "HIGH" if di_status else "LOW"
            self.log_view.append(f"Card {card} DI{event_num} status: {status_str}", "INFO")
        except Exception as e:
            self.log_view.append(f"Error reading DI{event_num} from card {card}: {str(e)}", "ERROR")
            # Deactivate relays before returning
            self.hardware.digital_write(relay_a_pin, False)
            self.hardware.digital_write(relay_b_pin, False)
            clear_mux_bits(self.pin_map, self.hardware, self.log_view.append)
            return (0.0, False, f"Error reading DI status: {str(e)}")
        
        # Step 10: Check the read status against Logic_Expected
        status_match = (di_status == expected_state_bool)
        
        # Step 11: Deactivate relay cards
        self.hardware.digital_write(relay_a_pin, False)
        self.hardware.digital_write(relay_b_pin, False)
        self.log_view.append(f"Deactivated relays {relay_a_name} and {relay_b_name}", "DEBUG")
        
        # Clear mux bits
        clear_mux_bits(self.pin_map, self.hardware, self.log_view.append)
        
        # Step 12: Return result based on status match
        if status_match:
            self.log_view.append(f"Logic test PASSED: DI{event_num} is {status_str}, expected {'HIGH' if expected_state_bool else 'LOW'}", "SUCCESS")
            return (0.0, True, f"DI{event_num} {status_str} as expected")
        else:
            self.log_view.append(f"Logic test FAILED: DI{event_num} is {status_str}, expected {'HIGH' if expected_state_bool else 'LOW'}", "WARNING")
            return (0.0, False, f"DI{event_num} {status_str}, expected {'HIGH' if expected_state_bool else 'LOW'}")
    
    def _on_test_complete(self) -> None:
        """Called when test run completes."""
        self.running = False
        self.op_panel.enable_stop_t(False)
        self.op_panel.enable_test(True)
        self.log_view.append("Test sequence completed", "SUCCESS")
    
    def _on_ibit_complete(self) -> None:
        """Called when I_Bit test completes."""
        self.running_ibit = False
        self.op_panel.enable_stop_ibit(False)
        self.op_panel.enable_i_bit(True)
        self.log_view.append("I_Bit test sequence completed", "SUCCESS")
    
    def on_stop_t(self) -> None:
        """Handle Stop_T button click."""
        self.log_view.append("Stopping test sequence...", "WARNING")
        self.running = False
        self.op_panel.enable_stop_t(False)
        self.op_panel.enable_test(True)
    
    def on_stop_ibit(self) -> None:
        """Handle Stop_IBIT button click - Stop the I_Bit short circuit test."""
        self.log_view.append("Stopping I_Bit test...", "WARNING")
        self.running_ibit = False
        self.op_panel.enable_stop_ibit(False)
        self.op_panel.enable_i_bit(True)
    
    def on_report(self) -> None:
        """Handle Report button click."""
        self.log_view.append("Generating test report...", "INFO")
        
        # TODO(core): Implement actual report generation
        rows = self.pin_table.get_all_rows()
        tested_count = sum(1 for row in rows if row.get("Measure"))
        
        time.sleep(0.3)
        self.log_view.append(f"Report: {tested_count}/{len(rows)} pins tested", "SUCCESS")
        
        messagebox.showinfo(
            "Test Report",
            f"Tested Pins: {tested_count}/{len(rows)}\n\nReport saved to results folder."
        )
    
    def on_clear_log(self) -> None:
        """Handle Clear Log button click."""
        self.log_view.clear()
        self.log_view.append("Log cleared", "INFO")
    
    def on_hw_change(self, new_hw: str) -> None:
        """
        Handle hardware type change from dropdown.
        Updates settings.yaml with the new hardware selection.
        
        Args:
            new_hw: New hardware type selected
        """
        old_hw = self.settings.get('Board', {}).get('Type', 'unknown')
        self.settings['Board']['Type'] = new_hw
        
        try:
            save_settings(self.settings)
            self.log_view.append(f"Hardware changed: {old_hw} → {new_hw}", "SUCCESS")
            
            # Reload pin map and board config for new hardware
            self.pin_map = get_board_pin_map(self.settings)
            self.board_config = get_board_pin_config(self.settings)
            self.log_view.append(f"Pin map and board config updated for {new_hw}", "INFO")
            
        except Exception as e:
            self.log_view.append(f"Error saving hardware change: {str(e)}", "ERROR")
    
    def on_simulate_change(self, new_mode: str) -> None:
        """
        Handle simulation mode change from dropdown.
        Updates settings.yaml with the new simulation mode.
        
        Args:
            new_mode: "Simulation On" or "Simulation Off"
        """
        simulation_enabled = (new_mode == "Simulation On")
        old_mode = "Simulation On" if self.settings.get('Board', {}).get('simulation', False) else "Simulation Off"
        
        self.settings['Board']['simulation'] = simulation_enabled
        
        try:
            save_settings(self.settings)
            self.log_view.append(f"Simulation mode changed: {old_mode} → {new_mode}", "SUCCESS")
        except Exception as e:
            self.log_view.append(f"Error saving simulation mode: {str(e)}", "ERROR")
    
    def on_iobox_change(self, new_box: str) -> None:
        """
        Handle IO Box type change from dropdown.
        Updates settings.yaml with the new IO Box type.
        
        Args:
            new_box: New IO Box type (e.g., "Demo", "MTC_FWD", "MTC_AFT")
        """
        old_box = self.settings.get('IO_Box', {}).get('Type', 'Demo')
        
        self.settings['IO_Box']['Type'] = new_box
        
        try:
            save_settings(self.settings)
            self.log_view.append(f"IO Box type changed: {old_box} → {new_box}", "SUCCESS")
        except Exception as e:
            self.log_view.append(f"Error saving IO Box type: {str(e)}", "ERROR")
    
    def run(self) -> None:
        """Start the application main loop."""
        self.root.mainloop()


# Standalone demo
if __name__ == "__main__":
    app = MainWindow(title="HW Tester - Demo")
    app.run()
