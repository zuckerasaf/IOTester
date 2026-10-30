"""Operator panel for the Normal layout: choose project/connector, start/stop, see results, open reports."""
import tempfile
from enum import Enum
from pathlib import Path

from PySide6.QtCore import Qt, QPointF, QRectF, QSize, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
    QProgressBar, QPushButton, QSizePolicy, QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from hw_tester.ui.qt import normal_theme as theme

PANEL_TITLE = "GDU Tester"
PANEL_SUBTITLE = "Gunner Display Unit"
PANEL_WIDTH = 560
REPORTS_WIDTH = 480


class Phase(Enum):
    READY = "ready"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    STOPPED = "stopped"


def _icon(draw, size: int = 32, color: str = "#FFFFFF") -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(color), size / 11)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    draw(p, float(size))
    p.end()
    return QIcon(pm)


def _play(p, s):
    p.setBrush(p.pen().color())
    p.drawPolygon(QPolygonF([QPointF(s * .25, s * .15), QPointF(s * .25, s * .85), QPointF(s * .85, s * .5)]))


def _stop(p, s):
    p.setBrush(p.pen().color())
    p.drawRoundedRect(QRectF(s * .2, s * .2, s * .6, s * .6), s * .06, s * .06)


def _check(p, s):
    p.drawPolyline(QPolygonF([QPointF(s * .15, s * .55), QPointF(s * .4, s * .8), QPointF(s * .85, s * .25)]))


def _cross(p, s):
    p.drawLine(QPointF(s * .2, s * .2), QPointF(s * .8, s * .8))
    p.drawLine(QPointF(s * .8, s * .2), QPointF(s * .2, s * .8))


def _grid(p, s):
    p.drawRoundedRect(QRectF(s * .12, s * .15, s * .76, s * .7), s * .06, s * .06)
    p.drawLine(QPointF(s * .12, s * .5), QPointF(s * .88, s * .5))
    p.drawLine(QPointF(s * .38, s * .15), QPointF(s * .38, s * .85))
    p.drawLine(QPointF(s * .62, s * .15), QPointF(s * .62, s * .85))


def _document(p, s):
    p.drawRoundedRect(QRectF(s * .2, s * .1, s * .6, s * .8), s * .06, s * .06)
    for y in (.35, .5, .65):
        p.drawLine(QPointF(s * .32, s * y), QPointF(s * .68, s * y))


def _help(p, s):
    p.drawEllipse(QRectF(s * .1, s * .1, s * .8, s * .8))
    p.drawText(QRectF(0, 0, s, s), Qt.AlignCenter, "?")


def _chevron(p, s):
    p.drawPolyline(QPolygonF([QPointF(s * .2, s * .35), QPointF(s * .5, s * .65), QPointF(s * .8, s * .35)]))


def _chevron_url() -> str:
    path = Path(tempfile.gettempdir()) / "hw_tester_chevron.png"
    _icon(_chevron, 32, theme.TEXT).pixmap(32, 32).save(str(path))
    return path.as_posix()


def _check_url() -> str:
    """White tick PNG used inside the filled checkbox indicators."""
    path = Path(tempfile.gettempdir()) / "hw_tester_check.png"
    pm = QPixmap(32, 32)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor("#FFFFFF"), 4)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.drawPolyline(QPolygonF([QPointF(7, 17), QPointF(13, 23), QPointF(25, 9)]))
    p.end()
    pm.save(str(path))
    return path.as_posix()


class StepCard(QFrame):
    def __init__(self, heading: str):
        super().__init__()
        self.setObjectName("card")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(14, 12, 14, 12)
        self.body.setSpacing(6)
        label = QLabel(heading.upper())
        label.setObjectName("cardHeading")
        self.body.addWidget(label)


class CounterTile(QFrame):
    def __init__(self, caption: str, icon: QIcon):
        super().__init__()
        self.setObjectName("tile")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(0)
        row = QHBoxLayout()
        row.addStretch()
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(20, 20))
        row.addWidget(icon_label)
        cap = QLabel(caption)
        cap.setObjectName("tileCaption")
        row.addWidget(cap)
        row.addStretch()
        lay.addLayout(row)
        self.number = QLabel("0")
        self.number.setObjectName("tileNumber")
        self.number.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.number)

    def set_state(self, state: str):
        self.setProperty("state", state)
        _repolish(self)


