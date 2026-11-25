import os
import socket
import time
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from hw_tester.ui.qt.spider_i2c_test import (
    DISPLAY_ONE_PACKET, SpiderI2CTestWindow, describe_response,
)


class SpiderI2CTestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_platform = patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
        cls.qt_platform.start()
        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.qt_platform.stop()

    def setUp(self):
        self.window = SpiderI2CTestWindow()

    def tearDown(self):
        self.window.close()

    def wait_for(self, condition, timeout=2):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.app.processEvents()
            if condition():
                return
            time.sleep(0.005)
        self.fail("Timed out waiting for UDP test window")

    def test_packet_matches_one_block_example(self):
        self.assertEqual(len(DISPLAY_ONE_PACKET), 50)
        self.assertEqual(DISPLAY_ONE_PACKET[:11], bytes.fromhex("AA 01 07 00 70 00 77 06 00 00 00"))
        self.assertEqual(DISPLAY_ONE_PACKET[11:], bytes(39))

    def test_response_decoding_and_invalid_data(self):
        self.assertEqual(describe_response(bytes.fromhex("55 01 00 00 00 00 00 00 00 00")), "Block 1: OK")
        self.assertEqual(describe_response(bytes.fromhex("55 01 01 00 00 00 00 00 00 00")), "Block 1: I2C error")
        for data in (b"", b"\x55\x01", b"\x55\x00", b"\x54\x01" + bytes(8),
                     b"\x55\x05" + bytes(40), b"\x55\x01" + bytes(9)):
            with self.assertRaises(ValueError):
                describe_response(data)

    def test_start_response_and_stop_over_localhost(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            receiver.bind(("127.0.0.1", 0))
            receiver.setblocking(False)
            self.window.address.setText("127.0.0.1")
            self.window.destination_port.setValue(receiver.getsockname()[1])
            self.window.local_port.setValue(0)
            self.assertFalse(self.window.timer.isActive())
            self.window.on_button.click()
            self.assertTrue(self.window.timer.isActive())
            self.assertEqual(self.window.timer.interval(), 50)
            self.assertIn("unconfirmed", self.window.state.text())

            received = []

            def receive_packet():
                try:
                    received.append(receiver.recvfrom(1024))
                except BlockingIOError:
                    return False
                return len(received) >= 2

            self.wait_for(receive_packet)
            self.assertTrue(all(packet == DISPLAY_ONE_PACKET for packet, _ in received))
            local_port = self.window.socket.localPort()
            receiver.sendto(bytes.fromhex("55 01 00 00 00 00 00 00 00 00"), ("127.0.0.1", local_port))
            self.wait_for(lambda: "Block 1: OK" in self.window.response_status.text())
            receiver.sendto(b"not an I2C response", ("127.0.0.1", local_port))
            self.wait_for(lambda: "Invalid response" in self.window.response_status.text())

            self.window.off_button.click()
            self.assertFalse(self.window.timer.isActive())
            count = self.window.sent
            end = time.monotonic() + 0.2
            while time.monotonic() < end:
                self.app.processEvents()
                time.sleep(0.005)
            self.assertEqual(self.window.sent, count)
            self.assertIn("does not clear", self.window.state.text())

    def test_invalid_address_does_not_start(self):
        self.window.address.setText("not an ip address")
        self.window.on_button.click()
        self.assertFalse(self.window.timer.isActive())
        self.assertIn("valid IPv4", self.window.state.text())


if __name__ == "__main__":
    unittest.main()
