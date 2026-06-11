import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from hw_tester.ui.qt.main_window_qt import MainWindowQt


def load_stylesheet(app: QApplication, qss_path: Path) -> None:
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
        print(f"Loaded stylesheet: {qss_path}")
    else:
        print(f"Stylesheet not found: {qss_path}")


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Prefer external config folder next to the EXE
    exe_dir = Path(sys.argv[0]).resolve().parent
    external_qss = exe_dir / "config" / "dark.css"
    if external_qss.exists():
        load_stylesheet(app, external_qss)
    else:
        # Fall back to bundled or source QSS path
        qss_path = Path(__file__).resolve().parents[1] / "Styles" / "dark.css"
        load_stylesheet(app, qss_path)

    w = MainWindowQt()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
