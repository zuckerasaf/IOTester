"""
Qt PinTableView component - Displays pin data in a scrollable table.
Port of Tkinter PinTableView to Qt/PySide6 with enhanced features.
"""
from typing import List, Dict, Optional, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableView, QHeaderView,
    QLineEdit, QAbstractItemView, QStyledItemDelegate, QComboBox, QApplication
)
from PySide6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, Signal, Slot, QEvent
)
from PySide6.QtGui import QColor, QBrush, QFont

# Custom event for thread-safe row highlight — QApplication.postEvent is safe from any thread
_SET_TESTING_PIN_TYPE = QEvent.Type(QEvent.registerEventType())


class _SetTestingPinEvent(QEvent):
    """Carries a pin_id (or None to clear) across thread boundaries."""
    def __init__(self, pin_id: Optional[str]):
        super().__init__(_SET_TESTING_PIN_TYPE)
        self.pin_id = pin_id


class PinTableEditDelegate(QStyledItemDelegate):
    """Custom editor delegate to ensure edited values are always readable."""

    def paint(self, painter, option, index):
        # QStyleSheetStyle owns CE_ItemViewItem rendering when QTableView::item is in the
        # stylesheet. It draws nothing for the background (no CSS background set), so we
        # fill it manually first. The stylesheet then draws text/border on top without
        # overwriting this fill.
        bg = index.data(Qt.BackgroundRole)
        if bg is not None:
            painter.fillRect(option.rect, bg)
        super().paint(painter, option, index)

    def createEditor(self, parent, option, index):
        if not index.isValid():
            return super().createEditor(parent, option, index)

        # Only customize editors for editable cells.
        if not (index.flags() & Qt.ItemIsEditable):
            return super().createEditor(parent, option, index)

        editor = QLineEdit(parent)
        editor.setFrame(False)
        editor.setStyleSheet(
            "QLineEdit {"
            "background: #f8fafc;"
            "color: #0f172a;"
            "border: 1px solid #2563eb;"
            "border-radius: 7px;"
            "padding: 2px 6px;"
            "selection-background-color: #1d4ed8;"
            "selection-color: #ffffff;"
            "font-weight: 600;"
            "}"
        )
        editor.selectAll()
        return editor


