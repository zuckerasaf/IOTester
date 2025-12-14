"""
Pin and Connector classes representing physical pins and connectors on the device under test.
"""
from typing import Optional, List
from enum import Enum


class PinType(Enum):
    """Pin type enumeration for connector pins"""
    DIGITAL_OUT = "Digital_Output"
    DIGITAL_INPUT = "Digital_Input"
    ANALOG_OUTPUT = "Analog_Output"
    ANALOG_INPUT = "Analog_Input"
    PWM = "pwm"
    GROUND = "Ground"
    POWER = "Power"


class Pin:
    """
    Represents a physical pin on the connector (device being tested).
    
    The mux matrix routes connections between these connector pins and the Controllino
    for voltage measurement and circuit closing operations.
    
    Attributes:
        Id (str): Unique identifier for the connector pin (e.g., "J1-1") - Excel column B (Destination 1)
        Connect (str): Where the pin is connected to (e.g., "1P2 27" = card 1, connector 2, pin 27) - Excel column C (Destination 2)
        Type (str): Type of pin (e.g., "DI_25", "5V I/O_1") - Excel column F (Associated Potential/Substance)
        Power_Expected (float): Expected power test result (default: 0.0)
        Power_Measured (float): Measured power test result (default: 0.0)
        Power_Result (bool): Power test pass/fail result (default: False)
        PullUp_Expected (float): Expected pin voltage when pullup is on (default: 0.0)
        PullUp_Measured (float): Measured pin voltage when pullup is on (default: 0.0)
        PullUp_Result (bool): PullUp test pass/fail result (default: False)
        Power_Input (str): Pin number that needs to be connected for power test (default: "")
        Logic_Pin_Input (str): Pin number that needs to be connected as part of the test (default: "")
        Logic_DI_Result (bool): Logic test pass/fail result (default: False)
    """
    
    def __init__(
        self,
        Id: str,
        Connect: str = "",
        Type: str = "",
        Power_Expected: float = 0.0,
        Power_Measured: float = 0.0,
        Power_Result: bool = False,
        PullUp_Expected: float = 0.0,
        PullUp_Measured: float = 0.0,
        PullUp_Result: bool = False,
        Power_Input: str = "",
        Logic_Pin_Input: str = "",
        Logic_DI_Result: bool = False
    ):
        self.Id = Id
        self.Connect = Connect
        self.Type = Type
        # Power test attributes
        self.Power_Expected = Power_Expected
        self.Power_Measured = Power_Measured
        self.Power_Result = Power_Result
        # PullUp test attributes
        self.PullUp_Expected = PullUp_Expected
        self.PullUp_Measured = PullUp_Measured
        self.PullUp_Result = PullUp_Result
        # Logic test attributes
        self.Power_Input = Power_Input
        self.Logic_Pin_Input = Logic_Pin_Input
        self.Logic_DI_Result = Logic_DI_Result
    
    def __repr__(self) -> str:
        return (
            f"Pin(Id='{self.Id}', Connect='{self.Connect}', Type='{self.Type}', "
            f"Power_Expected={self.Power_Expected}, Power_Measured={self.Power_Measured}, Power_Result={self.Power_Result}, "
            f"PullUp_Expected={self.PullUp_Expected}, PullUp_Measured={self.PullUp_Measured}, PullUp_Result={self.PullUp_Result}, "
            f"Power_Input={self.Power_Input}, Logic_Pin_Input={self.Logic_Pin_Input}, Logic_DI_Result={self.Logic_DI_Result})"
        )
    
    def __str__(self) -> str:
        return f"{self.Id} (Type: {self.Type}, Connect: {self.Connect})"
    
    def to_dict(self) -> dict:
        """Convert pin to dictionary representation"""
        return {
            "Id": self.Id,
            "Connect": self.Connect,
            "Type": self.Type,
            "Power_Expected": self.Power_Expected,
            "Power_Measured": self.Power_Measured,
            "Power_Result": self.Power_Result,
            "PullUp_Expected": self.PullUp_Expected,
            "PullUp_Measured": self.PullUp_Measured,
            "PullUp_Result": self.PullUp_Result,
            "Power_Input": self.Power_Input,
            "Logic_Pin_Input": self.Logic_Pin_Input,
            "Logic_DI_Result": self.Logic_DI_Result
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Pin':
        """Create Pin instance from dictionary"""
        return cls(
            Id=data["Id"],
            Connect=data.get("Connect", ""),
            Type=data.get("Type", ""),
            Power_Expected=data.get("Power_Expected", 0.0),
            Power_Measured=data.get("Power_Measured", 0.0),
            Power_Result=data.get("Power_Result", False),
            PullUp_Expected=data.get("PullUp_Expected", 0.0),
            PullUp_Measured=data.get("PullUp_Measured", 0.0),
            PullUp_Result=data.get("PullUp_Result", False),
            Power_Input=data.get("Power_Input", ""),
            Logic_Pin_Input=data.get("Logic_Pin_Input", ""),
            Logic_DI_Result=data.get("Logic_DI_Result", False)
        )


class Connector:
    """
    Represents a physical connector containing multiple pins.
    
    A connector groups related pins together (e.g., a multi-pin connector on the device under test).
    
    Attributes:
        id (str): Unique identifier for the connector (e.g., "J1", "CONN_A", "USB1")
        pins (List[Pin]): List of pins belonging to this connector
    """
    
    def __init__(self, id: str, pins: Optional[List[Pin]] = None):
        self.id = id
        self.pins = pins if pins is not None else []
    
    def add_pin(self, pin: Pin) -> None:
        """Add a pin to the connector"""
        self.pins.append(pin)
    
    def get_pin(self, pin_id: str) -> Optional[Pin]:
        """Get a pin by its ID"""
        for pin in self.pins:
            if pin.id == pin_id:
                return pin
        return None
    
    def remove_pin(self, pin_id: str) -> bool:
        """Remove a pin by its ID. Returns True if removed, False if not found"""
        for i, pin in enumerate(self.pins):
            if pin.id == pin_id:
                self.pins.pop(i)
                return True
        return False
    
    def __repr__(self) -> str:
        return f"Connector(id='{self.id}', pins={len(self.pins)})"
    
    def __str__(self) -> str:
        return f"{self.id} ({len(self.pins)} pins)"
    
    def to_dict(self) -> dict:
        """Convert connector to dictionary representation"""
        return {
            "id": self.id,
            "pins": [pin.to_dict() for pin in self.pins]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Connector':
        """Create Connector instance from dictionary"""
        pins = [Pin.from_dict(pin_data) for pin_data in data.get("pins", [])]
        return cls(id=data["id"], pins=pins)
