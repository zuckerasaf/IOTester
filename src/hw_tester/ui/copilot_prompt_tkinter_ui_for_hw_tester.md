# Copilot Prompt: Build Tkinter UI for HW Tester

**Goal**: Generate production-ready Tkinter UI code for a desktop “HW Tester” app that controls routing/measurement of DUT pins via Controllino/Arduino. Follow the layout spec precisely. Create clean, testable code that separates UI from business logic.

---

## Tech Stack & Conventions
- Python 3.10+
- Tkinter + ttk **only** (no third-party UI libs)
- Use `ttk.Style` for theming, but keep defaults simple
- Use `grid` everywhere with correct row/column weights for resizing
- Type hints required, PEP8, docstrings, no wildcard imports
- Put long-running actions in a **thread** or `after()` loop, never block the UI

---

## File Structure (generate these files)
```
src/hw_tester/ui/main_window.py        # Main window class (Tk)
src/hw_tester/ui/views/pin_table.py     # PinTableView (ttk.Treeview)
src/hw_tester/ui/views/op_panel.py      # OperationalPanel (buttons & connector label)
src/hw_tester/ui/views/log_view.py      # LogView (ScrolledText)
```

Provide a single runnable entry point for demonstration: `if __name__ == "__main__": MainWindow().run()` inside `main_window.py` with **mock callbacks**.

---

## Layout Spec (match the mockup)
Main window is vertically divided into three sections:
1) **Pin Table** (top): selectable grid with vertical scroll
2) **Operational Panel** (middle): left = Connector label, right = action buttons
3) **Operational Log** (bottom): multiline log with vertical scroll

Use a top-level `Frame` with 3 grid rows: `rowconfigure(0, weight=3)`, `rowconfigure(1, weight=0)`, `rowconfigure(2, weight=1)` and a single column `columnconfigure(0, weight=1)`.

---

## Widgets & IDs
### Pin Table (PinTableView)
- `ttk.Treeview` with columns: `ID`, `type`, `volt`, `Measure`, `destination`, `substance`, `card`
- Show headings, zebra striping optional
- Attach vertical `ttk.Scrollbar`
- Enable **multiple selection**
- Public API:
  - `set_rows(rows: list[dict]) -> None`
  - `get_selected_ids() -> list[str]`
  - `update_row(id: str, values: dict) -> None`

### Operational Panel (OperationalPanel)
- Left: `ttk.Label` (id: `connector_label`) displaying active connector name
- Right: buttons in a grid:
  - `btn_connect`
  - `btn_run`
  - `btn_stop`
  - `btn_report`
  - `btn_clear_log`
- Public API: `set_connector(name: str) -> None`
- Buttons fire callbacks provided by MainWindow (functionality will be defined later)

### Log View (LogView)
- `tk.Text` inside `ScrolledText` with vertical scrollbar
- Methods: `append(message: str, level: str="INFO")` (prefix timestamp + level), `clear()`

---

## Callbacks (to be wired to core later)
In `MainWindow`, create **mock** async-safe callbacks with signatures below; UI must call these, but they just simulate behavior now:
- `on_connect(pin_ids: list[str]) -> None`
- `on_run_profile() -> None`
- `on_stop() -> None`
- `on_generate_report() -> None`
- `on_clear_log() -> None`

Simulate outcomes by updating rows and appending to the log.

---

## Styling
- Use `ttk.Style` to define styles: `Primary.TButton` (green Run), `Danger.TButton` (orange Stop), `Secondary.TButton` (blue Connect), `Info.TButton` (gray Report), `Utility.TButton` (light ClearLog)
- Ensure all widgets expand/shrink properly on window resize

---

## Data Model (for demo)
Provide sample rows to populate the table on startup:
```python
rows = [
    {"ID": "J1-01", "type": "digital", "volt": "", "Measure": "", "destination": "", "substance": "", "card": "A"},
    {"ID": "J1-02", "type": "analog",  "volt": "", "Measure": "", "destination": "", "substance": "", "card": "A"},
]
```

---

## Behavior Requirements
- Buttons disabled/enabled appropriately (e.g., `Stop` disabled when idle)
- Log automatically scrolls to the latest line
- No blocking calls in the main thread; use `after()` to simulate progress

---

## Deliverables
- Fully working UI with the files listed above
- Running `python src/hw_tester/ui/main_window.py` opens the window with demo data and functioning interactions (no real hardware)
- Clear placeholders marked `# TODO(core):` where integration with hardware/logic will happen

---

## Acceptance Criteria
- Window layout matches the mockup (Pin Table / Operational Panel / Log)
- Table supports multi-select and vertical scrolling
- Operational panel shows connector label and five buttons: Connect, Run, Stop, Report, ClearLog
- Log view scrolls, supports Save and Clear
- Code is modular, typed, and passes `flake8` basics

---

## Starter Snippet (place in `main_window.py` for quick run)
```python
if __name__ == "__main__":
    # Allow running this module directly for demo
    win = MainWindow(title="HW Tester – Demo")
    win.run()
```

> IMPORTANT: Generate complete implementations for all classes/files with mock logic so the UI is interactive and demonstrates the full workflow without real hardware.

