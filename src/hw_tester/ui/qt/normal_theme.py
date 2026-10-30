"""Colors and stylesheet for the Normal (operator) layout. All hex values live here."""

BG_WINDOW = "#EEF2F6"
CARD_BG = "#FFFFFF"
CARD_BORDER = "#D5DCE4"
TEXT = "#14202B"
TEXT_MUTED = "#4A5A6A"
FIELD_BORDER = "#8FA0B2"
FIELD_DISABLED = "#E6EBF0"
GREEN = "#1E7B34"
GREEN_HOVER = "#186A2D"
GREEN_PRESSED = "#145A26"
RED = "#B3261E"
RED_HOVER = "#9C201A"
RED_PRESSED = "#851B15"
BLUE = "#0B5CAD"
AMBER = "#B7791F"
SWITCH_BORDER = "#C5CFD9"
SWITCH_TEXT = "#2B3B4A"
TRACK = "#DCE3EA"

PASS_BG, PASS_BORDER, PASS_TEXT = "#E4F5EA", "#7DBE93", "#11522A"
FAIL_BG, FAIL_BORDER, FAIL_TEXT = "#FCE4E2", "#E08A84", "#8A1C15"
NEUTRAL_BG, NEUTRAL_BORDER, NEUTRAL_TEXT = "#F2F5F8", CARD_BORDER, TEXT_MUTED

# phase -> (banner bg, banner border, banner text, bar color)
PHASE_COLORS = {
    "ready": ("#E8EEF4", "#B7C4D1", TEXT, BLUE),
    "running": ("#E3EFFB", "#7FAEDD", "#0B3D75", BLUE),
    "passed": (PASS_BG, PASS_BORDER, PASS_TEXT, GREEN),
    "failed": (FAIL_BG, FAIL_BORDER, FAIL_TEXT, RED),
    "stopped": ("#FFF1DC", "#E3B565", "#6B4300", AMBER),
}


