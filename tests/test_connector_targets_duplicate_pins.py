import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook, load_workbook

with patch.object(sys, "path", [str(Path(__file__).resolve().parents[1] / "src" / "hw_tester" /
                                     "connector_targets_app")] + sys.path):
    from hw_tester.connector_targets_app import engine


class DuplicatePinReportTests(unittest.TestCase):
    def test_duplicates_are_reported_per_connector_with_source_and_target_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            workbook = Workbook()
            first = workbook.active
            first.title = "Spider Card #1"
            first["E7"], first["F7"] = "J10", 3
            first["E8"], first["F8"] = "J10", " A "
            first["E9"], first["F9"] = "J11", 3
            first["E10"] = "J10"
            second = workbook.create_sheet("Spider Card #2")
            second["E7"], second["F7"] = "J10", "3"
            second["E8"], second["F8"] = "J10", "a"
            second["E9"] = "J10"
            source = path / "source.xlsx"
            workbook.save(source)

            cfg = engine.default_config()
            cfg["source_sheets"] = [first.title, second.title]
            cfg["target_columns"][7], cfg["target_columns"][6] = (
                cfg["target_columns"][6], cfg["target_columns"][7])
            result = engine.run(source, path, cfg, log=lambda _: None, use_rules=False)

            target = load_workbook(path / "Target_J10.xlsx", data_only=True)
            self.assertEqual(target.active.max_row, 7)
            self.assertEqual(target.active["G1"].value, "Pin Out")
            target.close()
            issues = load_workbook(path / "Open_Issues.xlsx", data_only=True)
            entries = list(issues.active.iter_rows(min_row=2, values_only=True))
            self.assertEqual(len(entries), 4)
            self.assertTrue(all(entry[1] == engine.ISSUE_DUPLICATE_PIN for entry in entries))
            self.assertEqual([(entry[2], entry[4]) for entry in entries],
                             [(first.title, 7), (second.title, 7),
                              (first.title, 8), (second.title, 8)])
            self.assertTrue(all("Target_J10.xlsx" in entry[-2] for entry in entries))
            self.assertIn("duplicate target rows 2, 5", entries[0][-2])
            self.assertIn("duplicate target rows 3, 6", entries[2][-2])
            issues.close()
            self.assertIn("Duplicate Pin Out details:", result["report"])
            self.assertIn("source Spider Card #2, row 7", result["report"])
            self.assertEqual((path / "run_report.txt").read_text(encoding="utf-8").strip(),
                             result["report"])
            self.assertNotIn("Target_J11.xlsx: Pin Out", result["report"])

    def test_missing_pin_out_column_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            workbook = Workbook()
            workbook.active.title = "Spider Card #1"
            workbook.active["E7"] = "J10"
            source = path / "source.xlsx"
            workbook.save(source)
            cfg = engine.default_config()
            cfg["source_sheets"] = ["Spider Card #1"]
            cfg["target_columns"][7]["header"] = "Other"
            result = engine.run(source, path, cfg, log=lambda _: None, use_rules=False)
            self.assertIn("Duplicate Pin Out check skipped", result["report"])


if __name__ == "__main__":
    unittest.main()