class PinTableModel(QAbstractTableModel):
    """
    Custom table model for pin data with sorting and color coding support.
    """
    
    COLUMNS = (
        "ID", "Connect", "Discrete_Name", "Signal_Name", "Plug", "Type", "Pin",
        "Power_Expected", "Power_Input", "Power_Measured", "Power_Result", "Power_Result_Reason",
        "PullUp_Expected", "PullUp_Input", "PullUp_Measured", "PullUp_Result", "PullUp_Result_Reason",
        "Logic_Pin_Input", "Logic_Command", "Logic_Expected", "Logic_DI_Result", "Logic_DI_Result_Reason"
    )
    
    # Display names for headers (with newlines for wrapping)
    DISPLAY_NAMES = {
        "ID": "ID",
        "Connect": "Connect",
        "Discrete_Name": "Discrete\nName",
        "Signal_Name": "Signal\nName",
        "Plug": "Plug",
        "Type": "Type",
        "Pin": "Pin",
        "Power_Expected": "Power\nExpected",
        "Power_Input": "Power\nInput",
        "Power_Measured": "Power\nMeasured",
        "Power_Result": "Power\nResult",
        "Power_Result_Reason": "Power Result\nReason",
        "PullUp_Expected": "PullUp\nExpected",
        "PullUp_Input": "PullUp\nInput",
        "PullUp_Measured": "PullUp\nMeasured",
        "PullUp_Result": "PullUp\nResult",
        "PullUp_Result_Reason": "PullUp Result\nReason",
        "Logic_Pin_Input": "Logic Pin\nInput",
        "Logic_Command": "Logic\nCommand",
        "Logic_Expected": "Logic\nExpected",
        "Logic_DI_Result": "Logic DI\nResult",
        "Logic_DI_Result_Reason": "Logic DI Result\nReason"
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: List[List[str]] = []
        self._row_id_map: Dict[str, int] = {}  # Maps pin ID to row index
        self._sort_column = -1
        self._sort_order = Qt.AscendingOrder
        self._testing_pin_id: Optional[str] = None  # Currently testing pin ID
    
    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.COLUMNS)
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        
        row_data = self._rows[index.row()]
        col_idx = index.column()
        
        if role == Qt.DisplayRole or role == Qt.EditRole:
            # Always return strings to match Tkinter behavior
            return str(row_data[col_idx]) if row_data[col_idx] is not None else ""
        
        elif role == Qt.BackgroundRole:
            return self._get_row_background(row_data, index.row())
        
        elif role == Qt.ForegroundRole:
            # Color result columns: Pass=green, Fail=red
            col_name = self.COLUMNS[col_idx]
            if col_name in ("Power_Result", "PullUp_Result", "Logic_DI_Result"):
                cell_value = row_data[col_idx]
                if cell_value == "Pass":
                    return QBrush(QColor("#00FF00"))  # Bright green
                elif cell_value == "Fail":
                    return QBrush(QColor("#FF0000"))  # Bright red
            
            # Keep white text for all rows (goldenrod, Pass, Fail, normal)
            return QBrush(QColor("#e6edf3"))
        
        elif role == Qt.ToolTipRole:
            value = str(row_data[col_idx]) if row_data[col_idx] is not None else ""
            return value if value else None

        elif role == Qt.TextAlignmentRole:
            # Right-align numeric columns
            col_name = self.COLUMNS[col_idx]
            if col_name in ("Power_Expected", "Power_Input", "Power_Measured",
                           "PullUp_Expected", "PullUp_Input", "PullUp_Measured"):
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter
        
        return None
    
    def _get_row_background(self, row_data: List[str], row_idx: int) -> Optional[QBrush]:
        """
        Get background color for row based on test results.
        Priority: Fail > Pass > Testing > Zebra stripe
        """
        # Get result columns
        power_result = row_data[self.COLUMNS.index("Power_Result")] if "Power_Result" in self.COLUMNS else ""
        pullup_result = row_data[self.COLUMNS.index("PullUp_Result")] if "PullUp_Result" in self.COLUMNS else ""
        logic_result = row_data[self.COLUMNS.index("Logic_DI_Result")] if "Logic_DI_Result" in self.COLUMNS else ""
        
        # Check if this row is currently being tested
        pin_id = row_data[0]  # ID is first column
        pin_number = row_data[self.COLUMNS.index("Pin")] if "Pin" in self.COLUMNS else ""
        if self._testing_pin_id and (pin_id == self._testing_pin_id or pin_number == self._testing_pin_id):
            return QBrush(QColor("#FFF59D5E"))  # Soft yellow for active testing
        # if power_result == "Fail" or pullup_result == "Fail" or logic_result == "Fail":
        #     return QBrush(QColor("#FFB6C1"))  # Light red/pink
        
        # # Next: Pass (green)
        # if power_result == "Pass" or pullup_result == "Pass" or logic_result == "Pass":
        #     return QBrush(QColor("#90EE90"))  # Light green
        
        # Default: Zebra striping for dark theme (subtle alternating)
        if row_idx % 2 == 0:
            return QBrush(QColor("#1c2128"))  # Slightly lighter dark
        else:
            return QBrush(QColor("#22272e"))  # Base dark
        
    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                # Show sort indicator in header with display name
                col_name = self.COLUMNS[section]
                display_name = self.DISPLAY_NAMES.get(col_name, col_name)
                if section == self._sort_column:
                    arrow = " ↓" if self._sort_order == Qt.DescendingOrder else " ↑"
                    return display_name + arrow
                return display_name
            else:
                return str(section + 1)
        return None
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        
        # Make editable columns editable
        col_name = self.COLUMNS[index.column()]
        if col_name in ("Power_Expected", "Power_Input", "PullUp_Expected", "PullUp_Input",
                       "Logic_Pin_Input", "Logic_Command", "Logic_Expected"):
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
        
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable
    
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not index.isValid() or role != Qt.EditRole:
            return False
        
        # Validate numeric columns
        col_name = self.COLUMNS[index.column()]
        if col_name in ("Power_Expected", "PullUp_Expected"):
            try:
                float(value)
            except (ValueError, TypeError):
                return False  # Invalid numeric input
        
        # Update data
        self._rows[index.row()][index.column()] = str(value)
        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True
    
    def set_rows(self, rows: List[Dict[str, str]]) -> None:
        """
        Set all rows in the table (clears existing data).
        
        Args:
            rows: List of dictionaries with keys matching column names
        """
        self.beginResetModel()
        self._rows.clear()
        self._row_id_map.clear()
        
        for idx, row_dict in enumerate(rows):
            # Convert all values to strings to match Tkinter behavior
            row_list = [str(row_dict.get(col, "")) if row_dict.get(col, "") is not None else "" for col in self.COLUMNS]
            self._rows.append(row_list)
            
            # Map pin ID to row index
            pin_id = row_dict.get("ID", "")
            if pin_id:
                self._row_id_map[pin_id] = idx
        
        self.endResetModel()
    
    def update_row(self, pin_id: str, values: Dict[str, str]) -> None:
        """
        Update a specific row by pin ID.
        
        Args:
            pin_id: Pin ID to update
            values: Dictionary of column values to update
        """
        # Debug logging
        print(f"[PinTableQt] update_row called: pin_id={pin_id}, values={values}")
        
        if pin_id not in self._row_id_map:
            print(f"[PinTableQt] ERROR: pin_id {pin_id} not found in row map")
            return
        
        row_idx = self._row_id_map[pin_id]
        if row_idx >= len(self._rows):
            print(f"[PinTableQt] ERROR: row_idx {row_idx} out of range")
            return
        
        print(f"[PinTableQt] Updating row {row_idx} for pin {pin_id}")
        
        # Update specified columns
        for col_name, value in values.items():
            if col_name in self.COLUMNS:
                col_idx = self.COLUMNS.index(col_name)
                old_value = self._rows[row_idx][col_idx]
                self._rows[row_idx][col_idx] = str(value)
                print(f"  Column {col_name}: '{old_value}' -> '{value}'")
        
        # Emit dataChanged for the entire row (colors may change)
        left_index = self.index(row_idx, 0)
        right_index = self.index(row_idx, self.columnCount() - 1)
        self.dataChanged.emit(left_index, right_index, [Qt.DisplayRole, Qt.BackgroundRole])
        print(f"[PinTableQt] dataChanged emitted for row {row_idx}")
    
    def set_testing_pin(self, pin_id: Optional[str]) -> None:
        """
        Set which pin is currently being tested (highlights row with yellow background).

        Args:
            pin_id: Pin ID currently being tested, or None to clear
        """
        print(f"[PinTableModel.set_testing_pin] Setting testing pin: {pin_id}")
        self._testing_pin_id = pin_id

        # Repaint all rows — no roles specified so Qt repaints everything
        if self._rows:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._rows) - 1, self.columnCount() - 1)
            )
    
    def get_all_rows(self) -> List[Dict[str, str]]:
        """
        Get all row data as list of dictionaries.
        
        Returns:
            List of dictionaries with column names as keys (all values as strings)
        """
        rows = []
        for row_list in self._rows:
            # Ensure all values are strings to match Tkinter behavior
            row_dict = {col: str(row_list[idx]) if row_list[idx] is not None else "" for idx, col in enumerate(self.COLUMNS)}
            rows.append(row_dict)
        return rows
    
    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        """
        Sort the table by specified column.
        
        Args:
            column: Column index to sort by
            order: Sort order (Ascending or Descending)
        """
        if not self._rows:
            return
        
        self.layoutAboutToBeChanged.emit()
        
        self._sort_column = column
        self._sort_order = order
        
        # Sort with appropriate key function
        col_name = self.COLUMNS[column]
        
        def sort_key(row_list):
            value = row_list[column]
            
            # Numeric columns
            if col_name in ("Power_Expected", "Power_Measured", "PullUp_Expected", "PullUp_Measured"):
                try:
                    return float(value) if value else 0.0
                except (ValueError, TypeError):
                    return 0.0
            
            # ID column - extract numeric part
            elif col_name == "ID":
                try:
                    import re
                    numbers = re.findall(r'\d+', str(value))
                    return int(numbers[0]) if numbers else 0
                except (ValueError, TypeError):
                    return 0
            
            # String sort for other columns
            return str(value).lower()
        
        self._rows.sort(key=sort_key, reverse=(order == Qt.DescendingOrder))
        
        # Rebuild ID map after sort
        self._row_id_map.clear()
        for idx, row_list in enumerate(self._rows):
            pin_id = row_list[0]  # ID is first column
            if pin_id:
                self._row_id_map[pin_id] = idx
        
        self.layoutChanged.emit()


