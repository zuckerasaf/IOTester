"""
Main controller for the Qt UI - handles all button callbacks and business logic.
"""
from pathlib import Path
from datetime import datetime
import re
import subprocess
import sys
import threading
import time
import webbrowser
from typing import Optional, List, Dict

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QTimer, QMetaObject, Q_ARG
from PySide6.QtWidgets import QFileDialog, QMessageBox

import openpyxl

from hw_tester.utils.read_excell import load_connector_from_excel
from hw_tester.hardware.pin import Connector, Pin, TestResult
from hw_tester.utils.config_loader import load_settings, save_settings, get_board_pin_map, get_board_pin_config
from hw_tester.core.test_handle import TestHandle
from hw_tester.core.measurer import Measurer
from hw_tester.core.pin_pulser import PinPulser
from hw_tester.core.udp_card_manager import UDPCardManager
from hw_tester.hardware.hardware_factory import initialize_hardware
# from hw_tester.core.test_handle import run_i_bit_test


class MainController:
    """
    Controller for MainWindowQt - separates UI from business logic.
    
    Handles all button clicks, data loading, and updates to the UI.
    """
    
    def __init__(self, main_window):
        """
        Initialize controller with reference to the main window.
        
        Args:
            main_window: MainWindowQt instance
        """
        self.main_window = main_window
        self.connector = None  # Currently loaded connector
        self.settings = load_settings()  # Load settings for report paths
        
        # Test state flags
        self.running = False
        self.running_ibit = False
        self.connected = False
        
        # Threading event for Next button debug control
        self.next_event = threading.Event()
        self.debug_mode = self.settings.get('Debug', {}).get('mode', False)
        
        # HTTP server process for HTML viewing
        self.http_server_process = None
        
        # Initialize hardware and test components
        self._init_hardware()
        self._init_test_components()
        
        # Wire UI signals
        self._wire_signals()
        
        # Initialize UI state from settings
        self._init_ui_state()
    
    def _init_ui_state(self):
        """Initialize UI elements based on current settings."""
        # Set simulation button text and style based on settings
        is_simulation = self.settings.get('Board', {}).get('simulation', True)
        simulation_text = "Simulation: On" if is_simulation else "Simulation: Off"
        self.main_window.btn_simulation.setText(simulation_text)
        
        # Set active styling if simulation is on
        if is_simulation:
            self.main_window.btn_simulation.setObjectName("btnActive")
        else:
            self.main_window.btn_simulation.setObjectName("")
        self.main_window.btn_simulation.style().polish(self.main_window.btn_simulation)
        
        # Set localhost button text and style based on settings
        is_localhost = self.settings.get('UDP_Settings', {}).get('localhost_mode', False)
        localhost_text = "LocalHost" if is_localhost else "IO Box"
        self.main_window.btn_connection.setText(localhost_text)
        
        # Set active styling if localhost mode is on
        if is_localhost:
            self.main_window.btn_connection.setObjectName("btnActive")
        else:
            self.main_window.btn_connection.setObjectName("")
        self.main_window.btn_connection.style().polish(self.main_window.btn_connection)
        
        # Set debug button text and style based on settings
        debug_text = "Debug: True" if self.debug_mode else "Debug: False"
        self.main_window.btn_debug.setText(debug_text)
        
        if self.debug_mode:
            self.main_window.btn_debug.setObjectName("btnActive")
        else:
            self.main_window.btn_debug.setObjectName("")
        self.main_window.btn_debug.style().polish(self.main_window.btn_debug)
    
    def _init_hardware(self):
        """Initialize hardware connection."""
        try:
            self.hardware = initialize_hardware(self.settings, log_callback=self._log_callback)
            # Reload settings in case hardware initialization changed simulation mode
            self.settings = load_settings()
        except Exception as e:
            self.main_window.log.append(f"Hardware initialization failed: {e}", "ERROR")
            self.hardware = None
    
    def _init_test_components(self):
        """Initialize test-related components (Measurer, TestHandle, etc.)."""
        if not self.hardware:
            self.main_window.log.append("Hardware not initialized - test components disabled", "WARNING")
            self.test_handler = None
            return
        
        # Load pin maps and board config
        self.pin_map = get_board_pin_map(self.settings)
        self.board_config = get_board_pin_config(self.settings)
        
        # Initialize Measurer
        self.measurer = Measurer(hardware_io=self.hardware, settings=self.settings)
        
        # Initialize PinPulser for KeepAlive functionality
        self.keep_alive = PinPulser(hardware_io=self.hardware, settings=self.settings)
        
        # Initialize UDP Card Manager
        self.card_manager = UDPCardManager(create_all=False)
        binding_errors = self.card_manager.start_all()
        
        # Display binding errors if any
        if binding_errors:
            for error in binding_errors:
                self.main_window.log.append(error, "ERROR")
            
            # Show error messagebox to notify user
            error_summary = "\n".join(binding_errors)
            self._show_message(
                "UDP Binding Error",
                f"Failed to bind to one or more UDP cards:\n\n{error_summary}\n\n"
                f"The application will continue running, but affected cards will not function.\n"
                f"Check if another application is using the same ports.\n"
                f"---\n"
                f"In case you wish to work with localhost run the switch_to_localhost.bat and restart the application.",
                "critical"
            )
        else :
            self.main_window.log.append("no binding errors in the UDP connections", "SUCCESS")
        # Initialize TestHandle
        self.test_handler = TestHandle(
            hardware=self.hardware,
            settings=self.settings,
            pin_map=self.pin_map,
            board_config=self.board_config,
            measurer=self.measurer,
            card_manager=self.card_manager,
            log_callback=self._log_callback
        )
        
        # Share threading event with test handler
        self.test_handler.next_event = self.next_event
        
        self.main_window.log.append("Test components initialized", "INFO")
    
    def _log_callback(self, message: str, level: str = "INFO"):
        """Thread-safe log callback for hardware and test components."""
        # Use Qt's thread-safe mechanism to update UI from background threads
        QMetaObject.invokeMethod(
            self.main_window.log,
            "append",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, message),
            Q_ARG(str, level)
        )
    
    def _wire_signals(self):
        """Connect all UI signals (button clicks) to controller methods."""
        # Group 1: Connector/File buttons
        self.main_window.btn_load.clicked.connect(self.on_load)
        self.main_window.btn_report.clicked.connect(self.on_report)
        self.main_window.btn_doc.clicked.connect(self.on_doc)
        
        # Group 2: Run Controls
        self.main_window.btn_test.clicked.connect(self.on_test)
        self.main_window.btn_test_all.clicked.connect(self.on_test_all)
        self.main_window.btn_stop.clicked.connect(self.on_stop_t)
        
        # Group 3: Log controls
        self.main_window.btn_clear_log.clicked.connect(self.on_clear_log)
        
        # Log filter checkboxes
        self.main_window.cb_inf.stateChanged.connect(self.on_log_filter_change)
        self.main_window.cb_suc.stateChanged.connect(self.on_log_filter_change)
        self.main_window.cb_wrn.stateChanged.connect(self.on_log_filter_change)
        self.main_window.cb_err.stateChanged.connect(self.on_log_filter_change)
        self.main_window.cb_dbg.stateChanged.connect(self.on_log_filter_change)
        
        # Group 4: Test/Debug controls
        self.main_window.btn_simulation.clicked.connect(self.on_simulation_toggle)
        self.main_window.btn_connection.clicked.connect(self.on_localhost_toggle)
        self.main_window.btn_debug.clicked.connect(self.on_debug_toggle)
        self.main_window.btn_next.clicked.connect(self.on_next)
        self.main_window.btn_keepalive.clicked.connect(self.on_keepalive)
        self.main_window.btn_ibit.clicked.connect(self.on_ibit)
        self.main_window.btn_stop_ibit.clicked.connect(self.on_stop_ibit)
    
    def _show_message(self, title: str, message: str, msg_type: str = "information"):
        """
        Show a message box without icon for better text layout.
        
        Args:
            title: Dialog window title
            message: Message text to display
            msg_type: Type of message - "information", "warning", or "critical"
        """
        msg_box = QMessageBox(self.main_window)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.NoIcon)  # No icon for better text layout
        
        # Enable text word wrapping
        msg_box.setTextFormat(Qt.PlainText)
        
        # Dimensions are controlled by CSS (dark.css QMessageBox styling)
        
        # Set appropriate standard button based on type
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()
    
    def update_testing_pin(self, pin_id: str):
        """
        Update the testing pin label to show which pin is currently being tested.
        
        Args:
            pin_id: Pin ID being tested (e.g., "J1-1")
        """
        self.main_window.lbl_testing_pin.setText(pin_id if pin_id else "---")
    
    def update_test_results(self, power_result: str = None, pullup_result: str = None, logic_result: str = None):
        """
        Update the test result labels in the Run Controls group.
        
        Args:
            power_result: Power test result ("Pass", "Fail", or None to keep current)
            pullup_result: Pullup test result ("Pass", "Fail", or None to keep current)
            logic_result: Logic test result ("Pass", "Fail", or None to keep current)
        """
        if power_result is not None:
            self.main_window.lbl_power_result.setText(power_result)
            if power_result == "Pass":
                self.main_window.lbl_power_result.setStyleSheet("color: #00FF00; font-weight: bold;")  # Bright green
            elif power_result == "Fail":
                self.main_window.lbl_power_result.setStyleSheet("color: #FF0000; font-weight: bold;")  # Bright red
            else:
                self.main_window.lbl_power_result.setStyleSheet("")  # Default style
        
        if pullup_result is not None:
            self.main_window.lbl_pullup_result.setText(pullup_result)
            if pullup_result == "Pass":
                self.main_window.lbl_pullup_result.setStyleSheet("color: #00FF00; font-weight: bold;")
            elif pullup_result == "Fail":
                self.main_window.lbl_pullup_result.setStyleSheet("color: #FF0000; font-weight: bold;")
            else:
                self.main_window.lbl_pullup_result.setStyleSheet("")
        
        if logic_result is not None:
            self.main_window.lbl_logic_result.setText(logic_result)
            if logic_result == "Pass":
                self.main_window.lbl_logic_result.setStyleSheet("color: #00FF00; font-weight: bold;")
            elif logic_result == "Fail":
                self.main_window.lbl_logic_result.setStyleSheet("color: #FF0000; font-weight: bold;")
            else:
                self.main_window.lbl_logic_result.setStyleSheet("")
    
    def clear_test_results(self):
        """Clear all test result labels back to default state."""
        self.update_testing_pin("")
        self.main_window.lbl_power_result.setText("---")
        self.main_window.lbl_power_result.setStyleSheet("")
        self.main_window.lbl_pullup_result.setText("---")
        self.main_window.lbl_pullup_result.setStyleSheet("")
        self.main_window.lbl_logic_result.setText("---")
        self.main_window.lbl_logic_result.setStyleSheet("")
    
    def on_load(self):
        """
        Handle Load button click - open file dialog and load connector data from Excel file.
        
        Opens a file dialog to select Excel file, loads the data, and populates the table.
        """
        # Open file dialog to select Excel file
        initial_dir = str(Path.cwd() / "tests" / "DB")
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Select Connector Excel File",
            initial_dir,
            "Excel files (*.xlsx *.xls);;All files (*.*)"
        )
        
        if not file_path:
            # User cancelled
            return
        
        file_path = Path(file_path)
        file_name = file_path.name
        
        # Extract connector name from filename (remove .xlsx extension)
        connector_name = file_path.stem
        
        # Update the connector text field with the loaded file
        self.main_window.connector_edit.setText(connector_name)
        
        # Log the attempt
        self.main_window.log.append(f"Loading connector data from: {file_name}...", "INFO")
        
        try:
            # Load connector from Excel using the full file path
            self.connector = load_connector_from_excel(
                file_name=file_name,
                db_path=str(file_path.parent),
                connector_id=connector_name
            )
            
            # Convert connector pins to table rows
            rows = self._connector_to_rows(self.connector)
            
            # Update the table using PinTableQt API
            self.main_window.table.set_rows(rows)
            
            # Mark as connected
            self.connected = True
            
            # Enable test buttons
            self.main_window.btn_test.setEnabled(True)
            self.main_window.btn_test_all.setEnabled(True)
            
            # Log success
            self.main_window.log.append(
                f"Loaded {len(self.connector.pins)} pins from '{connector_name}'",
                "SUCCESS"
            )
            
        except FileNotFoundError as e:
            self.main_window.log.append(f"File not found - {e}", "ERROR")
            self._show_message(
                "File Not Found",
                f"Could not find Excel file:\n{file_name}\n\nMake sure it exists in tests/DB/",
                "critical"
            )
        except Exception as e:
            self.main_window.log.append(f"Failed to load connector - {e}", "ERROR")
            self._show_message(
                "Load Error",
                f"Error loading connector:\n{str(e)}",
                "critical"
            )
    
    def _connector_to_rows(self, connector: Connector) -> list:
        """
        Convert Connector object to table rows.
        
        Args:
            connector: Connector object with pins
        
        Returns:
            List of dictionaries with keys matching PinTableQt column names
        """
        rows = []
        for pin in connector.pins:
            row = {
                "ID": pin.Id,
                "Connect": connector.id,
                "Discrete_Name": pin.Discrete_Name,
                "Signal_Name": pin.Signal_Name,
                "Plug": pin.Plug,
                "Type": pin.Type,
                "Pin": pin.Pin,
                "Power_Expected": pin.Power_Expected,
                "Power_Input": pin.Power_Input,
                "Power_Measured": getattr(pin, 'Power_Measured', ''),
                "Power_Result": pin.Power_Result.value if isinstance(pin.Power_Result, TestResult) else str(pin.Power_Result),
                "Power_Result_Reason": getattr(pin, 'Power_Result_Reason', ''),
                "PullUp_Expected": pin.PullUp_Expected,
                "PullUp_Input": getattr(pin, 'PullUp_Input', ''),
                "PullUp_Measured": getattr(pin, 'PullUp_Measured', ''),
                "PullUp_Result": pin.PullUp_Result.value if isinstance(pin.PullUp_Result, TestResult) else str(pin.PullUp_Result),
                "PullUp_Result_Reason": getattr(pin, 'PullUp_Result_Reason', ''),
                "Logic_Pin_Input": getattr(pin, 'Logic_Pin_Input', ''),
                "Logic_Command": pin.Logic_Command if isinstance(pin.Logic_Command, str) else (", ".join(pin.Logic_Command) if pin.Logic_Command else ""),
                "Logic_Expected": pin.Logic_Expected if isinstance(pin.Logic_Expected, str) else (", ".join(pin.Logic_Expected) if pin.Logic_Expected else ""),
                "Logic_DI_Result": pin.Logic_DI_Result.value if isinstance(pin.Logic_DI_Result, TestResult) else str(pin.Logic_DI_Result),
                "Logic_DI_Result_Reason": getattr(pin, 'Logic_DI_Result_Reason', '')
            }
            rows.append(row)
        return rows
    
    def on_report(self):
        """
        Handle Report button click - generate Excel report with all pin table data.
        
        Creates an Excel file with timestamped filename containing all table rows.
        """
        try:
            self.main_window.log.append("Generating test report...", "INFO")
            
            # Get all rows from the table model
            rows = self._get_table_rows_as_dicts()
            
            if not rows:
                self.main_window.log.append("No data to export", "WARNING")
                self._show_message(
                    "No Data",
                    "No data available to export. Please load a connector first.",
                    "warning"
                )
                return
            
            # Get connector name from the text field
            connector_name = self.main_window.connector_edit.text().strip().rstrip('_')
            if not connector_name:
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
                # Use workspace Results folder
                reports_dir = Path.cwd() / "Results"
            
            reports_dir.mkdir(parents=True, exist_ok=True)
            out_path = reports_dir / filename
            
            # Create Excel workbook and write rows
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Report"
            
            # Write header from keys of first row
            headers = list(rows[0].keys())
            ws.append(headers)
            
            for row in rows:
                # Ensure consistent order matching headers
                ws.append([row.get(h, "") for h in headers])
            
            wb.save(str(out_path))
            
            # Count tested pins (those with measurements)
            tested_count = sum(1 for row in rows if row.get("Power_Result") != "No Result")
            
            self.main_window.log.append(
                f"Report: {tested_count}/{len(rows)} pins tested - saved to {out_path}",
                "SUCCESS"
            )
            
            self._show_message(
                "Test Report",
                f"Tested Pins: {tested_count}/{len(rows)}\n\nReport saved to:\n{out_path}",
                "information"
            )
            
        except Exception as e:
            error_msg = f"Error generating report: {e}"
            self.main_window.log.append(error_msg, "ERROR")
            self._show_message(
                "Report Error",
                error_msg,
                "critical"
            )
    
    def on_doc(self):
        """
        Handle DOC button click - generate Word document report.
        
        Opens a dialog to select files and generate a Word document report.
        """
        try:
            from hw_tester.core.doc_handle import create_doc_report_via_dialog
            
            self.main_window.log.append("Starting DOC report generation...", "INFO")
            
            output_path = create_doc_report_via_dialog()
            
            if output_path:
                self.main_window.log.append(f"DOC report saved to {output_path}", "SUCCESS")
                self._show_message(
                    "DOC Report",
                    f"Report saved to:\n{output_path}",
                    "information"
                )
            else:
                self.main_window.log.append("DOC report creation canceled", "INFO")
                
        except Exception as e:
            error_msg = f"DOC report generation failed: {e}"
            self.main_window.log.append(error_msg, "ERROR")
            self._show_message(
                "DOC Report Error",
                error_msg,
                "critical"
            )
    
    def _get_table_rows_as_dicts(self) -> list:
        """
        Get all rows from the table as list of dictionaries.
        
        Returns:
            List of dictionaries, where each dict has column headers as keys
        """
        return self.main_window.table.get_all_rows()
    
    def on_clear_log(self):
        """Handle Clear Log button click - clear the operational log."""
        self.main_window.log.clear()
        self.main_window.log.append("Log cleared", "INFO")
    
    def on_log_filter_change(self):
        """
        Handle log filter checkbox changes - update log display filtering.
        
        Only shows log entries matching the selected levels.
        """
        # Collect checked levels
        selected_levels = []
        
        if self.main_window.cb_inf.isChecked():
            selected_levels.append("INFO")
        if self.main_window.cb_suc.isChecked():
            selected_levels.append("SUCCESS")
        if self.main_window.cb_wrn.isChecked():
            selected_levels.append("WARNING")
        if self.main_window.cb_err.isChecked():
            selected_levels.append("ERROR")
        if self.main_window.cb_dbg.isChecked():
            selected_levels.append("DEBUG")
        
        # Apply filter (empty list = show all)
        self.main_window.log.filter_by_level(selected_levels if selected_levels else None)
    
    def on_simulation_toggle(self):
        """
        Handle simulation mode toggle button click.
        
        Toggles between "Simulation: On" and "Simulation: Off".
        Updates settings.yaml with the new simulation mode.
        """
        # Get current button text to determine current state
        current_text = self.main_window.btn_simulation.text()
        
        # Toggle state
        if "On" in current_text:
            # Currently On, switch to Off
            new_simulation_enabled = False
            new_text = "Simulation: Off"
            old_mode = "Simulation On"
            new_mode = "Simulation Off"
        else:
            # Currently Off, switch to On
            new_simulation_enabled = True
            new_text = "Simulation: On"
            old_mode = "Simulation Off"
            new_mode = "Simulation On"
        
        # Update settings
        self.settings['Board']['simulation'] = new_simulation_enabled
        
        try:
            # Save settings to YAML file
            save_settings(self.settings)
            
            # Update button text
            self.main_window.btn_simulation.setText(new_text)
            
            # Update button styling
            if new_simulation_enabled:
                self.main_window.btn_simulation.setObjectName("btnActive")
            else:
                self.main_window.btn_simulation.setObjectName("")
            self.main_window.btn_simulation.style().polish(self.main_window.btn_simulation)
            
            # Log success
            self.main_window.log.append(
                f"Simulation mode changed: {old_mode} → {new_mode}",
                "SUCCESS"
            )
        except Exception as e:
            self.main_window.log.append(
                f"Error saving simulation mode: {str(e)}",
                "ERROR"
            )
    
    def on_localhost_toggle(self):
        """
        Handle localhost mode toggle button click.
        
        Toggles between "LocalHost" and "IO Box".
        Updates settings.yaml localhost_mode and restarts UDP card manager.
        """
        # Get current button text to determine current state
        current_text = self.main_window.btn_connection.text()
        
        # Toggle state
        if "LocalHost" in current_text:
            # Currently LocalHost, switch to IO Box
            localhost_enabled = False
            new_text = "IO Box"
            new_mode = "IO_box"
        else:
            # Currently IO Box, switch to LocalHost
            localhost_enabled = True
            new_text = "LocalHost"
            new_mode = "Local Host"
        
        self.main_window.log.append(
            f"Localhost mode changed to: {new_mode} (localhost_mode={localhost_enabled})",
            "INFO"
        )
        
        # Update settings
        if 'UDP_Settings' not in self.settings:
            self.settings['UDP_Settings'] = {}
        self.settings['UDP_Settings']['localhost_mode'] = localhost_enabled
        
        try:
            # Save updated settings
            save_settings(self.settings)
            self.main_window.log.append(
                f"Settings saved with localhost_mode={localhost_enabled}",
                "SUCCESS"
            )
            
            # Restart UDP card manager with new settings
            self.main_window.log.append(
                "Restarting UDP card manager with new settings...",
                "WARNING"
            )
            
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
                    self.main_window.log.append(error, "ERROR")
                self._show_message(
                    "UDP Binding Error",
                    f"Failed to bind to one or more UDP cards after mode change:\n\n{chr(10).join(binding_errors)}",
                    "critical"
                )
            else:
                self.main_window.log.append(
                    "UDP card manager restarted successfully",
                    "SUCCESS"
                )
            
            # Update button text
            self.main_window.btn_connection.setText(new_text)
            
            # Update button styling
            if localhost_enabled:
                self.main_window.btn_connection.setObjectName("btnActive")
            else:
                self.main_window.btn_connection.setObjectName("")
            self.main_window.btn_connection.style().polish(self.main_window.btn_connection)
            
        except Exception as e:
            self.main_window.log.append(
                f"Error changing localhost mode: {str(e)}",
                "ERROR"
            )
            self._show_message(
                "Configuration Error",
                f"Failed to change localhost mode:\n{str(e)}",
                "critical"
            )
    
    def on_debug_toggle(self):
        """
        Handle debug mode toggle button click.
        
        Toggles between "Debug: True" and "Debug: False".
        Updates settings.yaml with the new debug mode.
        """
        # Get current button text to determine current state
        current_text = self.main_window.btn_debug.text()
        
        # Toggle state
        if "True" in current_text:
            # Currently True, switch to False
            self.debug_mode = False
            new_text = "Debug: False"
            mode_str = "OFF"
        else:
            # Currently False, switch to True
            self.debug_mode = True
            new_text = "Debug: True"
            mode_str = "ON"
        
        # Update settings
        if 'Debug' not in self.settings:
            self.settings['Debug'] = {}
        self.settings['Debug']['mode'] = self.debug_mode
        
        try:
            # Save settings to YAML file
            save_settings(self.settings)
            
            # Update button text
            self.main_window.btn_debug.setText(new_text)
            
            # Update button styling
            if self.debug_mode:
                self.main_window.btn_debug.setObjectName("btnActive")
            else:
                self.main_window.btn_debug.setObjectName("")
            self.main_window.btn_debug.style().polish(self.main_window.btn_debug)
            
            # Update test handler's settings
            if hasattr(self, 'test_handler') and self.test_handler:
                self.test_handler.settings = self.settings
            
            # Log success
            self.main_window.log.append(
                f"Debug mode: {mode_str}",
                "SUCCESS"
            )
        except Exception as e:
            self.main_window.log.append(
                f"Error saving debug mode: {str(e)}",
                "ERROR"
            )
    
    def on_next(self):
        """
        Handle Next button click - Resume test execution from debug pause.
        
        Sets the threading event to allow test execution to continue from
        wait_debug() pause points during debug mode.
        """
        self.next_event.set()
        self.main_window.log.append("Next button pressed - resuming execution", "INFO")
    
    def on_keepalive(self):
        """
        Handle KeepAlive button click - Pulse all digital ports for the configured board.
        
        Retrieves all digital ports from the pin map and pulses each one asynchronously.
        This is used to maintain board activity and verify digital output functionality.
        """
        self.main_window.log.append("Starting KeepAlive pulse sequence...", "INFO")
        
        # Get all digital ports from pin map
        digital_ports = self.pin_map.get('D', {})
        
        if not digital_ports:
            board_type = self.settings.get('Board', {}).get('Type', 'unknown')
            self.main_window.log.append(f"No digital ports found for {board_type}", "WARNING")
            return
        
        self.main_window.log.append(f"Pulsing {len(digital_ports)} digital ports...", "INFO")
        
        # Pulse all digital ports asynchronously
        for port_name, port_number in digital_ports.items():
            try:
                # Pulse the digital port (async, non-blocking)
                timer = self.keep_alive.pulse_async(digital_port=port_number)
                
                if timer == 999:
                    self.main_window.log.append(
                        f"Error pulsing {port_name} (port {port_number}) - Invalid port state",
                        "ERROR"
                    )
                else:
                    self.main_window.log.append(f"Pulsing {port_name} (port {port_number})", "DEBUG")
            except Exception as e:
                self.main_window.log.append(f"Error pulsing {port_name}: {str(e)}", "ERROR")
        
        self.main_window.log.append(
            f"KeepAlive pulse sequence initiated for all {len(digital_ports)} ports",
            "SUCCESS"
        )
    
    def on_ibit(self):
        """
        Handle IBIT button click - Run Ibit test on all pins.
        
        Runs relay fuse tests on 4 pin pairs followed by comprehensive short circuit test.
        All tests execute in background thread with thread-safe logging and UI updates.
        """
        self.main_window.log.append("Starting I_Bit short circuit test...", "INFO")
        self.running_ibit = True
        if self.test_handler:
            self.test_handler.running_ibit = True
        
        self.main_window.btn_stop_ibit.setEnabled(True)
        self.main_window.btn_ibit.setEnabled(False)
        
        # Run Ibit test in background thread using TestHandle
        def run_i_bit_test():
            if self.test_handler:
                self.test_handler.run_i_bit_test()
        threading.Thread(target=run_i_bit_test, daemon=True).start()
    
    def on_stop_ibit(self):
        """
        Handle Stop IBIT button click - Stop the I_Bit short circuit test.
        
        Sets running flags to False, causing the test thread to exit gracefully.
        """
        self.main_window.log.append("Stopping I_Bit test...", "WARNING")
        self.running_ibit = False
        if self.test_handler:
            self.test_handler.running_ibit = False
        
        self.main_window.btn_stop_ibit.setEnabled(False)
        self.main_window.btn_ibit.setEnabled(True)

        # Wait 2 seconds, then clear mux bits to ensure all pins are shut down
        import time
        time.sleep(2.0)
        try:
            from hw_tester.utils.general import clear_mux_bits
            clear_mux_bits(self.pin_map, self.hardware, self.main_window.log.append)
            self.main_window.log.append("All mux matrix pins cleared after stop.", "DEBUG")
        except Exception as e:
            self.main_window.log.append(f"Error clearing mux bits after stop: {e}", "ERROR")

    
    def _on_ibit_complete_threadsafe(self):
        """Thread-safe callback when IBIT test completes - schedules UI update."""
        QMetaObject.invokeMethod(
            self.main_window,
            "_on_ibit_complete",
            Qt.ConnectionType.QueuedConnection
        )
    
    def _on_ibit_complete(self):
        """Called when IBIT test completes (runs in main thread)."""
        self.running_ibit = False
        self.main_window.btn_stop_ibit.setEnabled(False)
        self.main_window.btn_ibit.setEnabled(True)
        self.main_window.log.append("I_Bit test sequence completed", "SUCCESS")
    
    def on_html_file_change(self, filename: str):
        """
        Handle HTML file selection change from debug options combo box.
        Starts HTTP server and opens selected HTML file in browser.
        
        Args:
            filename: Selected HTML filename or "none"
        """
        if filename == "none":
            # Clear trace.json to remove old data
            self._clear_trace_file()
            
            # Stop HTTP server if running
            if self.http_server_process is not None:
                self.main_window.log.append("Stopping HTTP server...", "INFO")
                try:
                    self.http_server_process.terminate()
                    self.http_server_process.wait(timeout=3)
                    self.http_server_process = None
                    self.main_window.log.append("HTTP server stopped", "SUCCESS")
                except Exception as e:
                    self.main_window.log.append(f"Error stopping HTTP server: {str(e)}", "ERROR")
            return
        
        # Get web directory path
        # main_controller.py -> qt -> ui -> hw_tester -> web
        web_dir = Path(__file__).resolve().parent.parent.parent.parent / "web"
        
        # Start HTTP server if not already running
        if self.http_server_process is None:
            self.main_window.log.append(f"Starting HTTP server (no-cache) in {web_dir}...", "INFO")
            try:
                # Use custom server script that disables caching for trace.json
                server_script = web_dir / "serve_nocache.py"
                # Start server in visible console window so we can see trace_writer and SSE logs
                # This helps diagnose trace update issues
                self.http_server_process = subprocess.Popen(
                    [sys.executable, str(server_script)],
                    cwd=str(web_dir)
                )
                # Give server time to start
                time.sleep(0.5)
                self.main_window.log.append("HTTP server started on port 8000 (trace.json caching disabled)", "SUCCESS")
            except Exception as e:
                self.main_window.log.append(f"Error starting HTTP server: {str(e)}", "ERROR")
                self._show_message(
                    "HTTP Server Error",
                    f"Failed to start HTTP server:\\n{str(e)}",
                    "critical"
                )
                return
        
        # Open HTML file in browser
        url = f"http://localhost:8000/{filename}"
        self.main_window.log.append(f"Opening {filename} in browser...", "INFO")
        try:
            webbrowser.open(url)
            self.main_window.log.append(f"Opened {url} in default browser", "SUCCESS")
        except Exception as e:
            self.main_window.log.append(f"Error opening browser: {str(e)}", "ERROR")
            self._show_message(
                "Browser Error",
                f"Failed to open browser:\\n{str(e)}",
                "critical"
            )
    
    def _clear_trace_file(self):
        """Clear trace.json file to prevent displaying old data."""
        try:
            # main_controller.py -> qt -> ui -> hw_tester -> web
            web_dir = Path(__file__).resolve().parent.parent.parent.parent / "web"
            trace_file = web_dir / "trace.json"
            
            if trace_file.exists():
                # Write empty array to trace.json
                trace_file.write_text("[]")
                self.main_window.log.append("Cleared trace.json", "DEBUG")
        except Exception as e:
            self.main_window.log.append(f"Error clearing trace.json: {str(e)}", "WARNING")
    
    def on_test(self):
        """Handle Test button click - Execute test sequence on selected pins."""
        if not self.connected:
            self.main_window.log.append("Not connected. Please load connector data first.", "WARNING")
            self._show_message(
                "Not Connected",
                "Please load a connector file first.",
                "warning"
            )
            return
        
        selected_ids = self._get_selected_pin_ids()
        if not selected_ids:
            self.main_window.log.append("No pins selected. Please select pins to test.", "WARNING")
            self._show_message(
                "No Selection",
                "Please select one or more pins to test.",
                "warning"
            )
            return
        
        all_rows = self._get_table_rows_as_dicts()
        self._start_test(selected_ids, all_rows, "selected")
    
    def on_test_all(self):
        """Handle Test_All button click - Execute test sequence on all pins."""
        if not self.connected:
            self.main_window.log.append("Not connected. Please load connector data first.", "WARNING")
            self._show_message(
                "Not Connected",
                "Please load a connector file first.",
                "warning"
            )
            return
        
        all_rows = self._get_table_rows_as_dicts()
        if not all_rows:
            self.main_window.log.append("No pins available. Please load pins first.", "WARNING")
            return
        
        # Select all rows
        self.main_window.table.select_all()
        
        # Get all IDs
        selected_ids = [row.get("ID", "") for row in all_rows if row.get("ID")]
        self._start_test(selected_ids, all_rows, "all")
    
    def _start_test(self, selected_ids: List[str], all_rows: List[dict], scope_label: str):
        """
        Start a test run for the provided pin IDs.
        
        Args:
            selected_ids: List of pin IDs to test
            all_rows: All pin table rows as dictionaries
            scope_label: "selected" or "all"
        """
        if not selected_ids:
            self.main_window.log.append("No pins selected. Please select pins to test.", "WARNING")
            return
        
        if not self.test_handler:
            self.main_window.log.append("Test handler not initialized. Cannot run tests.", "ERROR")
            return
        
        # Clear Measure column for all rows (would need to add this column to table model)
        # For now, we'll skip this step
        
        is_simulation = self.settings.get('Board', {}).get('simulation', True)
        mode_str = "SIMULATION" if is_simulation else "HARDWARE"
        label = "all" if scope_label == "all" else "selected"
        
        self.main_window.log.append(
            f"Starting test sequence on {len(selected_ids)} {label} pins ({mode_str} mode)",
            "INFO"
        )
        
        # Update UI state
        self.running = True
        self.test_handler.running = True
        self.main_window.btn_stop.setEnabled(True)
        self.main_window.btn_test.setEnabled(False)
        self.main_window.btn_test_all.setEnabled(False)
        
        # Clear previous test results
        self.clear_test_results()
        
        # Clear selection to avoid visual conflicts with Pass/Fail row colors
        self.main_window.table.clear_selection()
        
        # Create Qt-compatible table adapter
        qt_table_adapter = QtTableAdapter(self.main_window, self)
        

        def run_test(selected_ids, all_rows, qt_table_adapter1, qt_table_adapter2, callback):
            if self.running:
                self.test_handler.run_tests(selected_ids, all_rows, qt_table_adapter1, qt_table_adapter2, callback)

        # Run test sequence in background thread, passing all required arguments
        threading.Thread(
            target=run_test,
            args=(selected_ids, all_rows, qt_table_adapter, qt_table_adapter, self._on_test_complete_threadsafe),
            daemon=True
        ).start()
    
    def _on_test_complete_threadsafe(self):
        """Thread-safe callback when test completes - schedules UI update."""
        QMetaObject.invokeMethod(
            self.main_window,
            "_on_test_complete",
            Qt.ConnectionType.QueuedConnection
        )
    
    def _on_test_complete(self):
        """Called when test run completes (runs in main thread)."""
        self.running = False
        self.main_window.btn_stop.setEnabled(False)
        self.main_window.btn_test.setEnabled(True)
        self.main_window.btn_test_all.setEnabled(True)
        
        # Clear test result labels
        self.clear_test_results()
        
        self.main_window.log.append("Test sequence completed", "SUCCESS")
    
    def on_stop_t(self):
        """Handle Stop button click - stop running test."""
        self.main_window.log.append("Stopping test sequence...", "WARNING")
        self.running = False
        if self.test_handler:
            self.test_handler.running = False

        self.main_window.btn_stop.setEnabled(False)
        self.main_window.btn_test.setEnabled(True)
        self.main_window.btn_test_all.setEnabled(True)
        
    
    def _get_selected_pin_ids(self) -> List[str]:
        """
        Get list of selected pin IDs from the table.
        
        Returns:
            List of pin ID strings
        """
        return self.main_window.table.get_selected_ids()
    
    def on_closing(self):
        """Clean up resources before closing the application."""
        self.main_window.log.append("[MainWindow] Shutting down application...", "INFO")
        
        # Stop any running tests (sets flags to exit thread loops)
        if self.running:
            self.main_window.log.append("[MainWindow] Stopping running test...", "WARNING")
            self.running = False
            if self.test_handler:
                self.test_handler.running = False
        
        if self.running_ibit:
            self.main_window.log.append("[MainWindow] Stopping I_Bit test...", "WARNING")
            self.running_ibit = False
            if self.test_handler:
                self.test_handler.running_ibit = False
        
        # Give threads a moment to exit gracefully
        time.sleep(0.2)
        
        # Stop UDP card manager
        if hasattr(self, 'card_manager') and self.card_manager is not None:
            self.main_window.log.append("[MainWindow] Stopping UDP card manager...", "INFO")
            try:
                self.card_manager.stop_all()
            except Exception as e:
                self.main_window.log.append(f"Error stopping card manager: {e}", "ERROR")
        
        # Close hardware connection
        if hasattr(self, 'hardware') and self.hardware is not None:
            self.main_window.log.append("[MainWindow] Closing hardware connection...", "INFO")
            try:
                self.hardware.close()
            except Exception as e:
                self.main_window.log.append(f"Error closing hardware: {e}", "ERROR")
        
        # Stop HTTP server if running
        if hasattr(self, 'http_server_process') and self.http_server_process is not None:
            self.main_window.log.append("[MainWindow] Stopping HTTP server...", "INFO")
            try:
                self.http_server_process.terminate()
                self.http_server_process.wait(timeout=3)
            except Exception as e:
                self.main_window.log.append(f"Error stopping HTTP server: {e}", "WARNING")
        
        # Final log message before closing
        self.main_window.log.append("[MainWindow] Exiting application...", "INFO")


