from pathlib import Path
import time
import sys
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QFont, QCloseEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QComboBox, QLineEdit, QCheckBox,
    QGroupBox, QLabel, QSizePolicy, QSpacerItem, QApplication, QStackedWidget
)

from hw_tester.ui.qt.normal_panel_qt import NormalPanel
from hw_tester.ui.qt.controllers import MainController
from hw_tester.ui.qt.widgets import LogViewQt, PinTableQt
from hw_tester.utils.config_loader import load_settings


class MainWindowQt(QMainWindow):
    def __init__(self):
        super().__init__()
        app_info = load_settings().get("IO_Tester", {})
        app_name = app_info.get("Name", "HW Tester")
        app_version = app_info.get("Version", "")
        title = f"{app_name} v{app_version}" if app_version else app_name
        self.setWindowTitle(title)
        self.resize(620, 900)

        # Stylesheet is loaded at app level in _main() for proper QMessageBox styling

        # Two layouts: "Normal" (simplified) and "Engineering" (full, the original one)
        # Hidden pages are ignored by layouts, so the Normal page can shrink the window freely
        self.layout_stack = QWidget()
        self._pages_layout = QVBoxLayout(self.layout_stack)
        self._pages_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self.layout_stack)

        self.normal_page = self._build_normal_page()
        root = QWidget()  # Engineering page
        self.engineering_page = root
        self._pages_layout.addWidget(self.normal_page)
        self._pages_layout.addWidget(root)
        root.hide()

        main = QVBoxLayout(root)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(12)

        # Top: Pin table (using custom widget)
        self.table = PinTableQt()
        main.addWidget(self.table, stretch=6)

        # Middle: controls (3 groups like your app)
        controls_row = QHBoxLayout()
        controls_row.setSpacing(12)

        # Group 1: connector/file
        g1 = QGroupBox("Connector / File")
        g1l = QVBoxLayout(g1)
        
        # Connector field row
        conn_layout = QHBoxLayout()
        conn_layout.addWidget(QLabel("Connector:"))
        self.connector_edit = QLineEdit("")
        conn_layout.addWidget(self.connector_edit)
        g1l.addLayout(conn_layout)

        self.btn_settings = QPushButton("Settings")
        self.btn_settings.setMinimumSize(120, 35)
        self.btn_load = QPushButton("Load")
        self.btn_load.setObjectName("btnPrimary")  # QSS primary styling
        self.btn_load.setMinimumSize(120, 35)
        self.btn_report = QPushButton("Report")
        self.btn_report.setMinimumSize(120, 35)
        self.btn_doc = QPushButton("DOC")
        self.btn_doc.setMinimumSize(120, 35)
        self.btn_fails = QPushButton("Fails")
        self.btn_fails.setMinimumSize(120, 35)
        
        # First row: Settings, Load (centered)
        row1_layout = QHBoxLayout()
        row1_layout.addStretch()
        row1_layout.addWidget(self.btn_settings)
        row1_layout.addWidget(self.btn_load)
        row1_layout.addStretch()
        g1l.addLayout(row1_layout)
        
        # Second row: Report, DOC, Fails (centered)
        row2_layout = QHBoxLayout()
        row2_layout.addStretch()
        row2_layout.addWidget(self.btn_report)
        row2_layout.addWidget(self.btn_doc)
        row2_layout.addWidget(self.btn_fails)
        row2_layout.addStretch()
        g1l.addLayout(row2_layout)

        controls_row.addWidget(g1, stretch=2)

        # Group 2: run controls
        g2 = QGroupBox("Run Controls")
        g2l = QVBoxLayout(g2)  # Changed to VBoxLayout for better control
        
        # Buttons row
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        self.btn_test = QPushButton("Test")
        self.btn_test.setEnabled(False)  # Disabled until connector loaded
        self.btn_test.setMinimumSize(200, 40)
        buttons_layout.addWidget(self.btn_test)
        buttons_layout.addStretch()
        self.btn_test_all = QPushButton("Test_All")
        self.btn_test_all.setEnabled(False)  # Disabled until connector loaded
        self.btn_test_all.setMinimumSize(200, 40)
        buttons_layout.addWidget(self.btn_test_all)
        buttons_layout.addStretch()
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setMinimumSize(200, 40)
        buttons_layout.addWidget(self.btn_stop)
        buttons_layout.addStretch()
        g2l.addLayout(buttons_layout)
        
        # Add test status labels in a single horizontal line below buttons
        status_layout = QHBoxLayout()
        status_layout.addStretch()
        lbl_testing_caption = QLabel("Testing Pin:")
        lbl_testing_caption.setObjectName("runStatusCaption")
        status_layout.addWidget(lbl_testing_caption)
        self.lbl_testing_pin = QLabel("---")
        self.lbl_testing_pin.setObjectName("runStatusValue")
        self.lbl_testing_pin.setStyleSheet("font-size: 15pt; font-weight: bold; color: #58a6ff;")
        status_layout.addWidget(self.lbl_testing_pin)
        status_layout.addStretch()
        
        lbl_power_caption = QLabel("Power:")
        lbl_power_caption.setObjectName("runStatusCaption")
        status_layout.addWidget(lbl_power_caption)
        self.lbl_power_result = QLabel("---")
        self.lbl_power_result.setObjectName("runStatusValue")
        status_layout.addWidget(self.lbl_power_result)
        status_layout.addStretch()
        
        lbl_pullup_caption = QLabel("Pullup:")
        lbl_pullup_caption.setObjectName("runStatusCaption")
        status_layout.addWidget(lbl_pullup_caption)
        self.lbl_pullup_result = QLabel("---")
        self.lbl_pullup_result.setObjectName("runStatusValue")
        status_layout.addWidget(self.lbl_pullup_result)
        status_layout.addStretch()
        
        lbl_logic_caption = QLabel("Logic:")
        lbl_logic_caption.setObjectName("runStatusCaption")
        status_layout.addWidget(lbl_logic_caption)
        self.lbl_logic_result = QLabel("---")
        self.lbl_logic_result.setObjectName("runStatusValue")
        status_layout.addWidget(self.lbl_logic_result)
        status_layout.addStretch()
        
        g2l.addLayout(status_layout)

        controls_row.addWidget(g2, stretch=3)

        # Group 3: log option
        g3 = QGroupBox("Log")
        g3l = QVBoxLayout(g3)
        self.cb_inf = QCheckBox("INF"); self.cb_inf.setChecked(True)
        self.cb_suc = QCheckBox("SUC"); self.cb_suc.setChecked(True)
        self.cb_wrn = QCheckBox("WRN"); self.cb_wrn.setChecked(True)
        self.cb_err = QCheckBox("ERR"); self.cb_err.setChecked(True)
        self.cb_dbg = QCheckBox("DBG"); self.cb_dbg.setChecked(False)
        for cb in (self.cb_inf, self.cb_suc, self.cb_wrn, self.cb_err, self.cb_dbg):
            g3l.addWidget(cb)
        
        # Clear button
        self.btn_clear_log = QPushButton("Clear")
        g3l.addWidget(self.btn_clear_log)
        
        g3l.addItem(QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding))

        controls_row.addWidget(g3, stretch=1)

        # Group 4: Test/Debug
        g4 = QGroupBox("Test/Debug")
        g4l = QGridLayout(g4)
        g4l.setSpacing(8)
        
        # Column 0: Comm Check, IBIT, Stop IBIT
        self.btn_keepalive = QPushButton("Comm Check")
        self.btn_ibit = QPushButton("IBIT")
        self.btn_stop_ibit = QPushButton("Stop IBIT")
        self.btn_stop_ibit.setEnabled(False)  # Disabled until IBIT test starts
        
        g4l.addWidget(self.btn_keepalive, 0, 0)
        g4l.addWidget(self.btn_ibit, 1, 0)
        g4l.addWidget(self.btn_stop_ibit, 2, 0)
        
        # Column 1: Simulation, LocalHost
        self.btn_simulation = QPushButton("Simulation: On")
        self.btn_connection = QPushButton("LocalHost")
        
        g4l.addWidget(self.btn_simulation, 0, 1)
        g4l.addWidget(self.btn_connection, 1, 1)
        
        # Column 2: Next, Debug
        self.btn_next = QPushButton("Next")
        self.btn_debug = QPushButton("Debug: False")
        
        g4l.addWidget(self.btn_next, 0, 2)
        g4l.addWidget(self.btn_debug, 1, 2)
        
        # Wiki button - opens the local MkDocs site (replaces the old HTML dropdown opener)
        self.btn_wiki = QPushButton("Wiki")
        g4l.addWidget(self.btn_wiki, 2, 1, 1, 2)  # row 2, col 1, span 1 row, span 2 cols
        
        # Pin table column preset - same functionality as the Settings window preset selector
        self.lbl_column_preset = QLabel("Preset:")
        self.cmb_column_preset = QComboBox()
        g4l.addWidget(self.lbl_column_preset, 3, 0)
        g4l.addWidget(self.cmb_column_preset, 3, 1, 1, 2)  # row 3, col 1, span 1 row, span 2 cols

        self.btn_to_normal = QPushButton("Normal")
        g4l.addWidget(self.btn_to_normal, 4, 0, 1, 3)
        self.btn_to_normal.clicked.connect(self.show_normal_layout)

        controls_row.addWidget(g4, stretch=1)

        main.addLayout(controls_row, stretch=0)

        # Bottom: log
        log_group = QGroupBox("Operational Log")
        log_layout = QVBoxLayout(log_group)

        # Use LogViewQt with same API as Tkinter version
        self.log = LogViewQt()
        log_layout.addWidget(self.log)

        main.addWidget(log_group, stretch=3)

        self.log.append("Qt shell is running. Next we wire data + callbacks.", "INFO")
        
        # Initialize controller to handle button logic
        self.controller = MainController(self)
        self.log.append("Controller initialized - Load button is ready.", "INFO")

        # Populate and wire the column preset combo box after controller is initialized
        self.controller.populate_column_preset_combo(self.cmb_column_preset)
        self.cmb_column_preset.currentTextChanged.connect(self.controller.on_column_preset_change)
        self.controller.populate_project_combo(self.normal_cmb_project)
        self.normal_cmb_project.currentTextChanged.connect(
            lambda name: self.controller.populate_connector_combo(self.normal_cmb_connector, name)
        )
        
        # Storage for pending callbacks (for thread-safe updates)
        self._pending_callbacks = {}
        self._callback_counter = 0
    
    def _build_normal_page(self) -> QWidget:
        """Build the simplified 'Normal' layout (widgets only; behavior wired later)."""
        panel = NormalPanel()
        self.normal_panel = panel
        # Aliases used by the controller
        self.normal_cmb_project = panel.cmb_project
        self.normal_cmb_connector = panel.cmb_connector
        self.normal_btn_test = panel.start_button
        self.normal_btn_stop = panel.stop_button
        self.normal_btn_report_excel = panel.btn_report_excel
        self.normal_btn_report_word = panel.btn_report_word
        self.normal_btn_wiki = panel.btn_wiki
        panel.mode_changed.connect(
            lambda mode: self.show_engineering_layout() if mode == "engineer" else None
        )
        return panel

    @Slot()
    def show_normal_layout(self):
        self.normal_panel.select_normal_mode()
        self._show_page(self.normal_page)

    @Slot()
    def show_engineering_layout(self):
        self._show_page(self.engineering_page)

    def _show_page(self, page: QWidget):
        for p in (self.normal_page, self.engineering_page):
            p.setVisible(p is page)
        self.fit_to_current_layout()

    def fit_to_current_layout(self):
        """Normal layout: compact window sized to the panel. Engineering layout: maximized."""
        normal = self.normal_page.isVisibleTo(self)
        if normal:
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            if self.isMaximized() or self.isFullScreen():
                self.showNormal()
            self.normal_page.ensurePolished()
            self.normal_page.layout().activate()
            hint = self.normal_page.sizeHint()
            avail = self.screen().availableGeometry() if self.screen() else None
            width, height = hint.width() + 40, hint.height() + 20
            if avail is not None:
                height = min(height, avail.height() - 70)
            self.resize(width, height)
        else:
            self.showMaximized()

    @Slot()
    def _on_test_complete(self):
        """Slot called when test completes (from controller)."""
        self.controller._on_test_complete()
    
    @Slot()
    def _on_ibit_complete(self):
        """Slot called when IBIT test completes (from controller)."""
        self.controller._on_ibit_complete()
    
    @Slot(int, str)
    def _schedule_callback(self, delay_ms: int, callback_id: str):
        """Slot to schedule a callback on the main thread."""
        print(f"[MainWindow._schedule_callback] Scheduling callback {callback_id} with delay {delay_ms}ms")
        if callback_id in self._pending_callbacks:
            callback = self._pending_callbacks.pop(callback_id)
            QTimer.singleShot(delay_ms, callback)
            print(f"[MainWindow._schedule_callback] Callback {callback_id} scheduled with QTimer")
        else:
            print(f"[MainWindow._schedule_callback] ERROR: Callback {callback_id} not found")
    
    def closeEvent(self, event: QCloseEvent):
        """Handle window close event - clean up resources."""
        try:
            self.log.append("[MainWindow] Shutting down application...", "INFO")
            
            # Delegate cleanup to controller
            if hasattr(self, 'controller'):
                self.controller.on_closing()
            
            # Accept the close event
            event.accept()
        except Exception as e:
            print(f"Error during close: {e}")
            event.accept()


def _main():
    app = QApplication([])
    app.setStyle("Fusion")  # Use Fusion style for better cross-platform look
    
    # Load stylesheet at app level (required for QMessageBox styling)
    css_path = Path(__file__).resolve().parent.parent / "Styles" / "dark.css"
    if css_path.exists():
        css_content = css_path.read_text(encoding="utf-8")
        app.setStyleSheet(css_content)
        print(f"Stylesheet loaded: {css_path} ({len(css_content)} chars)")
    else:
        print(f"WARNING: Stylesheet not found at {css_path}")
    
    win = MainWindowQt()
    win.show()
    QTimer.singleShot(0, win.fit_to_current_layout)  # after first layout pass
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(_main())