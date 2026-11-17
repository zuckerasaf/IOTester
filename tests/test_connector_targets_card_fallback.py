import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook, load_workbook

with patch.object(sys, "path", [str(Path(__file__).resolve().parents[1] / "src" / "hw_tester" /
                                     "connector_targets_app")] + sys.path):
    from hw_tester.connector_targets_app import engine


class CardFallbackTests(unittest.TestCase):
    def test_power_tab_uses_card_100_in_preview_and_generated_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            workbook = Workbook()
            power = workbook.active
            power.title = "POWER"
            power["B7"], power["E7"], power["F7"] = "DI_5", "J10", 1
            power["B8"], power["E8"], power["F8"] = "DI_6", "J10", 2
            card = workbook.create_sheet("CARD 3")
            card["B7"], card["E7"], card["F7"] = "DI_7", "J10", 3
            source = path / "source.xlsx"
            workbook.save(source)

            cfg = engine.default_config()
            cfg["source_sheets"] = ["POWER", "CARD 3"]
            cfg["card_regex"] = r"(\d+)"
            self.assertEqual(engine.list_connectors(source, cfg), ["J10"])
            _, rows = engine.preview(source, cfg, "J10")
            self.assertEqual([row[0] for row in rows], [100, 100, 3])
            self.assertEqual(rows[0][19], "C100_DI5_0")

            result = engine.run(source, path, cfg, log=lambda _: None)
            target = load_workbook(path / "Target_J10.xlsx", data_only=True)
            self.assertEqual(target.active["A2"].value, 100)
            self.assertEqual(target.active["T2"].value, "C100_DI5_0")
            self.assertEqual(target.active["A4"].value, 3)
            target.close()
            issues = load_workbook(path / "Open_Issues.xlsx", data_only=True)
            fallback = [row for row in issues.active.iter_rows(min_row=2, values_only=True)
                        if row[1] == engine.ISSUE_CARD_FALLBACK]
            self.assertEqual(len(fallback), 1)
            self.assertEqual(fallback[0][2:5], ("POWER", 100, None))
            self.assertIn("pattern", fallback[0][-2])
            issues.close()
            self.assertIn("POWER: 1 x " + engine.ISSUE_CARD_FALLBACK, result["report"])


if __name__ == "__main__":
    unittest.main()
