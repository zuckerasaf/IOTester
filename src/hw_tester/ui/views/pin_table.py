"""
PinTableView component - Displays pin data in a scrollable table.
"""
import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Optional


class PinTableView(tk.Frame):
    """
    Table view for displaying pin information with multi-selection support.
    Uses ttk.Treeview with columns: ID, type, volt, Measure, destination, substance, card, Event, Eventvalue, Status.
    """
    
    COLUMNS = ("ID", "Connect", "Discrete_Name", "Signal_Name", "Plug", "Type", "Pin", 
               "Power_Expected", "Power_Input", "Power_Measured", "Power_Result", "Power_Result_Reason",
               "PullUp_Expected", "PullUp_Input", "PullUp_Measured", "PullUp_Result", "PullUp_Result_Reason",
               "Logic_Pin_Input", "Logic_Command", "Logic_Expected", "Logic_DI_Result", "Logic_DI_Result_Reason")
    
    def __init__(self, parent: tk.Widget):
        """
        Initialize PinTableView.
        
        Args:
            parent: Parent tkinter widget
        """
        super().__init__(parent)
        
        # Configure grid layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        # Create Treeview
        self.tree = ttk.Treeview(
            self,
            columns=self.COLUMNS,
            show="headings",
            selectmode="extended",  # Multi-select
            height=15
        )
        
        # Configure columns
        for col in self.COLUMNS:
            self.tree.heading(col, text=col)
            # Set column widths based on image layout
            if col == "ID":
                self.tree.column(col, width=35, minwidth=30)
            elif col == "Connect":
                self.tree.column(col, width=60, minwidth=50)
            elif col == "Discrete_Name":
                self.tree.column(col, width=120, minwidth=100)
            elif col == "Signal_Name":
                self.tree.column(col, width=180, minwidth=150)
            elif col in ("Plug", "Type"):
                self.tree.column(col, width=150, minwidth=120)
            elif col == "Pin":
                self.tree.column(col, width=60, minwidth=50)
            elif col in ("Power_Expected", "Power_Input", "Power_Measured"):
                self.tree.column(col, width=110, minwidth=90)
            elif col == "Power_Result":
                self.tree.column(col, width=90, minwidth=70)
            elif col == "Power_Result_Reason":
                self.tree.column(col, width=160, minwidth=140)
            elif col in ("PullUp_Expected", "PullUp_Input", "PullUp_Measured"):
                self.tree.column(col, width=110, minwidth=90)
            elif col == "PullUp_Result":
                self.tree.column(col, width=90, minwidth=70)
            elif col == "PullUp_Result_Reason":
                self.tree.column(col, width=160, minwidth=140)
            elif col in ("Logic_Pin_Input", "Logic_Command", "Logic_Expected"):
                self.tree.column(col, width=110, minwidth=90)
            elif col == "Logic_DI_Result":
                self.tree.column(col, width=100, minwidth=80)
            elif col == "Logic_DI_Result_Reason":
                self.tree.column(col, width=160, minwidth=140)
        
        # Add vertical scrollbar
        v_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scrollbar.set)
        
        # Add horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configure zebra striping first (lower priority)
        self.tree.tag_configure("oddrow", background="#f0f0f0")
        self.tree.tag_configure("evenrow", background="white")
        
        # Configure result status colors last (higher priority - these will override zebra stripes)
        self.tree.tag_configure("pass", background="#90EE90")  # Light green
        self.tree.tag_configure("fail", background="#FFB6C1")  # Light red/pink
        
        # Store row data mapping (id -> values)
        self._row_data: Dict[str, str] = {}  # Maps ID to tree item ID
        
        # Sorting state
        self._sort_column = None
        self._sort_reverse = False
        
        # Editable columns - user can double-click to edit these
        self.editable_columns = ["Power_Expected", "Power_Input", "PullUp_Expected", "PullUp_Input", "Logic_Pin_Input", "Logic_Command", "Logic_Expected"]
        
        # Bind double-click for editing
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        
        # Bind column header clicks for sorting
        for col in self.COLUMNS:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by_column(c))
        
        # Store reference to edit popup
        self._edit_popup = None
    
    def set_rows(self, rows: List[Dict[str, str]]) -> None:
        """
        Set all rows in the table (clears existing data).
        
        Args:
            rows: List of dictionaries with keys matching column names
                  Each dict must have at least 'ID' key
        
        Example:
            table.set_rows([
                {"ID": "J1-01", "type": "digital", "volt": "5.0", ...},
                {"ID": "J1-02", "type": "analog", "volt": "3.3", ...}
            ])
        """
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._row_data.clear()
        
        # Add new rows
        for idx, row in enumerate(rows):
            pin_id = row.get("ID", "")
            values = tuple(row.get(col, "") for col in self.COLUMNS)
            
            # Determine result status color tags - prioritize Fail over Pass
            power_result = row.get("Power_Result", "")
            pullup_result = row.get("PullUp_Result", "")
            logic_result = row.get("Logic_DI_Result", "")
            
            tags = []
            # If any result is Fail, color the row as Fail (no zebra stripe)
            if power_result == "Fail" or pullup_result == "Fail" or logic_result == "Fail":
                tags.append("fail")
                print(f"Row {pin_id}: Applying FAIL tag (Power={power_result}, PullUp={pullup_result}, Logic={logic_result})")
            # Otherwise, if any result is Pass, color as Pass (no zebra stripe)
            elif power_result == "Pass" or pullup_result == "Pass" or logic_result == "Pass":
                tags.append("pass")
                print(f"Row {pin_id}: Applying PASS tag (Power={power_result}, PullUp={pullup_result}, Logic={logic_result})")
            # No result - use zebra striping
            else:
                tags.append("oddrow" if idx % 2 == 1 else "evenrow")
                print(f"Row {pin_id}: No result tag (Power={power_result}, PullUp={pullup_result}, Logic={logic_result})")
            
            print(f"  Final tags for {pin_id}: {tags}")
            
            # Insert row
            item_id = self.tree.insert("", tk.END, values=values, tags=tuple(tags))
            self._row_data[pin_id] = item_id
    
    def get_selected_ids(self) -> List[str]:
        """
        Get list of selected pin IDs.
        
        Returns:
            List of pin ID strings (from ID column)
        """
        selected_items = self.tree.selection()
        ids = []
        for item in selected_items:
            values = self.tree.item(item, "values")
            if values:
                ids.append(values[0])  # ID is first column
        return ids
    
    def update_row(self, pin_id: str, values: Dict[str, str]) -> None:
        """
        Update a specific row by pin ID.
        
        Args:
            pin_id: Pin ID to update
            values: Dictionary of column values to update
        
        Example:
            table.update_row("J1-01", {"Measure": "5.02V", "volt": "5.0"})
        """
        if pin_id not in self._row_data:
            return
        
        item_id = self._row_data[pin_id]
        current_values = list(self.tree.item(item_id, "values"))
        
        # Update only specified columns
        for col_idx, col_name in enumerate(self.COLUMNS):
            if col_name in values:
                current_values[col_idx] = values[col_name]
        
        self.tree.item(item_id, values=tuple(current_values))
        
        # Update tags based on result status
        # Determine new result tag - prioritize Fail over Pass
        power_result = current_values[self.COLUMNS.index("Power_Result")] if "Power_Result" in self.COLUMNS else ""
        pullup_result = current_values[self.COLUMNS.index("PullUp_Result")] if "PullUp_Result" in self.COLUMNS else ""
        logic_result = current_values[self.COLUMNS.index("Logic_DI_Result")] if "Logic_DI_Result" in self.COLUMNS else ""
        
        new_tags = []
        # If any result is Fail, color the row as Fail (no zebra stripe)
        if power_result == "Fail" or pullup_result == "Fail" or logic_result == "Fail":
            new_tags.append("fail")
            print(f"UPDATE Row {pin_id}: Applying FAIL tag (Power={power_result}, PullUp={pullup_result}, Logic={logic_result})")
        # Otherwise, if any result is Pass, color as Pass (no zebra stripe)
        elif power_result == "Pass" or pullup_result == "Pass" or logic_result == "Pass":
            new_tags.append("pass")
            print(f"UPDATE Row {pin_id}: Applying PASS tag (Power={power_result}, PullUp={pullup_result}, Logic={logic_result})")
        # No result - preserve zebra striping from original tags
        else:
            old_tags = self.tree.item(item_id, "tags")
            for tag in old_tags:
                if tag in ["oddrow", "evenrow"]:
                    new_tags.append(tag)
                    break
            print(f"UPDATE Row {pin_id}: No result tag (Power={power_result}, PullUp={pullup_result}, Logic={logic_result})")
        
        print(f"  Final tags for {pin_id}: {new_tags}")
        
        self.tree.item(item_id, tags=tuple(new_tags))
    
    def clear_selection(self) -> None:
        """Clear current selection."""
        self.tree.selection_remove(*self.tree.selection())

    def select_all(self) -> None:
        """Select all rows in the table."""
        self.tree.selection_set(*self.tree.get_children())
    
    def _sort_by_column(self, col: str) -> None:
        """Sort table by the specified column.
        
        Args:
            col: Column name to sort by
        """
        # Toggle sort direction if clicking same column
        if self._sort_column == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = col
            self._sort_reverse = False
        
        # Get all current data
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            tags = self.tree.item(item, "tags")
            data.append((values, tags))
        
        # Get column index
        col_idx = self.COLUMNS.index(col)
        
        # Sort data - handle numeric values for certain columns
        def sort_key(item):
            value = item[0][col_idx]
            # Try to convert to number for numeric columns
            if col in ("Power_Expected", "Power_Measured", "PullUp_Expected", "PullUp_Measured"):
                try:
                    return float(value) if value else 0.0
                except (ValueError, TypeError):
                    return 0.0
            # Try to extract numeric part from ID (e.g., "21" from ID)
            elif col == "ID":
                try:
                    # Extract all digits and convert to int
                    import re
                    numbers = re.findall(r'\d+', str(value))
                    if numbers:
                        return int(numbers[0])
                    return 0
                except (ValueError, TypeError):
                    return 0
            # String sort for other columns
            return str(value).lower()
        
        data.sort(key=sort_key, reverse=self._sort_reverse)
        
        # Clear and repopulate tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._row_data.clear()
        
        # Re-insert sorted data
        for idx, (values, tags) in enumerate(data):
            pin_id = values[0]  # ID is first column
            item_id = self.tree.insert("", tk.END, values=values, tags=tags)
            self._row_data[pin_id] = item_id
        
        # Update column header to show sort direction
        for column in self.COLUMNS:
            if column == col:
                arrow = " ↓" if self._sort_reverse else " ↑"
                self.tree.heading(column, text=f"{column}{arrow}")
            else:
                self.tree.heading(column, text=column)
    
    def get_all_rows(self) -> List[Dict[str, str]]:
        """
        Get all row data.
        
        Returns:
            List of dictionaries with column names as keys
        """
        rows = []
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            row = {col: values[idx] for idx, col in enumerate(self.COLUMNS)}
            rows.append(row)
        return rows
    
    def _on_double_click(self, event) -> None:
        """
        Handle double-click on a cell to edit editable columns.
        
        Args:
            event: Click event
        """
        # Identify the row and column that was clicked
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        # Get the item and column
        item_id = self.tree.identify_row(event.y)
        column_id = self.tree.identify_column(event.x)
        
        if not item_id or not column_id:
            return
        
        # Convert column_id (e.g., "#4") to column index
        column_index = int(column_id.replace("#", "")) - 1
        if column_index < 0 or column_index >= len(self.COLUMNS):
            return
        
        column_name = self.COLUMNS[column_index]
        
        # Only allow editing of specific columns
        if column_name not in self.editable_columns:
            return
        
        # Get current value
        values = self.tree.item(item_id, "values")
        current_value = values[column_index]
        
        # Get the bounding box of the cell
        bbox = self.tree.bbox(item_id, column_id)
        if not bbox:
            return
        
        # Create entry widget for editing
        x, y, width, height = bbox
        
        # Destroy previous popup if exists
        if self._edit_popup:
            self._edit_popup.destroy()
        
        self._edit_popup = tk.Entry(self.tree, width=width // 10)
        self._edit_popup.insert(0, current_value)
        self._edit_popup.select_range(0, tk.END)
        self._edit_popup.focus()
        
        # Position the entry widget
        self._edit_popup.place(x=x, y=y, width=width, height=height)
        
        # Bind events
        def save_edit(event=None):
            new_value = self._edit_popup.get()
            
            # Validate numeric values for Power_Expected and PullUp_Expected
            if column_name in ["Power_Expected", "PullUp_Expected"]:
                try:
                    float(new_value)  # Validate it's a number
                except ValueError:
                    self._edit_popup.destroy()
                    self._edit_popup = None
                    return
            
            # Update the value in the tree
            new_values = list(values)
            new_values[column_index] = new_value
            self.tree.item(item_id, values=tuple(new_values))
            
            self._edit_popup.destroy()
            self._edit_popup = None
        
        def cancel_edit(event=None):
            self._edit_popup.destroy()
            self._edit_popup = None
        
        self._edit_popup.bind("<Return>", save_edit)
        self._edit_popup.bind("<Escape>", cancel_edit)
        self._edit_popup.bind("<FocusOut>", save_edit)


# Demo/Test code
if __name__ == "__main__":
    root = tk.Tk()
    root.title("PinTableView Demo")
    root.geometry("900x500")
    
    table = PinTableView(root)
    table.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Add demo data
    demo_rows = [
        {"ID": "J1-01", "type": "digital", "volt": "5.0", "Measure": "", "destination": "D5", "substance": "Signal", "card": "1", "Event": "PowerOn", "Eventvalue": "High", "Status": "Pass", "connection": ""},
        {"ID": "J1-02", "type": "analog", "volt": "3.3", "Measure": "", "destination": "A0", "substance": "Sensor", "card": "1", "Event": "ReadVoltage", "Eventvalue": "3.3V", "Status": "Pass", "connection": ""},
        {"ID": "J1-03", "type": "ground", "volt": "0.0", "Measure": "", "destination": "GND", "substance": "Ground", "card": "1", "Event": "", "Eventvalue": "", "Status": "Pass", "connection": ""},
        {"ID": "J1-04", "type": "power", "volt": "5.0", "Measure": "", "destination": "VCC", "substance": "Power", "card": "2", "Event": "PowerCheck", "Eventvalue": "5V", "Status": "Pass", "connection": ""},
        {"ID": "J1-05", "type": "pwm", "volt": "3.3", "Measure": "", "destination": "D9", "substance": "PWM Out", "card": "2", "Event": "PWMSet", "Eventvalue": "50%", "Status": "Pass", "connection": ""},
    ]
    table.set_rows(demo_rows)
    
    # Test button
    def on_test():
        selected = table.get_selected_ids()
        print(f"Selected IDs: {selected}")
        if selected:
            table.update_row(selected[0], {"Measure": "4.98V", "volt": "5.0"})
    
    btn = tk.Button(root, text="Update First Selected", command=on_test)
    btn.pack(pady=5)
    
    root.mainloop()
