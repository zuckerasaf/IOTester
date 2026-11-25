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
        saved_cfg = connector_app.engine.load_config(config_path)
        self.assertEqual(saved_cfg["file_name_template"], "V1_{conn}.xlsx")
        self.assertNotIn("connector_field", saved_cfg)
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

    def test_saving_existing_configuration_requires_confirmation(self):
        config_path = self.path / "config.json"
        config_path.write_text("existing configuration", encoding="utf-8")
        self.window.cfg_path = config_path

        with patch.object(QMessageBox, "question", side_effect=[QMessageBox.No, QMessageBox.Yes]) as confirm:
            self.window.save_cfg()
            self.assertEqual(config_path.read_text(encoding="utf-8"), "existing configuration")
            self.window.save_cfg()

        self.assertEqual(confirm.call_count, 2)
        self.assertIn('"file_name_template"', config_path.read_text(encoding="utf-8"))

    def test_generating_over_existing_output_requires_confirmation(self):
        workbook = Workbook()
        workbook.active.title = "Spider Card #1"
        workbook.active["E7"] = "J1"
        for sheet_name in ("Spider Card #2", "Spider Card #3", "Spider Card #4"):
            workbook.create_sheet(sheet_name)
        source = self.path / "source.xlsx"
        workbook.save(source)
        output = self.path / "output"
        output.mkdir()
        existing_target = output / "Target_J1.xlsx"
        existing_target.write_text("existing output", encoding="utf-8")
        self.window.run_tab.source_edit.setText(str(source))
        self.window.run_tab.out_edit.setText(str(output))

        with patch.object(QMessageBox, "question", return_value=QMessageBox.No) as confirm:
            self.window.run_tab.do_run()

        self.assertTrue(confirm.called)
        self.assertIn(str(existing_target), confirm.call_args.args[2])
        self.assertEqual(existing_target.read_text(encoding="utf-8"), "existing output")
        self.assertIsNone(self.window.run_tab.thread)

    def test_connector_column_comes_from_conn_source_field_row(self):
        source_tab = self.window.source_tab
        self.assertFalse(hasattr(source_tab, "conn_field"))
        self.assertEqual(source_tab.field_table.horizontalHeaderItem(0).text(),
                         "Key (use 'conn' for Connector)")
        conn_row = next(
            row for row in range(source_tab.field_table.rowCount())
            if source_tab.field_table.item(row, 0).text() == "conn"
        )
        source_tab.field_table.item(conn_row, 2).setText("G")
        source_tab.commit_to_cfg(self.window.cfg)
        self.window.cfg["source_sheets"] = ["Spider Card #1"]
        self.assertNotIn("connector_field", self.window.cfg)

        workbook = Workbook()
        workbook.active.title = "Spider Card #1"
        workbook.active["E7"] = "not a connector"
        workbook.active["G7"] = "J20"
        source = self.path / "source.xlsx"
        workbook.save(source)

        connector_app.engine.run(source, self.path, self.window.cfg)
        self.assertTrue((self.path / "Target_J20.xlsx").is_file())

    def test_empty_connector_list_logs_source_tabs_hint(self):
        source = self.path / "source.xlsx"
        source.touch()
        self.window.run_tab.source_edit.setText(str(source))

        with patch.object(connector_app.engine, "list_connectors", return_value=[]):
            self.window.run_tab.refresh_connectors(silent=True)

        self.assertIn("No connector loaded - see Source & Tabs.",
                      self.window.run_tab.log.toPlainText())

    def test_load_source_logs_hint_when_no_source_tabs_are_selected(self):
        workbook = Workbook()
        workbook.active.title = "Different tab name"
        source = self.path / "source.xlsx"
        workbook.save(source)
        self.window.run_tab.source_edit.setText(str(source))

        self.window.run_tab.load_source()

        log = self.window.run_tab.log.toPlainText()
        self.assertIn("Loaded 1 tab(s): Different tab name", log)
        self.assertIn("No connector loaded - see Source & Tabs.", log)
        self.assertEqual(self.window.run_tab.conn_combo.count(), 0)

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
