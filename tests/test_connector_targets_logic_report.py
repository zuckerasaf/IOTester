import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook, load_workbook

with patch.object(sys, "path", [str(Path(__file__).resolve().parents[1] / "src" / "hw_tester" /
                                     "connector_targets_app")] + sys.path):
    from hw_tester.connector_targets_app import engine


class LogicReportTests(unittest.TestCase):
    def test_reports_expected_values_with_empty_input_after_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Spider Card #1"
            for row in range(7, 14):
                sheet[f"E{row}"] = "J10"
            sheet["B7"] = "RULE"
            sheet["C8"], sheet["H8"] = "expected", 13
            sheet["C10"] = 0
            sheet["C11"], sheet["H11"] = " ", " "
            sheet["C12"], sheet["H12"] = "expected", 0
            sheet["C13"], sheet["H13"] = "expected", " "
            source = path / "source.xlsx"
            workbook.save(source)

            cfg = engine.default_config()
            cfg["source_sheets"] = [sheet.title]
            cfg["target_columns"][17]["source"] = "plug"
            cfg["target_columns"][19]["source"] = "signal"
            cfg["rules"] = [{
                "name": "Set expected", "enabled": True, "stop": True,
                "conditions": [{"column": "B", "op": "equals", "value": "RULE"}],
                "assignments": [{"column": "T", "value": "C5_DI33_0"}],
            }]
            result = engine.run(source, path, cfg, log=lambda _: None)

            target = load_workbook(path / "Target_J10.xlsx", data_only=True)
            self.assertEqual(target.active["T2"].value, "C5_DI33_0")
            self.assertIsNone(target.active["R2"].value)
            self.assertEqual(target.active["R7"].value, 0)
            target.close()
            issues = load_workbook(path / "Open_Issues.xlsx", data_only=True)
            entries = [row for row in issues.active.iter_rows(min_row=2, values_only=True)
                       if row[1] == engine.ISSUE_MISSING_LOGIC_INPUT]
            self.assertEqual([row[4] for row in entries], [7, 10, 13])
            self.assertIn("Target_J10.xlsx: row 2, column T = C5_DI33_0", entries[0][-2])
            self.assertIn("row 5, column T = 0", entries[1][-2])
            issues.close()
            self.assertIn("Missing logic input details:", result["report"])
            self.assertIn("source Spider Card #1, row 13", result["report"])
            self.assertIn("Target_J10.xlsx: row 2", result["report"])

    def test_missing_target_column_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            workbook = Workbook()
            workbook.active.title = "Spider Card #1"
            workbook.active["E7"] = "J10"
            source = path / "source.xlsx"
            workbook.save(source)
            cfg = engine.default_config()
            cfg["source_sheets"] = ["Spider Card #1"]
            cfg["target_columns"] = cfg["target_columns"][:19]
            cfg["rules"] = []
            result = engine.run(source, path, cfg, log=lambda _: None)
            self.assertIn("Missing logic input check skipped", result["report"])


if __name__ == "__main__":
    unittest.main()