class PinTableQt(QWidget):
    """
    Qt table view for displaying pin information with multi-selection support.
    Matches the API of the Tkinter PinTableView for easy migration.

    Features:
    - 22 columns for comprehensive pin data
    - Pass/Fail color coding (green/red)
    - Editable cells for input columns
    - Column sorting with visual indicators
    - Multi-row selection
    - Zebra striping for uncolored rows
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize PinTableQt.
        
        Args:
            parent: Parent Qt widget
        """
        super().__init__(parent)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create table view
        self.table = QTableView()
        self.table.setObjectName("pinTable")  # For CSS styling
        
        # Create and set model
        self.model = PinTableModel()
        self.table.setModel(self.model)
        self.table.setItemDelegate(PinTableEditDelegate(self.table))
        
        # Configure table appearance
        self.table.setAlternatingRowColors(False)  # We handle colors in model
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionsClickable(True)
        
        # Set column widths (based on UI requirements)
        header = self.table.horizontalHeader()
        for idx, col in enumerate(self.model.COLUMNS):
            if col == "ID":
                self.table.setColumnWidth(idx, 30)
            elif col == "Connect":
                self.table.setColumnWidth(idx, 60)
            elif col == "Discrete_Name":
                self.table.setColumnWidth(idx, 110)
            elif col == "Signal_Name":
                self.table.setColumnWidth(idx, 150)
            elif col == "Plug":
                self.table.setColumnWidth(idx, 75)
            elif col == "Type":
                self.table.setColumnWidth(idx, 80)
            elif col == "Pin":
                self.table.setColumnWidth(idx, 50)
            elif col in ("Power_Expected", "Power_Input", "Power_Measured",
                        "PullUp_Expected", "PullUp_Input", "PullUp_Measured",
                        "Logic_Pin_Input"):
                self.table.setColumnWidth(idx, 85)
            elif col in ("Logic_Command", "Logic_Expected"):
                self.table.setColumnWidth(idx, 105)
            elif col in ("Power_Result", "PullUp_Result", "Logic_DI_Result"):
                self.table.setColumnWidth(idx, 90)
            elif col in ("Power_Result_Reason", "PullUp_Result_Reason", "Logic_DI_Result_Reason"):
                self.table.setColumnWidth(idx, 115)
        
        # Make last section stretch
        header.setStretchLastSection(True)
        
        # Add to layout
        layout.addWidget(self.table)
        
        # Connect sorting signal
        self.table.horizontalHeader().sortIndicatorChanged.connect(self._on_sort)
    
    @Slot(int, Qt.SortOrder)
    def _on_sort(self, column: int, order: Qt.SortOrder) -> None:
        """Handle column header click for sorting."""
        self.model.sort(column, order)
    
    def set_rows(self, rows: List[Dict[str, str]]) -> None:
        """
        Set all rows in the table (clears existing data).
        
        Args:
            rows: List of dictionaries with keys matching column names
                  Each dict must have at least 'ID' key
        
        Example:
            table.set_rows([
                {"ID": "1", "Connect": "J1-01", "Type": "digital", ...},
                {"ID": "2", "Connect": "J1-02", "Type": "analog", ...}
            ])
        """
        self.model.set_rows(rows)
    
    def update_row(self, pin_id: str, values: Dict[str, str]) -> None:
        """
        Update a specific row by pin ID.
        
        Args:
            pin_id: Pin ID to update
            values: Dictionary of column values to update
        
        Example:
            table.update_row("1", {"Power_Measured": "5.02", "Power_Result": "Pass"})
        """
        self.model.update_row(pin_id, values)
    
    def get_selected_ids(self) -> List[str]:
        """
        Get list of selected pin IDs.
        
        Returns:
            List of pin ID strings (from ID column)
        """
        selected_rows = self.table.selectionModel().selectedRows()
        ids = []
        for model_index in selected_rows:
            row_idx = model_index.row()
            id_index = self.model.index(row_idx, 0)  # ID is first column
            pin_id = self.model.data(id_index, Qt.DisplayRole)
            if pin_id:
                ids.append(str(pin_id))
        return ids
    
    def get_all_rows(self) -> List[Dict[str, str]]:
        """
        Get all row data.
        
        Returns:
            List of dictionaries with column names as keys
        """
        return self.model.get_all_rows()
    
    def clear_selection(self) -> None:
        """Clear current selection."""
        self.table.clearSelection()
    
    def select_all(self) -> None:
        """Select all rows in the table."""
        self.table.selectAll()
    
    def set_testing_pin(self, pin_id: Optional[str]) -> None:
        """
        Highlight the row currently being tested with yellow background.
        Thread-safe: posts a custom event so the main-thread event loop applies the change.

        Args:
            pin_id: Pin ID currently being tested, or None to clear highlight
        """
        QApplication.postEvent(self, _SetTestingPinEvent(pin_id))

    def customEvent(self, event: QEvent) -> None:
        if event.type() == _SET_TESTING_PIN_TYPE:
            self.model.set_testing_pin(event.pin_id)
            self.table.viewport().update()
        else:
            super().customEvent(event)


