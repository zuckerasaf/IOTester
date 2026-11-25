import math
from xml.etree import ElementTree

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkProxy, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import QGridLayout, QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget


def parse_temperature(data: bytes) -> float:
    root = ElementTree.fromstring(data)
    text = root.findtext("temp")
    if text is None:
        raise ValueError("Temperature is missing from the card response")
    raw = int(text)
    if not 0 <= raw <= 65535:
        raise ValueError("Temperature reading is outside the ADC range")
    voltage = raw * 10 / 32767 if raw <= 32767 else (raw - 65535) * 10 / 32767
    # The card's web page rounds the ADC voltage before converting to Celsius.
    voltage = float(f"{voltage:.2f}")
    return float(f"{(voltage - 0.5) / 0.01:.2f}")


class SpiderTemperatureQt(QGroupBox):
    log_message = Signal(str, str)
    cards_changed = Signal(object, bool)
    card_status_changed = Signal(object, str, str)

    def __init__(self, settings_provider, parent=None):
        super().__init__("Spider Card CPU Temp", parent)
        self.settings_provider = settings_provider
        layout = QVBoxLayout(self)
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("spiderTemperatureScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("spiderTemperatureContent")
        self.grid = QGridLayout(content)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(content)
        margins = self.grid.contentsMargins()
        row_height = QLabel("Card 7").sizeHint().height()
        height = (7 * row_height + 6 * self.grid.spacing() + margins.top() +
                  margins.bottom() + 2 * self.scroll_area.frameWidth())
        self.scroll_area.setFixedHeight(height)
        layout.addWidget(self.scroll_area)
        self.network = QNetworkAccessManager(self)
        self.network.setProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        self.labels = {}
        self.requests = {}
        self.configuration = None
        self.zones = {}
        self.threshold_error = None

    def start(self):
        self.refresh()
        self.timer.start()

    def stop(self):
        self.timer.stop()
        requests = list(self.requests.values())
        self.requests.clear()
        for reply in requests:
            reply.abort()

    def refresh(self):
        udp = self.settings_provider().get("UDP_Settings", {})
        localhost = udp.get("localhost_mode", False)
        cards = udp.get("Cards_localhost" if localhost else "Cards", [])
        configuration = (localhost, tuple(
            (card.get("card_id"), card.get("send_ip"))
            for card in cards if card.get("enabled", False)
        ))
        if configuration != self.configuration:
            self._set_configuration(configuration)
        if localhost:
            return
        for card_id, host in configuration[1]:
            if card_id in self.requests:
                continue
            if not host:
                self._set_unavailable(card_id, "Card IP address is missing")
                continue
            url = QUrl()
            url.setScheme("http")
            url.setHost(str(host))
            url.setPath("/status.xml")
            if not url.isValid() or not url.host():
                self._set_unavailable(card_id, "Invalid card IP address")
                continue
            request = QNetworkRequest(url)
            request.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute,
                                 QNetworkRequest.CacheLoadControl.AlwaysNetwork)
            request.setRawHeader(b"Cache-Control", b"no-cache")
            reply = self.network.get(request)
            self.requests[card_id] = reply
            timeout = QTimer(reply)
            timeout.setSingleShot(True)
            timeout.timeout.connect(reply.abort)
            timeout.start(900)
            reply.finished.connect(lambda cid=card_id, r=reply: self._finished(cid, r))

    def _set_configuration(self, configuration):
        previous_cards = dict(self.configuration[1]) if self.configuration else {}
        current_cards = dict(configuration[1]) if not configuration[0] else {}
        self.zones = {
            card_id: zone for card_id, zone in self.zones.items()
            if card_id in current_cards and current_cards[card_id] == previous_cards.get(card_id)
        }
        old_requests = list(self.requests.values())
        self.requests.clear()
        for reply in old_requests:
            reply.abort()
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.labels.clear()
        self.configuration = configuration
        localhost, cards = configuration
        self.cards_changed.emit(cards, localhost)
        if not cards:
            self.grid.addWidget(QLabel("No enabled cards"), 0, 0)
            return
        for row, (card_id, _) in enumerate(cards):
            self.grid.addWidget(QLabel(f"Card {card_id}"), row, 0)
            label = QLabel("Unavailable" if localhost else "Reading...")
            if localhost:
                label.setToolTip("Temperature is unavailable in localhost mode")
            self.grid.addWidget(label, row, 1)
            self.labels[card_id] = label
            self.card_status_changed.emit(
                card_id, "unavailable", label.toolTip() if localhost else "Waiting for temperature"
            )

    def _set_unavailable(self, card_id, reason):
        label = self.labels[card_id]
        label.setText("Unavailable")
        label.setStyleSheet("")
        label.setToolTip(reason)
        self.card_status_changed.emit(card_id, "unavailable", reason)

    def _set_temperature(self, card_id, temperature):
        label = self.labels[card_id]
        label.setText(f"{temperature:.2f} °C")
        try:
            thresholds = self.settings_provider().get("Card_temperature", {})
            values = [thresholds[name] for name in ("green", "yellow", "red")]
            if any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not math.isfinite(value) for value in values):
                raise ValueError("limits must be finite numbers")
            green, yellow, red = values
            if not green < yellow < red:
                raise ValueError("limits must satisfy green < yellow < red")
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            message = f"Invalid Card_temperature settings: {exc}"
            label.setStyleSheet("")
            label.setToolTip(message)
            self.card_status_changed.emit(card_id, "unavailable", f"{label.text()}: {message}")
            if message != self.threshold_error:
                self.log_message.emit(message, "ERROR")
                self.threshold_error = message
            return
        self.threshold_error = None
        if temperature <= green:
            zone, color = "green", "#3fb950"
        elif temperature <= yellow:
            zone, color = "yellow", "#d29922"
        elif temperature <= red:
            zone, color = "orange", "#f0883e"
        else:
            zone, color = "red", "#f85149"
        label.setStyleSheet(f"color: {color};")
        label.setToolTip(f"Temperature zone: {zone}")
        self.card_status_changed.emit(card_id, zone, f"CPU temperature: {temperature:.2f} °C ({zone})")
        if zone != "green" and self.zones.get(card_id) != zone:
            self.log_message.emit(
                f"Spider card {card_id} CPU temperature {temperature:.2f} °C is in the {zone} zone.",
                "ERROR",
            )
        self.zones[card_id] = zone

    def _finished(self, card_id, reply):
        if self.requests.get(card_id) is not reply:
            reply.deleteLater()
            return
        del self.requests[card_id]
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self._set_unavailable(card_id, reply.errorString())
        else:
            try:
                temperature = parse_temperature(bytes(reply.readAll()))
            except (ElementTree.ParseError, ValueError) as exc:
                self._set_unavailable(card_id, f"Invalid temperature response: {exc}")
            else:
                self._set_temperature(card_id, temperature)
        reply.deleteLater()
