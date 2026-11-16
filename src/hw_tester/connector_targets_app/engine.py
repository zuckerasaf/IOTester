#!/usr/bin/env python3
"""Engine: build one Target_J#.xlsx per connector from a source workbook.

Everything that used to be hard coded (source tabs, source columns, the routing of
source columns to target columns, the fill rules for the test columns) is read from a
configuration dict (see default_config()). The Qt app edits that dict; this module can
also be used from the command line:

    python engine.py source.xlsx -o output [--config my_config.json] [--only J1 J2]
    python engine.py --dump-default-config > my_config.json

Requires: openpyxl
"""
import argparse
import copy
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, PatternFill, Side
from openpyxl.utils import column_index_from_string, get_column_letter

# ----------------------------------------------------------------------------
# Default configuration (reproduces the behaviour of the attached generate_targets.py)
# ----------------------------------------------------------------------------
# Target column "source" values:
#   "@card"   card number parsed from the tab name
#   "@const"  the text in "constant"
#   ""        left empty
#   <key>     the key of a source field (see "source_fields")
# Rule condition ops: contains, not_contains, equals, not_equals, starts_with,
#   regex (re.search; groups usable as {g1}, {g2} ...), is_empty, not_empty,
#   code_number (value = letters such as DI: matches DI5 / DI_5 and gives the number as {g1})
# Assignment templates: text with placeholders
#   {X}         value of target column X (letter) of the same row
#   {X|num}     first number found in column X
#   {X|rangemax} the larger of the two numbers in a range such as "0-24"
#   {g1}        group 1 of the last regex condition that matched
#   {H@J=text}  value of column H in the FIRST row of the connector whose column J contains "text"
# If any placeholder is empty the assignment is skipped. A result that looks like a
# number is stored as a number, anything else as text.


