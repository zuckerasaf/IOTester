#!/usr/bin/env python3
"""Connector Targets: Qt desktop app around engine.py.

Run:   python app.py
Needs: pip install PySide6 openpyxl
"""
import copy
import re
import sys
import traceback
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QSpinBox, QSplitter,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

import engine

APP_DIR = Path(__file__).resolve().parent
USER_CONFIG = APP_DIR / "config.json"


# ----------------------------------------------------------------------------
# Small helpers
# ----------------------------------------------------------------------------
def hbox(*widgets, stretch_last=False):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    for x in widgets:
        lay.addWidget(x)
    return w


def item(text="", editable=True):
    it = QTableWidgetItem("" if text is None else str(text))
    if not editable:
        it.setFlags(it.flags() & ~Qt.ItemIsEditable)
    return it


def default_db_dir():
    """Folder from 'DB Path (Load)' (Paths.database in settings.yaml); empty string if unavailable."""
    candidates = [
        Path(sys.argv[0]).resolve().parent / "config" / "settings.yaml",
        APP_DIR.parent / "config" / "settings.yaml",
    ]
    for settings in candidates:
        if not settings.is_file():
            continue
        try:
            in_paths = False
            for line in settings.read_text(encoding="utf-8").splitlines():
                if line and not line[0].isspace() and not line.startswith("#"):
                    in_paths = line.split(":")[0].strip() == "Paths"
                elif in_paths and line.strip().startswith("database:"):
                    path = line.split(":", 1)[1].strip().strip("\"'")
                    return path if path and Path(path).is_dir() else ""
        except OSError:
            pass
    return ""


def make_table(headers):
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.horizontalHeader().setStretchLastSection(True)
    t.verticalHeader().setVisible(False)
    t.setSelectionBehavior(QTableWidget.SelectRows)
    t.setSelectionMode(QTableWidget.SingleSelection)
    return t


def remove_selected_row(table):
    r = table.currentRow()
    if r >= 0:
        table.removeRow(r)


def combo_with(items, current_data):
    """items: list of (label, data)."""
    c = QComboBox()
    for label, data in items:
        c.addItem(label, data)
    i = c.findData(current_data)
    c.setCurrentIndex(i if i >= 0 else 0)
    return c


REGEX_DICTIONARY = [
    ("Characters", None, None),
    (".", "Any single character", "a.c  matches abc, a5c"),
    (r"\d", "A digit 0-9", r"\d\d  matches 07, 42"),
    (r"\D", "Anything except a digit", ""),
    (r"\w", "Letter, digit or underscore", ""),
    (r"\s", "A space or tab", r"\s*  = optional spaces"),
    ("[ABC]", "One of the listed characters", "[JK]1  matches J1, K1"),
    ("[A-Z]", "One character of a range", "[0-9] = a digit"),
    ("[^ABC]", "Any character NOT listed", ""),
    (r"\.", "A real dot (backslash switches off a special symbol)", r"3\.3  matches 3.3 only"),
    ("Repeat", None, None),
    ("*", "Zero or more times", r"\d*"),
    ("+", "One or more times", r"\d+  matches 5, 12, 2048"),
    ("?", "Optional (zero or one time)", "colou?r"),
    ("{3}", "Exactly 3 times", r"\d{3}  matches 123"),
    ("{2,4}", "2 to 4 times", ""),
    ("Position", None, None),
    ("^", "Start of the text", "^J  text must start with J"),
    ("$", "End of the text", r"V$  text must end with V"),
    (r"\b", "Word boundary (edge of a word)", r"V\b  matches V but not VDC"),
    ("Groups and choices", None, None),
    ("( )", "Capture group: its content becomes {g1}, {g2} ...", r"DI(\d+)  on DI5 gives {g1} = 5"),
    ("(?: )", "Group without capturing", r"(?:\.\d+)?  optional decimals"),
    ("A|B", "A or B", "IN|OUT"),
    ("(?<![A-Za-z])", "Not preceded by a letter", "(?<![A-Za-z])DI  matches DI5, not ADI5"),
    ("(?i)", "Ignore upper/lower case (put at the start)", "(?i)tab  matches Tab, TAB"),
    ("Examples", None, None),
    (r"^J\d+$", "Connector name: J then a number", "J1, J17"),
    (r"#(\d+)", "Number after a # sign", "Card #12 gives 12"),
    (r"(\d+(?:\.\d+)?)\s*V\b", "A voltage value", "3.3 V gives 3.3"),
    ("Value templates (Then write)", None, None),
    ("{A}", "Text of source column A", "A = Pin 3  gives  Pin 3"),
    ("{A|num}", "First number found in column A", "A = Pin 3  gives  3"),
    ("{A|rangemax}", "Larger number of a range in column A", "A = 0-24  gives  24"),
    ("{g1}, {g2}", "Capture group 1, 2 ... of the condition", "code_number DI on DI_5  gives  5"),
    ("{H@J=text}", "Column H of the FIRST row of the connector whose column J contains 'text'",
     r"{H@J=24V I\O RTN}  gives the Pin Out of the first 24V I\O RTN row"),
    ("{H@N==text}", "Same, but column N must EQUAL the text exactly (note the double =)",
     "{H@N==10}  gives the Pin Out of the first row with Power_Expected = 10"),
    ("C{A|num}_AI{g1}_10", "Combined template", "A = Pin 3, cell DI_5  gives  C3_AI5_10"),
]


class RegexDictionaryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Regex dictionary")
        self.resize(640, 560)
        lay = QVBoxLayout(self)
        t = make_table(["Symbol", "Meaning", "Example"])
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        t.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setWordWrap(True)
        t.setSelectionMode(QTableWidget.NoSelection)
        for sym, meaning, example in REGEX_DICTIONARY:
            r = t.rowCount()
            t.insertRow(r)
            if meaning is None:
                head = item(sym, editable=False)
                f = head.font()
                f.setBold(True)
                head.setFont(f)
                t.setItem(r, 0, head)
                t.setSpan(r, 0, 1, 3)
                continue
            s = item(sym, editable=False)
            f = s.font()
            f.setFamily("Consolas")
            s.setFont(f)
            t.setItem(r, 0, s)
            t.setItem(r, 1, item(meaning, editable=False))
            t.setItem(r, 2, item(example, editable=False))
        t.resizeRowsToContents()
        lay.addWidget(t)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        lay.addWidget(close, 0, Qt.AlignRight)


def show_regex_dictionary(parent):
    RegexDictionaryDialog(parent).exec()


# ----------------------------------------------------------------------------
# Worker thread
# ----------------------------------------------------------------------------
class RunThread(QThread):
    log = Signal(str)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, source, out, cfg, only, use_rules):
        super().__init__()
        self.args = (source, out, cfg, only, use_rules)

    def run(self):
        source, out, cfg, only, use_rules = self.args
        try:
            res = engine.run(source, out, cfg, only, log=self.log.emit, use_rules=use_rules)
            self.done.emit(res)
        except engine.FileLockedError as e:
            self.failed.emit(str(e))
        except engine.ConfigError as e:
            self.failed.emit(str(e))
        except Exception:
            self.failed.emit(traceback.format_exc())


# ----------------------------------------------------------------------------
# Tab: Run
# ----------------------------------------------------------------------------
class RunTab(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.thread = None
        self.db_dir = default_db_dir()
        lay = QVBoxLayout(self)

        self.source_edit = QLineEdit()
        b1 = QPushButton("Browse...")
        b1.clicked.connect(self.pick_source)
        self.out_edit = QLineEdit()
        self.out_edit.setPlaceholderText("empty = same folder as the source file")
        b2 = QPushButton("Browse...")
        b2.clicked.connect(self.pick_out)
        self.file_tpl = QLineEdit()
        self.file_tpl.setToolTip("Output file name, {conn} is replaced by the connector, e.g. J1")

        form = QFormLayout()
        form.addRow("Source workbook:", hbox(self.source_edit, b1))
        form.addRow("Output folder:", hbox(self.out_edit, b2))
        form.addRow("Target file name:", self.file_tpl)
        lay.addLayout(form)

        self.load_btn = QPushButton("Load tabs from source")
        self.load_btn.setToolTip("Reads the tab names of the source file into the 'Source & Tabs' page.")
        self.load_btn.clicked.connect(self.load_source)
        self.conn_combo = QComboBox()
        self.conn_combo.setMinimumWidth(90)
        self.preview_btn = QPushButton("Preview connector")
        self.preview_btn.setToolTip("Shows the rows of one target file without writing anything.")
        self.preview_btn.clicked.connect(self.do_preview)
        self.run_btn = QPushButton("Generate files")
        self.run_btn.setDefault(True)
        self.run_btn.clicked.connect(self.do_run)
        self.open_btn = QPushButton("Open output folder")
        self.open_btn.clicked.connect(self.open_folder)
        lay.addWidget(hbox(self.load_btn, QLabel("  Connector:"), self.conn_combo,
                           self.preview_btn, self.run_btn, self.open_btn))

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        lay.addWidget(self.log, 1)

    # --- helpers
    def write(self, text):
        self.log.appendPlainText(text)

    def out_dir(self):
        if self.out_edit.text().strip():
            return self.out_edit.text().strip()
        return str(Path(self.source_edit.text()).resolve().parent)

    def check_source(self):
        p = self.source_edit.text().strip()
        if not p or not Path(p).is_file():
            QMessageBox.warning(self, "Source", "Please choose an existing source .xlsx file.")
            return None
        return p

    def pick_source(self):
        start = self.source_edit.text().strip() or self.db_dir
        p, _ = QFileDialog.getOpenFileName(self, "Source workbook", start, "Excel (*.xlsx *.xlsm)")
        if p:
            self.source_edit.setText(p)
            self.load_source()

    def pick_out(self):
        start = self.out_edit.text().strip() or self.db_dir
        p = QFileDialog.getExistingDirectory(self, "Output folder", start)
        if p:
            self.out_edit.setText(p)

    def open_folder(self):
        p = self.out_dir() if self.source_edit.text().strip() else ""
        if p and Path(p).is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(p))

    # --- actions
    def load_source(self):
        src = self.check_source()
        if not src:
            return
        try:
            names = engine.list_sheets(src)
        except Exception as e:
            QMessageBox.critical(self, "Source", f"Cannot read the file:\n{e}")
            return
        self.main.source_tab.set_available_sheets(names)
        self.write(f"Loaded {len(names)} tab(s): {', '.join(names)}")
        self.refresh_connectors(silent=True)

    def refresh_connectors(self, silent=False):
        src = self.check_source()
        if not src or not self.main.commit_ok(silent=silent):
            return
        try:
            conns = engine.list_connectors(src, self.main.cfg)
        except Exception as e:
            if not silent:
                QMessageBox.warning(self, "Connectors", str(e))
            self.write(f"Could not list connectors: {e}")
            return
        self.conn_combo.clear()
        self.conn_combo.addItems(conns)
        self.write(f"Connectors found with the current settings: {', '.join(conns) or '(none)'}")

    def do_preview(self):
        src = self.check_source()
        if not src or not self.main.commit_ok():
            return
        if self.conn_combo.count() == 0:
            self.refresh_connectors()
        conn = self.conn_combo.currentText()
        if not conn:
            return
        try:
            headers, rows = engine.preview(src, self.main.cfg, conn)
        except Exception as e:
            QMessageBox.critical(self, "Preview", str(e))
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Preview {conn} ({len(rows)} rows)")
        dlg.resize(1200, 600)
        t = QTableWidget(len(rows), len(headers))
        t.setHorizontalHeaderLabels([f"{engine.target_letter(i)}: {h}" for i, h in enumerate(headers)])
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                t.setItem(r, c, item("" if v is None else v, editable=False))
        t.resizeColumnsToContents()
        QVBoxLayout(dlg).addWidget(t)
        dlg.exec()

    def do_run(self):
        src = self.check_source()
        if not src or not self.main.commit_ok():
            return
        self.run_btn.setEnabled(False)
        self.write("--- running ---")
        self.thread = RunThread(src, self.out_dir(), copy.deepcopy(self.main.cfg), None, True)
        self.thread.log.connect(self.write)
        self.thread.done.connect(self.run_done)
        self.thread.failed.connect(self.run_failed)
        self.thread.start()

    def run_done(self, res):
        self.run_btn.setEnabled(True)
        self.write(f"Done. {len(res['files'])} file(s) written to {self.out_dir()}")

    def run_failed(self, msg):
        self.run_btn.setEnabled(True)
        self.write("ERROR:\n" + msg)
        if msg.startswith("Need to close"):
            QMessageBox.warning(self, "File is open", msg)
            return
        QMessageBox.critical(self, "Run failed", msg[:1500])


