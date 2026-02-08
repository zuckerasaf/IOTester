"""
MainWindow - HW Tester application main window.
Integrates PinTableView, OperationalPanel, and LogView.
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import subprocess
import webbrowser
from datetime import datetime
import re
import openpyxl
from typing import List, Optional
import sys
from pathlib import Path
from hw_tester.hardware.controllino_io import connector_pin_to_bits
from hw_tester.hardware.pin import Pin
from hw_tester.utils.general import clear_mux_bits, parse_event_string, get_pin_pair_info_controlino, set_mux_bits, clear_bits, verify_card_output
from hw_tester.web.trace_writer import trace_step


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
from hw_tester.core.test_handle import TestHandle
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
        # Start maximized/fullscreen to see all columns
        self.root.state('zoomed')  # Windows: maximized window
        # Alternative for cross-platform fullscreen:
        # self.root.attributes('-fullscreen', True)
        
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
        
        # HTTP server process for HTML viewing
        self.http_server_process = None
        
        # Threading event for Next button debug control
        self.next_event = threading.Event()
        
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
        binding_errors = self.card_manager.start_all()  # Start communication threads
        
        # Initialize TestHandle for test execution logic
        self.test_handler = TestHandle(
            hardware=self.hardware,
            settings=self.settings,
            pin_map=self.pin_map,
            board_config=self.board_config,
            measurer=self.measurer,
            card_manager=self.card_manager,
            log_callback=self.log_view.append
        )
        # Share threading event and running flags
        self.test_handler.next_event = self.next_event
        
        # Display binding errors if any
        if binding_errors:
            for error in binding_errors:
                self.log_view.append(error, "ERROR")
            # Show error messagebox to notify user
            error_summary = "\n".join(binding_errors)
            messagebox.showerror(
                "UDP Binding Error",
                f"Failed to bind to one or more UDP cards:\n\n{error_summary}\n\n"
                f"The application will continue running, but affected cards will not function.\n"
                f"Check if another application is using the same ports."
                f"---"
                f"in case you wish to work with locahost run the switch_to_localhost.bat and start over the application."
            )
        
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
            on_test_all=self.on_test_all,
            on_doc=self.on_doc,
            on_stop_ibit=self.on_stop_ibit,
            on_stop_t=self.on_stop_t,
            on_report=self.on_report,
            on_clear_log=self.on_clear_log,
            settings=self.settings,
            on_hw_change=self.on_hw_change,
            on_simulate_change=self.on_simulate_change,
            on_iobox_change=self.on_iobox_change,
            on_log_filter_change=self.on_log_filter_change,
            on_localhost_change=self.on_localhost_change,
            on_next=self.on_next,
            on_html_file_change=self.on_html_file_change,
            on_debug_change=self.on_debug_change
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
                        "Discrete_Name": pin.Discrete_Name,
                        "Signal_Name": pin.Signal_Name,
                        "Plug": pin.Plug,
                        "Type": pin.Type,
                        "Pin": pin.Pin,
                        "Power_Expected": f"{pin.Power_Expected:.2f}",
                        "Power_Input": pin.Power_Input,
                        "Power_Measured": "" if pin.Power_Measured == 0.0 else f"{pin.Power_Measured:.2f}",
                        "Power_Result": pin.Power_Result.value,
                        "Power_Result_Reason": "",
                        "PullUp_Expected": f"{pin.PullUp_Expected:.2f}",
                        "PullUp_Input": pin.PullUp_Input,
                        "PullUp_Measured": "" if pin.PullUp_Measured == 0.0 else f"{pin.PullUp_Measured:.2f}",
                        "PullUp_Result": pin.PullUp_Result.value,
                        "PullUp_Result_Reason": "",
                        "Logic_Pin_Input": str(pin.Logic_Pin_Input),
                        "Logic_Command": str(pin.Logic_Command),
                        "Logic_Expected": str(pin.Logic_Expected),
                        "Logic_DI_Result": pin.Logic_DI_Result.value,
                        "Logic_DI_Result_Reason": ""
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
        self.op_panel.set_connector(filename.split(".")[0])  # Show filename instead of connector ID without the .xlsx
        self.connected = True
        self.op_panel.enable_test(True)
        self.op_panel.enable_test_all(True)
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

                if timer == 999:
                    self.log_view.append(f"on keep alive-  Error pulsing {port_name} (port {port_number}) - Invalid port state", "ERROR")

                self.log_view.append(f"Pulsing {port_name} (port {port_number})", "DEBUG")
            except Exception as e:
                self.log_view.append(f"on keep alive-  Error pulsing {port_name}: {str(e)}", "ERROR")
        
        self.log_view.append(f"KeepAlive pulse sequence initiated for all {len(digital_ports)} ports", "SUCCESS")
    
    def on_next(self) -> None:
        """Handle Next button click - Resume test execution from debug pause."""
        self.next_event.set()
        self.log_view.append("Next button pressed - resuming execution", "INFO")
    
    def on_i_bit(self) -> None:
        """Handle I_Bit button click - Run short circuit test on all pins."""
        self.log_view.append("Starting I_Bit short circuit test...", "INFO")
        self.running_ibit = True
        self.op_panel.enable_stop_ibit(True)
        self.op_panel.enable_i_bit(False)
        
        # Run short circuit test in background thread using TestHandle
        def run_i_bit_test():
            try:
                pair1_test_results,pair1_test_status = self.test_handler.relay_fuse_test("enable_Relay_pin_1_A","enable_Relay_pin_1_B","pullup_pins_pin_pair1","voltage_measure_pin_pair1","voltage_measure_pin_pair1_B")
                pair2_test_results,pair2_test_status = self.test_handler.relay_fuse_test("enable_Relay_pin_2_A","enable_Relay_pin_2_B","pullup_pins_pin_pair2","voltage_measure_pin_pair2","voltage_measure_pin_pair2_B")
                pair3_test_results,pair3_test_status = self.test_handler.relay_fuse_test("enable_Relay_pin_3_A","enable_Relay_pin_3_B","pullup_pins_pin_pair3","voltage_measure_pin_pair3","voltage_measure_pin_pair3_B")
                pair4_test_results,pair4_test_status = self.test_handler.relay_fuse_test("enable_Relay_pin_4_A","enable_Relay_pin_4_B","pullup_pins_pin_pair4","voltage_measure_pin_pair4","voltage_measure_pin_pair4_B")

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
                test_results = self.test_handler.short_circuit_test()
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

        all_rows = self.pin_table.get_all_rows()
        self._start_test(selected_ids, all_rows, "selected")

    def on_test_all(self) -> None:
        """Handle Test_All button click - Execute test sequence for all pins."""
        if not self.connected:
            self.log_view.append("Not connected. Please connect first.", "WARNING")
            return

        all_rows = self.pin_table.get_all_rows()
        if not all_rows:
            self.log_view.append("No pins available. Please load pins first.", "WARNING")
            return

        self.pin_table.select_all()
        selected_ids = [row.get("ID", "") for row in all_rows if row.get("ID")]
        self._start_test(selected_ids, all_rows, "all")

    def _start_test(self, selected_ids: List[str], all_rows: List[dict], scope_label: str) -> None:
        """Start a test run for the provided pin IDs."""
        if not selected_ids:
            self.log_view.append("No pins selected. Please select pins to test.", "WARNING")
            return
        
        # Clear all Measure column data before starting test
        for row in all_rows:
            self.pin_table.update_row(row["ID"], {"Measure": ""})
        
        is_simulation = self.settings.get('Board', {}).get('simulation', True)
        mode_str = "SIMULATION" if is_simulation else "HARDWARE"
        label = "all" if scope_label == "all" else "selected"
        self.log_view.append(f"Starting test sequence on {len(selected_ids)} {label} pins ({mode_str} mode)", "INFO")
        self.running = True
        self.test_handler.running = True  # Sync flag to test handler
        self.op_panel.enable_stop_t(True)
        self.op_panel.enable_test(False)
        self.op_panel.enable_test_all(False)
        
        # Get digital pin map for bit setting
        #digital_ports = self.pin_map.get('D', {})
        
        # Get all rows to access pin types
        all_rows = self.pin_table.get_all_rows()
        pin_types = {row["ID"]: row.get("type", "") for row in all_rows}
        
        # Run test sequence in background using TestHandle
        threading.Thread(
            target=self.test_handler.run_tests,
            args=(selected_ids, all_rows, self.root, self.pin_table, self._on_test_complete),
            daemon=True
        ).start()
    
    def wait_debug(self,ID: int = 0, status: str = "active") -> None:
        """
        Pause execution for debugging purposes.
        Waits for user to press next button .
        """
        trace_step(ID, status)

        self.root.after(0, lambda: self.log_view.append("Waiting for Next button press to continue...", "INFO"))
        self.next_event.wait()  # Wait for Next button press
        self.next_event.clear()  # Reset event for next pause
        self.root.after(0, lambda: self.log_view.append("Continuing test execution...", "INFO"))

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
    
    
    # def measure_all_pins_system_b(self, pin_number: int, voltage: float) -> tuple[list[float], bool, list[dict]]:
    #     """
    #     System B measurement for loop run with validation.
        
    #     Test Procedure:
    #     1. For each pin 1-50: Get pair info (voltage_measure_pin, pullup_pin, card enables, etc.) for connector pin
    #     2. Convert connector pin number to bit pattern and set mux matrix (D0-D15) - system B
    #     3. Measure voltage on pair-specific analog pin
    #     4. Validate measurements:
    #        - Pin matching pin_number should measure ~voltage (within tolerance)
    #        - All other pins should measure ~0V (within tolerance)
    #     5. Return result (array of 50 voltage measurement values + pass/fail status + failed pins list)
        
    #     Args:
    #         pin_number: The pin number that should show the voltage (1-50)
    #         voltage: Expected voltage value on the specified pin
            
    #     Returns:
    #         tuple[list[float], bool, list[dict]]: 
    #             - Array of 50 final voltage readings in volts
    #             - True if all measurements pass validation, False otherwise
    #             - List of failed pins with format: [{'pin': int, 'measured': float, 'expected': float}, ...]
    #     """
    #     voltage_measurements = []
    #     failed_pins = []  # Track failed pins with their measurements
    #     voltage_scale = 1
    #     tolerance = self.settings.get('Test', {}).get('voltage_degredation', 3.0)
    #     all_tests_passed = True
        
    #     self.log_view.append(f"Starting System B measurement for all pins (1-50)... Expected: Pin {pin_number} = {voltage}V, Others = ~0V", "INFO")
        
    #     for current_pin in range(1, 51):
    #         try:
    #             # Step 1: Get pair info
    #             pair_num, voltage_pin_key, voltage_pin_b_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(current_pin)
                
    #             # Get actual pin names from board config
    #             voltage_pin_name = self.board_config.get(voltage_pin_b_key, 'A1')
                
    #             # Step 2: Convert connector pin to bit representation using system B and set mux matrix
    #             bits = connector_pin_to_bits(current_pin, "b")
    #             success = set_mux_bits(bits, current_pin, self.pin_map, self.hardware, self.settings, self.log_view.append)
                
    #             if not success:
    #                 self.log_view.append(f"Failed to set mux bits for pin {current_pin}", "WARNING")
    #                 voltage_measurements.append(0.0)
    #                 failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': voltage if current_pin == pin_number else 0.0})
    #                 all_tests_passed = False
    #                 continue
                
    #             # Get physical analog port from pin map
    #             analog_ports = self.pin_map.get('A', {})
    #             analog_port = analog_ports.get(voltage_pin_name)
                
    #             self.log_view.append(f"Pin {current_pin}: Looking for {voltage_pin_name} in analog ports", "DEBUG")
    #             #self.log_view.append(f"Available analog ports: {list(analog_ports.keys())}", "DEBUG")
                
    #             if analog_port is None:
    #                 self.log_view.append(f"Analog pin {voltage_pin_name} not found in pin map for pin {current_pin}", "WARNING")
    #                 voltage_measurements.append(0.0)
    #                 failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': voltage if current_pin == pin_number else 0.0})
    #                 all_tests_passed = False
    #                 continue
                
    #             self.log_view.append(f"Pin {current_pin}: Using analog port {analog_port} ({voltage_pin_name})", "INFO")
                
    #             # Step 3: Measure voltage
    #             try:
    #                 measured_voltage = self.measurer.measure_voltage(analog_port) * voltage_scale 
    #                 voltage_measurements.append(measured_voltage)
                    
    #                 # Step 4: Validate measurement
    #                 if current_pin == pin_number:
    #                     # This pin should measure ~voltage
    #                     voltage_diff = abs(measured_voltage - voltage)
    #                     if voltage_diff <= tolerance:
    #                         self.log_view.append(f"in measure all pins sys B -  Pin {pin_number} check Pin {current_pin}: {measured_voltage:.3f}V (PASS - expected {voltage}V)", "SUCCESS")
    #                     else:
    #                         self.log_view.append(f"in measure all pins sys B  - Pin {pin_number} check Pin {current_pin}: {measured_voltage:.3f}V (FAIL - expected {voltage}V, diff: {voltage_diff:.3f}V)", "WARNING")
    #                         failed_pins.append({'pin': current_pin, 'measured': measured_voltage, 'expected': voltage})
    #                         all_tests_passed = False
    #                 else:
    #                     # This pin should measure ~0V
    #                     if abs(measured_voltage) <= tolerance:
    #                         self.log_view.append(f"for Pin {pin_number} check Pin {current_pin}: {measured_voltage:.3f}V (PASS - expected ~0V)", "DEBUG")
    #                     else:
    #                         self.log_view.append(f"in measure all pins sys B - for Pin {pin_number} check Pin {current_pin}: {measured_voltage:.3f}V (FAIL - expected ~0V)", "WARNING")
    #                         failed_pins.append({'pin': current_pin, 'measured': measured_voltage, 'expected': 0.0})
    #                         all_tests_passed = False
                            
    #             except Exception as e:
    #                 self.log_view.append(f"in measure all pins sys B -Measurement error on pin {current_pin}: {str(e)}", "ERROR")
    #                 voltage_measurements.append(0.0)
    #                 failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': voltage if current_pin == pin_number else 0.0})
    #                 all_tests_passed = False
                
    #             # Clear mux bits before next pin
    #             clear_bits(bits, self.pin_map, self.hardware, self.log_view.append)
                
    #         except Exception as e:
    #             self.log_view.append(f"in measure all pins sys B -Error processing pin {current_pin}: {str(e)}", "ERROR")
    #             voltage_measurements.append(0.0)
    #             failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': voltage if current_pin == pin_number else 0.0})
    #             all_tests_passed = False
        
    #     result_msg = "SUCCESS" if all_tests_passed else "FAILED"
    #     if failed_pins:
    #         self.log_view.append(f"System B measurement complete: {len(voltage_measurements)} pins measured - {result_msg} - {len(failed_pins)} failures", "SUCCESS" if all_tests_passed else "WARNING")
    #     else:
    #         self.log_view.append(f"System B measurement complete: {len(voltage_measurements)} pins measured - {result_msg}", "SUCCESS" if all_tests_passed else "WARNING")
    #     return voltage_measurements, all_tests_passed, failed_pins
    
    # def short_circuit_test(self) -> list[tuple[list[float], bool, list[dict]]]:
    #     """
    #     Short circuit test for all pins.
        
    #     Test Procedure:
    #     1. For each pin 1-50: Get pair info (voltage_measure_pin, pullup_pin, card enables, etc.) for connector pin
    #     2. Convert connector pin number to bit pattern and set mux matrix (D0-D15) - system A
    #     3. Activate pullup_pin_key (set HIGH)
    #     4. Wait for signal stabilization
    #     5. Measure voltage
    #     6. Run measure_all_pins_system_b(pin_number, measured_voltage) to verify routing
    #     7. Deactivate pullup_pin_key (set LOW)
    #     8. Clear mux bits
    #     9. Return result (array of test results from measure_all_pins_system_b)
        
    #     Args:
    #         none
            
    #     Returns:
    #         list[tuple[list[float], bool, list[dict]]]: Array of 50 test results, each containing:
    #             - list[float]: Voltage measurements for all 50 pins
    #             - bool: Pass/fail status for that test iteration
    #             - list[dict]: Failed pins with details {'pin': N, 'measured': V, 'expected': V}
    #     """
    #     test_results = []
    #     voltage_scale = 1
        
    #     self.log_view.append("Starting Short Circuit Test for all pins (1-50)...", "INFO")
        
    #     for pin_number in range(1, 51):
    #         if not self.running_ibit:
    #             self.log_view.append("I_Bit test stopped by user", "WARNING")
    #             break
            
    #         try:
    #             self.log_view.append(f"Testing pin {pin_number} for short circuits...", "INFO")
                
    #             # Step 1: Get pair info
    #             pair_num, voltage_pin_key, voltage_pin_b_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(pin_number)
                
    #             # Get actual pin names from board config
    #             voltage_pin_name = self.board_config.get(voltage_pin_key, 'A0')
    #             pullup_pin_name = self.board_config.get(pullup_pin_key, 'D20')
                
    #             # Step 2: Convert connector pin to bit representation using system A and set mux matrix
    #             bits = connector_pin_to_bits(pin_number, "a")
    #             success = set_mux_bits(bits, pin_number, self.pin_map, self.hardware, self.settings, self.log_view.append)
                
    #             if not success:
    #                 self.log_view.append(f"on short circut test  - Failed to set mux bits for pin {pin_number}", "ERROR")
    #                 test_results.append(([], False, []))
    #                 continue
                
    #             # Step 3: Activate pullup pin (set HIGH)
    #             digital_ports = self.pin_map.get('D', {})
    #             pullup_physical_pin = digital_ports.get(pullup_pin_name)
                
    #             if pullup_physical_pin is None:
    #                 self.log_view.append(f"on short circut test - Pullup pin {pullup_pin_name} not found in pin map for pin {pin_number}", "ERROR")
    #                 test_results.append(([], False, []))
    #                 continue
                
    #             self.log_view.append(f"Activating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) HIGH", "DEBUG")
    #             self.hardware.digital_write(pullup_physical_pin, True)
                
    #             # Step 4: Wait for signal stabilization
    #             stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
    #             time.sleep(stabilize_delay)
                
    #             # Step 5: Measure voltage
    #             analog_ports = self.pin_map.get('A', {})
    #             analog_port = analog_ports.get(voltage_pin_name)
                
    #             if analog_port is None:
    #                 self.log_view.append(f"in short circuit test - Analog pin {voltage_pin_name} not found in pin map for pin {pin_number}", "ERROR")
    #                 self.hardware.digital_write(pullup_physical_pin, False)
    #                 test_results.append(([], False, []))
    #                 continue
                
    #             try:
    #                 voltage_degredation = self.settings.get('scale', {}).get('voltage_degredation', 3.0)
    #                 measured_voltage = self.measurer.measure_voltage(analog_port) * voltage_scale - voltage_degredation
    #                 self.log_view.append(f"in card  A at Pin {pin_number} voltage with pullup: {measured_voltage:.3f}V", "DEBUG")
    #             except Exception as e:
    #                 self.log_view.append(f"in short circut test  - Measurement error on pin {pin_number}: {str(e)}", "ERROR")
    #                 self.hardware.digital_write(pullup_physical_pin, False)
    #                 test_results.append(([], False, []))
    #                 continue
                
    #             # Step 6: Run measure_all_pins_system_b to verify routing

    #             voltage_measurements, test_passed, failed_pins = self.measure_all_pins_system_b(pin_number, measured_voltage)
    #             test_results.append((voltage_measurements, test_passed, failed_pins))
                
    #             # Step 7: Deactivate pullup pin (set LOW)
    #             self.hardware.digital_write(pullup_physical_pin, False)
    #             self.log_view.append(f"Deactivating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) LOW", "DEBUG")
                
    #             # Step 8: Clear mux bits before next pin
    #             clear_mux_bits(self.pin_map, self.hardware, self.log_view.append)
                
    #         except Exception as e:
    #             self.log_view.append(f"Error in short circuit test processing pin {pin_number}: {str(e)}", "ERROR")
    #             test_results.append(([], False, []))
        
    #     # Summary
    #     passed_count = sum(1 for _, passed, _ in test_results if passed)
    #     total_count = len(test_results)
    #     self.log_view.append(f"Short Circuit Test complete: {passed_count}/{total_count} pins PASSED", "SUCCESS" if passed_count == total_count else "WARNING")
        
    #     return test_results
        
    
    # def relay_fuse_test(self, first_relay: str, second_relay: str, pullup_pin: str, voltage_measure_pin1: str, voltage_measure_pin2: str) -> str:
    #     """
    #     Relay fuse test.
        
    #     Test Procedure:
    #     1. Disable all cards - use the enable_cards() with no input
    #     2. Activate first_relay and second_relay
    #     3. Activate pullup_pin
    #     4. Wait for signal stabilization
    #     5. Measure voltage on voltage_measure_pin1, voltage_measure_pin2
    #     6. Status check that the voltage_measure_pin1, voltage_measure_pin2 are the same
    #     7. Deactivate pullup_pin (set LOW) and deactivate first_relay, second_relay
    #     8. Clear mux bits
    #     9. Return status of the compare
        
    #     Args:
    #         first_relay: Name of first relay pin (e.g., 'enable_Relay_pin_1_A')
    #         second_relay: Name of second relay pin (e.g., 'enable_Relay_pin_1_B')
    #         pullup_pin: Name of pullup pin (e.g., 'pullup_pins_pin_pair1')
    #         voltage_measure_pin1: Name of first voltage measurement pin (e.g., 'voltage_measure_pin_pair1')
    #         voltage_measure_pin2: Name of second voltage measurement pin (e.g., 'voltage_measure_pin_pair2')
            
    #     Returns:
    #         string with the status
    #     """
    #     self.log_view.append("Starting Relay Fuse Test...", "INFO")
        
    #     # Get tolerance from settings (default 0.5V)
    #     tolerance = self.settings.get('Test', {}).get('voltage_tolerance', 0.5)
        
    #     try:
    #         # Step 1: Disable all cards
    #         from hw_tester.utils.general import enable_cards
    #         enable_cards([], self.board_config, self.pin_map, self.hardware, self.log_view.append)
    #         self.log_view.append("All cards disabled", "DEBUG")
            
    #         # Step 2: Activate relay pins
    #         digital_ports = self.pin_map.get('D', {})
    #         relay_ports = self.pin_map.get('R', {})

    #         relay_1a_name = self.board_config.get(first_relay, None)
    #         relay_1b_name = self.board_config.get(second_relay, None)
            
    #         if not relay_1a_name or not relay_1b_name:
    #             error_msg = f"Relay pins not found in board configuration: {first_relay}, {second_relay}"
    #             self.log_view.append(error_msg, "ERROR")
    #             return f"FAIL: {error_msg}"
            
    #         relay_1a_pin = relay_ports.get(relay_1a_name)
    #         relay_1b_pin = relay_ports.get(relay_1b_name)
            
    #         if relay_1a_pin is None or relay_1b_pin is None:
    #             error_msg = f"Relay pins not found in pin map: {relay_1a_name}, {relay_1b_name}"
    #             self.log_view.append(error_msg, "ERROR")
    #             return f"FAIL: {error_msg}"
            
    #         self.log_view.append(f"Activating relay pins: {relay_1a_name} (pin {relay_1a_pin}), {relay_1b_name} (pin {relay_1b_pin})", "DEBUG")
    #         self.hardware.digital_write(relay_1a_pin, True)
    #         self.hardware.digital_write(relay_1b_pin, True)
            
    #         # Step 3: Activate pullup pin
    #         pullup_pin_name = self.board_config.get(pullup_pin, None)
            
    #         if not pullup_pin_name:
    #             error_msg = f"Pullup pin not found in board configuration: {pullup_pin}"
    #             self.log_view.append(error_msg, "ERROR")
    #             # Cleanup
    #             self.hardware.digital_write(relay_1a_pin, False)
    #             self.hardware.digital_write(relay_1b_pin, False)
    #             return f"FAIL: {error_msg}"
            
    #         pullup_pin_physical = digital_ports.get(pullup_pin_name)
            
    #         if pullup_pin_physical is None:
    #             error_msg = f"Pullup pin not found in pin map: {pullup_pin_name}"
    #             self.log_view.append(error_msg, "ERROR")
    #             # Cleanup
    #             self.hardware.digital_write(relay_1a_pin, False)
    #             self.hardware.digital_write(relay_1b_pin, False)
    #             return f"FAIL: {error_msg}"
            
    #         self.log_view.append(f"Activating pullup pin: {pullup_pin_name} (pin {pullup_pin_physical})", "DEBUG")
    #         self.hardware.digital_write(pullup_pin_physical, True)
            
    #         # Step 4: Wait for signal stabilization
    #         stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
    #         time.sleep(stabilize_delay)
            
    #         # Step 5: Measure voltages on both pairs
    #         analog_ports = self.pin_map.get('A', {})
            
    #         voltage_pin_1_name = self.board_config.get(voltage_measure_pin1, None)
    #         voltage_pin_2_name = self.board_config.get(voltage_measure_pin2, None)
            
    #         if not voltage_pin_1_name or not voltage_pin_2_name:
    #             error_msg = f"Voltage measurement pins not found in board configuration: {voltage_measure_pin1}, {voltage_measure_pin2}"
    #             self.log_view.append(error_msg, "ERROR")
    #             # Cleanup
    #             self.hardware.digital_write(pullup_pin_physical, False)
    #             self.hardware.digital_write(relay_1a_pin, False)
    #             self.hardware.digital_write(relay_1b_pin, False)
    #             return f"FAIL: {error_msg}"
            
    #         voltage_pin_1 = analog_ports.get(voltage_pin_1_name)
    #         voltage_pin_2 = analog_ports.get(voltage_pin_2_name)
            
    #         if voltage_pin_1 is None or voltage_pin_2 is None:
    #             error_msg = f"Voltage pins not found in pin map: {voltage_pin_1_name}, {voltage_pin_2_name}"
    #             self.log_view.append(error_msg, "ERROR")
    #             # Cleanup
    #             self.hardware.digital_write(pullup_pin_physical, False)
    #             self.hardware.digital_write(relay_1a_pin, False)
    #             self.hardware.digital_write(relay_1b_pin, False)
    #             return f"FAIL: {error_msg}"
            
    #         self.log_view.append(f"Measuring voltage on {voltage_pin_1_name} (pin {voltage_pin_1})", "DEBUG")
    #         voltage_1 = self.measurer.measure_voltage(voltage_pin_1)
            
    #         self.log_view.append(f"Measuring voltage on {voltage_pin_2_name} (pin {voltage_pin_2})", "DEBUG")
    #         voltage_2 = self.measurer.measure_voltage(voltage_pin_2)
            
    #         self.log_view.append(f"Measured voltages: {voltage_pin_1_name}={voltage_1:.3f}V, {voltage_pin_2_name}={voltage_2:.3f}V", "INFO")
            
    #         # Step 6: Compare voltages
    #         voltage_diff = abs(voltage_1 - voltage_2)
    #         voltages_match = voltage_diff <= tolerance
            
    #         status_msg = f"Voltage difference: {voltage_diff:.3f}V (tolerance: {tolerance}V)"
    #         self.log_view.append(status_msg, "INFO")
            
    #         # Step 7: Deactivate all pins
    #         self.log_view.append("Deactivating pullup and relay pins", "DEBUG")
    #         self.hardware.digital_write(pullup_pin_physical, False)
    #         self.hardware.digital_write(relay_1a_pin, False)
    #         self.hardware.digital_write(relay_1b_pin, False)
    #         time.sleep(stabilize_delay)
            
    #         # Step 8: Clear mux bits
    #         clear_mux_bits(self.pin_map, self.hardware, self.log_view.append)
            
    #         # Step 9: Return status
    #         if voltages_match:
    #             result = f"PASS: Relay fuse test successful.fuse is intact,relays  {relay_1a_name} and {relay_1a_name} are operational, analogs {voltage_pin_1_name}, {voltage_pin_2_name} are operational, pullup {pullup_pin_name} is operational."
    #             self.log_view.append(result, "SUCCESS")
    #             status = True
    #         else:
    #             result = f"FAIL: Relay fuse test failed. {status_msg} some thing in the configuration of {relay_1a_pin, relay_1b_pin, voltage_pin_1_name, voltage_pin_2_name, pullup_pin_name} is not operational."
    #             self.log_view.append(result, "WARNING")
    #             status = False
            
    #         return result, status 
            
    #     except Exception as e:
    #         error_msg = f"Error during relay fuse test: {str(e)}"
    #         self.log_view.append(error_msg, "ERROR")
    #         # Attempt cleanup
    #         try:
    #             clear_mux_bits(self.pin_map, self.hardware, self.log_view.append)
    #         except:
    #             pass
    #         return f"FAIL: {error_msg}"
    

    def _on_test_complete(self) -> None:
        """Called when test run completes."""
        self.running = False
        self.op_panel.enable_stop_t(False)
        self.op_panel.enable_test(True)
        self.op_panel.enable_test_all(True)
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
        self.test_handler.running = False  # Sync flag to test handler
        self.op_panel.enable_stop_t(False)
        self.op_panel.enable_test(True)
        self.op_panel.enable_test_all(True)
    
    def on_stop_ibit(self) -> None:
        """Handle Stop_IBIT button click - Stop the I_Bit short circuit test."""
        self.log_view.append("Stopping I_Bit test...", "WARNING")
        self.running_ibit = False
        self.test_handler.running_ibit = False  # Sync flag to test handler
        self.op_panel.enable_stop_ibit(False)
        self.op_panel.enable_i_bit(True)
    
    def on_report(self) -> None:
        """Handle Report button click.

        Creates an Excel file named with the connector label and current
        timestamp in the reports directory configured in settings (falls
        back to workspace Results folder). Copies all pin table rows
        into the spreadsheet and notifies the user.
        """
        try:
            self.log_view.append("Generating test report...", "INFO")

            # Get rows from pin table
            rows = self.pin_table.get_all_rows()

            # Determine connector name from operational panel label
            try:
                connector_name = self.op_panel.connector_label.cget("text")
            except Exception:
                connector_name = "connector"

            # Sanitize connector name for filename
            safe_name = re.sub(r"[^0-9A-Za-z._-]", "_", connector_name).strip("_") or "connector"

            # Build timestamped filename
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_name}_{ts}.xlsx"

            # Determine reports directory from settings or default Results folder
            reports_dir_setting = self.settings.get('Paths', {}).get('reports', None)
            if reports_dir_setting:
                reports_dir = Path(reports_dir_setting)
            else:
                # Use workspace Results folder relative to cwd
                reports_dir = Path.cwd() / "Results"

            reports_dir.mkdir(parents=True, exist_ok=True)
            out_path = reports_dir / filename

            # Create Excel workbook and write rows
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Report"

            if rows:
                # Write header from keys of first row
                headers = list(rows[0].keys())
                ws.append(headers)

                for row in rows:
                    # Ensure consistent order matching headers
                    ws.append([row.get(h, "") for h in headers])
            else:
                ws.append(["No data"])

            wb.save(str(out_path))

            tested_count = sum(1 for row in rows if row.get("Measure"))
            self.log_view.append(f"Report: {tested_count}/{len(rows)} pins tested - saved to {out_path}", "SUCCESS")

            messagebox.showinfo(
                "Test Report",
                f"Tested Pins: {tested_count}/{len(rows)}\n\nReport saved to: {out_path}"
            )

        except Exception as e:
            error_msg = f"Error generating report: {e}"
            self.log_view.append(error_msg, "ERROR")
            messagebox.showerror("Report Error", error_msg)

    def on_doc(self) -> None:
        """Handle DOC button click (placeholder)."""
        try:
            from hw_tester.core.doc_handle import create_doc_report_via_dialog

            output_path = create_doc_report_via_dialog()
            if output_path:
                self.log_view.append(f"DOC report saved to {output_path}", "SUCCESS")
            else:
                self.log_view.append("DOC report creation canceled", "INFO")
        except Exception as e:
            error_msg = f"DOC report generation failed: {e}"
            self.log_view.append(error_msg, "ERROR")
            messagebox.showerror("DOC Report Error", error_msg)
    
    def on_clear_log(self) -> None:
        """Handle Clear Log button click."""
        self.log_view.clear()
        self.log_view.append("Log cleared", "INFO")
    
    def on_log_filter_change(self, levels: list) -> None:
        """Handle log filter checkbox changes."""
        self.log_view.filter_by_level(levels)
        if levels:
            filter_str = ", ".join(levels)
            self.log_view.append(f"Log filter set to: {filter_str}", "DEBUG")
        else:
            self.log_view.append("Log filter: No levels selected (nothing will be shown)", "DEBUG")
    
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
    
    def on_localhost_change(self, new_mode: str) -> None:
        """
        Handle localhost mode change (IO_box or Local Host).
        Updates settings.yaml localhost_mode and restarts UDP card manager.
        
        Args:
            new_mode: New mode ("IO_box" or "Local Host")
        """
        localhost_enabled = (new_mode == "Local Host")
        mode_display = "enabled" if localhost_enabled else "disabled"
        
        self.log_view.append(f"Localhost mode changed to: {new_mode} (localhost_mode={localhost_enabled})", "INFO")
        
        # Update settings
        if 'UDP_Settings' not in self.settings:
            self.settings['UDP_Settings'] = {}
        self.settings['UDP_Settings']['localhost_mode'] = localhost_enabled
        
        try:
            # Save updated settings
            save_settings(self.settings)
            self.log_view.append(f"Settings saved with localhost_mode={localhost_enabled}", "SUCCESS")
            
            # Restart UDP card manager with new settings
            self.log_view.append("Restarting UDP card manager with new settings...", "WARNING")
            
            # Stop existing card manager
            if hasattr(self, 'card_manager') and self.card_manager is not None:
                self.card_manager.stop_all()
            
            # Reload settings and recreate card manager
            self.settings = load_settings()
            self.card_manager = UDPCardManager(create_all=False)
            binding_errors = self.card_manager.start_all()
            
            # Display binding errors if any
            if binding_errors:
                for error in binding_errors:
                    self.log_view.append(error, "ERROR")
                messagebox.showerror(
                    "UDP Binding Error",
                    f"Failed to bind to one or more UDP cards after mode change:\n\n{chr(10).join(binding_errors)}"
                )
            else:
                self.log_view.append("UDP card manager restarted successfully", "SUCCESS")
        except Exception as e:
            self.log_view.append(f"Error changing localhost mode: {str(e)}", "ERROR")
            messagebox.showerror("Configuration Error", f"Failed to change localhost mode:\n{str(e)}")
    
    def on_html_file_change(self, filename: str) -> None:
        """
        Handle HTML file selection change.
        Starts HTTP server and opens selected HTML file in browser.
        
        Args:
            filename: Selected HTML filename or "none"
        """
        if filename == "none":
            # Clear trace.json to remove old data
            self._clear_trace_file()
            
            # Stop HTTP server if running
            if self.http_server_process is not None:
                self.log_view.append("Stopping HTTP server...", "INFO")
                try:
                    self.http_server_process.terminate()
                    self.http_server_process.wait(timeout=3)
                    self.http_server_process = None
                    self.log_view.append("HTTP server stopped", "SUCCESS")
                except Exception as e:
                    self.log_view.append(f"Error stopping HTTP server: {str(e)}", "ERROR")
            return
        
        # Get web directory path
        web_dir = Path(__file__).resolve().parent.parent / "web"
        
        # Start HTTP server if not already running
        if self.http_server_process is None:
            self.log_view.append(f"Starting HTTP server (no-cache) in {web_dir}...", "INFO")
            try:
                # Use custom server script that disables caching for trace.json
                server_script = web_dir / "serve_nocache.py"
                self.http_server_process = subprocess.Popen(
                    [sys.executable, str(server_script)],
                    cwd=str(web_dir),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                # Give server time to start
                time.sleep(0.5)
                self.log_view.append("HTTP server started on port 8000 (trace.json caching disabled)", "SUCCESS")
            except Exception as e:
                self.log_view.append(f"Error starting HTTP server: {str(e)}", "ERROR")
                messagebox.showerror("HTTP Server Error", f"Failed to start HTTP server:\n{str(e)}")
                return
        
        # Open HTML file in browser
        url = f"http://localhost:8000/{filename}"
        self.log_view.append(f"Opening {filename} in browser...", "INFO")
        try:
            webbrowser.open(url)
            self.log_view.append(f"Opened {url} in default browser", "SUCCESS")
        except Exception as e:
            self.log_view.append(f"Error opening browser: {str(e)}", "ERROR")
            messagebox.showerror("Browser Error", f"Failed to open browser:\n{str(e)}")
    
    def on_debug_change(self, new_mode: str) -> None:
        """
        Handle debug mode change (Debug or Normal).
        Updates settings.yaml Debug.mode setting.
        
        Args:
            new_mode: New mode ("Debug" or "Normal")
        """
        debug_enabled = (new_mode == "Debug")
        
        self.log_view.append(f"Debug mode changed to: {new_mode} (mode={debug_enabled})", "INFO")
        
        # Update settings
        if 'Debug' not in self.settings:
            self.settings['Debug'] = {}
        self.settings['Debug']['mode'] = debug_enabled
        
        try:
            # Save updated settings
            save_settings(self.settings)
            self.log_view.append(f"Settings saved with Debug.mode={debug_enabled}", "SUCCESS")
        except Exception as e:
            self.log_view.append(f"Error saving Debug mode: {str(e)}", "ERROR")
            messagebox.showerror("Configuration Error", f"Failed to save Debug mode:\n{str(e)}")
    
    def run(self) -> None:
        """Start the application main loop."""
        # Register cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.root.mainloop()
    
    def _clear_trace_file(self) -> None:
        """Reset trace.json to clear old test data."""
        try:
            web_dir = Path(__file__).resolve().parent.parent / "web"
            trace_file = web_dir / "trace.json"
            
            # Write a reset state instead of deleting (keeps browser polling happy)
            import json
            reset_data = {"key": 0, "status": "none", "ts": time.time()}
            trace_file.write_text(json.dumps(reset_data), encoding='utf-8')
            
            self.log_view.append("✓ Cleared trace.json", "INFO")
        except Exception as e:
            self.log_view.append(f"Warning: Could not clear trace.json: {e}", "WARNING")
    
    def _on_closing(self) -> None:
        """Handle window closing - cleanup resources."""
        # Stop HTTP server if running
        if self.http_server_process is not None:
            try:
                self.http_server_process.terminate()
                self.http_server_process.wait(timeout=2)
            except Exception:
                pass
        
        # Destroy window
        self.root.destroy()


# Standalone demo
if __name__ == "__main__":
    app = MainWindow(title="HW Tester - Demo")
    app.run()
