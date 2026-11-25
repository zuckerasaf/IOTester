import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

from hw_tester.ui.qt.controllers.main_controller import MainController
from hw_tester.ui.qt.normal_panel_qt import NormalPanel
from hw_tester.ui.qt.widgets.spider_temperature_qt import SpiderTemperatureQt


class NormalConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_platform = patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
        cls.qt_platform.start()
        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.qt_platform.stop()

    def setUp(self):
        self.panel = NormalPanel()

    def tearDown(self):
        self.panel.close()
        self.panel.deleteLater()

    def test_temperature_chips_follow_existing_reader_and_configuration(self):
        settings = {
            "Card_temperature": {"green": 40, "yellow": 50, "red": 60},
            "UDP_Settings": {"localhost_mode": True, "Cards_localhost": [
                {"card_id": 1, "enabled": True, "send_ip": "127.0.0.1"},
                {"card_id": 2, "enabled": False, "send_ip": "127.0.0.1"},
                {"card_id": 3, "enabled": True, "send_ip": "127.0.0.1"},
            ]},
        }
        reader = SpiderTemperatureQt(lambda: settings)
        reader.cards_changed.connect(self.panel.set_temperature_cards)
        reader.card_status_changed.connect(self.panel.set_card_temperature_status)
        try:
            reader.refresh()
            self.assertEqual(list(self.panel.card_chips), [1, 3])
            self.assertEqual(self.panel.card_chips[1].text(), "1")
            self.assertEqual(self.panel.card_chips[1].property("state"), "warn")
            self.assertIn("localhost", self.panel.card_chips[1].toolTip())

            for value, expected in ((36, "ok"), (45, "warn"), (55, "hot"), (65, "fail")):
                reader._set_temperature(1, value)
                self.assertEqual(self.panel.card_chips[1].property("state"), expected)
                self.assertIn(f"{value:.2f}", self.panel.card_chips[1].toolTip())
            reader._set_unavailable(1, "Timed out")
            self.assertEqual(self.panel.card_chips[1].property("state"), "warn")
            self.assertIn("Timed out", self.panel.card_chips[1].toolTip())
            self.assertEqual(self.panel.card_chips[3].property("state"), "warn")

            reader._set_configuration((False, ((1, "192.168.195.11"), (5, "192.168.195.15"))))
            self.assertEqual(list(self.panel.card_chips), [1, 5])
            self.assertEqual(self.panel.card_chips[1].text(), "1")
            self.assertEqual(self.panel.card_chips[5].text(), "5")
            self.assertIn("Card 5 (192.168.195.15)", self.panel.card_chips[5].toolTip())
            reader._set_configuration((False, ()))
            self.assertFalse(self.panel.card_chips)
        finally:
            reader.stop()
            reader.deleteLater()

    def test_port_indicator_tracks_actual_connection_and_last_check(self):
        controller = MainController.__new__(MainController)
        controller.main_window = SimpleNamespace(normal_panel=self.panel, log=MagicMock())
        controller.settings = {"Board": {"Port": "COM3", "Type": "ControllinoMega", "simulation": True}}
        controller._port_check = None
        hardware = SimpleNamespace(connected=True)
        with patch("hw_tester.ui.qt.controllers.main_controller.initialize_hardware", return_value=hardware), \
                patch("hw_tester.ui.qt.controllers.main_controller.load_settings", return_value=controller.settings):
            controller._init_hardware()
        self.assertEqual(self.panel.chip_port.text(), "Port: COM3")
        self.assertEqual(self.panel.chip_port.property("state"), "ok")
        self.assertIn("not continuously monitored", self.panel.chip_port.toolTip())

        with patch("hw_tester.ui.qt.controllers.main_controller.initialize_hardware",
                   return_value=SimpleNamespace(connected=False)), \
                patch("hw_tester.ui.qt.controllers.main_controller.load_settings", return_value=controller.settings):
            controller._init_hardware()
        self.assertEqual(self.panel.chip_port.property("state"), "fail")

        with patch("hw_tester.ui.qt.controllers.main_controller.ControllinoIO", side_effect=RuntimeError("not found")):
            self.assertFalse(controller._test_com_connection())
        self.assertEqual(self.panel.chip_port.property("state"), "fail")
        self.assertIn("not found", self.panel.chip_port.toolTip())

        with patch("hw_tester.ui.qt.controllers.main_controller.ControllinoIO") as board:
            self.assertTrue(controller._test_com_connection())
            board.return_value.close.assert_called_once()
        self.assertEqual(self.panel.chip_port.property("state"), "ok")
        controller.settings["Board"]["Port"] = "COM4"
        controller._sync_port_status()
        self.assertEqual(self.panel.chip_port.text(), "Port: COM4")
        self.assertEqual(self.panel.chip_port.property("state"), "warn")
        self.assertIn("restart", self.panel.chip_port.toolTip())

    def test_seven_chips_render_with_status_colors(self):
        previous_style = self.app.styleSheet()
        stylesheet = Path(__file__).resolve().parents[1] / "src" / "hw_tester" / "ui" / "Styles" / "dark.css"
        self.app.setStyleSheet(stylesheet.read_text(encoding="utf-8"))
        self.addCleanup(self.app.setStyleSheet, previous_style)
        self.panel.set_temperature_cards(tuple((i, f"192.168.195.{i + 10}") for i in range(1, 8)), False)
        self.panel.set_card_temperature_status(1, "green", "CPU temperature: 36.00 °C")
        self.panel.show()
        self.app.processEvents()
        self.assertEqual([chip.text() for chip in self.panel.card_chips.values()],
                         [str(i) for i in range(1, 8)])
        self.assertEqual(self.panel.card_chips[1].grab().toImage().pixelColor(8, 8).name(), "#e4f5ea")
        self.assertEqual(self.panel.card_chips_layout.rowCount(), 1)
        for chip in self.panel.card_chips.values():
            self.assertFalse(chip.visibleRegion().isEmpty())
        self.panel.resize(self.panel.width(), 730)
        self.app.processEvents()
        self.assertLessEqual(self.panel.height(), 730)
        self.assertGreater(self.panel.controls_scroll.verticalScrollBar().maximum(), 0)
        self.panel.controls_scroll.ensureWidgetVisible(self.panel.tile_pass)
        self.app.processEvents()
        self.assertFalse(self.panel.tile_pass.visibleRegion().isEmpty())


if __name__ == "__main__":
    unittest.main()
