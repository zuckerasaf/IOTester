"""
OperationalPanel component - Connector label and action buttons.
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Dict


class OperationalPanel(tk.Frame):
    """
    Operational panel with connector label and action buttons.
    Layout: Left side = connector label, Right side = 5 buttons in grid.
    """
    
    def __init__(
        self,
        parent: tk.Widget,
        on_load: Optional[Callable[[], None]] = None,
        on_keep_alive: Optional[Callable[[], None]] = None,
        on_i_bit: Optional[Callable[[], None]] = None,
        on_test: Optional[Callable[[], None]] = None,
        on_stop_ibit: Optional[Callable[[], None]] = None,
        on_stop_t: Optional[Callable[[], None]] = None,
        on_report: Optional[Callable[[], None]] = None,
        on_clear_log: Optional[Callable[[], None]] = None,
        settings: Optional[Dict] = None,
        on_hw_change: Optional[Callable[[str], None]] = None,
        on_simulate_change: Optional[Callable[[str], None]] = None,
        on_iobox_change: Optional[Callable[[str], None]] = None
    ):
        """
        Initialize OperationalPanel.
        
        Args:
            parent: Parent tkinter widget
            on_load: Callback for Load button
            on_keep_alive: Callback for KeepAlive button
            on_i_bit: Callback for I_Bit button
            on_test: Callback for Test button
            on_stop_ibit: Callback for Stop_IBIT button
            on_stop_t: Callback for Stop_T button
            on_report: Callback for Report button
            on_clear_log: Callback for ClearLog button
            settings: Settings dictionary from settings.yaml
            on_hw_change: Callback when hardware selection changes (receives new hw type)
            on_simulate_change: Callback when simulation mode changes (receives "Simulation On" or "Simulation Off")
            on_iobox_change: Callback when IO Box selection changes (receives new box type)
        """
        super().__init__(parent)
        
        # Configure grid layout - multiple columns for new layout
        # Layout: connector_label | Load | HW dropdown | KeepAlive | I_Bit | Test | Report (row 0)
        #                         |      | Sim dropdown |          | Stop_IBIT  | Stop_T | ClearLog (row 1)
        self.columnconfigure(0, weight=1)  # Connector label (resizable)
        for i in range(1, 8):  # Columns 1-7 for controls
            self.columnconfigure(i, weight=0)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        # Store callbacks
        self.on_load = on_load or (lambda: None)
        self.on_keep_alive = on_keep_alive or (lambda: None)
        self.on_i_bit = on_i_bit or (lambda: None)
        self.on_test = on_test or (lambda: None)
        self.on_stop_ibit = on_stop_ibit or (lambda: None)
        self.on_stop_t = on_stop_t or (lambda: None)
        self.on_report = on_report or (lambda: None)
        self.on_clear_log = on_clear_log or (lambda: None)
        self.on_hw_change = on_hw_change or (lambda hw: None)
        self.on_simulate_change = on_simulate_change or (lambda mode: None)
        self.on_iobox_change = on_iobox_change or (lambda box: None)
        
        # Store settings
        self.settings = settings or {}
        
        # Create left side - Connector label (resized)
        label_frame = tk.Frame(self, relief=tk.SUNKEN, borderwidth=2)
        label_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10))
        
        self.connector_label = tk.Label(
            label_frame,
            text="Connector Name",
            font=("Arial", 12, "bold"),
            anchor=tk.W,
            padx=8,
            pady=8
        )
        self.connector_label.pack(fill=tk.BOTH, expand=True)
        
        # Define button styles
        self._setup_styles()
        
        # Row 0: Load | HW dropdown | KeepAlive | I_Bit | Test | Report
        # Column 1: Load button
        self.btn_load = ttk.Button(
            self,
            text="Load",
            style="Secondary.TButton",
            command=self.on_load
        )
        self.btn_load.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # Row 1: IO Box dropdown - populated from settings.yaml
        io_box_config = self.settings.get('IO_Box', {})
        available_boxes = io_box_config.get('AvailableTypes', ['Demo', 'MTC_FWD', 'MTC_AFT'])
        current_box = io_box_config.get('Type', 'Demo')
        
        self.iobox_combo = ttk.Combobox(
            self,
            values=available_boxes,
            state="readonly",
            width=15
        )
        self.iobox_combo.set(current_box)
        self.iobox_combo.bind('<<ComboboxSelected>>', self._on_iobox_changed)
        self.iobox_combo.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # Column 2: Hardware dropdown - populated from settings.yaml
        board_config = self.settings.get('Board', {})
        available_types = board_config.get('AvailableTypes', ['ControllinoMega', 'ArduinoUno', 'none'])
        current_type = board_config.get('Type', 'ControllinoMega')
        
        self.hw_combo = ttk.Combobox(
            self,
            values=available_types,
            state="readonly",
            width=15
        )
        self.hw_combo.set(current_type)
        self.hw_combo.bind('<<ComboboxSelected>>', self._on_hw_changed)
        self.hw_combo.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        
        # Column 3: KeepAlive button
        self.btn_connect = ttk.Button(
            self,
            text="KeepAlive",
            style="Secondary.TButton",
            command=self.on_keep_alive
        )
        self.btn_connect.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        
        # Column 4: I_Bit button
        self.btn_i_bit = ttk.Button(
            self,
            text="I_Bit",
            style="Info.TButton",
            command=self.on_i_bit
        )
        self.btn_i_bit.grid(row=0, column=4, padx=5, pady=5, sticky="ew")
        
        # Column 5: Test button
        self.btn_run = ttk.Button(
            self,
            text="Test",
            style="Primary.TButton",
            command=self.on_test
        )
        self.btn_run.grid(row=0, column=5, padx=5, pady=5, sticky="ew")
        
        # Column 6: Report button
        self.btn_report = ttk.Button(
            self,
            text="Report",
            style="Info.TButton",
            command=self.on_report
        )
        self.btn_report.grid(row=0, column=6, padx=5, pady=5, sticky="ew")
        
        # Row 1: (empty) | Simulate dropdown | (empty) | Stop_IBIT | Stop_T | ClearLog
        # Column 2: Simulate dropdown - populated from settings.yaml
        current_simulation = board_config.get('simulation', False)
        simulate_mode = "Simulation On" if current_simulation else "Simulation Off"
        
        self.simulate_combo = ttk.Combobox(
            self,
            values=["Simulation On", "Simulation Off"],
            state="readonly",
            width=15
        )
        self.simulate_combo.set(simulate_mode)
        self.simulate_combo.bind('<<ComboboxSelected>>', self._on_simulate_changed)
        self.simulate_combo.grid(row=1, column=2, padx=5, pady=5, sticky="ew")
        
        # Column 4: Stop_IBIT button
        self.btn_stop_ibit = ttk.Button(
            self,
            text="Stop_IBIT",
            style="Danger.TButton",
            command=self.on_stop_ibit,
            state=tk.DISABLED
        )
        self.btn_stop_ibit.grid(row=1, column=4, padx=5, pady=5, sticky="ew")
        
        # Column 5: Stop_T button
        self.btn_stop = ttk.Button(
            self,
            text="Stop_T",
            style="Danger.TButton",
            command=self.on_stop_t,
            state=tk.DISABLED
        )
        self.btn_stop.grid(row=1, column=5, padx=5, pady=5, sticky="ew")
        
        # Column 6: ClearLog button
        self.btn_clear_log = ttk.Button(
            self,
            text="ClearLog",
            style="Utility.TButton",
            command=self.on_clear_log
        )
        self.btn_clear_log.grid(row=1, column=6, padx=5, pady=5, sticky="ew")
    
    def _setup_styles(self) -> None:
        """Setup custom button styles."""
        style = ttk.Style()
        
        # Primary button (green for Test)
        style.configure("Primary.TButton", background="#28a745", foreground="black")
        style.map("Primary.TButton",
                  background=[("active", "#218838"), ("disabled", "#c3e6cb")])
        
        # Danger button (orange/red for Stop_T)
        style.configure("Danger.TButton", background="#fd7e14", foreground="black")
        style.map("Danger.TButton",
                  background=[("active", "#e36209"), ("disabled", "#ffc9a0")])
        
        # Secondary button (blue for KeepAlive)
        style.configure("Secondary.TButton", background="#007bff", foreground="black")
        style.map("Secondary.TButton",
                  background=[("active", "#0056b3"), ("disabled", "#99c9ff")])
        
        # Info button (gray for Report)
        style.configure("Info.TButton", background="#6c757d", foreground="black")
        style.map("Info.TButton",
                  background=[("active", "#545b62"), ("disabled", "#c6c9cc")])
        
        # Utility button (light for ClearLog)
        style.configure("Utility.TButton", background="#f8f9fa", foreground="black")
        style.map("Utility.TButton",
                  background=[("active", "#e2e6ea"), ("disabled", "#f8f9fa")])
    
    def _on_hw_changed(self, event) -> None:
        """Called when hardware dropdown selection changes."""
        new_hw = self.hw_combo.get()
        self.on_hw_change(new_hw)
    
    def _on_simulate_changed(self, event) -> None:
        """Called when simulate dropdown selection changes."""
        new_mode = self.simulate_combo.get()
        self.on_simulate_change(new_mode)
    
    def _on_iobox_changed(self, event) -> None:
        """Called when IO Box dropdown selection changes."""
        new_box = self.iobox_combo.get()
        self.on_iobox_change(new_box)
    
    def set_connector(self, name: str) -> None:
        """
        Set the connector name displayed in the label.
        
        Args:
            name: Connector name to display
        """
        self.connector_label.config(text=name)
    
    def enable_stop_t(self, enabled: bool = True) -> None:
        """Enable or disable the Stop_T button."""
        self.btn_stop.config(state=tk.NORMAL if enabled else tk.DISABLED)
    
    def enable_stop_ibit(self, enabled: bool = True) -> None:
        """Enable or disable the Stop_IBIT button."""
        self.btn_stop_ibit.config(state=tk.NORMAL if enabled else tk.DISABLED)
    
    def enable_test(self, enabled: bool = True) -> None:
        """Enable or disable the Test button."""
        self.btn_run.config(state=tk.NORMAL if enabled else tk.DISABLED)
    
    def enable_i_bit(self, enabled: bool = True) -> None:
        """Enable or disable the I_Bit button."""
        self.btn_i_bit.config(state=tk.NORMAL if enabled else tk.DISABLED)
    
    def enable_load(self, enabled: bool = True) -> None:
        """Enable or disable the Load button."""
        self.btn_load.config(state=tk.NORMAL if enabled else tk.DISABLED)
    
    def enable_keep_alive(self, enabled: bool = True) -> None:
        """Enable or disable the KeepAlive button."""
        self.btn_connect.config(state=tk.NORMAL if enabled else tk.DISABLED)
    
    def get_hardware(self) -> str:
        """Get the selected hardware type."""
        return self.hw_combo.get()
    
    def set_hardware(self, hw: str) -> None:
        """Set the hardware type."""
        self.hw_combo.set(hw)
    
    def get_simulation_mode(self) -> str:
        """Get the simulation mode (On/Off)."""
        return self.simulate_combo.get()
    
    def set_simulation_mode(self, mode: str) -> None:
        """Set the simulation mode."""
        self.simulate_combo.set(mode)


# Demo/Test code
if __name__ == "__main__":
    root = tk.Tk()
    root.title("OperationalPanel Demo")
    root.geometry("1200x200")
    
    # Mock settings for demo
    demo_settings = {
        'Board': {
            'Type': 'ControllinoMega',
            'AvailableTypes': ['ControllinoMega', 'ControllinoMini', 'ArduinoUno', 'none'],
            'simulation': True
        }
    }
    
    def mock_load():
        print("Load clicked")
        panel.set_connector("J1 - Loaded")
    
    def mock_keep_alive():
        print("KeepAlive clicked")
        panel.enable_test(True)
        panel.enable_monitor(True)
    
    def mock_i_bit():
        print("I_Bit clicked")
        panel.enable_stop_ibit(True)
        panel.enable_i_bit(False)
    
    def mock_run():
        print("Test clicked")
        panel.enable_stop_t(True)
        panel.enable_test(False)
    
    def mock_stop_ibit():
        print("Stop_IBIT clicked")
        panel.enable_stop_ibit(False)
        panel.enable_i_bit(True)
    
    def mock_stop():
        print("Stop_T clicked")
        panel.enable_stop_t(False)
        panel.enable_test(True)
    
    def mock_report():
        print("Report clicked")
        print(f"Hardware: {panel.get_hardware()}")
        print(f"Simulation: {panel.get_simulation_mode()}")
    
    def mock_clear():
        print("Clear Log clicked")
    
    def mock_hw_change(new_hw: str):
        print(f"Hardware changed to: {new_hw}")
        demo_settings['Board']['Type'] = new_hw
    
    def mock_simulate_change(new_mode: str):
        print(f"Simulation mode changed to: {new_mode}")
        demo_settings['Board']['simulation'] = (new_mode == "On")
    
    panel = OperationalPanel(
        root,
        on_load=mock_load,
        on_keep_alive=mock_keep_alive,
        on_i_bit=mock_i_bit,
        on_test=mock_run,
        on_stop_ibit=mock_stop_ibit,
        on_stop_t=mock_stop,
        on_report=mock_report,
        on_clear_log=mock_clear,
        settings=demo_settings,
        on_hw_change=mock_hw_change,
        on_simulate_change=mock_simulate_change
    )
    panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    root.mainloop()
