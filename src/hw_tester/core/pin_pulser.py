"""
Pin pulser functionality for digital port control.
"""
import time
import threading
from typing import Optional
from pathlib import Path
import yaml
from hw_tester.hardware.hardware_factory import initialize_hardware


class PinPulser:
    """
    Manages digital port pulsing functionality.
    Sets a digital port HIGH and automatically sets it LOW after a timeout.
    """
    
    def __init__(self, hardware_io=None, settings: Optional[dict] = None):
        """
        Initialize PinPulser with hardware I/O interface.
        
        Args:
            hardware_io: Hardware abstraction object (controllino_io or mock_io)
                        Must implement digital_write(port, value) method
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
        
        # Get default timeout from settings
        timeouts = settings.get('Timeouts', {})
        self.default_timeout = timeouts.get('TestStep', 2.5)
        
        # Track active timers
        self._active_timers = {}
    
    def _load_settings(self) -> dict:
        """Load settings from settings.yaml"""
        project_root = Path(__file__).resolve().parents[3]
        settings_path = project_root / "src" / "hw_tester" / "config" / "settings.yaml"
        
        if not settings_path.exists():
            # Return defaults if settings file not found
            return {
                'Timeouts': {
                    'TestStep': 2.5
                }
            }
        
        with open(settings_path, 'r') as f:
            return yaml.safe_load(f)
    
    def pulse(self, digital_port: int, timeout: Optional[float] = None) -> None:
        """
        Set digital port HIGH and automatically set it LOW after timeout.
        
        This is a blocking operation - the function returns after the pulse is complete.
        
        Args:
            digital_port: Digital port number to pulse
            timeout: Time in seconds to keep port HIGH (default: from settings.yaml)
        
        Example:
            keep_alive.pulse(digital_port=5, timeout=3.0)  # D5 HIGH for 3 seconds
        """
        if timeout is None:
            timeout = self.default_timeout
        
        if timeout <= 0:
            raise ValueError("Timeout must be greater than 0")
        
        # Set port HIGH
        if self.hardware is not None:
            self.hardware.digital_write(digital_port, True)
        
        # Wait for timeout
        time.sleep(timeout)
        
        # Set port LOW
        if self.hardware is not None:
            self.hardware.digital_write(digital_port, False)
    
    def pulse_async(self, digital_port: int, timeout: Optional[float] = None) -> threading.Timer:
        """
        Set digital port HIGH and schedule it to go LOW after timeout (non-blocking).
        
        Returns immediately. The port will be set LOW automatically after timeout.
        
        Args:
            digital_port: Digital port number to pulse
            timeout: Time in seconds to keep port HIGH (default: from settings.yaml)
        
        Returns:
            Timer object that can be cancelled if needed
        
        Example:
            timer = keep_alive.pulse_async(digital_port=5, timeout=3.0)
            # Do other work...
            # timer.cancel()  # Optional: cancel before timeout
        """
        if timeout is None:
            timeout = self.default_timeout
        
        if timeout <= 0:
            raise ValueError("Timeout must be greater than 0")
        
        # Cancel existing timer for this port if any
        if digital_port in self._active_timers:
            self._active_timers[digital_port].cancel()
        
        # Set port HIGH immediately
        if self.hardware is not None:
            self.hardware.digital_write(digital_port, True)
        
        # Schedule LOW after timeout
        def set_low():
            if self.hardware is not None:
                self.hardware.digital_write(digital_port, False)
            # Remove from active timers
            if digital_port in self._active_timers:
                del self._active_timers[digital_port]
        
        timer = threading.Timer(timeout, set_low)
        self._active_timers[digital_port] = timer
        timer.start()
        
        return timer
    
    def set_high(self, digital_port: int) -> None:
        """
        Set digital port HIGH without automatic timeout.
        
        Args:
            digital_port: Digital port number to set HIGH
        """
        if self.hardware is not None:
            self.hardware.digital_write(digital_port, True)
    
    def set_low(self, digital_port: int) -> None:
        """
        Set digital port LOW.
        
        Args:
            digital_port: Digital port number to set LOW
        """
        # Cancel any pending timer for this port
        if digital_port in self._active_timers:
            self._active_timers[digital_port].cancel()
            del self._active_timers[digital_port]
        
        if self.hardware is not None:
            self.hardware.digital_write(digital_port, False)
    
    def cancel_all(self) -> None:
        """Cancel all active timers and set all ports LOW."""
        for port, timer in list(self._active_timers.items()):
            timer.cancel()
            if self.hardware is not None:
                self.hardware.digital_write(port, False)
        self._active_timers.clear()
