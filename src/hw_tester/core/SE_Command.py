#==========================================================#
import sys
import os
import pathlib
import platform
import json
import time
import threading
from datetime import datetime
try: 
	scriptDir = os.path.dirname(os.path.abspath(__file__))
	onesimpath = pathlib.Path(os.environ["GESSTPATH"]) / "CurrentProject/API/Python/"
	sys.path.insert(0, str(onesimpath))
	architecture = platform.architecture()[0]
	if architecture == '64bit':
		onesimBinPath = pathlib.Path(os.environ["GESSTPATH"]) / "Bin/Debug_x64/"
		os.chdir(onesimBinPath)
except KeyError:
	print('ERROR: Please set the environment variable GESSTPATH')
	sys.exit(1)
import OneSimLinkWrapper
from OneSimLinkWrapper import *
se = OneSimLinkWrapper.simWrapper.get_instance() # OneSimLink singleton (use se obj)


def load_test_cases(self, json_file_path):
		try:
			with open(json_file_path, 'r') as file:
				data = json.load(file)
			type = data.get('Type', '')
			steps = data.get('Steps', [])
			test_cases = []
			for test_id, test_data in steps.items():
				input_element = test_data.get('input_element', '')
				input_value = test_data.get('input_value', '')
				input_value_start = test_data.get('input_value_start', 0)
				input_value_end = test_data.get('input_value_end', 0)
				input_value_step = test_data.get('input_value_step', 1)
				test_time = test_data.get('test_time', 0.0)
				output_value_start = test_data.get('output_value_start', 0)
				output_value_end = test_data.get('output_value_end', 0)
				output_value_step = test_data.get('output_value_step', 1)
				
				test_case = [input_element, input_value, input_value_start, input_value_end, input_value_step,
				  test_time, output_value_start, output_value_end, output_value_step]
				test_cases.append(test_case)
			
			return test_cases, type
		except Exception as e:
			self.log_status(f"Error loading test cases: {e}")
			return [], ""
def execute_single_test(self, test_case, type):
		"""
		This method executes a single test case.
		It handles all the OneSimLink operations and error checking.
		Simplified version: only sets input values, no output validation.
		"""

		global number_of_test, number_of_success, number_of_fail 
		# Unpack test case parameters
		input_element, input_value, input_value_start, input_value_end, input_value_step, test_time, output_value_start, output_value_end, output_value_step = test_case
		reason = ""
		status = "PASS"

		for i in range(input_value_step):
			try:
				# Step 1: Verify input element exists in OneSimLink
				se.get_element_value(input_element, '', sys.maxsize)
			except ElementNotDefinedException as e:
				# Input element doesn't exist - return failure
				status = "FAIL"
				reason = f"Input element is not defined: {str(e)}"
				return f"FAIL: {reason}"
			
			if type == "discrete":
				try:
					# Step 2: Set the input value in OneSimLink
					se.set_element_value_request(input_element, input_value, '')
				except InvalidArgumentException as e:
					# Invalid input value - return failure
					status = "FAIL"
					reason = f"Invalid input value: {str(e)}"
					return f"FAIL: {reason}"
				
				# Step 3: Wait for the specified test time
				time.sleep(test_time)
				
			elif type == "range":
				try:
					if input_value_start < input_value_end:
						input_value = ((input_value_end - input_value_start) / (input_value_step)) * (i+1) + input_value_start
					else:
						input_value = input_value_start - ((input_value_start - input_value_end) / (input_value_step)) * (i+1) 
				except (ValueError, ZeroDivisionError) as e:
					# Invalid input value - return failure
					status = "FAIL"
					reason = f"Invalid input value (end - start) / step: {str(e)}"
					return f"FAIL: {reason}"

				try:
					# Step 2: Set the input value in OneSimLink
					se.set_element_value_request(input_element, str(input_value), '')
				except InvalidArgumentException as e:
					# Invalid input value - return failure
					status = "FAIL"
					reason = f"Invalid input value: {str(e)}"
					return f"FAIL: {reason}"
				
				# Step 3: Wait for the specified test time
				time.sleep(test_time)
			else:
				status = "FAIL"
				reason = f"Invalid type: {str(type)}"
				return f"FAIL: {reason}"

		# Test completed successfully
		number_of_success += 1
		return "PASS"
# Global counters for test statistics
number_of_test = 0
number_of_success = 0
number_of_fail = 0


class TestExecutor:
	"""Class to handle test execution."""
	
	def __init__(self):
		pass
	
	def load_test_cases(self, json_file_path):
		"""Load test cases from JSON file."""
		return load_test_cases(self, json_file_path)
	
	def execute_single_test(self, test_case, type):
		"""Execute a single test case."""
		return execute_single_test(self, test_case, type)
	
	def log_status(self, message):
		"""Print status message."""
		print(message)
	
	def run_all_tests(self, json_file_path):
		"""Run all tests from a JSON file."""
		global number_of_test, number_of_success, number_of_fail
		
		print(f"Loading test cases from: {json_file_path}")
		test_cases, test_type = self.load_test_cases(json_file_path)
		
		if not test_cases:
			print("ERROR: No test cases loaded!")
			return
		
		print(f"Loaded {len(test_cases)} test cases of type '{test_type}'")
		number_of_test = len(test_cases)
		
		# Execute each test case
		for idx, test_case in enumerate(test_cases, 1):
			print(f"\n--- Executing test {idx}/{len(test_cases)} ---")
			result = self.execute_single_test(test_case, test_type)
			print(f"Result: {result}")
		
		# Print summary
		print("\n" + "="*50)
		print(f"Test Execution Summary:")
		print(f"  Total Tests: {number_of_test}")
		print(f"  Passed: {number_of_success}")
		print(f"  Failed: {number_of_fail}")
		print("="*50)


def main():
	"""Main function to test the SE_Command module."""
	#json_path = r"C:\ArduinoProject\IO_Tester\tests\DB\MTC_AFT\powerup_MTC_AFT.json"
	json_path = r"C:\ArduinoProject\IO_Tester\tests\DB\MTC_AFT\powerdown_MTC_AFT.json"

	
	print("="*60)
	print("SE_Command Test Execution")
	print("="*60)
	print(f"Test file: {json_path}")
	print("="*60 + "\n")
	
	try:
		executor = TestExecutor()
		executor.run_all_tests(json_path)
	except Exception as e:
		print(f"ERROR: Error during test execution: {e}")
		import traceback
		traceback.print_exc()
		return 1
	
	return 0


if __name__ == "__main__":
	sys.exit(main())		