"""
Doc Handle - Word report generation for HW Tester.
"""
from __future__ import annotations

from pathlib import Path
from copy import deepcopy
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import openpyxl
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from tkinter import filedialog


DEFAULT_OUTPUT_DIR = Path(r"C:\ArduinoProject\IO_Tester\tests\Results")
DEFAULT_GENERAL_DATA_PATH = DEFAULT_OUTPUT_DIR / "general_data.docx"


def _parse_filename_details(file_path: Path) -> Tuple[str, str]:
	"""Extract connector name and test date/time string from file name."""
	stem_parts = file_path.stem.split("_")
	if len(stem_parts) >= 3:
		date_part = stem_parts[-2]
		time_part = stem_parts[-1]
		if date_part.isdigit() and time_part.isdigit() and len(date_part) == 8 and len(time_part) == 6:
			connector_name = "_".join(stem_parts[:-2])
			try:
				dt = datetime.strptime(f"{date_part}_{time_part}", "%Y%m%d_%H%M%S")
				return connector_name, dt.strftime("%Y-%m-%d %H:%M:%S")
			except ValueError:
				pass

	return file_path.stem, "Unknown"


def _load_report_rows(file_path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
	"""Load report rows from Excel file."""
	wb = openpyxl.load_workbook(file_path, data_only=True)
	ws = wb.active

	rows = list(ws.iter_rows(values_only=True))
	wb.close()

	if not rows:
		return [], []

	headers = [str(h).strip() if h is not None else "" for h in rows[0]]
	headers = [h for h in headers if h]
	if not headers:
		return [], []

	data_rows: List[Dict[str, str]] = []
	for row in rows[1:]:
		row_dict: Dict[str, str] = {}
		for idx, header in enumerate(headers):
			value = row[idx] if idx < len(row) else ""
			row_dict[header] = "" if value is None else str(value)
		data_rows.append(row_dict)

	return headers, data_rows


def _analyze_report(rows: List[Dict[str, str]]) -> Tuple[str, Dict[str, Tuple[int, int]], int]:
	"""Return summary result, pass/total counts by test type, and not-tested count."""
	counts = {
		"power": [0, 0],
		"pullup": [0, 0],
		"logic": [0, 0],
	}
	not_tested = 0
	any_fail = False

	for row in rows:
		power_result = row.get("Power_Result", "")
		pullup_result = row.get("PullUp_Result", "")
		logic_result = row.get("Logic_DI_Result", "")

		results = [power_result, pullup_result, logic_result]
		has_pass_fail = any(r in ("Pass", "Fail") for r in results)

		if not has_pass_fail:
			not_tested += 1

		if power_result in ("Pass", "Fail"):
			counts["power"][1] += 1
			if power_result == "Pass":
				counts["power"][0] += 1
			else:
				any_fail = True

		if pullup_result in ("Pass", "Fail"):
			counts["pullup"][1] += 1
			if pullup_result == "Pass":
				counts["pullup"][0] += 1
			else:
				any_fail = True

		if logic_result in ("Pass", "Fail"):
			counts["logic"][1] += 1
			if logic_result == "Pass":
				counts["logic"][0] += 1
			else:
				any_fail = True

	if any_fail:
		summary = "FAIL"
	elif not_tested > 0:
		summary = "PARTIAL"
	else:
		summary = "PASS"

	return summary, {
		"power": (counts["power"][0], counts["power"][1]),
		"pullup": (counts["pullup"][0], counts["pullup"][1]),
		"logic": (counts["logic"][0], counts["logic"][1]),
	}, not_tested


def _add_field_run(paragraph, field_name: str):
	"""Add a Word field code (PAGE, NUMPAGES) to a paragraph."""
	run = paragraph.add_run()
	field_begin = OxmlElement("w:fldChar")
	field_begin.set(qn("w:fldCharType"), "begin")
	field_instr = OxmlElement("w:instrText")
	field_instr.set(qn("xml:space"), "preserve")
	field_instr.text = field_name
	field_sep = OxmlElement("w:fldChar")
	field_sep.set(qn("w:fldCharType"), "separate")
	field_end = OxmlElement("w:fldChar")
	field_end.set(qn("w:fldCharType"), "end")
	run._r.extend([field_begin, field_instr, field_sep, field_end])
	return run


def _set_run_style(run, size_pt: int, rgb: tuple[int, int, int]) -> None:
	"""Apply font size and color to a run."""
	run.font.size = Pt(size_pt)
	run.font.color.rgb = RGBColor(*rgb)


def _add_header_footer(doc: Document) -> None:
	"""Apply header/footer layout: left title, right date, right page numbering."""
	for section in doc.sections:
		header = section.header
		footer = section.footer

		# Clear default empty paragraph text.
		if header.paragraphs:
			header.paragraphs[0].text = ""
		if footer.paragraphs:
			footer.paragraphs[0].text = ""

		usable_width = section.page_width - section.left_margin - section.right_margin

		# Header table with two columns: title left, date right.
		header_table = header.add_table(rows=1, cols=2, width=usable_width)
		header_table.autofit = True
		left_cell, right_cell = header_table.rows[0].cells

		title_run = left_cell.paragraphs[0].add_run("IO Tester")
		_set_run_style(title_run, 12, (102, 153, 204))
		left_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT

		date_text = datetime.now().strftime("%Y-%m-%d")
		date_run = right_cell.paragraphs[0].add_run(date_text)
		_set_run_style(date_run, 10, (0, 0, 0))
		right_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT

		# Footer table: right aligned page numbering.
		footer_table = footer.add_table(rows=1, cols=1, width=usable_width)
		footer_table.autofit = True
		footer_paragraph = footer_table.rows[0].cells[0].paragraphs[0]
		footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT

		label_run = footer_paragraph.add_run("Page ")
		_set_run_style(label_run, 9, (128, 128, 128))
		page_run = _add_field_run(footer_paragraph, "PAGE")
		_set_run_style(page_run, 9, (128, 128, 128))
		mid_run = footer_paragraph.add_run(" of ")
		_set_run_style(mid_run, 9, (128, 128, 128))
		numpages_run = _add_field_run(footer_paragraph, "NUMPAGES")
		_set_run_style(numpages_run, 9, (128, 128, 128))


def _append_document_body(target: Document, source: Document) -> None:
	"""Append all body elements (paragraphs, tables) from source into target."""
	for element in source.element.body:
		if element.tag == qn("w:sectPr"):
			continue
		target.element.body.append(deepcopy(element))


def create_doc_report(report_files: List[Path], output_path: Path) -> Path:
	"""Create a Word document report from selected Excel files."""
	document = Document()
	_add_header_footer(document)
	if DEFAULT_GENERAL_DATA_PATH.exists():
		general_doc = Document(DEFAULT_GENERAL_DATA_PATH)
		_append_document_body(document, general_doc)
	else:
		document.add_paragraph("Section 1 text will be defined later.")

	document.add_paragraph("-------- start section 2 -----")

	document.add_paragraph("Section 2 text will be defined later.")
	document.add_paragraph("-------- end section 2 -----")

	document.add_paragraph("-------- start section 3 -----")

	summary_table = document.add_table(rows=1, cols=8)
	summary_table.style = "Table Grid"
	summary_table.autofit = False
	summary_col_widths = [
		Inches(0.35),
		Inches(0.9),
		Inches(1.7),
		Inches(0.9),
		Inches(0.7),
		Inches(0.7),
		Inches(0.7),
		Inches(0.7),
	]

	summary_headers = [
		"#",
		"Connector",
		"Test Date/Time",
		"Summary Result",
		"Power Result",
		"PullUp Result",
		"Logic Result",
		"Not Tested",
	]
	for idx, header in enumerate(summary_headers):
		summary_table.rows[0].cells[idx].text = header
		summary_table.rows[0].cells[idx].width = summary_col_widths[idx]

	for idx, file_path in enumerate(report_files, start=1):
		connector_name, test_datetime = _parse_filename_details(file_path)
		headers, rows = _load_report_rows(file_path)
		summary, counts, not_tested = _analyze_report(rows)

		row_cells = summary_table.add_row().cells
		row_cells[0].text = str(idx)
		row_cells[1].text = connector_name
		row_cells[2].text = test_datetime
		row_cells[3].text = summary
		row_cells[4].text = f"{counts['power'][0]}/{counts['power'][1]}"
		row_cells[5].text = f"{counts['pullup'][0]}/{counts['pullup'][1]}"
		row_cells[6].text = f"{counts['logic'][0]}/{counts['logic'][1]}"
		row_cells[7].text = str(not_tested)
		for col_idx, width in enumerate(summary_col_widths):
			row_cells[col_idx].width = width

	document.add_paragraph("-------- end section 3 -----")

	output_path.parent.mkdir(parents=True, exist_ok=True)
	document.save(output_path)
	return output_path


def select_report_files(initial_dir: Optional[Path] = None) -> List[Path]:
	"""Open file dialog to select Excel report files."""
	initial = initial_dir or DEFAULT_OUTPUT_DIR
	file_paths = filedialog.askopenfilenames(
		title="Select Report Excel Files",
		initialdir=str(initial),
		filetypes=[("Excel files", "*.xlsx")]
	)
	return [Path(path) for path in file_paths]


def prompt_output_path(default_dir: Optional[Path] = None) -> Optional[Path]:
	"""Prompt user for Word report output path."""
	initial = default_dir or DEFAULT_OUTPUT_DIR
	output_path = filedialog.asksaveasfilename(
		title="Save Word Report",
		initialdir=str(initial),
		defaultextension=".docx",
		filetypes=[("Word Document", "*.docx")],
		initialfile="IO_Tester_Report.docx"
	)
	return Path(output_path) if output_path else None


def create_doc_report_via_dialog() -> Optional[Path]:
	"""Select files via dialog and create the Word report."""
	report_files = select_report_files()
	if not report_files:
		return None

	output_path = prompt_output_path()
	if not output_path:
		return None

	return create_doc_report(report_files, output_path)
