"""
Voltage measurement and continuity checking module.
"""
import time
from typing import Optional, List
from pathlib import Path
from statistics import mean
import yaml
from hw_tester.hardware.hardware_factory import initialize_hardware


class Measurer:
    """
    Handles voltage reading and continuity checks via the hardware layer.
    """
    
    def __init__(self, hardware_io=None, settings: Optional[dict] = None):
        """
        Initialize the Measurer with a hardware I/O interface.
        
        Args:
            hardware_io: Hardware abstraction object (controllino_io or mock_io)
                        Must implement analog_read(port) method
                        If None, will auto-initialize based on settings Board->Type
            settings: Optional settings dictionary. If None, will load from settings.yaml
        """
        # Load settings if not provided
        if settings is None:
            settings = self._load_settings()
        
        self.settings = settings
        
        # Initialize hardware if not provided - use factory to get hardware based on Type
        if hardware_io is None:
            hardware_io = initialize_hardware(settings)
        
        self.hardware = hardware_io
        
        # Get default values from settings
        timeouts = settings.get('Timeouts', {})
        self.default_duration = timeouts.get('duration', 3.0)
        self.default_sample_interval = timeouts.get('sample_interval', 0.1)
    
    def _load_settings(self) -> dict:
        """Load settings from settings.yaml"""
        project_root = Path(__file__).resolve().parents[3]
        settings_path = project_root / "src" / "hw_tester" / "config" / "settings.yaml"
        
        if not settings_path.exists():
            # Return defaults if settings file not found
            return {
                'Timeouts': {
                    'duration': 3.0,
                    'sample_interval': 0.1
                }
            }
        
        with open(settings_path, 'r') as f:
            return yaml.safe_load(f)
    
    def measure_voltage(
        self, 
        analog_port: int, 
        duration: Optional[float] = None,
        sample_interval: Optional[float] = None
    ) -> float:
        """
        Measure voltage on an analog port over a specified time period.
        
        Args:
            analog_port: Analog port number (e.g., 0 for A0, 1 for A1, etc.)
            duration: Time to measure in seconds (default: from settings.yaml)
            sample_interval: Time between samples in seconds (default: from settings.yaml)
        
        Returns:
            Average voltage reading (float), defaults to 0.0 if no readings
        
        Example:
            voltage = measurer.measure_voltage(analog_port=0)  # Uses settings
            voltage = measurer.measure_voltage(analog_port=0, duration=1.0)  # Override
        """
        # Use settings defaults if not provided
        if duration is None:
            duration = self.default_duration
        if sample_interval is None:
            sample_interval = self.default_sample_interval
        
        if duration <= 0:
            raise ValueError("Duration must be greater than 0")
        
        if sample_interval <= 0:
            raise ValueError("Sample interval must be greater than 0")
        
        # Check if simulation mode is enabled
        is_simulation = self.settings.get('Board', {}).get('simulation', True)
        
        if is_simulation:
            # Simulation mode: Return predefined/fake voltage data
            # Simulate realistic voltage reading with small variations
            import random
            base_voltage = 3.3 if analog_port % 2 == 0 else 5.0
            simulated_voltage = base_voltage + random.uniform(-0.1, 0.1)
            time.sleep(duration)  # Simulate measurement time
            return round(simulated_voltage, 2)
        
        # Real hardware mode: Read actual data from board
        if self.hardware is None:
            raise RuntimeError("Hardware I/O not initialized. Cannot measure voltage.")
        
        readings: List[float] = []
        start_time = time.time()
        end_time = start_time + duration
        
        # Collect samples during the specified duration
        while time.time() < end_time:
            # Read voltage from hardware
            voltage = self.hardware.analog_read(analog_port)
            readings.append(voltage)
            
            # Wait for next sample (if time remaining)
            remaining_time = end_time - time.time()
            if remaining_time > sample_interval:
                time.sleep(sample_interval)
        

        # Apply voltage scaling factor from settings
        voltage_scale = self.settings.get('scale', {}).get('voltage', 1.0)

        # Return average voltage, or 0.0 if no readings
        if not readings:
            return 0.0
        
        return mean(readings)*voltage_scale
    
    