class CommEnabledDelegate(QStyledItemDelegate):
    """Delegate for editing enabled state with a dropdown."""

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(["True", "False"])
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        current = "True" if str(value).strip().lower() in ("1", "true", "yes", "on") else "False"
        editor.setCurrentText(current)

    def setModelData(self, editor, model, index):
        text = editor.currentText()
        model.setData(index, text, Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class CommCardsTableModel(QAbstractTableModel):
    """Table model for UDP card settings."""

    COLUMNS = (
        "card_id", "enabled", "send_ip", "send_port", "receive_ip", "receive_port"
    )

    DISPLAY_NAMES = {
        "card_id": "Card ID",
        "enabled": "Enabled",
        "send_ip": "Send IP",
        "send_port": "Send Port",
        "receive_ip": "Receive IP",
        "receive_port": "Receive Port"
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: List[Dict[str, str]] = []

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None

        row = self._rows[index.row()]
        column = self.COLUMNS[index.column()]
        value = row.get(column, "")

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if column == "enabled":
                return "True" if row.get("enabled", False) else "False"
            return str(value)

        if role == Qt.TextAlignmentRole:
            if column in ("send_port", "receive_port", "card_id"):
                return Qt.AlignRight | Qt.AlignVCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.DISPLAY_NAMES.get(self.COLUMNS[section], self.COLUMNS[section])
        return str(section + 1)

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.NoItemFlags

        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        column = self.COLUMNS[index.column()]
        if column == "card_id":
            return flags
        return flags | Qt.ItemIsEditable

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:
        if not index.isValid():
            return False

        column = self.COLUMNS[index.column()]
        row = self._rows[index.row()]

        if column == "enabled" and role == Qt.CheckStateRole:
            row["enabled"] = value == Qt.Checked
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.CheckStateRole])
            return True

        if role != Qt.EditRole:
            return False

        if column in ("send_port", "receive_port", "card_id"):
            try:
                row[column] = int(value)
            except (ValueError, TypeError):
                return False
        elif column == "enabled":
            row["enabled"] = str(value).strip().lower() in ("1", "true", "yes", "on")
        else:
            row[column] = str(value)

        self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
        return True

    def set_rows(self, rows: List[Dict[str, str]]) -> None:
        self.beginResetModel()
        self._rows = []
        for row in rows:
            normalized = {
                "card_id": int(row.get("card_id", 0)),
                "enabled": bool(row.get("enabled", False)),
                "send_ip": str(row.get("send_ip", "")),
                "send_port": int(row.get("send_port", 0)),
                "receive_ip": str(row.get("receive_ip", "")),
                "receive_port": int(row.get("receive_port", 0)),
            }
            self._rows.append(normalized)
        self.endResetModel()

    def get_rows(self) -> List[Dict[str, object]]:
        return [
            {
                "card_id": row["card_id"],
                "enabled": row["enabled"],
                "send_ip": row["send_ip"],
                "send_port": row["send_port"],
                "receive_ip": row["receive_ip"],
                "receive_port": row["receive_port"],
            }
            for row in self._rows
        ]


