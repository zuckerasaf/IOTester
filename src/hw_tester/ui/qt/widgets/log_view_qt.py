"""
Qt LogView component - Operational log display with filtering and color coding.
Matches the API of the Tkinter LogView for easy migration.
"""
from datetime import datetime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PySide6.QtGui import QTextCharFormat, QColor, QFont
from PySide6.QtCore import Qt, Slot


class LogViewQt(QWidget):
    """
    Qt log display widget with the same API as Tkinter LogView.
    
    Supports:
    - append(message, level) - add log entries with timestamps
    - clear() - clear all logs
    - filter_by_level(levels) - filter display by log levels
    - Color coding for different log levels
    """
    
    def __init__(self, parent=None):
        """
        Initialize LogViewQt.
        
        Args:
            parent: Parent Qt widget
        """
        super().__init__(parent)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create text widget
        self.text_widget = QTextEdit()
        self.text_widget.setReadOnly(True)
        self.text_widget.setFont(QFont("Consolas", 9))
        self.text_widget.setObjectName("logWindow")  # Apply CSS styling
        layout.addWidget(self.text_widget)
        
        # Store log entries for filtering
        self.log_entries = []  # List of tuples: (timestamp, level, message)
        self.current_filter = []  # List of selected filter levels (empty = show all)
        
        # Define log level colors for dark theme (light colors on dark background)
        self.level_colors = {
            "INFO": QColor("#e6edf3"),      # Light gray/white
            "INF": QColor("#e6edf3"),
            "SUCCESS": QColor("#3fb950"),   # Light green
            "SUC": QColor("#3fb950"),
            "WARNING": QColor("#d29922"),   # Amber/orange
            "WRN": QColor("#d29922"),
            "ERROR": QColor("#f85149"),     # Light red
            "ERR": QColor("#f85149"),
            "DEBUG": QColor("#7d8590"),     # Gray
            "DBG": QColor("#7d8590"),
        }
    
    @Slot(str, str)
    def append(self, message: str, level: str = "INFO") -> None:
        """
        Append a message to the log with timestamp and level.
        
        Args:
            message: Log message text
            level: Log level (INFO/INF, SUCCESS/SUC, WARNING/WRN, ERROR/ERR, DEBUG/DBG)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Normalize level names (accept both long and short forms)
        level_map = {
            "INFO": "INFO", "INF": "INFO",
            "SUCCESS": "SUCCESS", "SUC": "SUCCESS",
            "WARNING": "WARNING", "WRN": "WARNING",
            "ERROR": "ERROR", "ERR": "ERROR",
            "DEBUG": "DEBUG", "DBG": "DEBUG"
        }
        normalized_level = level_map.get(level.upper(), level.upper())
        
        # Store log entry for filtering
        self.log_entries.append((timestamp, normalized_level, message))
        
        # Only display if it passes the current filter
        if not self.current_filter or normalized_level in self.current_filter:
            self._append_to_display(timestamp, normalized_level, message)
    
    def _append_to_display(self, timestamp: str, level: str, message: str) -> None:
        """
        Append formatted log entry to the display.
        
        Args:
            timestamp: Formatted timestamp string
            level: Log level
            message: Log message
        """
        log_line = f"[{timestamp}] [{level}] {message}"
        
        # Get color for this level
        color = self.level_colors.get(level, QColor("black"))
        
        # Create text format with color
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        
        # Move cursor to end
        cursor = self.text_widget.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        
        # Insert colored text
        cursor.insertText(log_line + "\n", fmt)
        
        # Auto-scroll to bottom
        self.text_widget.ensureCursorVisible()
    
    @Slot()
    def clear(self) -> None:
        """Clear all log messages."""
        self.text_widget.clear()
        self.log_entries.clear()
    
    def filter_by_level(self, levels: list = None) -> None:
        """
        Filter log display by multiple levels.
        
        Args:
            levels: List of log levels to display (e.g., ["INFO", "ERROR"]). 
                   Empty list or None means show all.
        """
        self.current_filter = levels if levels else []
        
        # Clear current display
        self.text_widget.clear()
        
        # Redisplay filtered entries
        for timestamp, entry_level, message in self.log_entries:
            if not self.current_filter or entry_level in self.current_filter:
                self._append_to_display(timestamp, entry_level, message)
