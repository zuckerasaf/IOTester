"""
Localhost Simulator - Simulates 7 cards responding to UDP requests on localhost.

This simulator mimics real card behavior:
1. Listens for 32-byte send data from UDPSender
2. When data received, responds with fixed 64-byte data
3. Each card has its own response data loaded from text files

Perfect for local testing without real hardware or network.

Usage:
    1. Configure settings.yaml with all IPs as 127.0.0.1
    2. Run simulator: python localhost_simulator.py
    3. In another terminal, run UDPSender/UDPCardManager
    4. Simulator responds to each send with fixed data
"""
import socket
import threading
import time
from typing import Optional, Dict
from pathlib import Path


class LocalhostCardSimulator:
    """
    Simulates a single card: listens for 32-byte requests, responds with fixed 64-byte data.
    """
    
    def __init__(
        self,
        card_id: int,
        listen_port: int,
        response_ip: str,
        response_port: int,
        response_data: bytes
    ):
        """
        Initialize localhost card simulator.
        
        Args:
            card_id: Card identifier (1-7)
            listen_port: Port to listen for incoming 32-byte data (UDPSender send_port)
            response_ip: IP to send response to (usually 127.0.0.1)
            response_port: Port to send response to (UDPSender receive_port)
            response_data: Fixed 64-byte data to send as response
        """
        self.card_id = card_id
        self.listen_port = listen_port
        self.response_ip = response_ip
        self.response_port = response_port
        self.response_data = response_data
        
        if len(response_data) != 64:
            raise ValueError(f"Card {card_id}: Response data must be 64 bytes, got {len(response_data)}")
        
        # Socket and thread
        self.socket = None
        self.running = False
        self.thread = None
        
        # Statistics
        self.receive_count = 0
        self.send_count = 0
        self.last_receive_time = None
    
    def start(self) -> None:
        """Start listening for requests and responding."""
        if self.running:
            return
        
        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(("127.0.0.1", self.listen_port))
            self.socket.settimeout(1.0)
            
            # Start listener thread
            self.running = True
            self.thread = threading.Thread(
                target=self._listen_loop,
                daemon=True,
                name=f"LocalhostSim-Card{self.card_id}"
            )
            self.thread.start()
            
            print(f"[Card {self.card_id}] Listening on 127.0.0.1:{self.listen_port}, "
                  f"responding to {self.response_ip}:{self.response_port}")
        
        except Exception as e:
            print(f"[Card {self.card_id} ERROR] Failed to start: {e}")
            self.running = False
    
    def stop(self) -> None:
        """Stop listening and responding."""
        if not self.running:
            return
        
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
        
        if self.socket:
            self.socket.close()
        
        print(f"[Card {self.card_id}] Stopped. Received {self.receive_count}, Sent {self.send_count}")
    
    def _listen_loop(self) -> None:
        """Listen for 32-byte requests and respond with 64-byte data."""
        while self.running:
            try:
                # Wait for incoming data (expecting 32 bytes)
                data, addr = self.socket.recvfrom(1024)
                
                # Update statistics
                self.receive_count += 1
                self.last_receive_time = time.time()
                
                # Check if data is 32 bytes (expected send structure)
                if len(data) == 32:
                    # Send fixed 64-byte response
                    self.socket.sendto(self.response_data, (self.response_ip, self.response_port))
                    self.send_count += 1
                else:
                    print(f"[Card {self.card_id} WARNING] Received {len(data)} bytes, expected 32")
            
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[Card {self.card_id} ERROR] {e}")
    
    def get_statistics(self) -> Dict:
        """Get simulator statistics."""
        time_since_last = None
        if self.last_receive_time is not None:
            time_since_last = time.time() - self.last_receive_time
        
        return {
            "card_id": self.card_id,
            "receive_count": self.receive_count,
            "send_count": self.send_count,
            "running": self.running,
            "last_receive_time": time_since_last
        }
    
    def __repr__(self) -> str:
        return (
            f"LocalhostCardSimulator(card_id={self.card_id}, "
            f"listen={self.listen_port}, respond={self.response_ip}:{self.response_port}, "
            f"recv={self.receive_count}, sent={self.send_count})"
        )


