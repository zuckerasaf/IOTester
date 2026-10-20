import random
import time
import traceback

from hw_tester.hardware.controllino_io import connector_pin_to_bits
from hw_tester.utils.general import (
    clear_bits,
    clear_mux_bits,
    get_debug_setting,
    get_pin_pair_info_controlino,
    set_mux_bits,
)


def ibit_test(test_handle, fuse_test_prompt=None, ibit_test_prompt=None) -> tuple[int, int, bool]:
    """
    Run the I-BIT circuit and fuse tests.

    Test Procedure:
    1. Ask whether to run the circuit checks, when a prompt callback is supplied.
    2. Run measure_all_pins_system() for systems A and B if not skipped.
    3. Ask whether the fuse-test cable is connected.
    4. Run Fuses_test() on system A when the user chooses Continue.
    5. Skip the fuse test and treat it as passed when the user chooses Ignore.
    6. Return success when all selected checks pass.

    Args:
        test_handle: TestHandle instance providing hardware, settings, logging,
            measurement, relay, and mux-control dependencies.
        fuse_test_prompt: Optional callback that returns True to run the fuse
            test or False to skip it.
        ibit_test_prompt: Optional callback that returns True to run the circuit
            checks or False to skip them and continue to the fuse-test prompt.

    Returns:
        Tuple of (passed_count, total_count, success):
            - passed_count: Number of pins that passed the I-BIT checks.
            - total_count: Number of pins tested across systems A and B.
            - success: True when every circuit and fuse check passed, otherwise False.
    """
    self = test_handle
    is_simulation = self.settings.get('Board', {}).get('simulation', True)

    pin_number = 51
    run_ibit_test = ibit_test_prompt() if ibit_test_prompt else True
    passed_count = 0
    total_count = 0
    circuit_success = True
    if run_ibit_test:
        ibit_a = measure_all_pins_system(self, "a", 4.0, is_simulation, pin_number)
        ibit_b = measure_all_pins_system(self, "b", 4.0, is_simulation, pin_number)
        total_count = len(ibit_a[0]) + len(ibit_b[0])
        failed_count = len(ibit_a[2]) + len(ibit_b[2])
        passed_count = total_count - failed_count
        circuit_success = passed_count == total_count
        self.log(
            f"Ibit Circuit Test complete: {passed_count}/{total_count} pins PASSED",
            "SUCCESS" if circuit_success else "WARNING"
        )
        self.log(f"Ibit result: {'SUCCESS' if circuit_success else 'FAILURE'}", "SUCCESS" if circuit_success else "ERROR")
    else:
        self.log("Ibit circuit test ignored by user", "WARNING")


    run_fuse_test = fuse_test_prompt() if fuse_test_prompt else True
    if run_fuse_test:
        fuse_test = Fuses_test(self, "a", 4.0, is_simulation, pin_number)
    else:
        self.log("Fuse test ignored by user", "WARNING")
        fuse_test = ([], True, [])
    if not fuse_test[1]:
        self.log(f"Fuse test failed; faulty fuses: {fuse_test[2]}", "ERROR")

    success = circuit_success and fuse_test[1]
    return passed_count, total_count, success


