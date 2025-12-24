"""
UDP Card Manager - Manages multiple UDP cards in parallel.
Provides simple interface to control all 7 cards simultaneously.
"""
from typing import List, Dict, Optional

# Import handling for both direct execution and package import
try:
    from .udp_sender import UDPSender
except ImportError:
    from udp_sender import UDPSender


class UDPCardManager:
    """
    Manager for controlling multiple UDP cards in parallel.
    
    Example usage:
        manager = UDPCardManager()
        manager.start_all()
        
        # Set DO1=1 on card 1, DO16=1 on card 3
        manager.set_digital_output(card_id=1, do_number=1, state=True)
        manager.set_digital_output(card_id=3, do_number=16, state=True)
        
        # Read DI5 from card 2
        di_state = manager.get_digital_input(card_id=2, di_number=5)
        
        manager.stop_all()
    """
    
    def __init__(self, settings_path: str = None, create_all: bool = False):
        """
        Initialize card manager.
        
        Args:
            settings_path: Path to settings.yaml file (default: auto-detect)
            create_all: If True, create all 7 cards. If False, only enabled cards.
        """
        self.settings_path = settings_path
        self.cards: Dict[int, UDPSender] = {}
        
        # Create card instances
        if create_all:
            card_list = UDPSender.create_all_cards(settings_path=settings_path)
        else:
            card_list = UDPSender.create_enabled_cards(settings_path=settings_path)
        
        # Store cards in dictionary by card_id
        for card in card_list:
            self.cards[card.card_id] = card
    
    def get_card(self, card_id: int) -> Optional[UDPSender]:
        """
        Get card instance by ID.
        
        Args:
            card_id: Card identifier (1-7)
        
        Returns:
            UDPSender instance or None if not found
        """
        return self.cards.get(card_id)
    
    def get_all_cards(self) -> List[UDPSender]:
        """Get list of all card instances."""
        return list(self.cards.values())
    
    def get_enabled_cards(self) -> List[UDPSender]:
        """Get list of enabled card instances."""
        return [card for card in self.cards.values() if card.enabled]
    
    def start_all(self) -> None:
        """Start all card communication threads."""
        for card in self.cards.values():
            card.start()
    
    def stop_all(self) -> None:
        """Stop all card communication threads."""
        for card in self.cards.values():
            card.stop()
    
    def start_card(self, card_id: int) -> bool:
        """
        Start specific card.
        
        Args:
            card_id: Card identifier
        
        Returns:
            True if successful, False if card not found
        """
        card = self.get_card(card_id)
        if card:
            card.start()
            return True
        return False
    
    def stop_card(self, card_id: int) -> bool:
        """
        Stop specific card.
        
        Args:
            card_id: Card identifier
        
        Returns:
            True if successful, False if card not found
        """
        card = self.get_card(card_id)
        if card:
            card.stop()
            return True
        return False
    
    # ===== Digital Output Methods =====
    
    def set_digital_output(self, card_id: int, do_number: int, state: bool) -> bool:
        """
        Set digital output on specific card.
        
        Args:
            card_id: Card identifier (1-7)
            do_number: Digital output number (1-32)
            state: True for ON, False for OFF
        
        Returns:
            True if successful, False if card not found
        """
        card = self.get_card(card_id)
        if card:
            card.set_digital_output(do_number, state)
            return True
        return False
    
    def set_digital_outputs(self, card_id: int, do_list: List[int]) -> bool:
        """
        Set multiple digital outputs on specific card.
        
        Args:
            card_id: Card identifier (1-7)
            do_list: List of DO numbers to set ON (all others OFF)
        
        Returns:
            True if successful, False if card not found
        """
        card = self.get_card(card_id)
        if card:
            card.set_digital_outputs(do_list)
            return True
        return False
    
    def get_digital_output(self, card_id: int, do_number: int) -> Optional[bool]:
        """
        Get digital output state from specific card.
        
        Args:
            card_id: Card identifier (1-7)
            do_number: Digital output number (1-32)
        
        Returns:
            State (True/False) or None if card not found
        """
        card = self.get_card(card_id)
        if card:
            return card.get_digital_output(do_number)
        return None
    
    # ===== TTL Output Methods =====
    
    def set_ttl_output(self, card_id: int, ttl_number: int, state: bool) -> bool:
        """
        Set TTL output on specific card.
        
        Args:
            card_id: Card identifier (1-7)
            ttl_number: TTL output number (1-16)
            state: True for ON, False for OFF
        
        Returns:
            True if successful, False if card not found
        """
        card = self.get_card(card_id)
        if card:
            card.set_ttl_output(ttl_number, state)
            return True
        return False
    
    def set_ttl_outputs(self, card_id: int, ttl_list: List[int]) -> bool:
        """
        Set multiple TTL outputs on specific card.
        
        Args:
            card_id: Card identifier (1-7)
            ttl_list: List of TTL numbers to set ON (all others OFF)
        
        Returns:
            True if successful, False if card not found
        """
        card = self.get_card(card_id)
        if card:
            card.set_ttl_outputs(ttl_list)
            return True
        return False
    
    def get_ttl_output(self, card_id: int, ttl_number: int) -> Optional[bool]:
        """
        Get TTL output state from specific card.
        
        Args:
            card_id: Card identifier (1-7)
            ttl_number: TTL output number (1-16)
        
        Returns:
            State (True/False) or None if card not found
        """
        card = self.get_card(card_id)
        if card:
            return card.get_ttl_output(ttl_number)
        return None
    
    # ===== Analog Output Methods =====
    
    def set_analog_output(self, card_id: int, ao_number: int, voltage: float) -> bool:
        """
        Set analog output voltage on specific card.
        
        Args:
            card_id: Card identifier (1-7)
            ao_number: Analog output number (0-7)
            voltage: Voltage value (-13.5 to +13.5)
        
        Returns:
            True if successful, False if card not found
        """
        card = self.get_card(card_id)
        if card:
            card.set_analog_output(ao_number, voltage)
            return True
        return False
    
    def get_analog_output(self, card_id: int, ao_number: int) -> Optional[float]:
        """
        Get analog output voltage from specific card.
        
        Args:
            card_id: Card identifier (1-7)
            ao_number: Analog output number (0-7)
        
        Returns:
            Voltage or None if card not found
        """
        card = self.get_card(card_id)
        if card:
            return card.get_analog_output(ao_number)
        return None
    
    def set_multiple_analog_outputs(self, card_id: int, analog_values: Dict[int, float]) -> bool:
        """
        Set multiple analog outputs on specific card.
        
        Args:
            card_id: Card identifier (1-7)
            analog_values: Dictionary mapping AO number -> voltage
        
        Returns:
            True if successful, False if card not found
        """
        card = self.get_card(card_id)
        if card:
            card.set_multiple_analog_outputs(analog_values)
            return True
        return False
    
    # ===== Matrix Methods =====
    
    def set_matrix_dimensions(self, card_id: int, rows: int, columns: int) -> bool:
        """
        Set matrix dimensions on specific card.
        
        Args:
            card_id: Card identifier (1-7)
            rows: Number of rows (0-8)
            columns: Number of columns (0-8)
        
        Returns:
            True if successful, False if card not found
        """
        card = self.get_card(card_id)
        if card:
            card.set_matrix_dimensions(rows, columns)
            return True
        return False
    
    def get_matrix_dimensions(self, card_id: int) -> Optional[tuple]:
        """
        Get matrix dimensions from specific card.
        
        Args:
            card_id: Card identifier (1-7)
        
        Returns:
            Tuple (rows, columns) or None if card not found
        """
        card = self.get_card(card_id)
        if card:
            return card.get_matrix_dimensions()
        return None
    
    # ===== Digital Input Methods =====
    
    def get_digital_input(self, card_id: int, di_number: int) -> Optional[bool]:
        """
        Get digital input state from specific card.
        
        Args:
            card_id: Card identifier (1-7)
            di_number: Digital input number (1-64)
        
        Returns:
            State (True/False) or None if card not found
        """
        card = self.get_card(card_id)
        if card:
            return card.get_digital_input(di_number)
        return None
    
    def get_digital_inputs_active(self, card_id: int) -> Optional[List[int]]:
        """
        Get list of active digital inputs from specific card.
        
        Args:
            card_id: Card identifier (1-7)
        
        Returns:
            List of active DI numbers or None if card not found
        """
        card = self.get_card(card_id)
        if card:
            return card.get_digital_inputs_active()
        return None
    
    # ===== Analog Input Methods =====
    
    def get_analog_input(self, card_id: int, ai_number: int) -> Optional[float]:
        """
        Get analog input voltage from specific card.
        
        Args:
            card_id: Card identifier (1-7)
            ai_number: Analog input number (1-16)
        
        Returns:
            Voltage or None if card not found
        """
        card = self.get_card(card_id)
        if card:
            return card.get_analog_input(ai_number)
        return None
    
    # ===== Utility Methods =====
    
    def clear_all_outputs(self, card_id: int = None) -> None:
        """
        Clear all outputs on specific card or all cards.
        
        Args:
            card_id: Card identifier (1-7), or None for all cards
        """
        if card_id is None:
            # Clear all cards
            for card in self.cards.values():
                card.clear_all_outputs()
        else:
            # Clear specific card
            card = self.get_card(card_id)
            if card:
                card.clear_all_outputs()
    
    def is_communication_active(self, card_id: int) -> Optional[bool]:
        """
        Check if communication is active for specific card.
        
        Args:
            card_id: Card identifier (1-7)
        
        Returns:
            True if active, False if inactive, None if card not found
        """
        card = self.get_card(card_id)
        if card:
            return card.is_communication_active()
        return None
    
    def get_statistics(self, card_id: int = None) -> Dict:
        """
        Get statistics for specific card or all cards.
        
        Args:
            card_id: Card identifier (1-7), or None for all cards
        
        Returns:
            Dictionary with statistics
        """
        if card_id is None:
            # Get stats for all cards
            stats = {}
            for cid, card in self.cards.items():
                stats[cid] = card.get_statistics()
            return stats
        else:
            # Get stats for specific card
            card = self.get_card(card_id)
            if card:
                return card.get_statistics()
            return {}
    
    def get_all_communication_status(self) -> Dict[int, bool]:
        """
        Get communication status for all cards.
        
        Returns:
            Dictionary mapping card_id -> communication_active (True/False)
        """
        status = {}
        for card_id, card in self.cards.items():
            status[card_id] = card.is_communication_active()
        return status
    
    def __repr__(self) -> str:
        enabled_count = len(self.get_enabled_cards())
        total_count = len(self.cards)
        return f"UDPCardManager(cards={total_count}, enabled={enabled_count})"


