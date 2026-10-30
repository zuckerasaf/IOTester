#!/usr/bin/env python3
"""Generate one Target_J#.xlsx per connector from the Spider Card tabs of a source
workbook, plus Open_Issues.xlsx for rows that need manual review.

Usage:
    python generate_targets.py source_file.xlsx -o output
    python generate_targets.py source_file.xlsx -o output --only J1 J2
    python generate_targets.py source_file.xlsx --compare Target_J1.xlsx --only J1
    python generate_targets.py

Requires: openpyxl
"""
import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, PatternFill, Side

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
SOURCE_SHEETS = ["Spider Card #1", "Spider Card #2", "Spider Card #3", "Spider Card #4"]
CONNECTOR_REGEX = re.compile(r"^J\d+$")
FILE_NAME_TEMPLATE = "Target_{conn}.xlsx"
ISSUES_FILE_NAME = "Open_Issues.xlsx"
FIRST_DATA_ROW = 7

# Source columns (1-based): B..K
SRC = dict(discrete=2, signal=3, type=4, conn=5, pin_out=6,
           from_=7, plug=8, pin=9, color=10, awg=11)

# Target headers, kept exactly as in the example (including its spelling).
TARGET_HEADERS = [
    "Card", "Discrete Mame", "Signal Name", "Type", "Connector", "SPS", "Orignal",
    "Pin Out", "From", "Plug", "Pin", "Color", "AWG",
    # Test columns: left empty for now, add values here later if needed.
    "Power_Expected", "Power_Input", "PullUp_Expected", "PullUp_Input",
    "logic_input", "Logic_Command", "Logic_Expected", "Test_Result",
]
N_EMPTY_TEST_COLS = 8

ISSUE_HEADERS = [
    "Issue ID", "Issue Type", "Source Tab", "Card", "Source Row",
    "Connector Above", "Connector Below", "Discrete Name", "Signal Name", "Type",
    "Connector", "Pin Out", "From", "Plug", "Pin", "Color", "AWG", "Notes", "Status",
]
ISSUE_UNASSIGNED = "Unassigned row: empty connector, not between two rows of the same J#"
ISSUE_INCLUDED = "Included in {conn} file, connector cell empty in source"

THIN = Side(style="thin")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WHITE = PatternFill(fill_type="solid", fgColor="FFFFFF")
CENTER = Alignment(horizontal="center", vertical="center")


# ----------------------------------------------------------------------------
# Reading the source
# ----------------------------------------------------------------------------
def conn_of(ws, r):
    """Return 'J#' (normalised), 'OTHER' (non-J text such as headers/TB7) or None (empty)."""
    v = ws.cell(r, SRC["conn"]).value
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, str) and CONNECTOR_REGEX.match(v.strip().upper()):
        return v.strip().upper()
    return "OTHER"


def row_is_empty(ws, r):
    return all(ws.cell(r, c).value in (None, "") for c in range(2, 12))


def row_values(ws, r):
    return {k: ws.cell(r, c).value for k, c in SRC.items()}


def card_number(sheet_name):
    m = re.search(r"#(\d+)", sheet_name)
    if not m:
        sys.exit(f"Cannot find a card number in tab name: {sheet_name!r}")
    return int(m.group(1))


def collect_rows(wb, sheet_names):
    """Return (rows_by_conn, issues).

    rows_by_conn: OrderedDict conn -> list of dict(card, row, values)
    issues: list of dict(type, sheet, card, row, above, below, values)
    """
    missing = [n for n in sheet_names if n not in wb.sheetnames]
    if missing:
        sys.exit(f"Missing tab(s) {missing}. Tabs in file: {wb.sheetnames}")

    rows_by_conn = OrderedDict()
    issues = []

    for sheet in sheet_names:
        ws = wb[sheet]
        card = card_number(sheet)
        max_r = ws.max_row
        r = FIRST_DATA_ROW
        while r <= max_r:
            c = conn_of(ws, r)
            if c and c != "OTHER":
                rows_by_conn.setdefault(c, []).append(
                    dict(card=card, row=r, values=row_values(ws, r)))
                r += 1
            elif c is None and not row_is_empty(ws, r):
                # Run of consecutive rows with empty Connector but other content.
                start = r
                while r <= max_r and conn_of(ws, r) is None and not row_is_empty(ws, r):
                    r += 1
                end = r - 1
                above = conn_of(ws, start - 1) if start > FIRST_DATA_ROW else None
                below = conn_of(ws, end + 1) if end + 1 <= max_r else None
                same = above not in (None, "OTHER") and above == below
                for rr in range(start, end + 1):
                    vals = row_values(ws, rr)
                    if same:
                        rows_by_conn.setdefault(above, []).append(
                            dict(card=card, row=rr, values=vals))
                    issues.append(dict(
                        type=ISSUE_INCLUDED.format(conn=above) if same else ISSUE_UNASSIGNED,
                        sheet=sheet, card=card, row=rr,
                        above=None if above == "OTHER" else above,
                        below=None if below == "OTHER" else below,
                        values=vals))
            else:
                r += 1
    return rows_by_conn, issues