def measure_all_pins_system(test_handle, system: str, voltage: float, isSimulate: bool, pinNumber) -> tuple[list[float], bool, list[dict]]:
    """
    Measure and validate all pins for one I-BIT connector system.

    Test Procedure:
    1. For each pin in the requested system, clear the mux matrix.
    2. Resolve the pin's analog measurement and pull-up pins from the board map.
    3. Convert the connector pin to mux bits and route it to the measurement path.
    4. Measure the pin before the pull-up and validate that it is approximately 0V.
    5. Activate the pull-up and general relay, then wait for stabilization.
    6. Measure the pin after the pull-up and validate the expected voltage.
    7. Deactivate the pull-up and continue with the next pin.
    8. Open the general relay, clear the final mux bits, and return the results.

    Args:
        test_handle: TestHandle instance providing hardware, settings, logging,
            measurement, relay, and mux-control dependencies.
        system: Connector system to test, either "a" or "b".
        voltage: Expected voltage after the pull-up is activated.
        isSimulate: If True, generate simulated voltage readings instead of
            reading from hardware.
        pinNumber: Exclusive upper bound for the pin loop. A value of 51 tests
            connector pins 1 through 50.

    Returns:
        Tuple of (voltage_measurements, all_tests_passed, failed_pins):
            - voltage_measurements: Initial voltage reading for each tested pin.
            - all_tests_passed: True when all voltage checks pass, otherwise False.
            - failed_pins: List of failed pin dictionaries containing pin,
              measured, and expected voltage values.
    """
    self = test_handle
    voltage_measurements = []
    failed_pins = []
    voltage_scale = 1
    tolerance = self.settings.get('Test', {}).get('voltage_degredation', 3.0)
    pins_to_stabilize = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.5)
    all_tests_passed = True

    if get_debug_setting(self.settings, "Ibit_Test"):
        self.log(f"start I_Bit test for all the pins ", "INFO")
        self.wait_debug(500, "active")
    for current_pin in range(1, pinNumber):
        if not self.running_ibit:
            self.log("I_Bit test stopped by user", "WARNING")
            break

        try:
            clear_max = clear_mux_bits(self.pin_map, self.hardware, self.log)
            if not clear_max:
                self.log(f"Failed to clear mux bits before testing pin {current_pin} on system {system}", "WARNING")
                break

            pair_num, voltage_pin_key, voltage_pin_b_key, pullup_pin_key, card_enable_a_key, card_enable_b_key, relay_enable_a_key, relay_enable_b_key = get_pin_pair_info_controlino(current_pin)
            voltage_pin_name = self.board_config.get(voltage_pin_key if system.upper() == "A" else voltage_pin_b_key, 'A0')
            pullup_pin_name = self.board_config.get(pullup_pin_key, 'D23')
            bits = connector_pin_to_bits(current_pin, system.lower())
            success = set_mux_bits(bits, current_pin, self.pin_map, self.hardware, self.settings, self.log)
            if not success:
                self.log(f"Failed to set mux bits for pin {current_pin}", "WARNING")
                voltage_measurements.append(0.0)
                failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': 0.0})
                all_tests_passed = False
                continue
            analog_ports = self.pin_map.get('A', {})
            analog_port = analog_ports.get(voltage_pin_name)
            mux_addr = f"{system.upper()}:{current_pin}"
            if analog_port is None:
                self.log(f"Analog pin {voltage_pin_name} not found in pin map for pin {current_pin}", "WARNING")
                voltage_measurements.append(0.0)
                failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': 0.0})
                all_tests_passed = False
                break

            if isSimulate:
                time.sleep(0.1)
                measured_voltage = random.uniform(-0.05, 0.05)
            else:
                measured_voltage = self.measurer.measure_voltage(analog_port) * voltage_scale
            if abs(measured_voltage) <= tolerance:
                self.log(f"Pin {current_pin} on system {system} ({bits}) Volt measurement {measured_voltage:.3f}V - PASS (expected ~0V)", "SUCCESS")
            else:
                self.log(f"Pin {current_pin} on system {system} ({bits}) Volt measurement {measured_voltage:.3f}V - FAIL (expected ~0V)", "WARNING")
                failed_pins.append({'pin': current_pin, 'measured': measured_voltage, 'expected': 0.0})
                all_tests_passed = False

            if get_debug_setting(self.settings, "Ibit_Test"):
                self.wait_debug(560, "active")
            voltage_measurements.append(measured_voltage)
            digital_ports = self.pin_map.get('D', {})
            pullup_physical_pin = digital_ports.get(pullup_pin_name)
            if pullup_physical_pin is None:
                self.log(f"Pullup pin {pullup_pin_name} not found in pin map for pin {current_pin}", "WARNING")
                all_tests_passed = False
                continue
            self.hardware.digital_write(pullup_physical_pin, True)
            time.sleep(pins_to_stabilize)

            relay_connect = self.relay_general_operate(True)
            if relay_connect == False:
                return (0, False, f"the relay logic didnt operate")

            if isSimulate:
                measured_voltage_pullup = voltage + random.uniform(-0.1, 0.1)
            else:
                measured_voltage_pullup = self.measurer.measure_voltage(analog_port) * voltage_scale
            voltage_diff = abs(measured_voltage_pullup - voltage)
            if voltage_diff <= tolerance:
                self.log(f"Pin {current_pin} on system {system} ({mux_addr}) Volt measurement {measured_voltage_pullup:.3f}V - PASS (expected {voltage}V)", "SUCCESS")
            else:
                self.log(f"Pin {current_pin} on system {system} ({mux_addr}) Volt measurement {measured_voltage_pullup:.3f}V - FAIL (expected {voltage}V, diff: {voltage_diff:.3f}V)", "WARNING")
                failed_pins.append({'pin': current_pin, 'measured': measured_voltage_pullup, 'expected': voltage})
                all_tests_passed = False

            if get_debug_setting(self.settings, "Ibit_Test"):
                self.wait_debug(600, "active")
            time.sleep(pins_to_stabilize)
            self.hardware.digital_write(pullup_physical_pin, False)
            time.sleep(pins_to_stabilize)
        except Exception as e:
            self.log(f"Error processing pin {current_pin} on system {system}: {str(e)}\n{traceback.format_exc()}", "ERROR")
            voltage_measurements.append(0.0)
            failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': 0.0})
            all_tests_passed = False

    relay_connect = self.relay_general_operate(False)
    if relay_connect == False:
        return (0, False, f"the relay logic didnt operate")
    result_msg = "SUCCESS" if all_tests_passed else "FAILED"
    clear_bits(bits, self.pin_map, self.hardware, self.log)
    self.log(f"System {system} measurement complete: {len(voltage_measurements)} pins measured - {result_msg} - {len(failed_pins)} failures", "SUCCESS" if all_tests_passed else "WARNING")
    return voltage_measurements, all_tests_passed, failed_pins


