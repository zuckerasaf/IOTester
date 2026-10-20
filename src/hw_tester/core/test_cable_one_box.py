import time
import random
import re
from typing import TYPE_CHECKING

from hw_tester.hardware.controllino_io import connector_pin_to_bits
from hw_tester.utils.general import (
    get_pin_pair_info_controlino,
    set_mux_bits,
    clear_mux_bits,
)

if TYPE_CHECKING:
    from hw_tester.hardware.pin import Pin


def Cable_test(test_handle, pin: "Pin", pin_table_rows: list) -> tuple[float, bool, str]:
    """
    Run logic test on a pin.
    
    Test Procedure:
    1. read the input pin and input connector from pin_out and Logic_input
    2. Resolve the pin pair, analog measurement pin, and pull-up pin.
    3. Route the connector pin through the mux matrix.
    4. Activate the configured pull-up behavior and wait for stabilization.
    5. Close the general relay 
    6. read the allowed output pins and output connector from Logic_Espected (connector name and pin ID  - e.g., k(1) = connector "K" pin 1)
    7. translate the output connector names pins to list (output pin list - OPL) of pin number 1-50 according to connector name and offset data logic from setting.yaml
    8. translate the allowed output pins to list (allowed output pin list - APL) of pin number 1-50 according to connector name, pin ID and offset data logic from setting.yaml
    9. for every pin in the Pin output list (OPL), measure the pull-up voltage.
    10. compare the measured voltage for every pin in the allowed output pin list (APL) against the expected criteria.
    11. Record the test result for each pin, including measured voltage and pass/fail status.
    12. Deactivate the Relay cards and the pull-up behavior.
    13. Return result (status)
    
    Args:
        pin: Pin object containing test parameters (Id, Logic_Pin_Input, Logic_Expected, etc.)
        pin_table_rows: All rows from pin table (for looking up second pin data)

    info: input connector -> output connector logic mapping
        C (25 Pin)->D (25 Pin)
        C (25 Pin)->G (15 Pin)
        C (25 Pin)->K (9 Pin)
        C (25 Pin)->K (9 Pin) + L (9 Pin)
        E (15 Pin)->F (15 Pin)
        E (15 Pin)->F (15 Pin) + G (15 Pin)
        E (15 Pin)->F (15 Pin) + L (9 Pin)
        E (15 Pin)->J (9 Pin)
        E (15 Pin)->J (9 Pin) + K (9 Pin)
        E (15 Pin)->J (9 Pin) + K (9 Pin) + L (9 Pin)
        H (9 Pin)->I (9 Pin)
        H (9 Pin)->I (9 Pin) + J (9 Pin)
        H (9 Pin)->I (9 Pin) + J (9 Pin) + K (9 Pin)
        H (9 Pin)->I (9 Pin) + J (9 Pin) + K (9 Pin) + L (9 Pin)     

    Returns:
        Tuple of (success, list of faulty pins):
            - success: True if status matches expected, False otherwise
            - list of faulty pins: List of pins out of the allowed output pin list (APL) that failed the test
    """

    self = test_handle
    settings = self.settings
    connectors = settings.get("Connectors", {})
    is_simulation = settings.get("Board", {}).get("simulation", True)
    scale_settings = settings.get("scale", {})
    high_threshold = scale_settings.get("fuse_voltage_test", 5.0)
    low_threshold = scale_settings.get("zero_voltage_threshold", 0.5)
    voltage_tolerance =scale_settings.get("voltage_tolerance", 1.5)
    measured_values = []
    failures = []
    pullup_pin_name = None

    try:
        source_connector = str(pin.Logic_Pin_Input).strip().upper()
        source_config = connectors.get(source_connector)
        if not source_config or str(source_config.get("Type", "")).strip().lower() != "input":
            message = f"Wrong connector configuration: {source_connector} must be defined as an input connector"
            self.log(message, "ERROR")
            return (0.0, False, message)

        pin_match = re.search(r"(\d+)\s*$", str(pin.Id))
        if not pin_match:
            return (0.0, False, f"Pin ID has no pin number: {pin.Id}")
        source_local_pin = int(pin_match.group(1))
        source_pin_number = int(source_config["offset"]) + source_local_pin
        if not 1 <= source_pin_number <= 50:
            return (0.0, False, f"Input pin is outside mux range: {source_pin_number}")

        expected_value = pin.Logic_Expected
        if isinstance(expected_value, (list, tuple)):
            expected_value = ",".join(str(value) for value in expected_value)
        expected_matches = re.findall(r"([A-L])\s*\(([^)]*)\)", str(expected_value), re.IGNORECASE)
        if not expected_matches:
            return (0.0, False, f"No allowed connector pins found in Logic_Expected: {expected_value}")

        allowed_pins = set()
        target_connectors = set()
        for connector_name, local_pin_values in expected_matches:
            connector_name = connector_name.upper()
            connector_config = connectors.get(connector_name)
            if not connector_config or str(connector_config.get("Type", "")).strip().lower() != "output":
                message = f"Wrong connector configuration: {connector_name} must be defined as an output connector"
                self.log(message, "ERROR")
                return (0.0, False, message)
            connector_size = int(connector_config["size"])
            for local_pin_text in local_pin_values.split(","):
                try:
                    local_pin = int(local_pin_text.strip())
                except ValueError:
                    return (0.0, False, f"Invalid pin list for connector {connector_name}: {local_pin_values}")
                if not 1 <= local_pin <= connector_size:
                    return (0.0, False, f"Pin {local_pin} is outside connector {connector_name}")
                allowed_pins.add(int(connector_config["offset"]) + local_pin)
            target_connectors.add(connector_name)

        valid_output_sets = {
            "C": {frozenset(outputs) for outputs in (("D",), ("G",), ("K",), ("K", "L"))},
            "E": {frozenset(outputs) for outputs in (("F",), ("F", "G"), ("F", "L"), ("J",), ("J", "K"), ("J", "K", "L"))},
            "H": {frozenset(outputs) for outputs in (("I",), ("I", "J"), ("I", "J", "K"), ("I", "J", "K", "L"))},
        }
        if frozenset(target_connectors) not in valid_output_sets.get(source_connector, set()):
            output_list = ", ".join(sorted(target_connectors))
            message = f"Wrong connector configuration: {source_connector} cannot be tested with output connector(s) {output_list}"
            self.log(message, "ERROR")
            return (0.0, False, message)

        _, voltage_pin_key, _, pullup_pin_key, _, _, _, _ = get_pin_pair_info_controlino(source_pin_number)
        # Get actual pin names from board config
        voltage_pin_name = self.board_config.get(voltage_pin_key, 'A0')
        if voltage_pin_name is None:
            return (0.0, False, f"Analog pin {voltage_pin_name} not found in pin map")

        pullup_pin_name = self.board_config.get(pullup_pin_key, 'D23')
        if pullup_pin_name is None:
            return (0.0, False, f"Pull-up pin {pullup_pin_name} not found in pin map")
        
        # Convert connector pin to bit representation and set mux matrix
        bits = connector_pin_to_bits(source_pin_number, "a")

        success = set_mux_bits(bits, source_pin_number, self.pin_map, self.hardware, self.settings, self.log)
        if not success:
            self.log(f"in pullup test - Failed to set mux bits for pin {source_pin_number}", "ERROR")
            return (0.0, False, "Error: Failed to set mux matrix")

        self.hardware.digital_write(pullup_pin_name, True)
        if not self.relay_general_operate(True):
            return (0.0, False, "Failed to activate general relay")
        time.sleep(settings.get("Timeouts", {}).get("pins_to_stabilize", 0.1))

        for connector_name in sorted(target_connectors):
            connector_config = connectors[connector_name]
            connector_offset = int(connector_config["offset"])
            connector_size = int(connector_config["size"])
            for local_pin in range(1, connector_size + 1):
                output_pin_number = connector_offset + local_pin
                output_bits = connector_pin_to_bits(output_pin_number, "b")
                if not set_mux_bits(output_bits, output_pin_number, self.pin_map, self.hardware, settings, self.log):
                    return (0.0, False, f"Failed to route output pin {output_pin_number}")

                voltage = self.measurer.measure_voltage(voltage_pin_name)
                if is_simulation:
                    simulated_voltage = high_threshold + 0.5 if output_pin_number in allowed_pins else 0.0
                    voltage = simulated_voltage + random.uniform(-0.1, 0.1)
                measured_values.append(voltage)

                if output_pin_number in allowed_pins:
                    passed = abs(voltage  - high_threshold) <= voltage_tolerance
                else:
                    passed = abs(voltage  - low_threshold) <= voltage_tolerance
                result_text = "PASS" if passed else "FAIL"
                self.log(
                    f"Cable output {connector_name}({local_pin}): {voltage:.3f}V ({result_text})",
                    "SUCCESS" if passed else "WARNING",
                )
                if not passed:
                    failures.append(f"{connector_name}({local_pin})={voltage:.2f}V")

        average_voltage = sum(measured_values) / len(measured_values) if measured_values else 0.0
        if failures:
            message = "Cable test failed: " + ", ".join(failures)
            self.log(message, "WARNING")
            return (average_voltage, False, message)

        message = f"Cable test passed ({len(allowed_pins)} allowed pin(s) verified)"
        self.log(message, "SUCCESS")
        return (average_voltage, True, message)
    except Exception as error:
        message = f"Cable test error: {error}"
        self.log(message, "ERROR")
        average_voltage = sum(measured_values) / len(measured_values) if measured_values else 0.0
        return (average_voltage, False, message)
    finally:
        if pullup_pin_name is not None:
            try:
                self.hardware.digital_write(pullup_pin_name, False)
            except Exception as error:
                self.log(f"Failed to deactivate pull-up: {error}", "ERROR")
        try:
            self.relay_general_operate(False)
        except Exception as error:
            self.log(f"Failed to deactivate general relay: {error}", "ERROR")
        try:
            clear_mux_bits(self.pin_map, self.hardware, self.log)
        except Exception as error:
            self.log(f"Failed to clear mux bits: {error}", "ERROR")



    return (0.0, False, "Logic test FAILED")
