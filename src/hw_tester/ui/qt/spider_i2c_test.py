"""Standalone UDP test window for the Spider card's I2C channel."""

import sys
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtNetwork import QAbstractSocket, QHostAddress, QUdpSocket
from PySide6.QtWidgets import (
    QApplication, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)


DISPLAY_ONE_PACKET = bytes.fromhex("AA 01 07 00 70 00 77 06 00 00 00") + bytes(39)


def describe_response(data):
    if len(data) < 2 or data[0] != 0x55:
        raise ValueError("Missing I2C response header 55")
    block_count = data[1]
    if not 1 <= block_count <= 4 or len(data) < 2 + 8 * block_count or len(data) > 34 or len(data) % 2:
        raise ValueError("Invalid I2C response length or block count")
    statuses = []
    for index in range(block_count):
        status = data[2 + 8 * index]
        description = {0: "OK", 1: "I2C error"}.get(status, f"unknown 0x{status:02X}")
        statuses.append(f"Block {index + 1}: {description}")
    return ", ".join(statuses)


class SpiderI2CTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spider I2C Test")
        self.resize(650, 520)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        form = QFormLayout()
        self.address = QLineEdit("192.168.195.15")
        self.destination_port = QSpinBox()
        self.destination_port.setRange(1, 65535)
        self.destination_port.setValue(2881)
        self.local_port = QSpinBox()
        self.local_port.setRange(0, 65535)
        self.local_port.setValue(1315)
        self.local_port.setSpecialValueText("Automatic")
        form.addRow("Spider IP:", self.address)
        form.addRow("Destination port:", self.destination_port)
        form.addRow("Local reply port:", self.local_port)
        layout.addLayout(form)

        note = QLabel(
            "20 Hz test: one I2C block to SAA1064 write address 0x70. "
            "The 50-byte packet uses zero padding; verify the address and panel wiring before starting."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addWidget(QLabel("Packet to send (hex):"))
        self.packet_view = QPlainTextEdit(DISPLAY_ONE_PACKET.hex(" ").upper())
        self.packet_view.setReadOnly(True)
        self.packet_view.setMaximumHeight(70)
        layout.addWidget(self.packet_view)

        buttons = QHBoxLayout()
        self.on_button = QPushButton("On")
        self.off_button = QPushButton("Off")
        self.off_button.setEnabled(False)
        buttons.addWidget(self.on_button)
        buttons.addWidget(self.off_button)
        layout.addLayout(buttons)
        self.state = QLabel("Stopped. Off stops sending; it does not clear the display.")
        self.state.setWordWrap(True)
        layout.addWidget(self.state)
        self.sent_count = QLabel("Datagrams sent: 0")
        layout.addWidget(self.sent_count)
        self.response_status = QLabel("No response received")
        self.response_status.setWordWrap(True)
        layout.addWidget(self.response_status)
        layout.addWidget(QLabel("Last received datagram (hex):"))
        self.response_view = QPlainTextEdit()
        self.response_view.setReadOnly(True)
        layout.addWidget(self.response_view)

        self.socket = QUdpSocket(self)
        self.socket.readyRead.connect(self._receive)
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.timeout.connect(self._send)
        self.on_button.clicked.connect(self.start_sending)
        self.off_button.clicked.connect(self.stop_sending)
        self.target = QHostAddress()
        self.sent = 0
        self.last_response = None

    def start_sending(self):
        target = QHostAddress()
        if not target.setAddress(self.address.text().strip()) or target.protocol() != QAbstractSocket.NetworkLayerProtocol.IPv4Protocol:
            self.state.setText("Error: enter a valid IPv4 address.")
            return
        if not self.socket.bind(QHostAddress(QHostAddress.SpecialAddress.AnyIPv4), self.local_port.value()):
            self.state.setText(f"Error binding local reply port: {self.socket.errorString()}")
            return
        self.target = target
        self.sent = 0
        self.last_response = None
        self.sent_count.setText("Datagrams sent: 0")
        self.response_status.setText("No response received (UDP delivery is unconfirmed)")
        self.response_view.clear()
        for field in (self.address, self.destination_port, self.local_port, self.on_button):
            field.setEnabled(False)
        self.off_button.setEnabled(True)
        self.state.setText("Transmitting at 20 Hz. UDP delivery is unconfirmed.")
        self.timer.start()
        self._send()

    def stop_sending(self):
        self.timer.stop()
        self.socket.close()
        for field in (self.address, self.destination_port, self.local_port, self.on_button):
            field.setEnabled(True)
        self.off_button.setEnabled(False)
        self.state.setText("Stopped. Off stops sending; it does not clear the display.")

    def _send(self):
        written = self.socket.writeDatagram(DISPLAY_ONE_PACKET, self.target, self.destination_port.value())
        if written != len(DISPLAY_ONE_PACKET):
            error = self.socket.errorString()
            self.stop_sending()
            self.state.setText(f"Send error; transmission stopped: {error}")
            return
        self.sent += 1
        self.sent_count.setText(f"Datagrams sent: {self.sent}")
        if self.last_response is not None and time.monotonic() - self.last_response > 2:
            self.response_status.setText("No recent response (UDP delivery is unconfirmed)")

    def _receive(self):
        while self.socket.hasPendingDatagrams():
            data, address, port = self.socket.readDatagram(self.socket.pendingDatagramSize())
            if address != self.target:
                self.response_status.setText(f"Ignored unexpected datagram from {address.toString()}:{port}")
                continue
            data = bytes(data)
            self.response_view.setPlainText(data.hex(" ").upper())
            try:
                description = describe_response(data)
            except ValueError as exc:
                self.response_status.setText(f"Invalid response from {address.toString()}:{port}: {exc}")
                continue
            self.last_response = time.monotonic()
            self.response_status.setText(f"Response from {address.toString()}:{port}: {description}")

    def closeEvent(self, event):
        self.stop_sending()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = SpiderI2CTestWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
