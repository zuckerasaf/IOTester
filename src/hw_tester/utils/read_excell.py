"""
Utility functions for reading Excel files and creating connector/pin objects.
"""
from pathlib import Path
from typing import Optional, Dict
import openpyxl
import yaml

from ..hardware.pin import Pin, Connector


def _column_letter_to_index(column_letter: str) -> int:
    """Convert Excel column letter (A, B, C, etc.) to 0-based index."""
    column_letter = column_letter.upper()
    result = 0
    for char in column_letter:
        result = result * 26 + (ord(char) - ord('A') + 1)
    return result - 1


def _load_excel_column_config(settings_path: Optional[str] = None) -> Dict[str, int]:
    """
    Load Excel column configuration from settings.yaml.
    
    Returns:
        Dictionary mapping property names to 0-based column indices
    """
    if settings_path is None:
        project_root = Path(__file__).resolve().parents[3]
        settings_path = project_root / "src" / "hw_tester" / "config" / "settings.yaml"
    else:
        settings_path = Path(settings_path)
    
    if not settings_path.exists():
        # Return default column mapping if settings not found
        return {
            'Id': 1,                    # B
            'Connect': 2,               # C
            'Type': 5,                  # F
            'Power_Expected': 7,        # H
            'Power_Input': 8,           # I
            'PullUp_Expected': 9,       # J
            'Logic_Pin_Input': 10,      # K
            'Test_Result': 11           # L
        }
    
    with open(settings_path, 'r') as f:
        settings = yaml.safe_load(f)
    
    excel_cols = settings.get('ExcelColumns', {})
    
    return {
        'Id': _column_letter_to_index(excel_cols.get('ID', 'B')),
        'Connect': _column_letter_to_index(excel_cols.get('Connect', 'C')),
        'Type': _column_letter_to_index(excel_cols.get('Type', 'F')),
        'Power_Expected': _column_letter_to_index(excel_cols.get('Power_Expected', 'H')),
        'Power_Input': _column_letter_to_index(excel_cols.get('Power_Input', 'I')),
        'PullUp_Expected': _column_letter_to_index(excel_cols.get('PullUp_Expected', 'J')),
        'Logic_Pin_Input': _column_letter_to_index(excel_cols.get('Logic_Pin_Input', 'K')),
        'Test_Result': _column_letter_to_index(excel_cols.get('Test_Result', 'L'))
    }


def load_connector_from_excel(
    file_name: str = "J17_Armant.xlsx",
    db_path: str = "tests/DB",
    connector_id: str = "J17",
    sheet_name: Optional[str] = None,
    settings_path: Optional[str] = None
) -> Connector:
    """
    Read an Excel file and create a Connector with pins.
    
    Args:
        file_name: Name of the Excel file (default: "J17_Armant.xlsx")
        db_path: Path to the database folder (default: "tests/DB")
        connector_id: ID for the connector (default: "J17")
        sheet_name: Name of the sheet to read (default: first sheet)
        settings_path: Path to settings.yaml (default: auto-detected)
    
    Returns:
        Connector object populated with pins from the Excel file
    
    Raises:
        FileNotFoundError: If the Excel file doesn't exist
        ValueError: If the Excel file format is invalid
    
    Excel columns are configured in settings.yaml under ExcelColumns section.
    Data starts from row 2 (row 1 is assumed to be header).
    """
    # Load column configuration from settings
    col_map = _load_excel_column_config(settings_path)
    
    # Build the full path to the Excel file
    # If db_path is absolute, use it directly; otherwise, resolve from project root
    db_path_obj = Path(db_path)
    if db_path_obj.is_absolute():
        excel_path = db_path_obj / file_name
    else:
        project_root = Path(__file__).resolve().parents[3]
        excel_path = project_root / db_path / file_name
    
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    
    # Load the workbook and get the sheet
    workbook = openpyxl.load_workbook(excel_path, data_only=True)
    sheet = workbook[sheet_name] if sheet_name else workbook.active
    
    # Create the connector
    connector = Connector(id=connector_id)
    
    # Read data starting from row 2 (skip header)
    for row in sheet.iter_rows(min_row=2, values_only=True):
        # Read values from configured columns
        pin_id = row[col_map['Id']] if len(row) > col_map['Id'] else None
        connect = row[col_map['Connect']] if len(row) > col_map['Connect'] else None
        pin_type_str = row[col_map['Type']] if len(row) > col_map['Type'] else None
        power_expected = row[col_map['Power_Expected']] if len(row) > col_map['Power_Expected'] else None
        power_input = row[col_map['Power_Input']] if len(row) > col_map['Power_Input'] else None
        pullup_expected = row[col_map['PullUp_Expected']] if len(row) > col_map['PullUp_Expected'] else None
        logic_pin_input = row[col_map['Logic_Pin_Input']] if len(row) > col_map['Logic_Pin_Input'] else None
        
        # Skip empty rows or rows without pin ID
        if not pin_id:
            continue
        
        # Convert to string and strip whitespace
        pin_id = str(pin_id).strip()
        connect = str(connect).strip() if connect else ""
        pin_type_str = str(pin_type_str).strip() if pin_type_str else ""
        
        # Parse power input - keep as string from Excel
        power_input_value = str(power_input).strip() if power_input else ""
        
        # Parse power expected voltage
        try:
            power_expected_value = float(power_expected) if power_expected else 0.0
        except (ValueError, TypeError):
            power_expected_value = 0.0
        
        # Parse pullup expected voltage
        try:
            pullup_expected_value = float(pullup_expected) if pullup_expected else 0.0
        except (ValueError, TypeError):
            pullup_expected_value = 0.0
        
        # Parse logic pin input - keep as string from Excel
        logic_pin_input_value = str(logic_pin_input).strip() if logic_pin_input else ""
        
        # Create pin with new structure
        pin = Pin(
            Id=pin_id,
            Connect=connect,
            Type=pin_type_str,
            Power_Expected=power_expected_value,
            Power_Measured=0.0,
            Power_Result=False,
            PullUp_Expected=pullup_expected_value,
            PullUp_Measured=0.0,
            PullUp_Result=False,
            Power_Input=power_input_value,
            Logic_Pin_Input=logic_pin_input_value,
            Logic_DI_Result=False
        )
        
        connector.add_pin(pin)
    
    workbook.close()
    
    return connector
