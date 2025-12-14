"""
UDP Sender - Bidirectional UDP communication at 20 Hz.
Sends 32 bytes to remote host.
Receives 64 bytes from remote host.
"""
import socket
import struct
import threading
import time
from typing import Optional, Callable, List, Dict
import yaml
from pathlib import Path

# Import handling for both direct execution and package import
try:
    from .udp_data_mapper import SendData, ReceiveData
except ImportError:
    from udp_data_mapper import SendData, ReceiveData


class UDPSender:
    """
    UDP communication handler for sending and receiving data at configurable frequency.
    
    Sends 32 bytes to remote host (SendData structure).
    Receives 64 bytes from remote host (ReceiveData structure).
    
    Uses udp_data_mapper for logical parameter abstraction:
    - SendData: Maps logical outputs to 32-byte send structure
    - ReceiveData: Parses 64-byte receive structure to logical inputs
    
    Supports up to 7 cards with independent UDP configurations loaded from settings.yaml.
    """
    
    @staticmethod
    def load_settings(settings_path: str = None) -> dict:
        """
        Load UDP settings from settings.yaml file.
        
        Args:
            settings_path: Path to settings.yaml file (default: auto-detect)
        
        Returns:
            Dictionary with UDP settings
        """
        if settings_path is None:
            # Try to find settings.yaml relative to this file
            current_file = Path(__file__)
            settings_path = current_file.parent.parent / "config" / "settings.yaml"
        
        try:
            with open(settings_path, 'r') as f:
                settings = yaml.safe_load(f)
                return settings.get('UDP_Settings', {})
        except Exception as e:
            return {}
    
    @classmethod
    def get_card_configs_from_settings(cls, settings_path: str = None) -> List[dict]:
        """
        Get all card configurations from settings.yaml.
        
        Args:
            settings_path: Path to settings.yaml file (default: auto-detect)
        
        Returns:
            List of card configuration dictionaries
            
        Raises:
            FileNotFoundError: If settings.yaml not found or Cards section missing
        """
        udp_settings = cls.load_settings(settings_path)
        cards = udp_settings.get('Cards', [])
        
        if not cards:
            if settings_path is None:
                settings_path = Path(__file__).parent.parent / "config" / "settings.yaml"
            raise FileNotFoundError(
                f"ERROR: No cards found in settings.yaml!\n"
                f"Please check: {settings_path}\n"
                f"Make sure 'UDP_Settings.Cards' section exists and contains card configurations."
            )
        
        return cards
    
    @classmethod
    def get_frequency_from_settings(cls, settings_path: str = None) -> float:
        """
        Get frequency setting from settings.yaml.
        
        Args:
            settings_path: Path to settings.yaml file (default: auto-detect)
        
        Returns:
            Frequency in Hz (default: 20.0)
        """
        udp_settings = cls.load_settings(settings_path)
        return udp_settings.get('Frequency_Hz', 20.0)
    
    @classmethod
    def get_timeout_from_settings(cls, settings_path: str = None) -> float:
        """
        Get communication timeout setting from settings.yaml.
        
        Args:
            settings_path: Path to settings.yaml file (default: auto-detect)
        
        Returns:
            Timeout in seconds (default: 2.0)
        """
        udp_settings = cls.load_settings(settings_path)
        return udp_settings.get('Communication_Timeout', 2.0)
    
    def __init__(
        self,
        card_id: int = 1,
        frequency_hz: float = None,
        communication_timeout: float = None,
        settings_path: str = None
    ):
        """
        Initialize UDP sender/receiver.
        
        Args:
            card_id: Card identifier (1-7)
            frequency_hz: Update frequency in Hz (default: from settings.yaml or 20 Hz)
            communication_timeout: Timeout in seconds for declaring "no communication" (default: from settings.yaml or 2.0s)
            settings_path: Path to settings.yaml file (default: auto-detect)
        """
        self.card_id = card_id
        self.settings_path = settings_path
        
        # Load frequency from settings if not provided
        if frequency_hz is None:
            frequency_hz = self.get_frequency_from_settings(settings_path)
        
        # Load communication timeout from settings if not provided
        if communication_timeout is None:
            communication_timeout = self.get_timeout_from_settings(settings_path)
        
        self.communication_timeout = communication_timeout
        
        # Load card configuration from settings.yaml
        cards_config = self.get_card_configs_from_settings(settings_path)
        
        # Find configuration for this card_id
        card_config = None
        for config in cards_config:
            if config.get('card_id') == card_id:
                card_config = config
                break
        
        if card_config:
            # Use configuration from settings.yaml
            self.enabled = card_config.get("enabled", False)
            self.send_ip = card_config.get("send_ip", "192.168.195.11")
            self.send_port = card_config.get("send_port", 2880)
            self.receive_ip = card_config.get("receive_ip", "192.168.195.10")
            self.receive_port = card_config.get("receive_port", 1011)
        else:
            # Card not found in settings
            raise ValueError(
                f"ERROR: Card {card_id} not found in settings.yaml!\n"
                f"Please add card_id: {card_id} to the UDP_Settings.Cards section.\n"
                f"Available cards: {[c.get('card_id') for c in cards_config]}"
            )
        
        self.frequency_hz = frequency_hz
        self.period = 1.0 / frequency_hz  # 50ms for 20 Hz
        
        # Sockets
        self.send_socket = None
        self.receive_socket = None
        
        # Thread control
        self.running = False
        self.send_thread = None
        self.receive_thread = None
        
        # Data mappers
        self._send_data = SendData()  # 32 bytes to send
        self._receive_data = ReceiveData()  # 64 bytes received
        self._data_lock = threading.Lock()
        
        # Communication status tracking
        self.last_receive_time = None
        self.communication_active = False
        
        # Statistics
        self.send_count = 0
        self.receive_count = 0
        
        # Callbacks
        self.on_data_received: Optional[Callable[[List[int]], None]] = None
    
    def start(self) -> None:
        """Start UDP sender and receiver threads."""
        if not self.enabled:
            return
        
        if self.running:
            return
        
        # Create send socket
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Create receive socket
        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.receive_socket.bind((self.receive_ip, self.receive_port))
        self.receive_socket.settimeout(1.0)
        
        # Start threads
        self.running = True
        self.send_thread = threading.Thread(target=self._send_loop, daemon=True, name=f"UDPSend-Card{self.card_id}")
        self.receive_thread = threading.Thread(target=self._receive_loop, daemon=True, name=f"UDPRecv-Card{self.card_id}")
        
        self.send_thread.start()
        self.receive_thread.start()
    
    def stop(self) -> None:
        """Stop UDP sender and receiver threads."""
        if not self.running:
            return
        
        self.running = False
        
        # Wait for threads to finish
        if self.send_thread:
            self.send_thread.join(timeout=2.0)
        if self.receive_thread:
            self.receive_thread.join(timeout=2.0)
        
        # Close sockets
        if self.send_socket:
            self.send_socket.close()
        if self.receive_socket:
            self.receive_socket.close()
    
    # ===== SendData Pass-through Methods =====
    
    def set_digital_output(self, do_number: int, state: bool) -> None:
        """Set digital output state (DO 1-32)."""
        with self._data_lock:
            self._send_data.set_digital_output(do_number, state)
    
    def set_digital_outputs(self, do_list: List[int]) -> None:
        """Set multiple digital outputs to ON, all others to OFF."""
        with self._data_lock:
            self._send_data.set_digital_outputs(do_list)
    
    def get_digital_output(self, do_number: int) -> bool:
        """Get digital output state."""
        with self._data_lock:
            return self._send_data.get_digital_output(do_number)
    
    def set_ttl_output(self, ttl_number: int, state: bool) -> None:
        """Set TTL output state (TTL 1-16)."""
        with self._data_lock:
            self._send_data.set_ttl_output(ttl_number, state)
    
    def set_ttl_outputs(self, ttl_list: List[int]) -> None:
        """Set multiple TTL outputs to ON, all others to OFF."""
        with self._data_lock:
            self._send_data.set_ttl_outputs(ttl_list)
    
    def get_ttl_output(self, ttl_number: int) -> bool:
        """Get TTL output state."""
        with self._data_lock:
            return self._send_data.get_ttl_output(ttl_number)
    
    def set_matrix_dimensions(self, rows: int, columns: int) -> None:
        """Set matrix dimensions (0-8 each)."""
        with self._data_lock:
            self._send_data.set_matrix_dimensions(rows, columns)
    
    def get_matrix_dimensions(self) -> tuple:
        """Get matrix dimensions."""
        with self._data_lock:
            return self._send_data.get_matrix_dimensions()
    
    def set_analog_output(self, ao_number: int, voltage: float) -> None:
        """Set analog output voltage (AO 0-7, -13.5 to +13.5V)."""
        with self._data_lock:
            self._send_data.set_analog_output(ao_number, voltage)
    
    def get_analog_output(self, ao_number: int) -> Optional[float]:
        """Get analog output voltage."""
        with self._data_lock:
            return self._send_data.get_analog_output(ao_number)
    
    def set_multiple_analog_outputs(self, analog_values: Dict[int, float]) -> None:
        """Set multiple analog outputs at once."""
        with self._data_lock:
            self._send_data.set_multiple_analog_outputs(analog_values)
    
    def get_send_data_dict(self) -> Dict:
        """Export send data as dictionary."""
        with self._data_lock:
            return self._send_data.to_dict()
    
    def clear_all_outputs(self) -> None:
        """Clear all output data."""
        with self._data_lock:
            self._send_data.clear_all()
    
    # ===== ReceiveData Pass-through Methods =====
    
    def get_digital_input(self, di_number: int) -> bool:
        """Get digital input state (DI 1-64)."""
        with self._data_lock:
            return self._receive_data.get_digital_input(di_number)
    
    def get_digital_inputs_active(self) -> List[int]:
        """Get list of active digital inputs."""
        with self._data_lock:
            return self._receive_data.get_digital_inputs_active()
    
    def get_analog_input(self, ai_number: int) -> Optional[float]:
        """Get analog input voltage (AI 1-16)."""
        with self._data_lock:
            return self._receive_data.get_analog_input(ai_number)
    
    def get_receive_data_dict(self) -> Dict:
        """Export received data as dictionary."""
        with self._data_lock:
            return self._receive_data.to_dict()
    
    def _send_loop(self) -> None:
        """Send loop running at specified frequency."""
        while self.running:
            start_time = time.time()
            
            try:
                # Get current send data from mapper
                with self._data_lock:
                    data_to_send = self._send_data.get_bytes()
                
                # Send data (32 bytes)
                self.send_socket.sendto(data_to_send, (self.send_ip, self.send_port))
                self.send_count += 1
                
            except Exception as e:
                pass  # Silent failure, communication_active flag will handle timeout
            
            # Sleep to maintain frequency
            elapsed = time.time() - start_time
            sleep_time = max(0, self.period - elapsed)
            time.sleep(sleep_time)
    
    def _receive_loop(self) -> None:
        """Receive loop for incoming data."""
        while self.running:
            try:
                # Receive data: 64 bytes
                data, addr = self.receive_socket.recvfrom(1024)
                
                if len(data) == 64:
                    # Update receive data mapper
                    with self._data_lock:
                        self._receive_data.update(data)
                        self.last_receive_time = time.time()
                        self.communication_active = True
                    
                    self.receive_count += 1
                    
                    # Call callback if registered
                    if self.on_data_received:
                        self.on_data_received(list(data))
                
            except socket.timeout:
                # Check if communication timeout has occurred
                if self.last_receive_time is not None:
                    time_since_last = time.time() - self.last_receive_time
                    if time_since_last > self.communication_timeout:
                        if self.communication_active:
                            self.communication_active = False
                continue
            except Exception as e:
                if self.running:
                    pass  # Silent failure
    
    def get_statistics(self) -> dict:
        """
        Get communication statistics.
        
        Returns:
            Dictionary with send_count, receive_count, and communication status
        """
        with self._data_lock:
            time_since_last = None
            if self.last_receive_time is not None:
                time_since_last = time.time() - self.last_receive_time
        
        return {
            "send_count": self.send_count,
            "receive_count": self.receive_count,
            "frequency_hz": self.frequency_hz,
            "period_ms": self.period * 1000,
            "communication_active": self.communication_active,
            "time_since_last_receive": time_since_last,
            "communication_timeout": self.communication_timeout
        }
    
    def is_communication_active(self) -> bool:
        """
        Check if communication with the card is active.
        
        Returns:
            True if data received within timeout period, False otherwise
        """
        if self.last_receive_time is None:
            return False
        
        time_since_last = time.time() - self.last_receive_time
        return time_since_last <= self.communication_timeout
    
    def __repr__(self) -> str:
        comm_status = "active" if self.communication_active else "inactive"
        enabled_status = "enabled" if self.enabled else "disabled"
        return (
            f"UDPSender(card_id={self.card_id}, {enabled_status}, send={self.send_ip}:{self.send_port}, "
            f"receive={self.receive_ip}:{self.receive_port}, "
            f"freq={self.frequency_hz}Hz, running={self.running}, comm={comm_status})"
        )
    
    @classmethod
    def create_all_cards(cls, frequency_hz: float = None, settings_path: str = None) -> List['UDPSender']:
        """
        Create UDPSender instances for all cards defined in settings.yaml.
        
        Args:
            frequency_hz: Update frequency in Hz for all cards (default: from settings.yaml)
            settings_path: Path to settings.yaml file (default: auto-detect)
        
        Returns:
            List of UDPSender instances (one per card in settings)
        """
        cards_config = cls.get_card_configs_from_settings(settings_path)
        
        if frequency_hz is None:
            frequency_hz = cls.get_frequency_from_settings(settings_path)
        
        cards = []
        for config in cards_config:
            card_id = config.get('card_id', len(cards) + 1)
            sender = cls(
                card_id=card_id,
                frequency_hz=frequency_hz,
                settings_path=settings_path
            )
            cards.append(sender)
        
        return cards
    
    @classmethod
    def create_enabled_cards(cls, frequency_hz: float = None, settings_path: str = None) -> List['UDPSender']:
        """
        Create UDPSender instances only for enabled cards in settings.yaml.
        
        Args:
            frequency_hz: Update frequency in Hz for all cards (default: from settings.yaml)
            settings_path: Path to settings.yaml file (default: auto-detect)
        
        Returns:
            List of UDPSender instances (only enabled cards)
        """
        all_cards = cls.create_all_cards(frequency_hz, settings_path)
        enabled_cards = [card for card in all_cards if card.enabled]
        return enabled_cards
    
    @classmethod
    def get_card_config(cls, card_id: int, settings_path: str = None) -> dict:
        """
        Get configuration for a specific card from settings.yaml.
        
        Args:
            card_id: Card identifier
            settings_path: Path to settings.yaml file (default: auto-detect)
        
        Returns:
            Dictionary with card configuration
        """
        cards_config = cls.get_card_configs_from_settings(settings_path)
        
        for config in cards_config:
            if config.get('card_id') == card_id:
                return config.copy()
        
        # Card not found
        raise ValueError(
            f"ERROR: Card {card_id} not found in settings.yaml!\n"
            f"Please add card_id: {card_id} to the UDP_Settings.Cards section.\n"
            f"Available cards: {[c.get('card_id') for c in cards_config]}"
        )