def default_config():
    return {
        "version": 1,
        "source_sheets": ["Spider Card #1", "Spider Card #2", "Spider Card #3", "Spider Card #4"],
        "first_data_row": 7,
        "connector_regex": r"^J\d+$",
        "card_regex": r"#(\d+)",
        "file_name_template": "Target_{conn}.xlsx",
        "issues_file_name": "Open_Issues.xlsx",
        "output_sheet_name": "Sheet",
        "connector_field": "conn",
        "source_fields": [
            {"key": "discrete", "label": "Discrete Name", "column": "B"},
            {"key": "signal", "label": "Signal Name", "column": "C"},
            {"key": "type", "label": "Type", "column": "D"},
            {"key": "conn", "label": "Connector", "column": "E"},
            {"key": "pin_out", "label": "Pin Out", "column": "F"},
            {"key": "from_", "label": "From", "column": "G"},
            {"key": "plug", "label": "Plug", "column": "H"},
            {"key": "pin", "label": "Pin", "column": "I"},
            {"key": "color", "label": "Color", "column": "J"},
            {"key": "awg", "label": "AWG", "column": "K"},
        ],
        # Headers are kept exactly as in the example target (including its spelling).
        "target_columns": [
            {"header": "Card", "source": "@card", "constant": ""},
            {"header": "Discrete Mame", "source": "discrete", "constant": ""},
            {"header": "Signal Name", "source": "signal", "constant": ""},
            {"header": "Type", "source": "type", "constant": ""},
            {"header": "Connector", "source": "conn", "constant": ""},
            {"header": "SPS", "source": "pin_out", "constant": ""},
            {"header": "Orignal", "source": "pin_out", "constant": ""},
            {"header": "Pin Out", "source": "pin_out", "constant": ""},
            {"header": "From", "source": "from_", "constant": ""},
            {"header": "Plug", "source": "plug", "constant": ""},
            {"header": "Pin", "source": "pin", "constant": ""},
            {"header": "Color", "source": "color", "constant": ""},
            {"header": "AWG", "source": "awg", "constant": ""},
            {"header": "Power_Expected", "source": "", "constant": ""},
            {"header": "Power_Input", "source": "", "constant": ""},
            {"header": "PullUp_Expected", "source": "", "constant": ""},
            {"header": "PullUp_Input", "source": "", "constant": ""},
            {"header": "logic_input", "source": "", "constant": ""},
            {"header": "Logic_Command", "source": "", "constant": ""},
            {"header": "Logic_Expected", "source": "", "constant": ""},
            {"header": "Test_Result", "source": "", "constant": ""},
        ],
        # Rules are tried top to bottom. "stop" = stop after this rule matched.
        # Conditions refer to TARGET columns (letters A, B, ...).
        "rules": [
            {"name": "AI rows", "enabled": True, "stop": True,
             "conditions": [{"column": "B", "op": "regex", "value": r"(?<![A-Za-z])AI_?(\d+)"}],
             "assignments": [{"column": "N", "value": "1"},
                             {"column": "R", "value": "TBD"},
                             {"column": "T", "value": "C{A|num}_AI{g1}_10"}]},
            {"name": "Red wire with voltage in Plug", "enabled": True, "stop": True,
             "conditions": [{"column": "L", "op": "contains", "value": "RED"},
                            {"column": "J", "op": "regex", "value": r"(\d+(?:\.\d+)?)\s*V\b"}],
             "assignments": [{"column": "N", "value": "{g1}"},
                             {"column": "O", "value": "P"}]},
            {"name": "RTN plug", "enabled": True, "stop": True,
             "conditions": [{"column": "J", "op": "contains", "value": "RTN"}],
             "assignments": [{"column": "N", "value": "0"},
                             {"column": "P", "value": "0"},
                             {"column": "Q", "value": "G"}]},
            {"name": "CH. minus pin", "enabled": True, "stop": True,
             "conditions": [{"column": "K", "op": "contains", "value": "CH."},
                            {"column": "K", "op": "contains", "value": "-"}],
             "assignments": [{"column": "N", "value": "0"},
                             {"column": "P", "value": "0"},
                             {"column": "Q", "value": "G"}]},
            {"name": "Red CH. plus pin (voltage from From range)", "enabled": True, "stop": True,
             "conditions": [{"column": "L", "op": "contains", "value": "RED"},
                            {"column": "K", "op": "contains", "value": "CH"},
                            {"column": "K", "op": "contains", "value": "+"}],
             "assignments": [{"column": "N", "value": "{I|rangemax}"},
                             {"column": "O", "value": "TBD"}]},
            {"name": "DI rows", "enabled": True, "stop": True,
             "conditions": [{"column": "B", "op": "regex", "value": r"(?<![A-Za-z])DI_?(\d+)"}],
             "assignments": [{"column": "N", "value": "3.5"},
                             {"column": "R", "value": "TBD"},
                             {"column": "T", "value": "C{A|num}_DI{g1}_0"}]},
            {"name": "DO rows", "enabled": True, "stop": True,
             "conditions": [{"column": "B", "op": "regex", "value": r"(?<![A-Za-z])DO_?(\d+)"}],
             "assignments": [{"column": "N", "value": "0"},
                             {"column": "P", "value": "4"},
                             {"column": "Q", "value": "C{A|num}_DO{g1}_1"}]},
        ],
    }


ISSUE_UNASSIGNED = "Unassigned row: empty connector, not between two rows of the same J#"
ISSUE_INCLUDED = "Included in {conn} file, connector cell empty in source"
ISSUE_NO_RULE_MATCH = "No fill rule matched; rule target columns stayed empty"
ISSUE_TBD = "TBD value in target file; needs manual fix"

THIN = Side(style="thin")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WHITE = PatternFill(fill_type="solid", fgColor="FFFFFF")
CENTER = Alignment(horizontal="center", vertical="center")

OPS = ["contains", "not_contains", "equals", "not_equals", "starts_with",
       "code_number", "regex", "is_empty", "not_empty"]
PLACEHOLDER_RE = re.compile(r"\{([A-Za-z]{1,3}|g\d+)(?:\|(\w+))?\}")
LOOKUP_RE = re.compile(r"\{([A-Za-z]{1,3})@([A-Za-z]{1,3})=([^{}]*)\}")
NUMBER_RE = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?")
FIRST_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
RANGE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)")