class QtTableAdapter:
    """
    Adapter to make Qt table work with TestHandle which expects Tkinter API.
    Provides thread-safe update methods.
    """
    
    def __init__(self, main_window, controller):
        self.main_window = main_window
        self.controller = controller
        self.current_testing_pin = None
    
    def after(self, delay_ms, callback):
        """
        Qt equivalent of Tkinter's root.after() for thread-safe UI updates.
        
        Args:
            delay_ms: Delay in milliseconds (0 means execute on next event loop)
            callback: Function to call in main thread
        """
        # Debug logging
        import threading
        print(f"[QtTableAdapter.after] Scheduling callback from thread {threading.current_thread().name}, delay={delay_ms}ms")
        
        # Store callback with unique ID
        callback_id = str(id(callback))
        self.main_window._pending_callbacks[callback_id] = callback
        print(f"[QtTableAdapter.after] Stored callback ID {callback_id}")
        
        # Use invokeMethod to schedule on main thread
        QMetaObject.invokeMethod(
            self.main_window,
            "_schedule_callback",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(int, delay_ms),
            Q_ARG(str, callback_id)
        )
        print(f"[QtTableAdapter.after] invokeMethod called for callback {callback_id}")
    
    def update_row(self, pin_id: str, values: Dict[str, str]):
        """
        Update a table row (Qt implementation) - thread-safe.
        Also updates status labels when test results are available.
        
        Args:
            pin_id: Pin ID to update
            values: Dictionary of column values to update
        """
        # Debug logging to trace execution
        print(f"[QtTableAdapter] update_row called: pin_id={pin_id}, values={values}")
        
        # Check if we're testing a new pin
        if pin_id != self.current_testing_pin:
            self.current_testing_pin = pin_id
            # Update "Testing Pin" status label
            self.controller.update_testing_pin(pin_id)
        
        # Extract test results from values dict
        power_result = values.get('Power_Result')
        pullup_result = values.get('PullUp_Result')
        logic_result = values.get('Logic_DI_Result')
        
        # Update test result labels if any results are present
        if power_result or pullup_result or logic_result:
            self.controller.update_test_results(
                power_result=power_result,
                pullup_result=pullup_result,
                logic_result=logic_result
            )
        
        # Update the table (thread-safe)
        QTimer.singleShot(0, lambda: self.main_window.table.update_row(pin_id, values))
    
    def select_all(self):
        """Select all rows in the table."""
        QMetaObject.invokeMethod(
            self.main_window.table,
            "selectAll",
            Qt.ConnectionType.QueuedConnection
        )
    
    def set_testing_pin(self, pin_id: Optional[str]):
        """
        Highlight the row currently being tested (thread-safe).
        
        Args:
            pin_id: Pin ID currently being tested, or None to clear
        """
        print(f"[QtTableAdapter.set_testing_pin] Called with pin_id={pin_id}")
        QTimer.singleShot(0, lambda: self.main_window.table.set_testing_pin(pin_id))
    
    def get_all_rows(self) -> List[dict]:
        """Get all table rows as dictionaries."""
        # TestHandle passes all_rows explicitly, so this isn't needed
        # Just return empty list as placeholder
        return []