class CommSettingsTable(QWidget):
    """Table widget for editing UDP card configuration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableView()
        self.model = CommCardsTableModel()
        self.table.setModel(self.model)
        self.table.setItemDelegateForColumn(1, CommEnabledDelegate(self.table))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.verticalHeader().setVisible(False)

        self.table.setColumnWidth(0, 70)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 140)
        self.table.setColumnWidth(5, 90)
        self.table.horizontalHeader().setStretchLastSection(True)

        layout.addWidget(self.table)

    def set_rows(self, rows: List[Dict[str, object]]) -> None:
        self.model.set_rows(rows)

    def get_rows(self) -> List[Dict[str, object]]:
        return self.model.get_rows()


# Demo/Test code
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    
    # Create main window
    window = QWidget()
    window.setWindowTitle("PinTableQt Demo")
    window.resize(1200, 600)
    
    layout = QVBoxLayout(window)
    
    # Create table
    table = PinTableQt()
    layout.addWidget(table)
    
    # Add demo data
    demo_rows = [
        {
            "ID": "1", "Connect": "J1-01", "Discrete_Name": "Power Input", "Signal_Name": "VCC_5V",
            "Plug": "Main", "Type": "Power", "Pin": "1",
            "Power_Expected": "5.0", "Power_Input": "5V", "Power_Measured": "5.02",
            "Power_Result": "Pass", "Power_Result_Reason": "Within tolerance",
            "PullUp_Expected": "", "PullUp_Input": "", "PullUp_Measured": "",
            "PullUp_Result": "", "PullUp_Result_Reason": "",
            "Logic_Pin_Input": "", "Logic_Command": "", "Logic_Expected": "",
            "Logic_DI_Result": "", "Logic_DI_Result_Reason": ""
        },
        {
            "ID": "2", "Connect": "J1-02", "Discrete_Name": "Signal Line", "Signal_Name": "DIG_IN_1",
            "Plug": "Main", "Type": "Digital", "Pin": "2",
            "Power_Expected": "", "Power_Input": "", "Power_Measured": "",
            "Power_Result": "", "Power_Result_Reason": "",
            "PullUp_Expected": "3.3", "PullUp_Input": "3.3V", "PullUp_Measured": "2.1",
            "PullUp_Result": "Fail", "PullUp_Result_Reason": "Below threshold",
            "Logic_Pin_Input": "", "Logic_Command": "", "Logic_Expected": "",
            "Logic_DI_Result": "", "Logic_DI_Result_Reason": ""
        },
        {
            "ID": "3", "Connect": "J1-03", "Discrete_Name": "Ground", "Signal_Name": "GND",
            "Plug": "Main", "Type": "Ground", "Pin": "3",
            "Power_Expected": "0.0", "Power_Input": "0V", "Power_Measured": "0.01",
            "Power_Result": "Pass", "Power_Result_Reason": "Within tolerance",
            "PullUp_Expected": "", "PullUp_Input": "", "PullUp_Measured": "",
            "PullUp_Result": "", "PullUp_Result_Reason": "",
            "Logic_Pin_Input": "", "Logic_Command": "", "Logic_Expected": "",
            "Logic_DI_Result": "", "Logic_DI_Result_Reason": ""
        },
    ]
    table.set_rows(demo_rows)
    
    # Test buttons
    btn_layout = QVBoxLayout()
    
    def on_update():
        selected = table.get_selected_ids()
        print(f"Selected IDs: {selected}")
        if selected:
            table.update_row(selected[0], {
                "Power_Measured": "5.05",
                "Power_Result": "Pass",
                "Power_Result_Reason": "Updated value"
            })
    
    btn_update = QPushButton("Update First Selected")
    btn_update.clicked.connect(on_update)
    layout.addWidget(btn_update)
    
    btn_select_all = QPushButton("Select All")
    btn_select_all.clicked.connect(table.select_all)
    layout.addWidget(btn_select_all)
    
    window.show()
    sys.exit(app.exec())