class ConfigError(Exception):
    pass


class FileLockedError(ConfigError):
    """Output file(s) are open in another program (e.g. Excel)."""


def locked_files(paths):
    """Return the existing files among paths that cannot be written because another program holds them."""
    locked = []
    for p in paths:
        p = Path(p)
        if p.is_file():
            try:
                with open(p, "r+b"):
                    pass
            except OSError:
                locked.append(p.name)
    return locked


# ----------------------------------------------------------------------------
# Config helpers
# ----------------------------------------------------------------------------
def load_config(path):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    cfg = default_config()
    cfg.update(data)
    return cfg


def save_config(cfg, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)


def target_letter(i):
    return get_column_letter(i + 1)


def validate_config(cfg):
    """Return a list of error strings (empty list = valid)."""
    errors = []
    keys = [f["key"] for f in cfg["source_fields"]]
    if len(set(keys)) != len(keys):
        errors.append("Source fields: duplicate keys")
    for f in cfg["source_fields"]:
        try:
            column_index_from_string(f["column"].strip().upper())
        except Exception:
            errors.append(f"Source field '{f.get('label')}': bad column letter {f.get('column')!r}")
    if cfg["connector_field"] not in keys:
        errors.append("Connector field is not one of the source fields")
    for rx_name in ("connector_regex", "card_regex"):
        try:
            re.compile(cfg[rx_name])
        except re.error as e:
            errors.append(f"{rx_name}: {e}")
    if "{conn}" not in cfg["file_name_template"]:
        errors.append("File name template must contain {conn}")
    if not cfg["source_sheets"]:
        errors.append("No source tabs selected")
    letters = {target_letter(i) for i in range(len(cfg["target_columns"]))}
    for i, t in enumerate(cfg["target_columns"]):
        s = t["source"]
        if s not in ("", "@card", "@const") and s not in keys:
            errors.append(f"Target column {target_letter(i)}: unknown source {s!r}")
    for r in cfg["rules"]:
        nm = r.get("name", "?")
        for c in r["conditions"]:
            if c["column"].upper() not in letters:
                errors.append(f"Rule '{nm}': unknown column {c['column']!r}")
            if c["op"] not in OPS:
                errors.append(f"Rule '{nm}': unknown operator {c['op']!r}")
            if c["op"] == "code_number" and not re.fullmatch(r"[A-Za-z]+", c["value"].strip()):
                errors.append(f"Rule '{nm}': code_number needs letters only, e.g. DI (got {c['value']!r})")
            if c["op"] == "regex":
                try:
                    re.compile(c["value"])
                except re.error as e:
                    errors.append(f"Rule '{nm}': bad regex {c['value']!r}: {e}")
        for a in r["assignments"]:
            if a["column"].upper() not in letters:
                errors.append(f"Rule '{nm}': assignment to unknown column {a['column']!r}")
            for want, find, _t in LOOKUP_RE.findall(a["value"]):
                if want.upper() not in letters or find.upper() not in letters:
                    errors.append(f"Rule '{nm}': lookup {{{want}@{find}=...}} uses an unknown column")
            for ph, flt in PLACEHOLDER_RE.findall(a["value"]):
                if not ph.startswith("g") and ph.upper() not in letters:
                    errors.append(f"Rule '{nm}': placeholder {{{ph}}} is not a column")
                if flt and flt not in ("num", "rangemax"):
                    errors.append(f"Rule '{nm}': unknown filter {flt!r} (use num or rangemax)")
    return errors


