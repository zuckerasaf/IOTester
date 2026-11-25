import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from hw_tester.utils.report_status import normalize_report_status, read_report_status


class ReportStatusTests(unittest.TestCase):
    def test_reads_status_from_workbook_comments_property(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.xlsx"
            workbook = Workbook()
            workbook.properties.description = "Not Complete"
            workbook.save(path)

            self.assertEqual(read_report_status(path), "Not Complete")

    def test_ignores_unknown_metadata_status(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.xlsx"
            workbook = Workbook()
            workbook.properties.description = "Review needed"
            workbook.save(path)

            self.assertIsNone(read_report_status(path))

        for suffix, status in (
            ("Pass", "Pass"),
            ("Fail", "Fail"),
            ("Not_Complete", "Not Complete"),
        ):
            with self.subTest(suffix=suffix):
                self.assertEqual(normalize_report_status(suffix), status)


if __name__ == "__main__":
    unittest.main()