def build_stylesheet(arrow_url: str) -> str:
    banner = ""
    for phase, (bg, border, text, bar) in PHASE_COLORS.items():
        banner += f"""
QFrame#banner[phase="{phase}"] {{ background: {bg}; border: 2px solid {border}; }}
QFrame#banner[phase="{phase}"] QLabel {{ color: {text}; background: transparent; }}
QProgressBar[phase="{phase}"]::chunk {{ background: {bar}; border-radius: 7px; }}
"""
    return f"""
QWidget#normalPage {{ background: {BG_WINDOW}; }}
QWidget#normalPage QLabel {{ color: {TEXT}; background: transparent; font-family: "Segoe UI"; }}
QLabel#title {{ font-size: 24px; font-weight: bold; }}
QLabel#subtitle {{ font-size: 14px; color: {TEXT_MUTED}; }}
QLabel#cardHeading {{ font-size: 13px; font-weight: bold; color: {TEXT_MUTED}; letter-spacing: 1px; }}
QLabel#fieldLabel {{ font-size: 15px; font-weight: bold; }}
QLabel#statusChip {{
    font-size: 15px; font-weight: bold; padding: 0 16px; border-radius: 16px;
    color: {NEUTRAL_TEXT}; background: {NEUTRAL_BG}; border: 2px solid {NEUTRAL_BORDER};
}}
QLabel#statusChip[state="ok"] {{ color: {PASS_TEXT}; background: {PASS_BG}; border-color: {PASS_BORDER}; }}
QLabel#statusChip[state="warn"] {{ color: #6B4300; background: #FFF1DC; border-color: #E3B565; }}

QFrame#card {{ background: {CARD_BG}; border: 1px solid {CARD_BORDER}; border-radius: 16px; }}
QFrame#card QLabel {{ border: none; }}

QFrame#modeSwitch {{ background: {CARD_BG}; border: 1px solid {SWITCH_BORDER}; border-radius: 14px; }}
QPushButton#modeButton {{
    background: transparent; color: {SWITCH_TEXT}; border: none; border-radius: 12px;
    min-height: 44px; padding: 0 18px; font-size: 15px; font-weight: bold;
}}
QPushButton#modeButton:checked {{ background: {TEXT}; color: #FFFFFF; }}

QComboBox#field {{
    min-height: 44px; font-size: 17px; color: {TEXT}; background: {CARD_BG};
    border: 2px solid {FIELD_BORDER}; border-radius: 12px; padding-left: 12px;
}}
QComboBox#field:disabled {{ background: {FIELD_DISABLED}; color: {TEXT_MUTED}; }}
QComboBox#field::drop-down {{ border: none; width: 40px; }}
QComboBox#field::down-arrow {{ image: url({arrow_url}); width: 16px; height: 16px; }}
QComboBox#field QAbstractItemView {{
    background: {CARD_BG}; color: {TEXT}; selection-background-color: {BLUE};
    selection-color: #FFFFFF; font-size: 16px; outline: 0;
}}

QPushButton#startButton, QPushButton#stopButton {{
    min-height: 64px; border-radius: 16px; color: #FFFFFF; font-size: 26px; font-weight: bold; border: none;
}}
QPushButton#startButton {{ background: {GREEN}; }}
QPushButton#startButton:hover {{ background: {GREEN_HOVER}; }}
QPushButton#startButton:pressed {{ background: {GREEN_PRESSED}; }}
QPushButton#startButton:disabled {{ background: {FIELD_BORDER}; }}
QPushButton#stopButton {{ background: {RED}; }}
QPushButton#stopButton:hover {{ background: {RED_HOVER}; }}
QPushButton#stopButton:pressed {{ background: {RED_PRESSED}; }}

QFrame#banner {{ border-radius: 12px; }}
QLabel#bannerHeadline {{ font-size: 24px; font-weight: bold; }}
QLabel#bannerSub {{ font-size: 16px; }}
{banner}
QProgressBar {{ background: {TRACK}; border: none; border-radius: 7px; max-height: 14px; min-height: 14px; }}
QLabel#percent {{ font-size: 16px; font-weight: 600; }}

QFrame#tile {{ border-radius: 14px; border: 2px solid {NEUTRAL_BORDER}; background: {NEUTRAL_BG}; }}
QFrame#tile QLabel {{ color: {NEUTRAL_TEXT}; border: none; }}
QFrame#tile[state="pass"] {{ background: {PASS_BG}; border-color: {PASS_BORDER}; }}
QFrame#tile[state="pass"] QLabel {{ color: {PASS_TEXT}; }}
QFrame#tile[state="fail"] {{ background: {FAIL_BG}; border-color: {FAIL_BORDER}; }}
QFrame#tile[state="fail"] QLabel {{ color: {FAIL_TEXT}; }}
QLabel#tileCaption {{ font-size: 15px; font-weight: 600; }}
QLabel#tileNumber {{ font-size: 40px; font-weight: bold; }}

QPushButton#setupButton {{
    min-height: 44px; background: {CARD_BG}; color: {TEXT}; border: 2px solid {FIELD_BORDER};
    border-radius: 12px; font-size: 16px; font-weight: 600;
}}
QPushButton#setupButton:hover {{ background: {BG_WINDOW}; }}
QPushButton#setupButton:disabled {{ color: {FIELD_BORDER}; border-color: {CARD_BORDER}; }}
QPushButton#setupButton[result="pass"] {{ background: {PASS_BG}; border-color: {PASS_BORDER}; color: {PASS_TEXT}; }}
QPushButton#setupButton[result="fail"] {{ background: {FAIL_BG}; border-color: {FAIL_BORDER}; color: {FAIL_TEXT}; }}

QPushButton#reportButton {{ min-height: 60px; background: {CARD_BG}; color: {TEXT}; border: 2px solid {FIELD_BORDER};
    border-radius: 14px; font-size: 15px; font-weight: 600;
}}
QPushButton#reportButton:hover {{ background: {BG_WINDOW}; }}
QPushButton#reportButton:disabled {{ color: {FIELD_BORDER}; border-color: {CARD_BORDER}; }}

QPushButton:focus, QComboBox:focus {{ outline: none; border: 2px solid {BLUE}; }}
"""
