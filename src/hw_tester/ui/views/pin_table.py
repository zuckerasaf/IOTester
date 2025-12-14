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
    
    COLUMNS = ("ID", "Connect", "Type", "Power_Expected", "Power_Input", "Power_Measured", "Power_Result", 
               "PullUp_Expected", "PullUp_Measured", "PullUp_Result", 
               "Logic_Pin_Input", "Logic_DI_Result")
    
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
            # Set column widths
            if col == "ID":
                self.tree.column(col, width=100, minwidth=80)
            elif col in ("Connect", "Type"):
                self.tree.column(col, width=120, minwidth=100)
            elif col in ("Power_Expected", "Power_Measured", "PullUp_Expected", "PullUp_Measured"):
                self.tree.column(col, width=100, minwidth=80)
            elif col in ("Power_Result", "PullUp_Result", "Logic_DI_Result"):
                self.tree.column(col, width=80, minwidth=60)
            elif col in ("Power_Input", "Logic_Pin_Input"):
                self.tree.column(col, width=100, minwidth=80)
        
        # Add vertical scrollbar
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Configure zebra striping
        self.tree.tag_configure("oddrow", background="#f0f0f0")
        self.tree.tag_configure("evenrow", background="white")
        
        # Store row data mapping (id -> values)
        self._row_data: Dict[str, str] = {}  # Maps ID to tree item ID
        
        # Editable columns - user can double-click to edit these
        self.editable_columns = ["Power_Expected", "Power_Input", "PullUp_Expected", "Logic_Pin_Input"]
        
        # Bind double-click for editing
        self.tree.bind("<Double-Button-1>", self._on_double_click)
        
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
            
            # Alternate row colors
            tag = "oddrow" if idx % 2 == 1 else "evenrow"
            
            # Insert row
            item_id = self.tree.insert("", tk.END, values=values, tags=(tag,))
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
    
    def clear_selection(self) -> None:
        """Clear current selection."""
        self.tree.selection_remove(*self.tree.selection())
    
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
