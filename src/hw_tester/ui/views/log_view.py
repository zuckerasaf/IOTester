"""
LogView component - Operational log display with scrolling.
"""
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime


class LogView(tk.Frame):
    """
    Displays operational logs with timestamp and level prefix.
    Supports appending messages and clearing.
    """
    
    def __init__(self, parent: tk.Widget):
        """
        Initialize LogView.
        
        Args:
            parent: Parent tkinter widget
        """
        super().__init__(parent)
        
        # Create scrolled text widget
        self.text_widget = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            width=80,
            height=10,
            state=tk.DISABLED,  # Read-only by default
            font=("Consolas", 9)
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Configure tags for different log levels
        self.text_widget.tag_config("INFO", foreground="black")
        self.text_widget.tag_config("SUCCESS", foreground="green")
        self.text_widget.tag_config("WARNING", foreground="orange")
        self.text_widget.tag_config("ERROR", foreground="red")
        self.text_widget.tag_config("DEBUG", foreground="gray")
    
    def append(self, message: str, level: str = "INFO") -> None:
        """
        Append a message to the log with timestamp and level.
        
        Args:
            message: Log message text
            level: Log level (INFO, SUCCESS, WARNING, ERROR, DEBUG)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}\n"
        
        # Enable editing temporarily
        self.text_widget.config(state=tk.NORMAL)
        
        # Insert text with appropriate tag
        self.text_widget.insert(tk.END, log_line, level)
        
        # Auto-scroll to bottom
        self.text_widget.see(tk.END)
        
        # Disable editing again
        self.text_widget.config(state=tk.DISABLED)
    
    def clear(self) -> None:
        """Clear all log messages."""
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.config(state=tk.DISABLED)


# Demo/Test code
if __name__ == "__main__":
    root = tk.Tk()
    root.title("LogView Demo")
    root.geometry("600x300")
    
    log_view = LogView(root)
    log_view.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Add some demo messages
    log_view.append("Application started", "INFO")
    log_view.append("Connected to COM5", "SUCCESS")
    log_view.append("Voltage reading unstable", "WARNING")
    log_view.append("Connection timeout", "ERROR")
    log_view.append("Debug: Reading analog port 0", "DEBUG")
    
    root.mainloop()