# ----------------------------------------------------------------------------
# Writing outputs
# ----------------------------------------------------------------------------
def style_cell(cell, centered):
    cell.border = BORDER
    cell.fill = WHITE
    if centered:
        cell.alignment = CENTER


def write_target(conn, rows, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet"
    ws.append(TARGET_HEADERS)
    for item in rows:
        v = item["values"]
        pin_out = v["pin_out"]
        ws.append([
            item["card"], v["discrete"], v["signal"], v["type"], v["conn"],
            pin_out, pin_out, pin_out,           # SPS, Orignal, Pin Out
            v["from_"], v["plug"], v["pin"], v["color"], v["awg"],
        ] + [None] * N_EMPTY_TEST_COLS)
    for r in range(2, ws.max_row + 1):
        for c in range(1, len(TARGET_HEADERS) + 1):
            style_cell(ws.cell(r, c), centered=2 <= c <= 13)
    ws.column_dimensions["B"].width = 14.42578125
    ws.column_dimensions["C"].width = 40.85546875
    wb.save(path)


DI_REGEX = re.compile(r"(?<![A-Za-z])DI_?(\d+)", re.IGNORECASE)
DO_REGEX = re.compile(r"(?<![A-Za-z])DO_?(\d+)", re.IGNORECASE)
AI_REGEX = re.compile(r"(?<![A-Za-z])AI_?(\d+)", re.IGNORECASE)
FIRST_NUMBER_REGEX = re.compile(r"\d+")
COL_N, COL_O, COL_P, COL_Q, COL_R, COL_T = 14, 15, 16, 17, 18, 20
RANGE_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)")
VOLTAGE_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*V\b", re.IGNORECASE)


def add_di_data(path):
    """Open a Target file and fill extra columns for DI and DO rows (column B).

    DI: N = 3.5, R = "TBD", T = C<first number of column A>_DI<number from B>_0
    DO: N = 0,   P = 4,     Q = C<first number of column A>_DO<number from B>_1
    AI: N = 1,   T = C<first number of column A>_AI<number from B>_10
    Returns the number of rows updated.
    """
    wb = load_workbook(path)
    ws = wb.active
    updated = 0
    for r in range(2, ws.max_row + 1):
        b = ws.cell(r, 2).value
        if isinstance(b, str):
            a = FIRST_NUMBER_REGEX.search(str(ws.cell(r, 1).value or ""))
            m = AI_REGEX.search(b)
            if m:
                ws.cell(r, COL_N).value = 1
                ws.cell(r, COL_R).value = "TBD"
                if a:
                    ws.cell(r, COL_T).value = f"C{a.group()}_AI{m.group(1)}_10"
                updated += 1
                continue

        j = ws.cell(r, 10).value
        k = ws.cell(r, 11).value
        l = ws.cell(r, 12).value
        voltage = VOLTAGE_REGEX.search(j) if isinstance(j, str) else None
        if (isinstance(l, str) and "RED" in l.upper() and voltage):
            value = float(voltage.group(1))
            ws.cell(r, COL_N).value = int(value) if value.is_integer() else value
            ws.cell(r, COL_O).value = "P"
            updated += 1
            continue

        is_rtn = isinstance(j, str) and "RTN" in j.upper()
        is_ch_minus = isinstance(k, str) and "CH." in k.upper() and "-" in k
        if is_rtn or is_ch_minus:
            ws.cell(r, COL_N).value = 0
            ws.cell(r, COL_P).value = 0
            ws.cell(r, COL_Q).value = "G"
            updated += 1
            continue
        if (isinstance(l, str) and "RED" in l.upper() and isinstance(k, str)
                and "CH" in k.upper() and "+" in k):
            i_val = ws.cell(r, 9).value
            rng = RANGE_REGEX.search(i_val) if isinstance(i_val, str) else None
            if rng:
                ws.cell(r, COL_N).value = max(float(rng.group(1)), float(rng.group(2)))
                if ws.cell(r, COL_N).value.is_integer():
                    ws.cell(r, COL_N).value = int(ws.cell(r, COL_N).value)
            ws.cell(r, COL_O).value = "TBD"
            updated += 1
            continue
        if not isinstance(b, str):
            continue
        a = FIRST_NUMBER_REGEX.search(str(ws.cell(r, 1).value or ""))
        m = DI_REGEX.search(b)
        if m:
            ws.cell(r, COL_N).value = 3.5
            ws.cell(r, COL_R).value = "TBD"
            if a:
                ws.cell(r, COL_T).value = f"C{a.group()}_DI{m.group(1)}_0"
            updated += 1
            continue
        m = DO_REGEX.search(b)
        if m:
            ws.cell(r, COL_N).value = 0
            ws.cell(r, COL_P).value = 4
            if a:
                ws.cell(r, COL_Q).value = f"C{a.group()}_DO{m.group(1)}_1"
            updated += 1
    wb.save(path)
    return updated