class ReportsList(QFrame):
    """Right-hand list of saved reports: name, result and date/time."""

    open_requested = Signal(str)  # full path of the double-clicked report

    RESULT_COLORS = {"Pass": theme.PASS_TEXT, "Fail": theme.FAIL_TEXT, "Not Complete": "#6B4300"}

    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        self.setFixedWidth(REPORTS_WIDTH - 20)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)
        head = QHBoxLayout()
        label = QLabel("REPORTS")
        label.setObjectName("cardHeading")
        head.addWidget(label)
        head.addStretch()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.setObjectName("linkButton")
        head.addWidget(self.btn_refresh)
        lay.addLayout(head)
        self.folder_label = QLabel("")
        self.folder_label.setObjectName("bannerSub")
        lay.addWidget(self.folder_label)

        self.select_all = QCheckBox("Select / deselect all")
        self.select_all.setObjectName("selectAll")
        self.select_all.setTristate(False)
        self.select_all.clicked.connect(self._on_select_all)
        lay.addWidget(self.select_all)

        self.table = QTableWidget(0, 3)
        self.table.setObjectName("reportsTable")
        self.table.setHorizontalHeaderLabels(["Name", "Result", "Date / time"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.cellDoubleClicked.connect(self._on_double_click)
        self.table.itemChanged.connect(self._sync_select_all)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.table.setMinimumHeight(150)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        lay.addWidget(self.table, 1)
        hint = QLabel("Tick reports for Word / Fail report · double-click to open")
        hint.setObjectName("bannerSub")
        lay.addWidget(hint)

    def set_reports(self, folder: str, reports: list):
        """reports: list of (path, display name, result, datetime) newest first."""
        keep = set(self.checked_paths())
        self.folder_label.setText(folder)
        self.table.setRowCount(len(reports))
        for row, (path, name, result, when) in enumerate(reports):
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, path)
            name_item.setToolTip(path)
            name_item.setFlags(name_item.flags() | Qt.ItemIsUserCheckable)
            name_item.setCheckState(Qt.Checked if path in keep else Qt.Unchecked)
            result_item = QTableWidgetItem(result)
            result_item.setTextAlignment(Qt.AlignCenter)
            color = self.RESULT_COLORS.get(result)
            if color:
                result_item.setForeground(QColor(color))
                font = result_item.font()
                font.setBold(True)
                result_item.setFont(font)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, result_item)
            self.table.setItem(row, 2, QTableWidgetItem(when.strftime("%Y-%m-%d  %H:%M")))
        self._sync_select_all()

    def _on_select_all(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(state)
        self.table.blockSignals(False)

    def _sync_select_all(self, *_):
        """Tick the master box only when every row is ticked."""
        total = self.table.rowCount()
        self.select_all.blockSignals(True)
        self.select_all.setChecked(total > 0 and len(self.checked_paths()) == total)
        self.select_all.blockSignals(False)

    def checked_paths(self) -> list:
        """Full paths of the reports the user ticked, in list order."""
        paths = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                paths.append(item.data(Qt.UserRole))
        return paths

    def _on_double_click(self, row: int, _col: int):
        item = self.table.item(row, 0)
        if item:
            self.open_requested.emit(item.data(Qt.UserRole))


def _repolish(widget: QWidget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    for child in widget.findChildren(QWidget):
        child.style().unpolish(child)
        child.style().polish(child)


class NormalPanel(QWidget):
    """Single-screen operator panel. Only set_phase() and refresh_status() change its look."""

    mode_changed = Signal(str)  # "normal" or "engineer"
    start_clicked = Signal()
    stop_clicked = Signal()
    comm_result = Signal(bool)  # emitted from worker threads, handled on the GUI thread
    ibit_result = Signal(bool)
    comm_countdown = Signal(float)  # start the Comm check caption counter (seconds)
    ibit_countdown = Signal(float)  # start the IBIT caption counter (seconds)

    def __init__(self):
        super().__init__()
        self.setObjectName("normalPage")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(theme.build_stylesheet(_chevron_url(), _check_url()))
        self._phase = Phase.READY
        self._total = 0
        self._done = 0

        outer = QHBoxLayout(self)
        outer.setSpacing(16)
        outer.addStretch()
        column = QWidget()
        column.setFixedWidth(PANEL_WIDTH)
        outer.addWidget(column)
        self.reports_list = ReportsList()
        right = QWidget()
        right.setFixedWidth(REPORTS_WIDTH)
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 10, 20, 10)
        right_lay.setSpacing(20)
        right_lay.addWidget(self.reports_list, 1)
        outer.addWidget(right)
        outer.addStretch()

        root = QVBoxLayout(column)
        root.setContentsMargins(20, 10, 20, 10)
        root.setSpacing(20)

        root.addLayout(self._build_header())
        root.addWidget(self._build_step0())
        root.addWidget(self._build_step1())
        root.addWidget(self._build_action_button())
        root.addWidget(self._build_step2())
        root.addStretch()
        right_lay.addWidget(self._build_step3())

        self.start_button.clicked.connect(self.start_clicked)
        self.stop_button.clicked.connect(self.stop_clicked)
        self.cmb_project.currentIndexChanged.connect(self._update_enabled)
        self.cmb_connector.currentIndexChanged.connect(self._update_enabled)

        self.comm_result.connect(self.set_comm_result)
        self.ibit_result.connect(self.set_ibit_result)

        self.setTabOrder(self.btn_comm_check, self.btn_ibit)
        self.setTabOrder(self.btn_ibit, self.cmb_project)
        self.setTabOrder(self.cmb_project, self.cmb_connector)
        self.setTabOrder(self.cmb_connector, self.start_button)
        self.setTabOrder(self.start_button, self.stop_button)
        self.setTabOrder(self.stop_button, self.btn_report_excel)
        self.setTabOrder(self.btn_report_excel, self.btn_report_word)
        self.setTabOrder(self.btn_report_word, self.btn_report_fails)
        self.setTabOrder(self.btn_report_fails, self.btn_wiki)
        self.setTabOrder(self.btn_wiki, self.btn_engineer)

        self.set_phase(Phase.READY)

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        chips = QHBoxLayout()
        chips.setSpacing(8)
        self.chip_simulation = QLabel("Simulation: On")
        self.chip_connection = QLabel("IO Box")
        for chip, tip in ((self.chip_simulation, "Simulation mode (change it in Engineer view)"),
                          (self.chip_connection, "Connection target (change it in Engineer view)")):
            chip.setObjectName("statusChip")
            chip.setToolTip(tip)
            chip.setMinimumHeight(32)
            chip.setAlignment(Qt.AlignCenter)
            chip.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            chips.addWidget(chip)
        row.addLayout(chips)
        row.addStretch()

        switch = QFrame()
        switch.setObjectName("modeSwitch")
        sl = QHBoxLayout(switch)
        sl.setContentsMargins(3, 3, 3, 3)
        sl.setSpacing(0)
        self.btn_normal = QPushButton("Normal")
        self.btn_engineer = QPushButton("Engineer")
        group = QButtonGroup(self)
        group.setExclusive(True)
        for b, tip in ((self.btn_normal, "Simple view for operators"),
                       (self.btn_engineer, "Full view with all engineering tools")):
            b.setObjectName("modeButton")
            b.setCheckable(True)
            b.setToolTip(tip)
            group.addButton(b)
            sl.addWidget(b)
        self.btn_normal.setChecked(True)
        self.btn_engineer.clicked.connect(lambda: self.mode_changed.emit("engineer"))
        self.btn_normal.clicked.connect(lambda: self.mode_changed.emit("normal"))
        row.addWidget(switch)
        return row

    def _field(self, card: StepCard, caption: str) -> QComboBox:
        label = QLabel(caption)
        label.setObjectName("fieldLabel")
        combo = QComboBox()
        combo.setObjectName("field")
        combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(10)
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        combo.setPlaceholderText("Select data")
        label.setBuddy(combo)
        card.body.addWidget(label)
        card.body.addWidget(combo)
        return combo

    def _build_step0(self) -> StepCard:
        card = StepCard("Step 0 · Setup")
        row = QHBoxLayout()
        row.setSpacing(12)
        self.btn_comm_check = QPushButton("Comm check")
        self.btn_comm_check.setToolTip("Check the connection to the tester")
        self.btn_ibit = QPushButton("IBIT")
        self.btn_ibit.setToolTip("Run the built-in self test")
        for b in (self.btn_comm_check, self.btn_ibit):
            b.setObjectName("setupButton")
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            row.addWidget(b)
        card.body.addLayout(row)
        self._ibit_running = False
        self._countdowns = {}
        for key, btn, caption in (("comm", self.btn_comm_check, "Comm check"),
                                  ("ibit", self.btn_ibit, "IBIT")):
            timer = QTimer(self)
            timer.timeout.connect(lambda k=key: self._tick_countdown(k))
            self._countdowns[key] = {"button": btn, "caption": caption, "timer": timer, "left": 0}
        self.comm_countdown.connect(lambda s: self.start_countdown("comm", s))
        self.ibit_countdown.connect(lambda s: self.start_countdown("ibit", s))
        return card

    @staticmethod
    def _fmt_remaining(seconds: int) -> str:
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _tick_countdown(self, key: str):
        state = self._countdowns[key]
        state["left"] = max(0, state["left"] - 1)
        self._render_countdown(key)

    def _render_countdown(self, key: str):
        state = self._countdowns[key]
        text = f"{state['caption']}  ·  {self._fmt_remaining(state['left'])}"
        state["button"].setText(text)

    def start_countdown(self, key: str, seconds: float):
        """Show a ticking mm:ss counter in the caption of the 'comm' or 'ibit' button."""
        state = self._countdowns[key]
        state["timer"].stop()
        state["left"] = int(round(seconds))
        self._render_countdown(key)
        state["timer"].start(1000)

    def stop_countdown(self, key: str):
        state = self._countdowns[key]
        state["timer"].stop()
        if key == "comm":
            state["button"].setText(state["caption"])
        else:
            state["button"].setText("Stop IBIT" if self._ibit_running else state["caption"])

    def set_ibit_caption(self, caption: str):
        """Change the base caption of the IBIT button (counter is appended while running)."""
        self._countdowns["ibit"]["caption"] = caption

    def set_comm_result(self, success: bool):
        self.stop_countdown("comm")
        self.btn_comm_check.setProperty("result", "pass" if success else "fail")
        _repolish(self.btn_comm_check)

    def reset_comm_result(self):
        self.btn_comm_check.setProperty("result", "")
        _repolish(self.btn_comm_check)

    def set_ibit_result(self, success: bool):
        self.btn_ibit.setProperty("result", "pass" if success else "fail")
        _repolish(self.btn_ibit)

    def set_ibit_running(self, running: bool):
        """While IBIT runs, its button becomes 'Stop IBIT'."""
        self._ibit_running = running
        if running:
            self.btn_ibit.setText("Stop IBIT")
            self._countdowns["ibit"]["caption"] = "Stop IBIT"
        else:
            self._countdowns["ibit"]["timer"].stop()
            self._countdowns["ibit"]["caption"] = "IBIT"
            self.btn_ibit.setText("IBIT")
        if running:
            self.btn_ibit.setProperty("result", "")
            _repolish(self.btn_ibit)
        self._update_enabled()

    def _build_step1(self) -> StepCard:
        card = StepCard("Step 1 · Choose what to test")
        self.cmb_project = self._field(card, "Project")
        self.cmb_connector = self._field(card, "Connector")
        return card

    def _build_action_button(self) -> QStackedWidget:
        self.start_button = QPushButton("  Start test")
        self.start_button.setObjectName("startButton")
        self.start_button.setIcon(_icon(_play))
        self.start_button.setIconSize(QSize(32, 32))
        self.stop_button = QPushButton("  Stop")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setIcon(_icon(_stop))
        self.stop_button.setIconSize(QSize(32, 32))
        self.action_stack = QStackedWidget()
        self.action_stack.addWidget(self.start_button)
        self.action_stack.addWidget(self.stop_button)
        return self.action_stack

    def _build_step2(self) -> StepCard:
        card = StepCard("Step 2 · Results")

        self.banner = QFrame()
        self.banner.setObjectName("banner")
        bl = QVBoxLayout(self.banner)
        bl.setContentsMargins(16, 12, 16, 12)
        bl.setSpacing(2)
        self.banner_headline = QLabel()
        self.banner_headline.setObjectName("bannerHeadline")
        self.banner_sub = QLabel()
        self.banner_sub.setObjectName("bannerSub")
        self.banner_sub.setWordWrap(True)
        bl.addWidget(self.banner_headline)
        bl.addWidget(self.banner_sub)
        card.body.addWidget(self.banner)

        progress_row = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.percent = QLabel("0%")
        self.percent.setObjectName("percent")
        self.percent.setFixedWidth(48)
        self.percent.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        progress_row.addWidget(self.progress, stretch=1)
        progress_row.addWidget(self.percent)
        card.body.addLayout(progress_row)

        tiles = QGridLayout()
        tiles.setSpacing(12)
        self.tile_pass = CounterTile("Passed", _icon(_check, 40, theme.PASS_TEXT))
        self.tile_fail = CounterTile("Failed", _icon(_cross, 40, theme.TEXT_MUTED))
        self.tile_pass.set_state("pass")
        tiles.addWidget(self.tile_pass, 0, 0)
        tiles.addWidget(self.tile_fail, 0, 1)
        tiles.setColumnStretch(0, 1)
        tiles.setColumnStretch(1, 1)
        card.body.addLayout(tiles)
        return card

    def _build_step3(self) -> StepCard:
        card = StepCard("Step 3 · Reports and help")
        specs = (
            ("btn_report_excel", "Excel report", _grid, "Open the Excel report", 0, 0, 1),
            ("btn_report_word", "Word report", _document, "Open the Word report", 0, 1, 1),
            ("btn_report_fails", "Fail report", _cross, "Open the combined fail report", 0, 2, 1),
            ("btn_wiki", "Wiki help", _help, "Open the help pages", 1, 0, 3),
        )
        grid = QGridLayout()
        grid.setSpacing(12)
        for attr, text, draw, tip, r, c, span in specs:
            b = QPushButton(text)
            b.setObjectName("reportButton")
            b.setIcon(_icon(draw, 40, theme.TEXT))
            b.setIconSize(QSize(22, 22))
            b.setToolTip(tip)
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            setattr(self, attr, b)
            grid.addWidget(b, r, c, 1, span)
        card.body.addLayout(grid)
        return card

    def _update_enabled(self):
        running = self._phase == Phase.RUNNING
        has_selection = self.cmb_project.currentIndex() >= 0 and self.cmb_connector.currentIndex() >= 0
        self.cmb_project.setEnabled(not running)
        self.cmb_connector.setEnabled(not running)
        self.start_button.setEnabled(has_selection and not running)
        self.btn_report_excel.setEnabled(not running)
        self.btn_report_word.setEnabled(not running)
        self.btn_report_fails.setEnabled(not running)
        self.btn_wiki.setEnabled(True)
        self.btn_comm_check.setEnabled(not running)
        self.btn_ibit.setEnabled(self._ibit_running or not running)

    def set_phase(self, phase: Phase):
        self._phase = phase
        key = phase.value
        self.action_stack.setCurrentWidget(self.stop_button if phase == Phase.RUNNING else self.start_button)
        self.start_button.setText("  Test again" if phase in (Phase.PASSED, Phase.FAILED, Phase.STOPPED) else "  Start test")
        for w in (self.banner, self.progress):
            w.setProperty("phase", key)
            _repolish(w)
        self._update_enabled()
        self._update_banner()

    def refresh_status(self, done: int, total: int, passed: int, failed: int):
        self._done, self._total = done, total
        self.progress.setRange(0, max(total, 1))
        self.progress.setValue(min(done, max(total, 1)))
        self.percent.setText(f"{round(100 * done / total) if total else 0}%")
        self.tile_pass.number.setText(str(passed))
        self.tile_fail.number.setText(str(failed))
        self.tile_fail.set_state("fail" if failed > 0 else "")
        self._failed = failed
        self._update_banner()

    def _update_banner(self):
        done, total = self._done, self._total
        failed = getattr(self, "_failed", 0)
        text = {
            Phase.READY: ("Ready to test", "Choose a project and connector, then press Start test."),
            Phase.RUNNING: ("Testing in progress", f"Test {done} of {total}. Please do not unplug the unit."),
            Phase.PASSED: ("PASSED", f"All {total} tests passed."),
            Phase.FAILED: ("FAILED", f"{failed} of {total} tests failed. Open a report for details."),
            Phase.STOPPED: ("Test stopped", f"Stopped at test {done} of {total}."),
        }[self._phase]
        self.banner_headline.setText(text[0])
        self.banner_sub.setText(text[1])
        self.banner.setAccessibleName(f"{text[0]}. {text[1]}")

    def set_connection_status(self, simulation_on: bool, localhost: bool):
        """Show simulation On/Off and IO Box / LocalHost as read-only status chips."""
        self.chip_simulation.setText("Simulation: On" if simulation_on else "Simulation: Off")
        self.chip_simulation.setProperty("state", "warn" if simulation_on else "ok")
        self.chip_connection.setText("LocalHost" if localhost else "IO Box")
        self.chip_connection.setProperty("state", "warn" if localhost else "ok")
        _repolish(self.chip_simulation)
        _repolish(self.chip_connection)

    def reset_counters(self):
        self._failed = 0
        self.refresh_status(0, 0, 0, 0)

    def select_normal_mode(self):
        self.btn_normal.setChecked(True)