class LocalhostSimulatorManager:
    """
    Manages 7 localhost card simulators for complete system testing.
    """
    
    # Default response data directory
    RESPONSE_DATA_DIR = Path(__file__).parent.parent.parent.parent / "tests" / "DB" / "simulator_responses"
    
    def __init__(self, response_data_dir: Path = None):
        """
        Initialize localhost simulator manager.
        
        Args:
            response_data_dir: Directory containing card response files (card1.txt - card7.txt)
        """
        if response_data_dir is None:
            response_data_dir = self.RESPONSE_DATA_DIR
        
        self.response_data_dir = Path(response_data_dir)
        self.simulators: Dict[int, LocalhostCardSimulator] = {}
        
        # Load default configurations from settings
        self._load_simulators()
    
    def _load_response_data(self, card_id: int) -> bytes:
        """
        Load 64-byte response data from text file.
        
        Args:
            card_id: Card identifier (1-7)
        
        Returns:
            64 bytes of response data
        """
        response_file = self.response_data_dir / f"card{card_id}.txt"
        
        if not response_file.exists():
            print(f"[WARNING] Response file not found: {response_file}")
            print(f"[WARNING] Creating default response for Card {card_id}")
            return self._create_default_response(card_id)
        
        try:
            # Read hex bytes from file
            with open(response_file, 'r') as f:
                content = f.read()
            
            # Remove comments and whitespace
            hex_bytes = []
            for line in content.split('\n'):
                # Remove comments
                if '#' in line:
                    line = line[:line.index('#')]
                
                # Extract hex values
                parts = line.split()
                for part in parts:
                    if len(part) == 2:
                        try:
                            hex_bytes.append(int(part, 16))
                        except ValueError:
                            continue
            
            if len(hex_bytes) != 64:
                print(f"[WARNING] Card {card_id}: Expected 64 bytes, got {len(hex_bytes)}")
                return self._create_default_response(card_id)
            
            return bytes(hex_bytes)
        
        except Exception as e:
            print(f"[ERROR] Failed to load response for Card {card_id}: {e}")
            return self._create_default_response(card_id)
    
    def _create_default_response(self, card_id: int) -> bytes:
        """
        Create default 64-byte response data.
        
        Args:
            card_id: Card identifier
        
        Returns:
            Default 64-byte response
        """
        data = bytearray(64)
        
        # Header
        data[0] = 0xAA
        data[1] = 0x55
        
        # DI pattern based on card_id
        data[2] = (1 << (card_id - 1)) % 256
        
        # TTL status
        data[10] = card_id
        data[11] = 0x00
        
        # Matrix row
        for i in range(4):
            data[12 + i] = (i + card_id) % 256
        
        # Rest is zeros
        return bytes(data)
    
    def _load_simulators(self) -> None:
        """Load simulators using typical configuration."""
        # Typical configuration: localhost testing
        # UDPSender sends to 127.0.0.1:2880+card_id
        # UDPSender receives on 127.0.0.1:1010+card_id
        
        for card_id in range(1, 8):
            # Load response data
            response_data = self._load_response_data(card_id)
            
            # Calculate ports (matching typical settings.yaml)
            listen_port = 2880 + card_id  # Where UDPSender sends to
            response_port = 1010 + card_id  # Where UDPSender listens
            
            # Create simulator
            sim = LocalhostCardSimulator(
                card_id=card_id,
                listen_port=listen_port,
                response_ip="127.0.0.1",
                response_port=response_port,
                response_data=response_data
            )
            
            self.simulators[card_id] = sim
    
    def start_all(self) -> None:
        """Start all card simulators."""
        print("\n" + "=" * 70)
        print("Localhost Simulator Manager - Starting All Cards")
        print("=" * 70)
        
        for sim in self.simulators.values():
            sim.start()
        
        print(f"\nAll {len(self.simulators)} cards started and listening...")
        print("Ready to respond to UDPSender requests on 127.0.0.1")
        print("=" * 70 + "\n")
    
    def stop_all(self) -> None:
        """Stop all card simulators."""
        print("\n" + "=" * 70)
        print("Stopping All Cards")
        print("=" * 70)
        
        for sim in self.simulators.values():
            sim.stop()
        
        print("=" * 70 + "\n")
    
    def start_card(self, card_id: int) -> bool:
        """Start specific card simulator."""
        sim = self.simulators.get(card_id)
        if sim:
            sim.start()
            return True
        return False
    
    def stop_card(self, card_id: int) -> bool:
        """Stop specific card simulator."""
        sim = self.simulators.get(card_id)
        if sim:
            sim.stop()
            return True
        return False
    
    def get_simulator(self, card_id: int) -> Optional[LocalhostCardSimulator]:
        """Get specific card simulator."""
        return self.simulators.get(card_id)
    
    def get_all_statistics(self) -> Dict[int, Dict]:
        """Get statistics for all simulators."""
        stats = {}
        for card_id, sim in self.simulators.items():
            stats[card_id] = sim.get_statistics()
        return stats
    
    def print_statistics(self) -> None:
        """Print statistics for all simulators."""
        print("\n" + "=" * 70)
        print("Simulator Statistics")
        print("=" * 70)
        
        stats = self.get_all_statistics()
        for card_id in sorted(stats.keys()):
            card_stats = stats[card_id]
            status = "RUNNING" if card_stats['running'] else "STOPPED"
            last_recv = card_stats['last_receive_time']
            last_str = f"{last_recv:.2f}s ago" if last_recv is not None else "Never"
            
            print(f"Card {card_id}: {status:8} | "
                  f"Recv={card_stats['receive_count']:4} | "
                  f"Sent={card_stats['send_count']:4} | "
                  f"Last: {last_str}")
        
        print("=" * 70 + "\n")
    
    def __repr__(self) -> str:
        running_count = sum(1 for sim in self.simulators.values() if sim.running)
        return f"LocalhostSimulatorManager(cards={len(self.simulators)}, running={running_count})"