def write_issues(issues, path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Open Issues"
    ws.append(ISSUE_HEADERS)
    for i, it in enumerate(issues, start=1):
        v = it["values"]
        ws.append([
            i, it["type"], it["sheet"], it["card"], it["row"], it["above"], it["below"],
            v["discrete"], v["signal"], v["type"], v["conn"], v["pin_out"], v["from_"],
            v["plug"], v["pin"], v["color"], v["awg"], None, None,
        ])
    for r in range(2, ws.max_row + 1):
        for c in range(1, len(ISSUE_HEADERS) + 1):
            style_cell(ws.cell(r, c), centered=c != 2)
    widths = {"B": 62, "C": 16, "H": 14, "I": 38, "J": 16, "M": 24, "R": 30, "S": 12}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = "A2"
    wb.save(path)


# ----------------------------------------------------------------------------
# Optional self check against an example target
# ----------------------------------------------------------------------------
def compare_with_example(generated_path, example_path):
    g = load_workbook(generated_path).active
    e = load_workbook(example_path).active
    diffs = 0
    rows = max(g.max_row, e.max_row)
    for r in range(1, rows + 1):
        for c in range(1, 22):
            gv, ev = g.cell(r, c).value, e.cell(r, c).value
            if gv != ev:
                diffs += 1
                print(f"  DIFF {g.cell(r, c).coordinate}: generated={gv!r} example={ev!r}")
    print(f"Compare {Path(generated_path).name} with {Path(example_path).name}: "
          f"{diffs} difference(s), generated rows={g.max_row}, example rows={e.max_row}")
    return diffs == 0


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def conn_sort_key(name):
    return int(name[1:])


def main():
    project_root = Path(__file__).resolve().parents[3]
    default_source = project_root / "tests" / "DB" / "DB_Volcan" / "source file .xlsx"

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "source",
        nargs="?",
        default=str(default_source),
        help=f"source workbook (.xlsx), default: {default_source}",
    )
    ap.add_argument(
        "-o",
        "--output-dir",
        default=None,
        help="output directory, default: the source workbook folder",
    )
    ap.add_argument("--sheets", nargs="+", default=SOURCE_SHEETS,
                    help="tabs to search, in order")
    ap.add_argument("--only", nargs="+", help="only generate these connectors, e.g. J1 J2")
    ap.add_argument("--compare", help="example target file to compare with (use with --only)")
    args = ap.parse_args()

    out = Path(args.output_dir) if args.output_dir else Path(args.source).resolve().parent
    out.mkdir(parents=True, exist_ok=True)

    wb = load_workbook(args.source, data_only=False)  # source is never modified
    rows_by_conn, issues = collect_rows(wb, args.sheets)

    wanted = sorted(rows_by_conn, key=conn_sort_key)
    if args.only:
        only = {c.strip().upper() for c in args.only}
        wanted = [c for c in wanted if c in only]
        for c in sorted(only - set(wanted)):
            print(f"WARNING: connector {c} not found in the searched tabs")

    report = []
    for conn in wanted:
        rows = rows_by_conn[conn]
        path = out / FILE_NAME_TEMPLATE.format(conn=conn)
        write_target(conn, rows, path)
        di_rows = add_di_data(path)
        per_card = OrderedDict()
        for it in rows:
            per_card[it["card"]] = per_card.get(it["card"], 0) + 1
        cards = ", ".join(f"card{k}={n}" for k, n in per_card.items())
        report.append(f"{conn}: {path.name}  {cards}, total={len(rows)}, DI rows={di_rows}")

    write_issues(issues, out / ISSUES_FILE_NAME)
    report.append("")
    report.append(f"{ISSUES_FILE_NAME}: {len(issues)} row(s)")
    summary = OrderedDict()
    for it in issues:
        key = (it["type"], it["sheet"])
        summary[key] = summary.get(key, 0) + 1
    for (t, s), n in summary.items():
        report.append(f"  {s}: {n} x {t}")

    text = "\n".join(report)
    print(text)
    (out / "run_report.txt").write_text(text + "\n", encoding="utf-8")

    if args.compare:
        if not args.only or len(wanted) != 1:
            sys.exit("--compare needs --only with exactly one connector")
        ok = compare_with_example(out / FILE_NAME_TEMPLATE.format(conn=wanted[0]), args.compare)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
