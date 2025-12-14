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
from hw_tester.utils.general import clear_mux_bits, parse_event_string, get_pin_pair_info_controlino, enable_cards, set_mux_bits

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
        self.root.geometry("1400x700")
        
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
        
        # Initialize hardware ONCE and share it between components
        # auto_detect=False uses the Type from settings.yaml
        # auto_detect=True attempts to detect board type (may be ambiguous for Controllino)
        from hw_tester.hardware.hardware_factory import initialize_hardware
        self.hardware = initialize_hardware(self.settings)
        
        # Reload settings in case hardware initialization changed simulation mode
        self.settings = load_settings()
        
        # Create main components (needs settings to be loaded first)
        self._create_widgets()
        
        # Initialize Measurer with shared hardware instance
        self.measurer = Measurer(hardware_io=self.hardware, settings=self.settings)
        
        # Initialize KeepAlive with shared hardware instance
        self.keep_alive = PinPulser(hardware_io=self.hardware, settings=self.settings)
        
        # Initialize UDP Card Manager for controlling IO cards
        self.card_manager = UDPCardManager(create_all=False)  # Only create enabled cards
        self.card_manager.start_all()  # Start communication threads
        
        # Set up proper cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Load demo data
        #self._load_demo_data()
    
    def on_closing(self) -> None:
        """Clean up resources before closing the application."""
        # Stop UDP card manager
        if hasattr(self, 'card_manager') and self.card_manager is not None:
            print("[MainWindow] Stopping UDP card manager...")
            self.card_manager.stop_all()
        
        # Close hardware connection
        if hasattr(self, 'hardware') and self.hardware is not None:
            print("[MainWindow] Closing hardware connection...")
            self.hardware.close()
        
        # Destroy window
        self.root.destroy()
        
        # Exit the application cleanly
        print("[MainWindow] Exiting application...")
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
            on_monitor=self.on_monitor,
            on_test=self.on_test,
            on_stop_m=self.on_stop_m,
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
    
    # TODO(core): Replace mock implementations with actual hardware control
    
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
                    # Display empty string for 0.0 values in Expected columns (means no test)
                    power_exp_display = str(pin.Power_Expected) if pin.Power_Expected != 0.0 else ""
                    pullup_exp_display = str(pin.PullUp_Expected) if pin.PullUp_Expected != 0.0 else ""
                    
                    rows.append({
                        "ID": pin.Id,
                        "Connect": pin.Connect,
                        "Type": pin.Type,
                        "Power_Expected": power_exp_display,
                        "Power_Input": pin.Power_Input,
                        "Power_Measured": str(pin.Power_Measured),
                        "Power_Result": "Pass" if pin.Power_Result else "Fail",
                        "PullUp_Expected": pullup_exp_display,
                        "PullUp_Measured": str(pin.PullUp_Measured),
                        "PullUp_Result": "Pass" if pin.PullUp_Result else "Fail",
                        "Logic_Pin_Input": str(pin.Logic_Pin_Input),
                        "Logic_DI_Result": "Pass" if pin.Logic_DI_Result else "Fail"
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
    
    def on_monitor(self) -> None:
        """Handle Monitor button click - Functionality to be defined later."""
        self.log_view.append("Monitor functionality not yet implemented", "INFO")
        # TODO: Implement monitor functionality
        pass
    
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
            # NEW APPROACH: Object-oriented testing with Pin objects
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
                        Logic_Pin_Input=pin_row.get("Logic_Pin_Input", ""),
                        Logic_DI_Result=False
                    )
                    
                    self.log_view.append(f"Processing {pin.Id} - Type: {pin.Type}", "INFO")
                    
                    # Step 3: Determine which tests to run based on whether values are provided (not empty)
                    # Empty values in Excel mean the test should be skipped
                    # 0.0 is a valid measurement, so we check if Power_Expected/PullUp_Expected were actually set
                    power_expected_str = pin_row.get("Power_Expected", "").strip()
                    pullup_expected_str = pin_row.get("PullUp_Expected", "").strip()
                    
                    run_power_test = (power_expected_str != "")
                    run_pullup_test = (pullup_expected_str != "")
                    run_logic_test = (pin.Logic_Pin_Input != "none" and pin.Logic_Pin_Input != "")
                    
                    # # Step 4: Get pair number and associated pins
                    # pair_num, voltage_pin_key, pullup_pin_key, card_enable_a_key, card_enable_b_key = get_pin_pair_info_controlino(int(pin.Id))
                    # # Get actual pin names from board config
                    # voltage_pin_name = self.board_config.get(voltage_pin_key, 'A0')
                    # pullup_pin_name = self.board_config.get(pullup_pin_key, 'D20')
                    # self.log_view.append(f"Pin {pin.Id} belongs to Pair {pair_num}, Cards: {card_enable_a_key}, {card_enable_b_key}", "INFO")
                    
                    # # Step 5: Enable only the relevant card enable pins, disable others
                    # all_card_pins = ["enable_card_1_A_pin", "enable_card_1_B_pin", "enable_card_2_A_pin", "enable_card_2_B_pin",
                    #                  "enable_card_3_A_pin", "enable_card_3_B_pin", "enable_card_4_A_pin", "enable_card_4_B_pin"]
                    # active_cards = [card_enable_a_key, card_enable_b_key]
                    # for card_pin_key in all_card_pins:
                    #     card_pin_name = self.board_config.get(card_pin_key)
                    #     if card_pin_name:
                    #         card_physical_pin = digital_ports.get(card_pin_name)
                    #         if card_physical_pin is not None:
                    #             # Set HIGH only for the active cards, LOW for all others
                    #             state = (card_pin_key in active_cards)
                    #             self.hardware.digital_write(card_physical_pin, state)
                    #             if state:
                    #                 self.log_view.append(f"Enabling card pin {card_pin_name} (pin {card_physical_pin}) HIGH", "DEBUG")
                    
                    # # Step 6: Convert connector pin to bit representation
                    # pin_number = int(''.join(filter(str.isdigit, pin.Id)))
                    # bits = connector_pin_to_bits(pin_number)
                    # self.log_view.append(f"Bits for pin {pin_number}: {''.join(str(b) for b in bits)}", "DEBUG")
                    
                    # # Step 7: Set digital pins based on bit pattern (D0-D14)
                    # pin_states = {}
                    # for bit_idx, bit_value in enumerate(bits):
                    #     digital_pin_name = f"D{bit_idx}"
                    #     if digital_pin_name in digital_ports:
                    #         pin_states[digital_pin_name] = bool(bit_value)
                    
                    # # Apply the digital pin states
                    # if pin_states:
                    #     high_pins = [name for name, state in pin_states.items() if state]
                    #     if high_pins:
                    #         self.log_view.append(f"Setting HIGH pins for connector pin {pin_number}: {', '.join(high_pins)}", "INFO")
                        
                    #     for logical_pin, state in pin_states.items():
                    #         physical_pin = digital_ports.get(logical_pin)
                    #         if physical_pin is not None:
                    #             self.hardware.digital_write(physical_pin, state)
                    
                    # # Step 8: Small delay to allow pins to stabilize
                    # stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
                    # time.sleep(stabilize_delay)
                    
                    # Step 9: Run tests
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
                    
                    if run_pullup_test:
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
                    
                    if run_logic_test:
                        self.log_view.append(f"Running Logic Test for {pin.Id} (Input: {pin.Logic_Pin_Input})", "INFO")
                        logic_result = self.run_logic_test(pin)
                        pin.Logic_DI_Result = logic_result
                        self.log_view.append(
                            f"Logic Test: Result={'PASS' if pin.Logic_DI_Result else 'FAIL'}",
                            "SUCCESS" if pin.Logic_DI_Result else "WARNING"
                        )
                    
                    # Step 10: Update UI with results
                    self.root.after(0, self._update_pin_results, pin)
                    
                except ValueError as e:
                    error_msg = f"Pin data error for {pin_id}: {str(e)}"
                    self.log_view.append(error_msg, "ERROR")
                except Exception as e:
                    error_msg = f"Unexpected error processing {pin_id}: {str(e)}"
                    self.log_view.append(error_msg, "ERROR")
            
            self.root.after(0, self._on_test_complete)
        
        # OLD APPROACH (Commented out for reference)
        # def run_tests_old():
        #     from hw_tester.hardware.controllino_io import connector_pin_to_bits
        #     
        #     for idx, pin_id in enumerate(selected_ids):
        #         if not self.running:
        #             break
        #         
        #         try:
        #             # Extract pin number from pin_id (e.g., "J1-05" -> 5, "Pin_25" -> 25)
        #             # Try different formats
        #             if '-' in pin_id:
        #                 pin_number = int(pin_id.split('-')[-1])
        #             elif '_' in pin_id:
        #                 pin_number = int(pin_id.split('_')[-1])
        #             else:
        #                 # Try to extract any digits from the pin_id
        #                 import re
        #                 numbers = re.findall(r'\d+', pin_id)
        #                 pin_number = int(numbers[-1]) if numbers else 1
        #             
        #             # Determine which pair based on pin number
        #             if 1 <= pin_number <= 16:
        #                 pair_num = 1
        #                 card_enable_pin = "enable_card_1_A_pin"
        #             elif 17 <= pin_number <= 32:
        #                 pair_num = 2
        #                 card_enable_pin = "enable_card_1_B_pin"
        #             elif 33 <= pin_number <= 48:
        #                 pair_num = 3
        #                 card_enable_pin = "enable_card_2_A_pin"
        #             else:
        #                 pair_num = 4
        #                 card_enable_pin = "enable_card_2_B_pin"
        #             
        #             # Get voltage measurement and pullup pins for this pair
        #             voltage_pin_name = self.board_config.get(f'voltage_measure_pin_pair{pair_num}', 'A0')
        #             pullup_pin_name = self.board_config.get(f'pullup_pins_pin_pair{pair_num}', 'D20')
        #             
        #             self.log_view.append(f"Processing {pin_id} (connector pin {pin_number}, pair {pair_num})", "INFO")
        #             
        #             # Step 1: Enable/Disable card pins - set only the active card HIGH, all others LOW
        #             all_card_pins = [
        #                 "enable_card_1_A_pin", "enable_card_1_B_pin",
        #                 "enable_card_2_A_pin", "enable_card_2_B_pin",
        #                 "enable_card_3_A_pin", "enable_card_3_B_pin",
        #                 "enable_card_4_A_pin", "enable_card_4_B_pin"
        #             ]
        #             
        #             for card_pin_key in all_card_pins:
        #                 card_pin_name = self.board_config.get(card_pin_key)
        #                 if card_pin_name:
        #                     card_physical_pin = digital_ports.get(card_pin_name)
        #                     if card_physical_pin is not None:
        #                         # Set HIGH only for the active card, LOW for all others
        #                         state = (card_pin_key == card_enable_pin)
        #                         self.hardware.digital_write(card_physical_pin, state)
        #                         if state:
        #                             self.log_view.append(f"Enabling card pin {card_pin_name} (pin {card_physical_pin}) HIGH", "DEBUG")
        #             
        #             # Step 2: Convert connector pin to bit representation
        #             bits = connector_pin_to_bits(pin_number)
        #             self.log_view.append(f"Bits for pin {pin_number}: {''.join(str(b) for b in bits)}", "DEBUG")
        #             
        #             # Step 3: Set digital pins based on bit pattern
        #             # Bits correspond to D0-D14
        #             pin_states = {}
        #             for bit_idx, bit_value in enumerate(bits):
        #                 digital_pin_name = f"D{bit_idx}"
        #                 if digital_pin_name in digital_ports:
        #                     pin_states[digital_pin_name] = bool(bit_value)
        #             
        #             # Apply the digital pin states
        #             if pin_states:
        #                 high_pins = [name for name, state in pin_states.items() if state]
        #                 if high_pins:
        #                     self.log_view.append(f"Setting HIGH pins for connector pin {pin_number}: {', '.join(high_pins)}", "INFO")
        #                 
        #                 for logical_pin, state in pin_states.items():
        #                     physical_pin = digital_ports.get(logical_pin)
        #                     if physical_pin is not None:
        #                         self.hardware.digital_write(physical_pin, state)
        #             
        #             # Small delay to allow pins to stabilize
        #             stabilize_delay = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.1)
        #             time.sleep(stabilize_delay)
        #             
        #             # Step 4: Measure voltage using pair-specific analog pin
        #             # Get physical pin number from pin_map
        #             analog_ports = self.pin_map.get('A', {})
        #             analog_port = analog_ports.get(voltage_pin_name)
        #             
        #             if analog_port is None:
        #                 self.log_view.append(f"Analog pin {voltage_pin_name} not found in pin map", "ERROR")
        #                 continue
        #             
        #             self.log_view.append(f"Measuring voltage on {voltage_pin_name} (pin {analog_port}) for pair {pair_num}", "DEBUG")
        #             self.measure_voltage(pin_id, analog_port, idx)
        #             
        #             # Step 5: Additional measurement for Digital_Out type pins only
        #             pin_type = pin_types.get(pin_id, "")
        #             pullup_physical_pin = digital_ports.get(pullup_pin_name)
        #             
        #             if pin_type == "Digital_Out":
        #                 # Enable pullup pin HIGH for Digital_Out pins
        #                 if pullup_physical_pin is not None:
        #                     self.log_view.append(f"Digital_Out detected - Setting pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) HIGH for second measurement", "INFO")
        #                     self.hardware.digital_write(pullup_physical_pin, True)
        #                     
        #                     # Small delay to stabilize
        #                     time.sleep(stabilize_delay)
        #                     
        #                     # Measure voltage again with pullup enabled
        #                     self.log_view.append(f"Second measurement with pullup enabled", "DEBUG")
        #                     self.measure_voltage(pin_id, analog_port, idx)
        #                     
        #                     # Step 6: Set pullup pin LOW after Digital_Out test
        #                     self.hardware.digital_write(pullup_physical_pin, False)
        #                     self.log_view.append(f"Setting pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) LOW", "DEBUG")
        #         
        #         except ValueError as e:
        #             error_msg = f"Pin mapping error for {pin_id}: {str(e)}"
        #             self.log_view.append(error_msg, "ERROR")
        #             self.root.after(0, self._update_measurement, pin_id, f"ERROR: {str(e)}")
        #         except Exception as e:
        #             error_msg = f"Unexpected error processing {pin_id}: {str(e)}"
        #             self.log_view.append(error_msg, "ERROR")
        #             self.root.after(0, self._update_measurement, pin_id, f"ERROR: {str(e)}")
        #     
        #     self.root.after(0, self._on_test_complete)
        
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
            "Power_Measured": str(pin.Power_Measured),
            "Power_Result": "Pass" if pin.Power_Result else "Fail",
            "PullUp_Measured": str(pin.PullUp_Measured),
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
        tolerance = self.settings.get('Test', {}).get('voltage_tolerance', 0.5)

        # Get pair number and associated pins
        pin_number = int(''.join(filter(str.isdigit, pin.Id)))
        pair_num, voltage_pin_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(pin_number)

        # Get actual pin names from board config
        voltage_pin_name = self.board_config.get(voltage_pin_key, 'A0')

        # Enable card A, disable all others
        #enable_cards([card_enable_a_key], self.board_config, self.pin_map, self.hardware, self.log_view.append)
        
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
        #voltage_scale = self.settings.get('scale', {}).get('voltage', 1.0)
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
        
        # get out of the function in case of no power input
        if pin.Power_Input == "none" or pin.Power_Input == "":
            exit
        
        # Parse Power_Input and activate card
        card, event_type, event_num, event_value = parse_event_string(pin.Power_Input)
        if card is None or event_type is None:
            self.log_view.append(f"Failed to parse Power_Input: {pin.Power_Input}", "ERROR")
            return (measured_voltage, False, f"Failed to parse Power_Input: {pin.Power_Input}")
        
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

        # Debug mode - wait for user confirmation
        mode_debug = self.settings.get('Debug', {}).get('mode', False)
        if mode_debug:
            input("\nWAIT...")

        # Measure voltage again after activation
        try:
            measured_voltage = self.measurer.measure_voltage(analog_port)
            self.log_view.append(f"Measurement after activation: {measured_voltage* voltage_scale:.3f}V", "DEBUG")

            # Set analog or digital output  buck to zero 
            if event_type == "AO":
                success = self.card_manager.set_analog_output(card_id=card, ao_number=event_num, voltage=0)
                self.log_view.append(f"DeActive: Set Card {card} AO{event_num} to {0}V: {'Success' if success else 'Failed'}", "INFO")
            elif event_type == "DO":
                success = self.card_manager.set_digital_output(card_id=card, do_number=event_num, state=False)
                self.log_view.append(f"DeActive: Set Card {card} DO{event_num} to False: {'Success' if success else 'Failed'}", "INFO")
        except Exception as e:
            self.log_view.append(f"Measurement error after activation: {str(e)}", "ERROR")

        
            return (0.0, False, f"Error: Measurement failed after activation - {str(e)}")
        
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
        4. If PullUp_Expected == 0.0 (no test):
           - Skip test and return 0V
        5. If PullUp_Expected is specified (e.g., 24V):
           - Verify initial measurement is ~0V (within tolerance)
           - Activate pullup_pin_key (set HIGH)
           - Wait for signal stabilization
           - Measure voltage again
           - Deactivate pullup_pin_key (set LOW)
           - Compare measurement to PullUp_Expected
           - Return result (pass/fail based on voltage tolerance)
        
        Args:
            pin: Pin object containing test parameters (Id, PullUp_Expected, etc.)
            
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
        tolerance = self.settings.get('Test', {}).get('voltage_tolerance', 0.5)

        # Get pair number and associated pins
        pin_number = int(''.join(filter(str.isdigit, pin.Id)))
        pair_num, voltage_pin_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(pin_number)

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
        
        # Step 2: Check if PullUp_Expected is 0.0 (no test)
        if pin.PullUp_Expected == 0.0:
            self.log_view.append(f"PullUp_Expected is 0.0 - skipping pullup test", "INFO")
            return (0.0, True, "Pullup test skipped (PullUp_Expected = 0.0)")
        
        # Step 3: Verify initial measurement is ~0V
        if abs(measured_voltage * voltage_scale) > tolerance:
            self.log_view.append(f"Initial voltage {measured_voltage * voltage_scale:.3f}V is not ~0V (tolerance: {tolerance}V) - test failed", "WARNING")
            return (measured_voltage * voltage_scale, False, f"Initial voltage {measured_voltage:.3f}V is not ~0V")
        
        self.log_view.append(f"Initial voltage {measured_voltage * voltage_scale:.3f}V is ~0V - proceeding to activate pullup", "DEBUG")
        
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

        # Step 5: Measure voltage again after pullup activation
        try:
            measured_voltage = self.measurer.measure_voltage(analog_port)
            self.log_view.append(f"Measurement after pullup activation: {measured_voltage * voltage_scale:.3f}V", "DEBUG")

            # Deactivate pullup pin (set LOW)
            self.hardware.digital_write(pullup_physical_pin, False)
            self.log_view.append(f"Deactivating pullup pin {pullup_pin_name} (pin {pullup_physical_pin}) LOW", "INFO")
        except Exception as e:
            self.log_view.append(f"Measurement error after pullup activation: {str(e)}", "ERROR")
            # Ensure pullup pin is deactivated even on error
            self.hardware.digital_write(pullup_physical_pin, False)
            return (0.0, False, f"Error: Measurement failed after pullup activation - {str(e)}")
        
        # Step 6: Compare to expected value
        voltage_diff = abs(measured_voltage * voltage_scale - pin.PullUp_Expected)
        if voltage_diff <= tolerance:
            self.log_view.append(f"Measurement {measured_voltage * voltage_scale:.3f}V is within tolerance of {pin.PullUp_Expected:.3f}V", "SUCCESS")
            return (measured_voltage * voltage_scale, True, "Measurement is in tolerance")
        else:
            self.log_view.append(f"Measurement {measured_voltage * voltage_scale:.3f}V is NOT within tolerance of {pin.PullUp_Expected:.3f}V (diff: {voltage_diff:.3f}V)", "WARNING")
            return (measured_voltage * voltage_scale, False, f"Measurement not in tolerance (diff: {voltage_diff:.3f}V)")
    
    def run_logic_test(self, pin: "Pin") -> bool:
        """
        Run logic test on a pin.
        TODO: Implement actual hardware testing logic.
        
        Args:
            pin: Pin object to test
            
        Returns:
            True if test passes, False otherwise
        """
        is_simulation = self.settings.get('Board', {}).get('simulation', True)
        
        if is_simulation:
            # Simulation mode - return fixed result
            time.sleep(0.2)  # Simulate test delay
            # Return pass 90% of the time for simulation
            import random
            return random.random() > 0.1
        else:
            # TODO: Real hardware logic test
            # Will need to:
            # 1. Connect Logic_Pin_Input to the test pin
            # 2. Check digital input state change
            # 3. Verify expected DI activation
            self.log_view.append("Real hardware logic test not yet implemented", "WARNING")
            return False
    
    def _on_test_complete(self) -> None:
        """Called when test run completes."""
        self.running = False
        self.op_panel.enable_stop_t(False)
        self.op_panel.enable_test(True)
        self.log_view.append("Test sequence completed", "SUCCESS")
    
    def on_stop_t(self) -> None:
        """Handle Stop_T button click."""
        self.log_view.append("Stopping test sequence...", "WARNING")
        self.running = False
        self.op_panel.enable_stop_t(False)
        self.op_panel.enable_test(True)
    
    def on_stop_m(self) -> None:
        """Handle Stop_M button click - Functionality to be defined later."""
        self.log_view.append("Stop_M functionality not yet implemented", "INFO")
        # TODO: Implement stop monitor functionality
        pass
    
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