# ----------------------------------------------------------------------------
# Tab: Source & tabs
# ----------------------------------------------------------------------------
class SourceTab(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        lay = QVBoxLayout(self)

        cfg_box = QGroupBox("Configuration file")
        cfg_lay = QHBoxLayout(cfg_box)
        self.cfg_label = QLabel()
        self.cfg_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.cfg_label.setWordWrap(True)
        load_btn = QPushButton("Load config file...")
        load_btn.setToolTip("Choose a .json configuration file to use. Save updates this file; "
                            "Reset reloads it.")
        load_btn.clicked.connect(self.main.open_cfg)
        cfg_lay.addWidget(self.cfg_label, 1)
        cfg_lay.addWidget(load_btn)
        lay.addWidget(cfg_box)

        box = QGroupBox("Layout of the source tabs")
        form = QFormLayout(box)
        self.first_row = QSpinBox()
        self.first_row.setRange(1, 100000)
        self.conn_prefix = QLineEdit()
        self.conn_prefix.setMaxLength(10)
        self.conn_prefix.setMaximumWidth(120)
        self.conn_prefix.setPlaceholderText("J")
        self.conn_prefix.setToolTip("The letter(s) every connector name starts with. Not case sensitive.")
        self._custom_conn_regex = None
        conn_help = QLabel("A connector name is the letter(s) above followed by a number, "
                           "e.g. J → J1, J2, J17.")
        conn_help.setStyleSheet("color: gray;")
        conn_box = QWidget()
        conn_lay = QVBoxLayout(conn_box)
        conn_lay.setContentsMargins(0, 0, 0, 0)
        conn_lay.addWidget(self.conn_prefix)
        conn_lay.addWidget(conn_help)
        self.card_regex = QLineEdit()
        self.card_regex.setToolTip("Applied to the tab name; group 1 is the card number. "
                                   "If the pattern does not match, card 100 is used and reported.")
        card_btn = QPushButton("Regex dictionary")
        card_btn.clicked.connect(lambda: show_regex_dictionary(self))
        card_box = hbox(self.card_regex, card_btn)
        self.card_regex.setMinimumWidth(200)
        self.issues_name = QLineEdit()
        self.sheet_name = QLineEdit()
        self.conn_field = QComboBox()
        form.addRow("First data row:", self.first_row)
        form.addRow("Connector letter(s):", conn_box)
        form.addRow("Card number from tab name (regex):", card_box)
        form.addRow("Connector column is source field:", self.conn_field)
        form.addRow("Open issues file name:", self.issues_name)
        form.addRow("Sheet name inside target files:", self.sheet_name)
        lay.addWidget(box)

        split = QSplitter(Qt.Horizontal)
        left = QGroupBox("Tabs to search (checked = used, order = row order in the target files)")
        ll = QVBoxLayout(left)
        self.sheet_list = QListWidget()
        ll.addWidget(self.sheet_list)
        up = QPushButton("Up")
        dn = QPushButton("Down")
        add = QPushButton("Add tab name...")
        up.clicked.connect(lambda: self.move(self.sheet_list, -1))
        dn.clicked.connect(lambda: self.move(self.sheet_list, 1))
        add.clicked.connect(self.add_sheet)
        ll.addWidget(hbox(up, dn, add))
        split.addWidget(left)

        right = QGroupBox("Source columns (which Excel column holds which field)")
        rl = QVBoxLayout(right)
        self.field_table = make_table(["Key (used internally)", "Label", "Column letter"])
        rl.addWidget(self.field_table)
        fa = QPushButton("Add field")
        fr = QPushButton("Remove selected")
        fa.clicked.connect(lambda: self.add_field_row("field%d" % (self.field_table.rowCount() + 1),
                                                      "New field", "L"))
        fr.clicked.connect(lambda: remove_selected_row(self.field_table))
        rl.addWidget(hbox(fa, fr))
        split.addWidget(right)
        lay.addWidget(split, 1)

    # --- list helpers
    def move(self, lst, d):
        r = lst.currentRow()
        n = r + d
        if r < 0 or n < 0 or n >= lst.count():
            return
        it = lst.takeItem(r)
        lst.insertItem(n, it)
        lst.setCurrentRow(n)

    def add_sheet(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Tab name", "Exact tab name:")
        if ok and name.strip():
            self.add_sheet_item(name.strip(), True)

    def add_sheet_item(self, name, checked):
        it = QListWidgetItem(name)
        it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
        it.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        self.sheet_list.addItem(it)

    def set_available_sheets(self, names):
        """Keep the current checked tabs, add the others (unchecked) in file order."""
        current = {self.sheet_list.item(i).text(): self.sheet_list.item(i).checkState()
                   for i in range(self.sheet_list.count())}
        self.sheet_list.clear()
        for n in names:
            self.add_sheet_item(n, current.get(n) == Qt.Checked)

    def add_field_row(self, key, label, col):
        r = self.field_table.rowCount()
        self.field_table.insertRow(r)
        self.field_table.setItem(r, 0, item(key))
        self.field_table.setItem(r, 1, item(label))
        self.field_table.setItem(r, 2, item(col))

    # --- cfg <-> widgets
    def _load_conn_prefix(self, regex: str):
        """Show the letter(s) of a simple '^<letters>\\d+$' pattern; keep any other pattern untouched."""
        m = re.fullmatch(r"\^?([A-Za-z_]*)\\d\+\$?", regex)
        if m:
            self._custom_conn_regex = None
            self.conn_prefix.setText(m.group(1))
            self.conn_prefix.setPlaceholderText("J")
        else:
            self._custom_conn_regex = regex
            self.conn_prefix.setText("")
            self.conn_prefix.setPlaceholderText("(advanced pattern in use - type letters to replace it)")

    def _conn_regex_from_prefix(self) -> str:
        text = self.conn_prefix.text().strip().upper()
        if not text and self._custom_conn_regex:
            return self._custom_conn_regex
        return "^" + re.escape(text or "J") + r"\d+$"

    def load_from_cfg(self, cfg):
        self.first_row.setValue(int(cfg["first_data_row"]))
        self._load_conn_prefix(cfg["connector_regex"])
        self.card_regex.setText(cfg["card_regex"])
        self.issues_name.setText(cfg["issues_file_name"])
        self.sheet_name.setText(cfg.get("output_sheet_name", "Sheet"))
        self.sheet_list.clear()
        for n in cfg["source_sheets"]:
            self.add_sheet_item(n, True)
        self.field_table.setRowCount(0)
        for f in cfg["source_fields"]:
            self.add_field_row(f["key"], f["label"], f["column"])
        self.conn_field.clear()
        for f in cfg["source_fields"]:
            self.conn_field.addItem(f"{f['label']} ({f['key']})", f["key"])
        i = self.conn_field.findData(cfg["connector_field"])
        self.conn_field.setCurrentIndex(max(i, 0))

    def commit_to_cfg(self, cfg):
        cfg["first_data_row"] = self.first_row.value()
        cfg["connector_regex"] = self._conn_regex_from_prefix()
        cfg["card_regex"] = self.card_regex.text()
        cfg["issues_file_name"] = self.issues_name.text()
        cfg["output_sheet_name"] = self.sheet_name.text() or "Sheet"
        cfg["source_sheets"] = [self.sheet_list.item(i).text() for i in range(self.sheet_list.count())
                                if self.sheet_list.item(i).checkState() == Qt.Checked]
        fields = []
        for r in range(self.field_table.rowCount()):
            fields.append({"key": self.field_table.item(r, 0).text().strip(),
                           "label": self.field_table.item(r, 1).text().strip(),
                           "column": self.field_table.item(r, 2).text().strip().upper()})
        cfg["source_fields"] = fields
        keep = self.conn_field.currentData()
        cfg["connector_field"] = keep if keep in [f["key"] for f in fields] else (fields[0]["key"] if fields else "")


# ----------------------------------------------------------------------------
# Tab: Column mapping (source -> target)
# ----------------------------------------------------------------------------
class MappingTab(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            "Each row is one column of the target file. Choose which source field feeds it "
            "(the same field can feed several columns), or leave it empty so the Fill Rules can fill it."))
        self.table = make_table(["Target column", "Header text", "Takes its value from", "Constant text"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(1, 160)
        lay.addWidget(self.table, 1)
        add = QPushButton("Add column at the end")
        rem = QPushButton("Remove last column")
        add.clicked.connect(lambda: self.add_row(engine.target_letter(self.table.rowCount()),
                                                 "New column", "", ""))
        rem.clicked.connect(self.remove_last)
        lay.addWidget(hbox(add, rem))
        self.fields = []

    def source_choices(self):
        ch = [("(empty)", ""), ("Card number (from tab name)", "@card"), ("Constant text", "@const")]
        ch += [(f"{f['label']}  [source column {f['column']}]", f["key"]) for f in self.fields]
        return ch

    def add_row(self, letter, header, source, constant):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, item(letter, editable=False))
        self.table.setItem(r, 1, item(header))
        self.table.setCellWidget(r, 2, combo_with(self.source_choices(), source))
        self.table.setItem(r, 3, item(constant))

    def remove_last(self):
        if self.table.rowCount() > 1:
            self.table.removeRow(self.table.rowCount() - 1)

    def load_from_cfg(self, cfg):
        self.fields = cfg["source_fields"]
        self.table.setRowCount(0)
        for i, t in enumerate(cfg["target_columns"]):
            self.add_row(engine.target_letter(i), t["header"], t["source"], t.get("constant", ""))

    def commit_to_cfg(self, cfg):
        cols = []
        for r in range(self.table.rowCount()):
            cols.append({"header": self.table.item(r, 1).text(),
                         "source": self.table.cellWidget(r, 2).currentData() or "",
                         "constant": self.table.item(r, 3).text()})
        cfg["target_columns"] = cols


# ----------------------------------------------------------------------------
# Tab: Fill rules
# ----------------------------------------------------------------------------
HELP = (
    "Rules are tried from top to bottom. A rule matches when ALL its conditions are true "
    "(upper/lower case is ignored). If 'Stop after this rule' is on, later rules are skipped for that row.\n"
    "Conditions look at target columns. Operator 'code_number' finds a name made of letters and a number: "
    "value DI matches DI5 or DI_5 (not ADI5) and the number is {g1}. "
    "Operator 'regex' searches with a regular expression; "
    "its groups can be used in the values as {g1}, {g2} ...\n"
    "Values to write: plain text or numbers, or templates with placeholders:  {A}  = text of column A,  "
    "{A|num} = first number in column A,  {I|rangemax} = larger number of a range like 0-24,  {g1} = regex group 1.\n"
    "Example:  C{A|num}_DI{g1}_0.  If a placeholder is empty, that value is not written. "
    "Results that look like numbers are saved as numbers."
)


ASG_LEGEND = (
    "Placeholders in curly braces are replaced for each row:  "
    "{g1} = the number found by the condition (e.g. condition code_number 'DI' on cell DI_5 gives 5; "
    "with a regex condition, the first (...) group);  "
    "{A} = text of source column A;  {A|num} = first number in column A;  "
    "{A|rangemax} = larger number of a range like 0-24.  "
    "Example: C{A|num}_AI{g1}_10  with A = 'Pin 3' and cell DI_5  →  C3_AI5_10"
)


class LookupDialog(QDialog):
    def __init__(self, parent, choices, template):
        super().__init__(parent)
        self.setWindowTitle("Look up a value in this connector")
        match = engine.LOOKUP_RE.fullmatch(template)
        result_col, search_col, value = match.groups() if match else ("H", "J", "")
        exact = value.startswith("=")
        self.result_col = combo_with(choices, result_col.upper())
        self.search_col = combo_with(choices, search_col.upper())
        self.match_type = combo_with([("Contains", "contains"), ("Equals", "equals")],
                                     "equals" if exact else "contains")
        self.search_value = QLineEdit(value[1:] if exact else value)
        form = QFormLayout(self)
        form.addRow("Return value from:", self.result_col)
        form.addRow("Look in:", self.search_col)
        form.addRow("Match:", self.match_type)
        form.addRow("Value to find:", self.search_value)
        info = QLabel("Uses the first matching row in the same connector; matching ignores case.")
        info.setWordWrap(True)
        form.addRow(info)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def accept(self):
        value = self.search_value.text().strip()
        if not value or "{" in value or "}" in value or (
                self.match_type.currentData() == "contains" and value.startswith("=")):
            QMessageBox.warning(self, "Lookup", "Enter a value without braces. "
                                "For a value starting with '=', use Equals.")
            return
        super().accept()

    def template(self):
        prefix = "=" if self.match_type.currentData() == "equals" else ""
        return "{" + self.result_col.currentData() + "@" + self.search_col.currentData() + "=" + \
               prefix + self.search_value.text().strip() + "}"


class RulesTab(QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self.rules = []
        self.cur = -1
        self.loading = False
        outer = QVBoxLayout(self)
        help_lbl = QLabel(HELP)
        help_lbl.setWordWrap(True)
        outer.addWidget(help_lbl)

        # Same connector list and preview as the Run page, so a rule can be tested right after editing it
        self.test_conn_combo = QComboBox()
        self.test_conn_combo.setMinimumWidth(90)
        self.test_conn_combo.setToolTip("Connector to test the rules on (same list as on the Run page).")
        self.test_preview_btn = QPushButton("Preview connector")
        self.test_preview_btn.setToolTip("Applies the rules, including unsaved edits, to this connector "
                                         "and shows the resulting rows. Nothing is written to disk.")
        self.test_preview_btn.clicked.connect(lambda: self.main.run_tab.do_preview())
        self.test_refresh_btn = QPushButton("Refresh connectors")
        self.test_refresh_btn.setToolTip("Reads the connector list from the source workbook again.")
        self.test_refresh_btn.clicked.connect(lambda: self.main.run_tab.refresh_connectors())
        regex_btn = QPushButton("Regex dictionary")
        regex_btn.setToolTip("Short list of regex symbols and what they mean.")
        regex_btn.clicked.connect(lambda: show_regex_dictionary(self))
        outer.addWidget(hbox(QLabel("Test the rules - Connector:"), self.test_conn_combo,
                             self.test_preview_btn, self.test_refresh_btn, regex_btn))

        split = QSplitter(Qt.Horizontal)
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.addWidget(QLabel("Rules (check = enabled)"))
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self.on_select)
        ll.addWidget(self.list)
        btns = {}
        for name, fn in (("Add", self.add_rule), ("Duplicate", self.dup_rule), ("Delete", self.del_rule),
                         ("Up", lambda: self.move_rule(-1)), ("Down", lambda: self.move_rule(1))):
            b = QPushButton(name)
            b.clicked.connect(fn)
            btns[name] = b
        ll.addWidget(hbox(btns["Add"], btns["Duplicate"], btns["Delete"]))
        ll.addWidget(hbox(btns["Up"], btns["Down"]))
        split.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.stop_check = QCheckBox("Stop after this rule matched")
        form.addRow("Rule name:", self.name_edit)
        form.addRow("", self.stop_check)
        rl.addLayout(form)
        rl.addWidget(QLabel("Conditions (all must be true)"))
        self.cond_table = make_table(["Target column", "Operator", "Value / regex"])
        self.cond_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.cond_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.cond_table.setColumnWidth(0, 230)
        self.cond_table.setColumnWidth(1, 150)
        rl.addWidget(self.cond_table)
        ca, cr = QPushButton("Add condition"), QPushButton("Remove condition")
        ca.clicked.connect(lambda: self.add_cond_row({"column": "A", "op": "contains", "value": ""}))
        cr.clicked.connect(lambda: remove_selected_row(self.cond_table))
        rl.addWidget(hbox(ca, cr))
        rl.addWidget(QLabel("Then write"))
        self.asg_table = make_table(["Target column", "Value or template"])
        self.asg_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.asg_table.setColumnWidth(0, 230)
        rl.addWidget(self.asg_table)
        legend = QLabel(ASG_LEGEND)
        legend.setWordWrap(True)
        legend.setStyleSheet("color: gray;")
        rl.addWidget(legend)
        aa, ar = QPushButton("Add value"), QPushButton("Remove value")
        lookup = QPushButton("Set lookup...")
        lookup.setToolTip("Set the selected value to a lookup in another row of the same connector.")
        aa.clicked.connect(lambda: self.add_asg_row({"column": "N", "value": ""}))
        ar.clicked.connect(lambda: remove_selected_row(self.asg_table))
        lookup.clicked.connect(self.set_lookup)
        rl.addWidget(hbox(aa, ar, lookup))
        split.addWidget(right)
        split.setStretchFactor(1, 3)
        outer.addWidget(split, 1)

    # --- column choices
    def col_choices(self):
        return [(f"{engine.target_letter(i)} - {t['header']}", engine.target_letter(i))
                for i, t in enumerate(self.main.cfg["target_columns"])]

    def add_cond_row(self, c):
        r = self.cond_table.rowCount()
        self.cond_table.insertRow(r)
        self.cond_table.setCellWidget(r, 0, combo_with(self.col_choices(), c["column"].upper()))
        self.cond_table.setCellWidget(r, 1, combo_with([(o, o) for o in engine.OPS], c["op"]))
        self.cond_table.setItem(r, 2, item(c["value"]))

    def add_asg_row(self, a):
        r = self.asg_table.rowCount()
        self.asg_table.insertRow(r)
        self.asg_table.setCellWidget(r, 0, combo_with(self.col_choices(), a["column"].upper()))
        it = item(a["value"])
        it.setToolTip(ASG_LEGEND)
        self.asg_table.setItem(r, 1, it)

    def set_lookup(self):
        row = self.asg_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Lookup", "Select a value in 'Then write' first.")
            return
        value = self.asg_table.item(row, 1)
        dialog = LookupDialog(self, self.col_choices(), value.text())
        if dialog.exec() == QDialog.Accepted:
            value.setText(dialog.template())

    # --- rule list handling
    def refresh_list(self, select=0):
        self.loading = True
        self.list.clear()
        for r in self.rules:
            it = QListWidgetItem(r["name"])
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if r.get("enabled", True) else Qt.Unchecked)
            self.list.addItem(it)
        self.loading = False
        self.cur = -1
        if self.rules:
            self.list.setCurrentRow(min(select, len(self.rules) - 1))
        else:
            self.show_rule(None)

    def show_rule(self, rule):
        self.loading = True
        self.cond_table.setRowCount(0)
        self.asg_table.setRowCount(0)
        if rule is None:
            self.name_edit.clear()
            self.stop_check.setChecked(True)
        else:
            self.name_edit.setText(rule["name"])
            self.stop_check.setChecked(rule.get("stop", True))
            for c in rule["conditions"]:
                self.add_cond_row(c)
            for a in rule["assignments"]:
                self.add_asg_row(a)
        self.loading = False

    def commit_current(self):
        """Write the editor widgets back into self.rules[self.cur]."""
        if self.cur < 0 or self.cur >= len(self.rules):
            return
        r = self.rules[self.cur]
        r["name"] = self.name_edit.text().strip() or f"Rule {self.cur + 1}"
        r["stop"] = self.stop_check.isChecked()
        r["conditions"] = [
            {"column": self.cond_table.cellWidget(i, 0).currentData(),
             "op": self.cond_table.cellWidget(i, 1).currentData(),
             "value": self.cond_table.item(i, 2).text()}
            for i in range(self.cond_table.rowCount())]
        r["assignments"] = [
            {"column": self.asg_table.cellWidget(i, 0).currentData(),
             "value": self.asg_table.item(i, 1).text()}
            for i in range(self.asg_table.rowCount())]
        for i in range(self.list.count()):
            if i < len(self.rules):
                self.rules[i]["enabled"] = self.list.item(i).checkState() == Qt.Checked
        self.list.item(self.cur).setText(r["name"])

    def on_select(self, row):
        if self.loading:
            return
        self.commit_current()
        self.cur = row
        self.show_rule(self.rules[row] if 0 <= row < len(self.rules) else None)

    def add_rule(self):
        self.commit_current()
        self.rules.append({"name": "New rule", "enabled": True, "stop": True,
                           "conditions": [{"column": "B", "op": "contains", "value": ""}],
                           "assignments": [{"column": "N", "value": ""}]})
        self.refresh_list(len(self.rules) - 1)

    def dup_rule(self):
        self.commit_current()
        if self.cur >= 0:
            c = copy.deepcopy(self.rules[self.cur])
            c["name"] += " (copy)"
            self.rules.insert(self.cur + 1, c)
            self.refresh_list(self.cur + 1)

    def del_rule(self):
        if self.cur >= 0 and QMessageBox.question(self, "Delete rule", "Delete this rule?") == QMessageBox.Yes:
            del self.rules[self.cur]
            self.cur = -1
            self.refresh_list(0)

    def move_rule(self, d):
        self.commit_current()
        n = self.cur + d
        if self.cur < 0 or n < 0 or n >= len(self.rules):
            return
        self.rules[self.cur], self.rules[n] = self.rules[n], self.rules[self.cur]
        self.refresh_list(n)

    # --- cfg <-> widgets
    def load_from_cfg(self, cfg):
        self.rules = copy.deepcopy(cfg["rules"])
        self.refresh_list(0)

    def commit_to_cfg(self, cfg):
        self.commit_current()
        cfg["rules"] = copy.deepcopy(self.rules)


# ----------------------------------------------------------------------------
# Main window
# ----------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1150, 800)
        self.cfg = engine.default_config()
        self.cfg_path = None

        self.tabs = QTabWidget()
        self.run_tab = RunTab(self)
        self.source_tab = SourceTab(self)
        self.map_tab = MappingTab(self)
        self.rules_tab = RulesTab(self)
        self.tabs.addTab(self.run_tab, "Run")
        self.tabs.addTab(self.source_tab, "Source && Tabs")
        self.tabs.addTab(self.map_tab, "Column Mapping")
        self.tabs.addTab(self.rules_tab, "Fill Rules")
        # One connector list for both pages: share the items and keep the selection in sync
        self.rules_tab.test_conn_combo.setModel(self.run_tab.conn_combo.model())
        self.run_tab.conn_combo.currentIndexChanged.connect(self.rules_tab.test_conn_combo.setCurrentIndex)
        self.rules_tab.test_conn_combo.currentIndexChanged.connect(self.run_tab.conn_combo.setCurrentIndex)

        central = QWidget()
        cl = QVBoxLayout(central)
        cl.addWidget(self.tabs, 1)
        self.save_btn = QPushButton("Save")
        self.save_btn.setToolTip("Save the settings (Run, Source && Tabs, Column Mapping, Fill Rules) to the configuration file.")
        self.save_btn.clicked.connect(self.save_cfg)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setToolTip("Discard the edits made since the last save and reload the saved settings "
                                   "(the built-in defaults if nothing was saved yet).")
        self.cancel_btn.clicked.connect(self.cancel_changes)
        self.defaults_btn = QPushButton("Reset")
        self.defaults_btn.setToolTip("Re-read the loaded configuration file (built-in defaults if none is loaded).")
        self.defaults_btn.clicked.connect(self.reset_cfg)
        bar = QHBoxLayout()
        bar.addWidget(self.defaults_btn)
        bar.addStretch()
        bar.addWidget(self.cancel_btn)
        bar.addWidget(self.save_btn)
        cl.addLayout(bar)
        self.setCentralWidget(central)
        self.last_tab = 0
        self.tabs.currentChanged.connect(self.on_tab_changed)

        m = self.menuBar().addMenu("&Configuration")
        for text, fn in (("Load config file...", self.open_cfg), ("Save", self.save_cfg),
                         ("Save as...", self.save_cfg_as), ("Reset (reload file)", self.reset_cfg),
                         ("Built-in defaults", self.defaults_cfg)):
            a = QAction(text, self)
            a.triggered.connect(fn)
            m.addAction(a)

        if USER_CONFIG.is_file():
            try:
                self.cfg = engine.load_config(USER_CONFIG)
                self.cfg_path = USER_CONFIG
            except Exception as e:
                QMessageBox.warning(self, "Configuration", f"Could not read {USER_CONFIG}:\n{e}\nUsing defaults.")
        self.load_all()

    # --- config <-> widgets
    def load_all(self, snapshot=True):
        self.run_tab.file_tpl.setText(self.cfg["file_name_template"])
        self.source_tab.load_from_cfg(self.cfg)
        self.map_tab.load_from_cfg(self.cfg)
        self.rules_tab.load_from_cfg(self.cfg)
        self.setWindowTitle("Connector Targets - " + (str(self.cfg_path) if self.cfg_path else "default configuration"))
        self.source_tab.cfg_label.setText(str(self.cfg_path) if self.cfg_path
                                          else "Built-in defaults (not saved to a file yet)")
        if snapshot:
            self.take_snapshot()

    def take_snapshot(self):
        """Remember the configuration as 'saved', to detect unsaved edits and to restore it on Cancel."""
        try:
            self.commit_all()
        except Exception:
            pass
        self._saved_cfg = copy.deepcopy(self.cfg)

    def commit_all(self):
        self.cfg["file_name_template"] = self.run_tab.file_tpl.text()
        self.source_tab.commit_to_cfg(self.cfg)
        self.map_tab.fields = self.cfg["source_fields"]
        self.map_tab.commit_to_cfg(self.cfg)
        self.rules_tab.commit_to_cfg(self.cfg)

    def commit_ok(self, silent=False):
        try:
            self.commit_all()
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "Settings", f"Cannot read the settings:\n{e}")
            return False
        errors = engine.validate_config(self.cfg)
        if errors:
            if not silent:
                QMessageBox.warning(self, "Settings need attention", "\n".join(errors[:15]))
            return False
        return True

    def on_tab_changed(self, idx):
        # Save what was edited, then refresh pages that depend on other pages.
        try:
            self.commit_all()
        except Exception:
            pass
        if idx == 2:
            self.map_tab.load_from_cfg(self.cfg)
        elif idx == 3:
            self.rules_tab.refresh_list(max(self.rules_tab.cur, 0))
        self.last_tab = idx

    # --- menu actions
    def open_cfg(self):
        start = str(self.cfg_path.parent) if self.cfg_path else str(APP_DIR)
        p, _ = QFileDialog.getOpenFileName(self, "Load configuration file", start, "JSON (*.json)")
        if p:
            try:
                self.cfg = engine.load_config(p)
            except Exception as e:
                QMessageBox.critical(self, "Configuration", str(e))
                return
            self.cfg_path = Path(p)
            self.load_all()

    def save_cfg(self):
        if not self.commit_ok():
            return
        if self.cfg_path is None:
            return self.save_cfg_as()
        engine.save_config(self.cfg, self.cfg_path)
        self._saved_cfg = copy.deepcopy(self.cfg)
        self.statusBar().showMessage(f"Saved {self.cfg_path}", 4000)

    def save_cfg_as(self):
        if not self.commit_ok():
            return
        p, _ = QFileDialog.getSaveFileName(self, "Save configuration", str(USER_CONFIG), "JSON (*.json)")
        if p:
            self.cfg_path = Path(p)
            engine.save_config(self.cfg, self.cfg_path)
            self._saved_cfg = copy.deepcopy(self.cfg)
            self.setWindowTitle("Connector Targets - " + p)

    def cancel_changes(self):
        """Throw away unsaved edits: reload the last saved configuration (built-in defaults if none)."""
        if not self.has_unsaved_changes():
            self.statusBar().showMessage("No unsaved changes", 3000)
            return
        if QMessageBox.question(self, "Cancel changes", "Discard all unsaved changes?") != QMessageBox.Yes:
            return
        self.cfg = copy.deepcopy(self._saved_cfg)
        self.load_all(snapshot=False)
        self.statusBar().showMessage("Unsaved changes discarded", 4000)

    def has_unsaved_changes(self) -> bool:
        try:
            self.commit_all()
        except Exception:
            return True
        return self.cfg != self._saved_cfg

    def reset_cfg(self):
        """Re-read the loaded configuration file (built-in defaults if no file is loaded)."""
        if self.cfg_path is None or not Path(self.cfg_path).is_file():
            return self.defaults_cfg()
        if QMessageBox.question(self, "Reset", f"Reload all settings from\n{self.cfg_path}?\n"
                                "Unsaved changes will be lost.") != QMessageBox.Yes:
            return
        try:
            self.cfg = engine.load_config(self.cfg_path)
        except Exception as e:
            QMessageBox.critical(self, "Configuration", str(e))
            return
        self.load_all()
        self.statusBar().showMessage(f"Reloaded {self.cfg_path}", 4000)

    def defaults_cfg(self):
        if QMessageBox.question(self, "Defaults", "Replace all settings with the built-in defaults?\n"
                                "(Press Save afterwards to keep them.)") == QMessageBox.Yes:
            self.cfg = engine.default_config()
            self.load_all(snapshot=False)

    def closeEvent(self, ev):
        if self.has_unsaved_changes():
            ans = QMessageBox.question(
                self, "Unsaved changes", "Save the changes before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
            if ans == QMessageBox.Cancel:
                ev.ignore()
                return
            if ans == QMessageBox.Save:
                self.save_cfg()
                if self.has_unsaved_changes():  # save was refused (invalid settings or dialog cancelled)
                    ev.ignore()
                    return
        super().closeEvent(ev)


EXTRA_QSS = """
QWidget { background: #1f2328; }
QTabWidget::pane { border: 1px solid #30363d; background: #1f2328; }
QTabBar::tab { background: #2a3038; color: #c9d1d9; padding: 6px 14px; border: 1px solid #30363d; border-bottom: none; }
QTabBar::tab:selected { background: #2f65d9; color: #ffffff; }
QTabBar::tab:hover:!selected { background: #333a45; }
QMenuBar { background: #1b222b; color: #e6edf3; }
QMenuBar::item:selected, QMenu::item:selected { background: #2f65d9; color: #ffffff; }
QMenu { background: #23272e; color: #e6edf3; border: 1px solid #30363d; }
QPlainTextEdit, QTextEdit, QListWidget, QTableWidget, QTreeWidget {
    background: #0b0f14; color: #e6edf3; border: 1px solid #30363d; selection-background-color: #2f65d9;
}
QListWidget::item:selected { background: #2f65d9; color: #ffffff; }
QLabel, QCheckBox, QGroupBox { background: transparent; }
QSplitter::handle { background: #30363d; }
QTableWidget QComboBox { padding: 0px 6px; border-radius: 4px; min-height: 20px; }
QTableWidget QComboBox::drop-down { width: 20px; }
QTableWidget QLineEdit {
    padding: 0px 4px; border-radius: 2px; min-height: 18px;
    background: #f8fafc; color: #0f172a; selection-background-color: #2f65d9; selection-color: #ffffff;
}
"""


def load_dark_style(app):
    """Apply the same Fusion + dark.css look as the IO Tester engineering UI."""
    app.setStyle("Fusion")
    candidates = [
        Path(sys.argv[0]).resolve().parent / "config" / "dark.css",
        APP_DIR.parent / "ui" / "Styles" / "dark.css",
        APP_DIR / "dark.css",
    ]
    base = ""
    for qss in candidates:
        if qss.is_file():
            base = qss.read_text(encoding="utf-8")
            break
    # Extra rules go first so dark.css keeps priority for the widgets it styles
    app.setStyleSheet(EXTRA_QSS + base)


def main():
    app = QApplication(sys.argv)
    load_dark_style(app)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