# Demo/Test code
if __name__ == "__main__":
    """Test card manager with multiple cards."""
    import time
    
    print("=" * 60)
    print("UDP Card Manager Test")
    print("=" * 60)
    
    # Create manager (only enabled cards)
    print("\n[TEST] Creating card manager (enabled cards only)...")
    manager = UDPCardManager(create_all=False)
    
    print(f"[TEST] {manager}")
    print(f"[TEST] Available cards: {list(manager.cards.keys())}")
    
    if not manager.cards:
        print("[TEST] No cards available. Enable cards in settings.yaml")
        print("=" * 60)
        exit(0)
    
    # Start all cards
    print("\n[TEST] Starting all cards...")
    manager.start_all()
    
    try:
        # Configure different outputs on different cards
        print("\n[TEST] Configuring outputs on multiple cards...")
        
        # Card 1: DO1=1, AO0=5.0V
        if 1 in manager.cards:
            manager.set_digital_output(card_id=1, do_number=1, state=True)
            manager.set_analog_output(card_id=1, ao_number=0, voltage=10.0)
            print("  [TEST] send Card 1: DO1=0, AO0=10.0V")
            ao = manager.get_analog_output(card_id=1, ao_number=0)
            do = manager.get_digital_output(card_id=1, do_number=1)
            print(f"  [TEST] received Card 1: AO0={ao:.2f}V" f", DO1={int(do)}")
        
        # Card 3: DO16=1, TTL5=1
        if 3 in manager.cards:
            manager.set_digital_output(card_id=3, do_number=16, state=False)
            manager.set_ttl_output(card_id=3, ttl_number=5, state=True)
            print("[TEST] Card 3: DO16=1, TTL5=1")
            ttl = manager.get_ttl_output(card_id=3, ttl_number=5)
            do = manager.get_digital_output(card_id=3, do_number=16)
            print(f"  [TEST] received Card 3: TTL5={int(ttl)}" f", DO16={int(do)}")
        
        # Card 2: Matrix 4x6
        if 2 in manager.cards:
            manager.set_digital_output(card_id=2, do_number=8, state=True)
            manager.set_matrix_dimensions(card_id=2, rows=4, columns=6)
            print("[TEST] Card 2: D8=1, Matrix=4x6")
            dims = manager.get_matrix_dimensions(card_id=2)
            do = manager.get_digital_output(card_id=2, do_number=8)
            print(f"  [TEST] received Card 2: Matrix={dims[0]}x{dims[1]}" f", DO8={int(do)}")
        
        # Monitor for 5 seconds
        print("\n[TEST] Monitoring communication...")
        for i in range(10):
            time.sleep(0.5)
            
            print(f"\n[TEST] === Iteration {i+1} ===")
            
            # Get communication status for all cards
            comm_status = manager.get_all_communication_status()
            for card_id, active in comm_status.items():
                status_str = "✓ ACTIVE" if active else "✗ INACTIVE"
                print(f"[TEST] Card {card_id}: {status_str}")
                
                # If active, show some data
                if active:
                    di_active = manager.get_digital_inputs_active(card_id)
                    if di_active:
                        print(f"[TEST]   Active DI: {di_active[:5]}{'...' if len(di_active) > 5 else ''}")
                    
                    ai1 = manager.get_analog_input(card_id, 1)
                    if ai1 is not None:
                        print(f"[TEST]   AI1: {ai1:.3f}V")
        
        # Get final statistics
        print("\n[TEST] Final Statistics:")
        all_stats = manager.get_statistics()
        for card_id, stats in all_stats.items():
            print(f"[TEST] Card {card_id}: Sent={stats['send_count']}, Received={stats['receive_count']}")
    
    except KeyboardInterrupt:
        print("\n[TEST] Interrupted by user")
    
    finally:
        # Stop all cards
        print("\n[TEST] Stopping all cards...")
        manager.stop_all()
        
        print("\n" + "=" * 60)
        print("Test complete")
        print("=" * 60)