def Fuses_test(test_handle, system: str, voltage: float, isSimulate: bool, pinNumber) -> tuple[list[float], bool, list[dict]]:
    """
    Validate fuse connections for all pins in one connector system.

    Test Procedure:
    1. For each pin in the requested system, clear the mux matrix.
    2. Resolve the pin's analog measurement pin from the board map and use
         the dedicated ``pullup_fuse_test`` pin from the board configuration.
    3. Convert the connector pin to mux bits and route it to the measurement path.
    4. Measure the pin before the fuse-test pull-up and validate that it is
       approximately 0V.
    5. Activate the fuse-test pull-up and wait for stabilization.
    6. Measure the pin after the pull-up and validate the configured
       ``fuse_voltage_test`` value within tolerance.
    7. Deactivate the pull-up and continue with the next pin.

    Args:
        test_handle: TestHandle instance providing hardware, settings, logging,
            measurement, and mux-control dependencies.
        system: Must be "a". Fuse validation is performed only on system A.
        voltage: Fallback expected voltage if ``scale.fuse_voltage_test`` is
            not present in the settings.
        isSimulate: If True, generate simulated voltage readings instead of
            reading from hardware.
        pinNumber: Exclusive upper bound for the pin loop. A value of 51 tests
            connector pins 1 through 50.

    Returns:
        Tuple of (voltage_measurements, all_tests_passed, failed_pins):
            - voltage_measurements: Initial voltage reading for each tested pin.
            - all_tests_passed: True when all voltage checks pass, otherwise False.
            - failed_pins: List of failed pin dictionaries containing pin,
              measured, and expected voltage values.
    """
    self = test_handle
    if system.lower() != "a":
        raise ValueError("Fuse validation is supported only for system A")

    voltage_measurements = []
    failed_pins = []
    voltage_scale = 1
    tolerance = self.settings.get('Test', {}).get('voltage_degredation', 3.0)
    pins_to_stabilize = self.settings.get('Timeouts', {}).get('pins_to_stabilize', 0.5)
    fuse_voltage = self.settings.get('scale', {}).get('fuse_voltage_test', voltage)
    fuse_pullup_name = self.board_config.get('pullup_fuse_test', 'D22')
    all_tests_passed = True
    last_bits = None

    for current_pin in range(1, pinNumber):
        if not getattr(self, 'running_ibit', True):
            self.log("Fuses test stopped by user", "WARNING")
            break

        try:
            if not clear_mux_bits(self.pin_map, self.hardware, self.log):
                self.log(f"Failed to clear mux bits before fuse testing pin {current_pin} on system {system}", "WARNING")
                break

            pair_info = get_pin_pair_info_controlino(current_pin)
            voltage_pin_key = pair_info[1]
            voltage_pin_name = self.board_config.get(voltage_pin_key, 'A0')
            bits = connector_pin_to_bits(current_pin, system.lower())
            last_bits = bits
            if not set_mux_bits(bits, current_pin, self.pin_map, self.hardware, self.settings, self.log):
                self.log(f"Failed to set mux bits for fuse test pin {current_pin}", "WARNING")
                voltage_measurements.append(0.0)
                failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': 0.0})
                all_tests_passed = False
                continue

            analog_port = self.pin_map.get('A', {}).get(voltage_pin_name)
            if analog_port is None:
                self.log(f"Analog pin {voltage_pin_name} not found in pin map for fuse test pin {current_pin}", "WARNING")
                voltage_measurements.append(0.0)
                failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': 0.0})
                all_tests_passed = False
                break

            if isSimulate:
                time.sleep(0.1)
                measured_voltage = random.uniform(-0.05, 0.05)
            else:
                measured_voltage = self.measurer.measure_voltage(analog_port) * voltage_scale
            voltage_measurements.append(measured_voltage)

            if abs(measured_voltage) <= tolerance:
                self.log(f"Fuse pin {current_pin} on system {system} Volt measurement {measured_voltage:.3f}V - PASS (expected ~0V)", "SUCCESS")
            else:
                self.log(f"Fuse pin {current_pin} on system {system} Volt measurement {measured_voltage:.3f}V - FAIL (expected ~0V)", "WARNING")
                failed_pins.append({'pin': current_pin, 'measured': measured_voltage, 'expected': 0.0})
                all_tests_passed = False

            pullup_physical_pin = self.pin_map.get('D', {}).get(fuse_pullup_name)
            if pullup_physical_pin is None:
                self.log(f"Fuse pullup pin {fuse_pullup_name} not found in pin map", "ERROR")
                all_tests_passed = False
                break

            self.hardware.digital_write(pullup_physical_pin, True)
            time.sleep(pins_to_stabilize)
            if isSimulate:
                measured_voltage_pullup = fuse_voltage + random.uniform(-0.1, 0.1)
            else:
                measured_voltage_pullup = self.measurer.measure_voltage(analog_port) * voltage_scale

            voltage_diff = abs(measured_voltage_pullup - fuse_voltage)
            if voltage_diff <= tolerance:
                self.log(f"Fuse pin {current_pin} on system {system} Volt measurement {measured_voltage_pullup:.3f}V - PASS (expected {fuse_voltage}V)", "SUCCESS")
            else:
                self.log(f"Fuse pin {current_pin} on system {system} Volt measurement {measured_voltage_pullup:.3f}V - FAIL (expected {fuse_voltage}V, diff: {voltage_diff:.3f}V)", "WARNING")
                failed_pins.append({'pin': current_pin, 'measured': measured_voltage_pullup, 'expected': fuse_voltage})
                all_tests_passed = False

            self.hardware.digital_write(pullup_physical_pin, False)
            time.sleep(pins_to_stabilize)
        except Exception as e:
            self.log(f"Error processing fuse test pin {current_pin} on system {system}: {str(e)}\n{traceback.format_exc()}", "ERROR")
            voltage_measurements.append(0.0)
            failed_pins.append({'pin': current_pin, 'measured': 0.0, 'expected': 0.0})
            all_tests_passed = False

    if last_bits is not None:
        clear_bits(last_bits, self.pin_map, self.hardware, self.log)
    result_msg = "SUCCESS" if all_tests_passed else "FAILED"
    self.log(f"Fuse test system {system} complete: {len(voltage_measurements)} pins measured - {result_msg} - {len(failed_pins)} failures", "SUCCESS" if all_tests_passed else "WARNING")
    return voltage_measurements, all_tests_passed, failed_pins