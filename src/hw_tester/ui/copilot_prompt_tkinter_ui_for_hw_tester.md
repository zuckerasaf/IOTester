# Tkinter UI: HW Tester (Current Implementation)

This document reflects the current Tkinter UI code in `src/hw_tester/ui/` and related views. It intentionally ignores `QT_Style.py` because that file is only a PySide6 UI experiment.

---

## Tech Stack & Conventions
- Python 3.10+
- Tkinter + ttk only (no third-party UI libraries)
- Grid-based layout for the main window; view widgets are self-contained
- Long-running work runs in background threads; UI updates happen via `after()`

---

## File Structure
```
src/hw_tester/ui/main_window.py        # Main window class (Tk), wiring to core/hardware
src/hw_tester/ui/views/pin_table.py     # PinTableView (ttk.Treeview)
src/hw_tester/ui/views/op_panel.py      # OperationalPanel (controls and filters)
src/hw_tester/ui/views/log_view.py      # LogView (ScrolledText)
```

---

## Layout Summary
The main window is divided into three stacked sections:
1) Pin Table (top)
2) Operational Panel (middle)
3) Operational Log (bottom)

The root window uses a 3-row grid with weights `(3, 0, 1)` and one stretching column.

---

## Pin Table (PinTableView)
Location: `src/hw_tester/ui/views/pin_table.py`

**Widget**: `ttk.Treeview` with vertical and horizontal scrollbars, multi-select enabled, header sorting, zebra striping, and pass/fail row coloring.

**Columns (current)**
```
ID, Connect, Discrete_Name, Signal_Name, Plug, Type, Pin,
Power_Expected, Power_Input, Power_Measured, Power_Result, Power_Result_Reason,
PullUp_Expected, PullUp_Input, PullUp_Measured, PullUp_Result, PullUp_Result_Reason,
Logic_Pin_Input, Logic_Command, Logic_Expected, Logic_DI_Result, Logic_DI_Result_Reason
```

**Editable columns**
`Power_Expected`, `Power_Input`, `PullUp_Expected`, `PullUp_Input`, `Logic_Pin_Input`, `Logic_Command`, `Logic_Expected`

**Public API**
- `set_rows(rows: list[dict]) -> None`
- `get_selected_ids() -> list[str]`
- `update_row(pin_id: str, values: dict) -> None`
- `clear_selection() -> None`
- `select_all() -> None`
- `get_all_rows() -> list[dict]`

---

## Operational Panel (OperationalPanel)
Location: `src/hw_tester/ui/views/op_panel.py`

**Layout**
- Left: connector label (sunk frame)
- Right: control grid across 3 rows

**Controls (current)**
- Buttons: `Load`, `KeepAlive`, `I_Bit`, `Stop_IBIT`, `Test`, `Test_All`, `Stop_T`, `ClearLog`, `Report`, `DOC`, `Next`
- Combos: `Simulation On/Off`, `Local Host/IO_box`, `Debug/Normal`, `HTML file selection`, `Hardware type`
- Log Filter: checkbox group for `INFO`, `SUCCESS`, `WARNING`, `ERROR`, `DEBUG`

**Behavior notes**
- HTML file combo is enabled only in Debug mode.
- Log filter checkboxes drive filtering in `LogView`.
- `trace.json` is reset on startup to avoid stale web trace data.

**Public API**
- `set_connector(name: str) -> None`
- `enable_stop_t(enabled: bool = True) -> None`
- `enable_stop_ibit(enabled: bool = True) -> None`
- `enable_test(enabled: bool = True) -> None`
- `enable_test_all(enabled: bool = True) -> None`
- `enable_i_bit(enabled: bool = True) -> None`
- `enable_load(enabled: bool = True) -> None`
- `enable_keep_alive(enabled: bool = True) -> None`
- `get_hardware() -> str`, `set_hardware(hw: str) -> None`
- `get_simulation_mode() -> str`, `set_simulation_mode(mode: str) -> None`
- `get_localhost_mode() -> str`, `set_localhost_mode(mode: str) -> None`
- `get_html_file() -> str`, `set_html_file(filename: str) -> None`, `enable_html_dropdown(enabled: bool = True) -> None`
- `get_debug_mode() -> str`, `set_debug_mode(mode: str) -> None`

---

## Operational Log (LogView)
Location: `src/hw_tester/ui/views/log_view.py`

**Widget**: `ScrolledText` (read-only) with color tags per log level.

**Public API**
- `append(message: str, level: str = "INFO") -> None`
- `clear() -> None`
- `filter_by_level(levels: list | None) -> None`

Logs are stored internally and re-rendered when filters change.

---

## Main Window Integration (MainWindow)
Location: `src/hw_tester/ui/main_window.py`

MainWindow wires the UI to real hardware/core logic:
- Loads settings and board pin mappings before creating widgets.
- Initializes hardware via `hardware_factory`, then creates `Measurer`, `PinPulser`, `UDPCardManager`, and `TestHandle`.
- Uses background threads for long tasks (loading Excel, running tests).
- Uses `after()` for UI updates and state changes.

---

## Run
```
python src/hw_tester/ui/main_window.py
```

This runs the full application with live wiring to the core modules (not a mock UI).


> IMPORTANT: Generate complete implementations for all classes/files with mock logic so the UI is interactive and demonstrates the full workflow without real hardware.