# Demo/Test code
if __name__ == "__main__":
    """
    Test UDP sender/receiver with data mapper integration.
    Run this script directly to test the UDP communication.
    """
    print("=" * 60)
    print("UDP Sender/Receiver Test (with Data Mapper)")
    print("=" * 60)
    
    def on_data_received(data: List[int]):
        """Callback for received data."""
        print(f"[Callback] Received {len(data)} bytes")
    
    # Create sender for Card 1
    print("\n[TEST] Creating UDPSender for Card 1...")
    sender = UDPSender(card_id=1)
    
    print(f"[TEST] Card 1 enabled: {sender.enabled}")
    
    if not sender.enabled:
        print("[TEST] Card 1 is disabled in settings.yaml")
        print("[TEST] Trying to find enabled cards...")
        enabled_cards = UDPSender.create_enabled_cards()
        if not enabled_cards:
            print("[TEST] No cards are enabled. Exiting test.")
            print("=" * 60)
            exit(0)
        else:
            print(f"[TEST] Using first enabled card: Card {enabled_cards[0].card_id}")
            sender = enabled_cards[0]
    
    # Register callback
    sender.on_data_received = on_data_received
    
    # Start communication
    print("\n[TEST] Starting UDP communication...")
    sender.start()
    
    # Configure outputs using data mapper
    print("\n[TEST] Configuring outputs...")
    
    # Set digital outputs
    sender.set_digital_outputs([1, 5, 9, 17, 32])
    print(f"[TEST] Set DO: 1, 5, 9, 17, 32")
    
    # Set TTL outputs
    sender.set_ttl_outputs([1, 8, 16])
    print(f"[TEST] Set TTL: 1, 8, 16")
    
    # Set matrix dimensions
    sender.set_matrix_dimensions(4, 6)
    print(f"[TEST] Set Matrix: 4x6")
    
    # Set analog outputs
    sender.set_analog_output(1, 5.0)
    sender.set_multiple_analog_outputs({2: -3.2, 8: 10.5})
    print(f"[TEST] Set AO: 1=5.0V, 2=-3.2V, 8=10.5V")
    
    # Display send data
    print(f"\n[TEST] Send data: {sender.get_send_data_dict()}")
    
    try:
        # Run for 5 seconds, monitoring communication
        for i in range(10):
            time.sleep(0.5)
            
            # Get statistics
            stats = sender.get_statistics()
            comm_status = "ACTIVE" if stats['communication_active'] else "INACTIVE"
            time_since = stats['time_since_last_receive']
            time_str = f"{time_since:.2f}s" if time_since is not None else "N/A"
            
            print(f"\n[TEST] Iteration {i+1}: Sent={stats['send_count']}, Received={stats['receive_count']}, "
                  f"Comm={comm_status}, Last={time_str}")
            
            # Check communication status
            if sender.is_communication_active():
                print(f"[TEST] ✓ Communication with Card {sender.card_id} is active")
                
                # Display some received data
                di_active = sender.get_digital_inputs_active()
                print(f"[TEST] Active DI: {di_active[:10]}{'...' if len(di_active) > 10 else ''}")
                
                ai1 = sender.get_analog_input(1)
                if ai1 is not None:
                    print(f"[TEST] AI1: {ai1:.3f}V")
            else:
                print(f"[TEST] ✗ No communication with Card {sender.card_id}")
    
    except KeyboardInterrupt:
        print("\n[TEST] Interrupted by user")
    
    finally:
        # Stop communication
        print("\n[TEST] Stopping...")
        sender.stop()
        print("\n" + "=" * 60)
        print("Test complete")
        print("=" * 60)
