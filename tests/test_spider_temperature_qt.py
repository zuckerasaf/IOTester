import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

import pytest
from PySide6.QtCore import QPoint, QUrl
from PySide6.QtGui import QPalette
from PySide6.QtNetwork import QNetworkRequest
from PySide6.QtWidgets import QApplication

from hw_tester.ui.qt.widgets.spider_temperature_qt import SpiderTemperatureQt, parse_temperature


@pytest.fixture(scope="module")
def app():
    with patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"}):
        yield QApplication.instance() or QApplication([])


@pytest.fixture
def server():
    class Handler(BaseHTTPRequestHandler):
        response = b"<response><temp>2747</temp></response>"
        status = 200
        paths = []

        def do_GET(self):
            self.paths.append(self.path)
            self.send_response(self.status)
            self.end_headers()
            self.wfile.write(self.response)

        def log_message(self, format, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd, Handler
    httpd.shutdown()
    httpd.server_close()
    thread.join()


def wait_for(app, condition, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return
        time.sleep(0.01)
    pytest.fail("Timed out waiting for temperature update")


def test_temperature_matches_card_web_conversion():
    assert parse_temperature(b"<response><temp>2747</temp></response>") == pytest.approx(34)
    assert parse_temperature(b"<response><temp>0</temp></response>") == pytest.approx(-50)
    assert parse_temperature(b"<response><temp>65535</temp></response>") == pytest.approx(-50)
    assert parse_temperature(b"<response><temp>3588</temp></response>") == 60.0
    for data in (b"<response/>", b"<response><temp>bad</temp></response>",
                 b"<response><temp>65536</temp></response>"):
        with pytest.raises(ValueError):
            parse_temperature(data)
    with pytest.raises(ElementTree.ParseError):
        parse_temperature(b"not xml")


def test_polling_refreshes_enabled_cards_and_reports_errors(app, server):
    httpd, handler = server
    settings = {"Card_temperature": {"green": 40, "yellow": 50, "red": 60},
                "UDP_Settings": {"Cards": [
        {"card_id": 1, "enabled": True, "send_ip": "127.0.0.1"},
        {"card_id": 2, "enabled": False, "send_ip": "127.0.0.2"},
    ]}}
    panel = SpiderTemperatureQt(lambda: settings)
    get = panel.network.get

    def local_get(request):
        url = QUrl(request.url())
        url.setPort(httpd.server_port)
        return get(QNetworkRequest(url))

    with patch.object(panel.network, "get", side_effect=local_get):
        panel.start()
        assert panel.timer.interval() == 1000
        wait_for(app, lambda: panel.labels[1].text() == "34.00 °C")
        assert list(panel.labels) == [1]
        assert handler.paths == ["/status.xml"]

        handler.response = b"<response><temp>3000</temp></response>"
        wait_for(app, lambda: panel.labels[1].text() == "42.00 °C")
        handler.response = b"<response/>"
        wait_for(app, lambda: panel.labels[1].text() == "Unavailable")
        assert "missing" in panel.labels[1].toolTip()
        handler.status = 503
        wait_for(app, lambda: "Service Unavailable" in panel.labels[1].toolTip())
        settings["UDP_Settings"]["localhost_mode"] = True
        settings["UDP_Settings"]["Cards_localhost"] = [
            {"card_id": 3, "enabled": True, "send_ip": "127.0.0.1"}
        ]
        panel.refresh()
        assert list(panel.labels) == [3]
        assert panel.labels[3].text() == "Unavailable"
        assert "localhost" in panel.labels[3].toolTip()
        panel.stop()
    panel.deleteLater()


def test_engineering_layout_places_log_options_below_log(app):
    from hw_tester.ui.qt import main_window_qt
    from hw_tester.ui.qt.controllers import main_controller

    settings = {
        "Card_temperature": {"green": 40, "yellow": 50, "red": 60},
        "UDP_Settings": {"localhost_mode": True, "Cards_localhost": [
            {"card_id": 1, "enabled": True, "send_ip": "127.0.0.1"}
        ]},
    }
    with patch.object(main_controller, "load_settings", return_value=settings), \
            patch.multiple(main_controller.MainController, _init_hardware=lambda self: None,
                           _init_test_components=lambda self: None,
                           _init_ui_state=lambda self: None,
                           populate_column_preset_combo=lambda self, combo: None,
                           populate_project_combo=lambda self, combo: None,
                           on_closing=lambda self: None):
        window = main_window_qt.MainWindowQt()
        try:
            layout = window.engineering_page.layout()
            assert layout.indexOf(window.log.parentWidget()) < layout.indexOf(window.btn_clear_log.parentWidget())
            assert window.spider_temperatures.title() == "Spider Card CPU Temp"
            options = window.btn_clear_log.parentWidget().layout()
            assert [options.itemAt(i).widget().text() for i in range(0, 10, 2)] == [
                "INF", "SUC", "WRN", "ERR", "DBG"
            ]
            assert options.itemAt(10).widget() is window.btn_clear_log
            assert window.btn_clear_log.text() == "Reset"
            window.cb_inf.setChecked(False)
            assert "INFO" not in window.log.current_filter
            window.btn_clear_log.click()
            assert [entry[2] for entry in window.log.log_entries] == ["Log cleared"]
            window.spider_temperatures._set_temperature(1, 41)
            assert window.log.log_entries[-1][1] == "ERROR"
            assert "card 1" in window.log.log_entries[-1][2]
            assert window.normal_panel.card_chips[1].property("state") == "warn"
            window.spider_temperatures._set_temperature(1, 55)
            assert window.normal_panel.card_chips[1].property("state") == "hot"
        finally:
            window.close()


def test_temperature_list_scrolls_after_seven_cards(app):
    previous_style = app.styleSheet()
    stylesheet = Path(__file__).resolve().parents[1] / "src" / "hw_tester" / "ui" / "Styles" / "dark.css"
    app.setStyleSheet(stylesheet.read_text(encoding="utf-8"))
    settings = {"UDP_Settings": {"localhost_mode": True, "Cards_localhost": [
        {"card_id": i, "enabled": True, "send_ip": "127.0.0.1"}
        for i in range(1, 8)
    ]}}
    panel = SpiderTemperatureQt(lambda: settings)
    try:
        panel.refresh()
        panel.show()
        app.processEvents()
        assert len(panel.labels) == 7
        assert panel.scroll_area.verticalScrollBar().maximum() == 0

        settings["UDP_Settings"]["Cards_localhost"].append(
            {"card_id": 8, "enabled": True, "send_ip": "127.0.0.1"}
        )
        panel.refresh()
        assert len(panel.labels) == 8
        wait_for(app, lambda: panel.scroll_area.verticalScrollBar().maximum() > 0)
    finally:
        panel.close()
        panel.deleteLater()
        app.setStyleSheet(previous_style)


def test_temperature_zones_and_transition_alerts(app):
    settings = {
        "Card_temperature": {"green": 40, "yellow": 50, "red": 60},
        "UDP_Settings": {"localhost_mode": True, "Cards_localhost": [
            {"card_id": 1, "enabled": True, "send_ip": "127.0.0.1"},
            {"card_id": 2, "enabled": True, "send_ip": "127.0.0.1"},
        ]},
    }
    panel = SpiderTemperatureQt(lambda: settings)
    messages = []
    panel.log_message.connect(lambda message, level: messages.append((message, level)))
    try:
        panel.refresh()
        for value, zone, color in [(40, "green", "#3fb950"), (40.01, "yellow", "#d29922"),
                                   (50, "yellow", "#d29922"), (50.01, "orange", "#f0883e"),
                                   (60, "orange", "#f0883e"), (60.01, "red", "#f85149")]:
            panel._set_temperature(1, value)
            assert panel.labels[1].toolTip() == f"Temperature zone: {zone}"
            assert color in panel.labels[1].styleSheet()
        assert len(messages) == 3
        assert all(level == "ERROR" for _, level in messages)
        panel._set_temperature(2, 45)
        assert len(messages) == 4
        assert "card 2" in messages[-1][0]
        panel._set_temperature(1, 40)
        panel._set_temperature(1, 45)
        assert len(messages) == 5

        panel._set_unavailable(1, "offline")
        assert panel.labels[1].styleSheet() == ""
        panel._set_temperature(1, 45)
        assert len(messages) == 5

        settings["Card_temperature"]["yellow"] = 30
        panel._set_temperature(1, 45)
        panel._set_temperature(2, 45)
        assert len(messages) == 6
        assert "green < yellow < red" in messages[-1][0]
        assert panel.labels[1].styleSheet() == ""
        assert "Invalid Card_temperature" in panel.labels[1].toolTip()
    finally:
        panel.close()
        panel.deleteLater()


def test_temperature_list_is_readable_with_dark_theme(app):
    settings = {
        "Card_temperature": {"green": 40, "yellow": 50, "red": 60},
        "UDP_Settings": {"localhost_mode": True, "Cards_localhost": [
            {"card_id": 1, "enabled": True, "send_ip": "127.0.0.1"}
        ]},
    }
    previous_style = app.styleSheet()
    stylesheet = Path(__file__).resolve().parents[1] / "src" / "hw_tester" / "ui" / "Styles" / "dark.css"
    app.setStyleSheet(stylesheet.read_text(encoding="utf-8"))
    panel = SpiderTemperatureQt(lambda: settings)
    try:
        panel.refresh()
        panel._set_temperature(1, 35)
        panel.show()
        app.processEvents()
        card_label = panel.grid.itemAtPosition(0, 0).widget()
        location = card_label.mapTo(
            panel, QPoint(card_label.width() - 1, card_label.height() - 1)
        )
        image = panel.grab().toImage()
        ratio = image.devicePixelRatio()
        background = image.pixelColor(round(location.x() * ratio), round(location.y() * ratio))
        assert background.name() == "#23272e"
        assert card_label.palette().color(QPalette.ColorRole.WindowText).name() == "#e6edf3"
        for value, color in [(35, "#3fb950"), (45, "#d29922"), (55, "#f0883e"), (65, "#f85149")]:
            panel._set_temperature(1, value)
            assert panel.labels[1].palette().color(QPalette.ColorRole.WindowText).name() == color
        panel._set_unavailable(1, "offline")
        assert panel.labels[1].palette().color(QPalette.ColorRole.WindowText).name() == "#e6edf3"
    finally:
        panel.close()
        panel.deleteLater()
        app.setStyleSheet(previous_style)