# Demo/Test code
if __name__ == "__main__":
    """
    Run localhost simulator for testing.
    
    Steps:
    1. Configure settings.yaml with all IPs as 127.0.0.1
    2. Run this script: python localhost_simulator.py
    3. In another terminal, run UDPSender test or UDPCardManager
    4. Simulator will respond to each request with fixed data
    """
    print("=" * 70)
    print("Localhost Card Simulator - UDP Request/Response Testing")
    print("=" * 70)
    print("\nThis simulator provides localhost testing without real hardware.")
    print("It listens for 32-byte UDP requests and responds with fixed 64-byte data.")
    print("\nConfiguration required in settings.yaml:")
    print("  - All send_ip: 127.0.0.1")
    print("  - All receive_ip: 127.0.0.1")
    print("  - send_port: 2881, 2882, 2883... (simulator listens here)")
    print("  - receive_port: 1011, 1021, 1031... (simulator sends here)")
    print("=" * 70 + "\n")
    
    # Create manager
    manager = LocalhostSimulatorManager()
    
    try:
        # Start all simulators
        manager.start_all()
        
        print("Simulator is running. Press Ctrl+C to stop.")
        print("Now run your UDPSender or UDPCardManager test in another terminal.\n")
        
        # Monitor activity
        last_stats = None
        while True:
            time.sleep(2)
            
            # Get current stats
            current_stats = manager.get_all_statistics()
            
            # Check for activity (new receives)
            if last_stats:
                for card_id, stats in current_stats.items():
                    prev_recv = last_stats[card_id]['receive_count']
                    curr_recv = stats['receive_count']
                    if curr_recv > prev_recv:
                        print(f"[Activity] Card {card_id}: "
                              f"Received {curr_recv - prev_recv} request(s), "
                              f"sent {stats['send_count']} response(s)")
            
            last_stats = current_stats
            
            # Print statistics every 10 seconds
            if int(time.time()) % 10 == 0:
                manager.print_statistics()
                time.sleep(1)  # Avoid multiple prints in same second
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    
    finally:
        # Stop all simulators
        manager.stop_all()
        
        # Final statistics
        manager.print_statistics()
        
        print("\nSimulator stopped.")
        print("\nUsage Summary:")
        print("  1. Start this simulator first")
        print("  2. Configure settings.yaml with 127.0.0.1 for all IPs")
        print("  3. Run your UDPSender/UDPCardManager test")
        print("  4. Simulator responds automatically to each request")
        print("=" * 70)