# ----------------------------------------------------------------------------
# Reading the source
# ----------------------------------------------------------------------------
class Source:
    """Pre-computed lookups for one run (column indexes, compiled regexes)."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.cols = {f["key"]: column_index_from_string(f["column"].strip().upper())
                     for f in cfg["source_fields"]}
        self.conn_col = self.cols[cfg["connector_field"]]
        self.conn_re = re.compile(cfg["connector_regex"])
        self.card_re = re.compile(cfg["card_regex"])
        self.first_row = int(cfg["first_data_row"])

    def conn_of(self, ws, r):
        """'J#' (normalised), 'OTHER' (non-matching text) or None (empty)."""
        v = ws.cell(r, self.conn_col).value
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        if isinstance(v, str) and self.conn_re.match(v.strip().upper()):
            return v.strip().upper()
        return "OTHER"

    def row_is_empty(self, ws, r):
        return all(ws.cell(r, c).value in (None, "") for c in self.cols.values())

    def row_values(self, ws, r):
        return {k: ws.cell(r, c).value for k, c in self.cols.items()}

    def card_number(self, sheet_name):
        m = self.card_re.search(sheet_name)
        if not m:
            raise ConfigError(f"Cannot find a card number in tab name {sheet_name!r} "
                              f"with pattern {self.card_re.pattern!r}")
        return int(m.group(1))


def collect_rows(wb, cfg):
    """Return (rows_by_conn, issues)."""
    src = Source(cfg)
    missing = [n for n in cfg["source_sheets"] if n not in wb.sheetnames]
    if missing:
        raise ConfigError(f"Missing tab(s) {missing}. Tabs in file: {wb.sheetnames}")

    rows_by_conn = OrderedDict()
    issues = []
    for sheet in cfg["source_sheets"]:
        ws = wb[sheet]
        card = src.card_number(sheet)
        max_r = ws.max_row
        r = src.first_row
        while r <= max_r:
            c = src.conn_of(ws, r)
            if c and c != "OTHER":
                rows_by_conn.setdefault(c, []).append(
                    dict(card=card, row=r, sheet=sheet, values=src.row_values(ws, r)))
                r += 1
            elif c is None and not src.row_is_empty(ws, r):
                # Run of rows with an empty connector cell but other content.
                start = r
                while r <= max_r and src.conn_of(ws, r) is None and not src.row_is_empty(ws, r):
                    r += 1
                end = r - 1
                above = src.conn_of(ws, start - 1) if start > src.first_row else None
                below = src.conn_of(ws, end + 1) if end + 1 <= max_r else None
                same = above not in (None, "OTHER") and above == below
                for rr in range(start, end + 1):
                    vals = src.row_values(ws, rr)
                    if same:
                        rows_by_conn.setdefault(above, []).append(
                            dict(card=card, row=rr, sheet=sheet, values=vals))
                    issues.append(dict(
                        type=ISSUE_INCLUDED.format(conn=above) if same else ISSUE_UNASSIGNED,
                        sheet=sheet, card=card, row=rr,
                        above=None if above == "OTHER" else above,
                        below=None if below == "OTHER" else below, values=vals))
            else:
                r += 1
    return rows_by_conn, issues


def list_sheets(path):
    wb = load_workbook(path, read_only=True)
    names = list(wb.sheetnames)
    wb.close()
    return names


# ----------------------------------------------------------------------------
# Building rows and applying the fill rules
# ----------------------------------------------------------------------------
def build_row(cfg, item):
    out = []
    for t in cfg["target_columns"]:
        s = t["source"]
        if s == "@card":
            out.append(item["card"])
        elif s == "@const":
            out.append(t.get("constant") or None)
        elif s == "":
            out.append(None)
        else:
            out.append(item["values"].get(s))
    return out


def _text(v):
    return "" if v is None else str(v).strip()


def _code_number_re(letters):
    """'code_number' operator: the letters (e.g. DI) not preceded by another letter, an optional
    '_', then a number. Same as the regex (?<![A-Za-z])DI_?(\\d+), the number is {g1}."""
    return re.compile(r"(?<![A-Za-z])" + re.escape(letters.strip()) + r"_?(\d+)", re.IGNORECASE)


def _eval_condition(cond, row, state):
    idx = column_index_from_string(cond["column"].upper()) - 1
    cell = _text(row[idx]) if idx < len(row) else ""
    op, val = cond["op"], cond["value"]
    cu, vu = cell.upper(), val.upper()
    if op == "contains":
        return vu in cu
    if op == "not_contains":
        return vu not in cu
    if op == "equals":
        return cu == vu
    if op == "not_equals":
        return cu != vu
    if op == "starts_with":
        return cu.startswith(vu)
    if op == "is_empty":
        return cell == ""
    if op == "not_empty":
        return cell != ""
    if op == "code_number":
        m = _code_number_re(val).search(cell)
        if m:
            state["groups"] = m.groups()
            return True
        return False
    if op == "regex":
        m = re.search(val, cell, re.IGNORECASE)
        if m:
            # A regex without groups must not wipe groups set by an earlier condition.
            if m.groups():
                state["groups"] = m.groups()
            return True
        return False
    raise ConfigError(f"Unknown operator {op!r}")


def _lookup(spec, all_rows):
    """{H@J=text}: value of column H in the first row of the connector whose column J contains text.
    {H@N==10}: same, but column N must equal the text exactly."""
    want_col, find_col, text = spec
    wi = column_index_from_string(want_col.upper()) - 1
    fi = column_index_from_string(find_col.upper()) - 1
    exact = text.startswith("=")
    needle = (text[1:] if exact else text).strip().upper()
    for r in all_rows or []:
        if fi < len(r) and wi < len(r):
            cell = _text(r[fi]).upper()
            if (cell == needle) if exact else (needle in cell):
                return _text(r[wi])
    return ""


def _render(template, row, groups, all_rows=None):
    """Return rendered value (number or text) or None if any placeholder is empty."""
    empty = False

    def sub_lookup(m):
        nonlocal empty
        val = _lookup(m.groups(), all_rows)
        if val == "":
            empty = True
        return val

    template = LOOKUP_RE.sub(sub_lookup, template)

    def sub(m):
        nonlocal empty
        ph, flt = m.group(1), m.group(2)
        if ph.startswith("g") and ph[1:].isdigit():
            n = int(ph[1:])
            val = groups[n - 1] if 0 < n <= len(groups) and groups[n - 1] is not None else ""
        else:
            idx = column_index_from_string(ph.upper()) - 1
            val = _text(row[idx]) if idx < len(row) else ""
            if flt == "num":
                mm = FIRST_NUMBER_RE.search(val)
                val = mm.group() if mm else ""
            elif flt == "rangemax":
                mm = RANGE_RE.search(val)
                if mm:
                    f = max(float(mm.group(1)), float(mm.group(2)))
                    val = str(int(f)) if f.is_integer() else str(f)
                else:
                    val = ""
        if val == "":
            empty = True
        return val

    result = PLACEHOLDER_RE.sub(sub, template)
    if empty or result == "":
        return None
    if NUMBER_RE.fullmatch(result):
        f = float(result)
        return int(f) if re.fullmatch(r"-?\d+", result) else f
    return result


def apply_rules(cfg, row, hits=None, all_rows=None):
    """Apply the fill rules to one row (list, modified in place). Returns names of
    the rules that matched. hits: optional dict rule name -> count.
    all_rows: all rows of the connector, used by {X@Y=text} lookups."""
    matched = []
    for rule in cfg["rules"]:
        if not rule.get("enabled", True):
            continue
        state = {"groups": ()}
        if not all(_eval_condition(c, row, state) for c in rule["conditions"]):
            continue
        matched.append(rule["name"])
        if hits is not None:
            hits[rule["name"]] = hits.get(rule["name"], 0) + 1
        for a in rule["assignments"]:
            value = _render(a["value"], row, state["groups"], all_rows)
            if value is not None:
                row[column_index_from_string(a["column"].upper()) - 1] = value
        if rule.get("stop", True):
            break
    return matched


def _rule_assignment_columns(cfg):
    cols = set()
    for rule in cfg["rules"]:
        if not rule.get("enabled", True):
            continue
        for a in rule["assignments"]:
            cols.add(column_index_from_string(a["column"].upper()) - 1)
    return sorted(cols)


def _is_empty_cell(v):
    return _text(v) == ""


def _build_no_rule_issue(issue_id):
    return dict(
        type=ISSUE_NO_RULE_MATCH,
        sheet=issue_id["sheet"],
        card=issue_id["card"],
        row=issue_id["row"],
        above=None,
        below=None,
        values=issue_id["values"],
    )


def _build_tbd_issues(cfg, item, row, target_name, target_row):
    """One issue per cell of the finished target row that still contains a TBD placeholder."""
    issues = []
    for i, v in enumerate(row):
        if "TBD" not in _text(v).upper():
            continue
        header = cfg["target_columns"][i]["header"]
        note = (f"{target_name or 'target file'}: row {target_row}, "
                f"column {target_letter(i)} ({header}) = {_text(v)}")
        issues.append(dict(type=ISSUE_TBD, sheet=item["sheet"], card=item["card"], row=item["row"],
                           above=None, below=None, values=item["values"], note=note))
    return issues


# ----------------------------------------------------------------------------
# Writing outputs
# ----------------------------------------------------------------------------
def style_cell(cell, centered):
    cell.border = BORDER
    cell.fill = WHITE
    if centered:
        cell.alignment = CENTER


def build_target_rows(cfg, rows, hits=None, use_rules=True, validation_issues=None, target_name=None):
    out = []
    rule_cols = _rule_assignment_columns(cfg) if use_rules else []
    built = [build_row(cfg, item) for item in rows]
    # First pass on copies: lookups such as {H@N==10} must see values that other rules write.
    lookup_rows = [list(b) for b in built]
    if use_rules:
        for b in lookup_rows:
            apply_rules(cfg, b, None, [list(x) for x in built])
    for n, (item, r) in enumerate(zip(rows, built)):
        matched = []
        if use_rules:
            matched = apply_rules(cfg, r, hits, lookup_rows)
            if validation_issues is not None and not matched and rule_cols:
                if all(_is_empty_cell(r[i]) for i in rule_cols):
                    validation_issues.append(_build_no_rule_issue(item))
        if validation_issues is not None:
            validation_issues.extend(_build_tbd_issues(cfg, item, r, target_name, n + 2))
        out.append(r)
    return out


def write_target(cfg, rows, path, hits=None, use_rules=True, validation_issues=None):
    wb = Workbook()
    ws = wb.active
    ws.title = cfg.get("output_sheet_name") or "Sheet"
    headers = [t["header"] for t in cfg["target_columns"]]
    ws.append(headers)
    for r in build_target_rows(cfg, rows, hits, use_rules, validation_issues, Path(path).name):
        ws.append(r)
    for r in range(2, ws.max_row + 1):
        for c in range(1, len(headers) + 1):
            style_cell(ws.cell(r, c), centered=2 <= c <= 13)
    ws.column_dimensions["B"].width = 14.42578125
    ws.column_dimensions["C"].width = 40.85546875
    wb.save(path)


def write_issues(cfg, issues, path):
    labels = [f["label"] for f in cfg["source_fields"]]
    keys = [f["key"] for f in cfg["source_fields"]]
    headers = ["Issue ID", "Issue Type", "Source Tab", "Card", "Source Row",
               "Connector Above", "Connector Below"] + labels + ["Notes", "Status"]
    wb = Workbook()
    ws = wb.active
    ws.title = "Open Issues"
    ws.append(headers)
    for i, it in enumerate(issues, start=1):
        ws.append([i, it["type"], it["sheet"], it["card"], it["row"], it["above"], it["below"]]
                  + [it["values"].get(k) for k in keys] + [it.get("note"), None])
    for r in range(2, ws.max_row + 1):
        for c in range(1, len(headers) + 1):
            style_cell(ws.cell(r, c), centered=c != 2)
    ws.column_dimensions["B"].width = 62
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions[get_column_letter(len(headers) - 1)].width = 70
    ws.auto_filter.ref = ws.dimensions
    ws.freeze_panes = "A2"
    wb.save(path)


# ----------------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------------
def conn_sort_key(name):
    m = re.search(r"\d+", name)
    return (int(m.group()) if m else 0, name)


def run(source_path, out_dir, cfg, only=None, log=print, use_rules=True):
    """Generate all files. Returns dict(files=[...], report=str)."""
    errors = validate_config(cfg)
    if errors:
        raise ConfigError("Configuration problems:\n- " + "\n- ".join(errors))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    log(f"Reading {source_path} ...")
    wb = load_workbook(source_path, data_only=False)  # the source is never modified
    rows_by_conn, issues = collect_rows(wb, cfg)

    wanted = sorted(rows_by_conn, key=conn_sort_key)
    if only:
        only_set = {c.strip().upper() for c in only}
        wanted = [c for c in wanted if c in only_set]
        for c in sorted(only_set - set(wanted)):
            log(f"WARNING: connector {c} not found in the searched tabs")

    report, files, hits = [], [], {}
    targets = [out / cfg["file_name_template"].format(conn=c) for c in wanted] + [out / cfg["issues_file_name"]]
    locked = locked_files(targets)
    if locked:
        raise FileLockedError("Need to close the file(s) before generating:\n- " + "\n- ".join(locked))
    for conn in wanted:
        rows = rows_by_conn[conn]
        path = out / cfg["file_name_template"].format(conn=conn)
        write_target(cfg, rows, path, hits, use_rules, issues)
        files.append(str(path))
        per_card = OrderedDict()
        for it in rows:
            per_card[it["card"]] = per_card.get(it["card"], 0) + 1
        cards = ", ".join(f"card{k}={n}" for k, n in per_card.items())
        line = f"{conn}: {path.name}  {cards}, total={len(rows)}"
        report.append(line)
        log(line)

    ipath = out / cfg["issues_file_name"]
    write_issues(cfg, issues, ipath)
    files.append(str(ipath))
    report += ["", f"{ipath.name}: {len(issues)} row(s)"]
    summary = OrderedDict()
    for it in issues:
        summary[(it["type"], it["sheet"])] = summary.get((it["type"], it["sheet"]), 0) + 1
    for (t, s), n in summary.items():
        report.append(f"  {s}: {n} x {t}")
    if use_rules:
        report += ["", "Rule hits (rows matched):"]
        for rule in cfg["rules"]:
            if rule.get("enabled", True):
                report.append(f"  {rule['name']}: {hits.get(rule['name'], 0)}")
    text = "\n".join(report)
    (out / "run_report.txt").write_text(text + "\n", encoding="utf-8")
    log("\n".join(report[len(wanted):]))
    return dict(files=files, report=text)


def preview(source_path, cfg, conn):
    """Return (headers, rows) for one connector without writing files."""
    errors = validate_config(cfg)
    if errors:
        raise ConfigError("Configuration problems:\n- " + "\n- ".join(errors))
    wb = load_workbook(source_path, data_only=False)
    rows_by_conn, _ = collect_rows(wb, cfg)
    headers = [t["header"] for t in cfg["target_columns"]]
    return headers, build_target_rows(cfg, rows_by_conn.get(conn, []))


def list_connectors(source_path, cfg):
    wb = load_workbook(source_path, data_only=False)
    rows_by_conn, _ = collect_rows(wb, cfg)
    return sorted(rows_by_conn, key=conn_sort_key)


# ----------------------------------------------------------------------------
# Command line
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", nargs="?")
    ap.add_argument("-o", "--output-dir", default=None)
    ap.add_argument("--config", help="JSON configuration (default: built-in)")
    ap.add_argument("--only", nargs="+")
    ap.add_argument("--no-rules", action="store_true")
    ap.add_argument("--dump-default-config", action="store_true")
    args = ap.parse_args()
    if args.dump_default_config:
        print(json.dumps(default_config(), indent=2))
        return
    if not args.source:
        ap.error("source workbook required")
    cfg = load_config(args.config) if args.config else default_config()
    out = args.output_dir or str(Path(args.source).resolve().parent)
    try:
        run(args.source, out, cfg, args.only, use_rules=not args.no_rules)
    except ConfigError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
