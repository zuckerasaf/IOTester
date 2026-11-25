import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook, load_workbook

with patch.object(sys, "path", [str(Path(__file__).resolve().parents[1] / "src" / "hw_tester" /
                                     "connector_targets_app")] + sys.path):
    from hw_tester.connector_targets_app import engine


class TextReportTests(unittest.TestCase):
    def test_tbd_details_are_listed_and_empty_connector_rows_are_omitted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Spider Card #1"
            sheet["B7"], sheet["E7"] = "DI", "J10"
            sheet["C8"] = "No connector"
            sheet["B9"], sheet["E9"] = "DI", "J11"
            source = path / "source.xlsx"
            workbook.save(source)

            cfg = engine.default_config()
            cfg["source_sheets"] = [sheet.title]
            cfg["rules"] = [{
                "name": "DI", "enabled": True, "stop": True,
                "conditions": [{"column": "B", "op": "equals", "value": "DI"}],
                "assignments": [{"column": "R", "value": "TBD_DI"},
                                {"column": "O", "value": "TBD_POWER"}],
            }]
            result = engine.run(source, path, cfg, log=lambda _: None)

            self.assertNotIn(engine.ISSUE_TBD, result["report"])
            self.assertIn("TBD value details:", result["report"])
            for name in ("Target_J10.xlsx", "Target_J11.xlsx"):
                self.assertIn(f"{name}: row 2, column R (logic_input) = TBD_DI", result["report"])
                self.assertIn(f"{name}: row 2, column O (Power_Input) = TBD_POWER", result["report"])
            self.assertEqual((path / "run_report.txt").read_text(encoding="utf-8").strip(),
                             result["report"])

            issues = load_workbook(path / "Open_Issues.xlsx", data_only=True)
            issue_rows = list(issues.active.iter_rows(min_row=2, values_only=True))
            types = [row[1] for row in issue_rows]
            self.assertNotIn(8, [row[4] for row in issue_rows])
            self.assertNotIn("No connector", [value for row in issue_rows for value in row])
            self.assertEqual(types.count(engine.ISSUE_TBD), 4)
            issues.close()


if __name__ == "__main__":
    unittest.main()
