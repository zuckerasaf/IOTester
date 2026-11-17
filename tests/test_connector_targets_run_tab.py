import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook, load_workbook
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFormLayout, QMessageBox

with patch.object(sys, "path", [str(Path(__file__).resolve().parents[1] / "src" / "hw_tester" /
                                     "connector_targets_app")] + sys.path):
    from hw_tester.connector_targets_app import app as connector_app


class ConnectorTargetsUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_platform = patch.dict(os.environ, {"QT_QPA_PLATFORM": "offscreen"})
        cls.qt_platform.start()
        cls.qt_app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.qt_platform.stop()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.config_patch = patch.object(connector_app, "USER_CONFIG", self.path / "missing.json")
        self.config_patch.start()
        self.window = connector_app.MainWindow()

    def tearDown(self):
        self.window.cfg = self.window._saved_cfg.copy()
        self.window.load_all(snapshot=False)
        self.window.close()
        self.config_patch.stop()
        self.temp.cleanup()

    def test_target_filename_is_on_run_tab_saved_and_used(self):
        window = self.window
        form = window.run_tab.layout().itemAt(0).layout()
        self.assertIsInstance(form, QFormLayout)
        self.assertEqual(form.labelForField(window.run_tab.file_tpl).text(), "Target file name:")
        self.assertEqual(form.getWidgetPosition(window.run_tab.file_tpl)[0], 2)
        self.assertFalse(hasattr(window.source_tab, "file_tpl"))

        window.run_tab.file_tpl.setText("V1_{conn}.xlsx")
        window.tabs.setCurrentWidget(window.source_tab)
        self.assertTrue(window.has_unsaved_changes())
        config_path = self.path / "config.json"
        window.cfg_path = config_path
        window.save_cfg()
        self.assertEqual(connector_app.engine.load_config(config_path)["file_name_template"], "V1_{conn}.xlsx")
        self.assertFalse(window.has_unsaved_changes())

        window.run_tab.file_tpl.setText("Other_{conn}.xlsx")
        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
            window.cancel_changes()
        self.assertEqual(window.run_tab.file_tpl.text(), "V1_{conn}.xlsx")

        workbook = Workbook()
        workbook.active.title = "Spider Card #1"
        workbook.active["E7"] = "J10"
        source = self.path / "source.xlsx"
        workbook.save(source)
        window.cfg["source_sheets"] = ["Spider Card #1"]
        connector_app.engine.run(source, self.path, window.cfg)
        self.assertTrue((self.path / "V1_J10.xlsx").is_file())

    def test_lookup_editor_populates_rule_and_generated_connector_files(self):
        window = self.window
        window.cfg["source_sheets"] = ["Spider Card #1"]
        window.cfg["rules"] = [{
            "name": "DI return pin", "enabled": True, "stop": True,
            "conditions": [{"column": "B", "op": "code_number", "value": "DI"}],
            "assignments": [{"column": "R", "value": "TBD"}],
        }]
        window.load_all()
        rules = window.rules_tab
        rules.asg_table.selectRow(0)

        def fill_dialog():
            dialog = QApplication.activeModalWidget()
            dialog.search_value.setText(r"24V I\O RTN")
            dialog.accept()

        QTimer.singleShot(0, fill_dialog)
        rules.set_lookup()
        self.assertEqual(rules.asg_table.item(0, 1).text(), r"{H@J=24V I\O RTN}")
        window.cfg_path = self.path / "rules.json"
        window.save_cfg()
        saved = connector_app.engine.load_config(window.cfg_path)
        self.assertEqual(saved["rules"][0]["assignments"][0]["value"], r"{H@J=24V I\O RTN}")

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Spider Card #1"
        sheet["E7"], sheet["F7"], sheet["H7"] = "J12", 3, r"24V I\O RTN"
        sheet["B8"], sheet["E8"] = "DI_19", "J12"
        sheet["B9"], sheet["E9"] = "DI_20", "J13"
        source = self.path / "source.xlsx"
        workbook.save(source)
        connector_app.engine.run(source, self.path, window.cfg)

        j12 = load_workbook(self.path / "Target_J12.xlsx", data_only=True)
        j13 = load_workbook(self.path / "Target_J13.xlsx", data_only=True)
        self.assertEqual(j12.active["R3"].value, 3)
        self.assertIsNone(j13.active["R2"].value)
        j12.close()
        j13.close()

        dialog = connector_app.LookupDialog(rules, rules.col_choices(), r"{H@J==24V I\O RTN}")
        self.assertEqual(dialog.match_type.currentData(), "equals")
        self.assertEqual(dialog.template(), r"{H@J==24V I\O RTN}")


if __name__ == "__main__":
    unittest.main()
