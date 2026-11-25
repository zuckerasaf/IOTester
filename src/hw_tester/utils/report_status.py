"""Helpers for storing and reading report status in Excel file properties."""

from pathlib import Path
from typing import Optional
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

import openpyxl
from openpyxl.utils.exceptions import InvalidFileException


REPORT_STATUSES = {"Pass", "Fail", "Not Complete"}


def normalize_report_status(status: str) -> str:
    """Convert report filename suffix values to display and metadata labels."""
    normalized = status.strip().replace("_", " ")
    if normalized not in REPORT_STATUSES:
        raise ValueError(f"Unsupported report status: {status}")
    return normalized


def read_report_status(path: Path) -> Optional[str]:
    """Read the report status from the workbook's core description property."""
    try:
        workbook = openpyxl.load_workbook(path, read_only=True)
    except (OSError, BadZipFile, InvalidFileException, ParseError):
        return None

    try:
        status = workbook.properties.description
    finally:
        workbook.close()
    return status if status in REPORT_STATUSES else None
