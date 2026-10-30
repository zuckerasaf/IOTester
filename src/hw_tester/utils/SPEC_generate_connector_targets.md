# Spec: Generate one target Excel file per connector (J#) from the source workbook

This document is a specification for a Python script (openpyxl based).
It was written from inspection of the two example files:
- Source workbook: `source_file.xlsx` (tabs: Spider Card #1..#4, Power Only, HSID MIV, Relay Card, Dim_Card 0-24v)
- Example target: `Target_J1.xlsx` (single sheet named `Sheet`, 49 data rows + 1 header row, columns A..U)

Everything marked **ASSUMPTION** was inferred and should be confirmed by the user. Everything else was verified against the example files.

---

## 1. Goal

Read the source workbook once. For every connector `J#` found in the Spider Card tabs, create one output file `Target_J#.xlsx` that has the same layout as `Target_J1.xlsx` and contains every source row belonging to that connector.

Example: `Target_J1.xlsx`, `Target_J2.xlsx`, `Target_J3.xlsx`, ... (one file per distinct J#).

## 2. Inputs and configuration

Put these at the top of the script as constants or CLI arguments:

| Name | Default | Meaning |
|---|---|---|
| `SOURCE_FILE` | `source_file.xlsx` | Source workbook path |
| `SOURCE_SHEETS` | `["Spider Card #1", "Spider Card #2", "Spider Card #3", "Spider Card #4"]` | Tabs to search, in this order (Card #4 added, confirmed by the user) |
| `OUTPUT_DIR` | `./output` | Where target files are written |
| `FILE_NAME_TEMPLATE` | `Target_{conn}.xlsx` | Output file name, e.g. `Target_J1.xlsx` |
| `CONNECTOR_REGEX` | `^J\d+$` | Which values in the Connector column count as a J# |
| `ONLY_CONNECTORS` | `None` | Optional list such as `["J1","J2"]` to generate a subset |
| `ISSUES_FILE_NAME` | `Open_Issues.xlsx` | Name of the extra file that collects all open issues (section 8) |

**Spider Card #4 is included** (confirmed by the user). It adds connectors J8, J19, J20, J22, J23 and extra rows for J7.

The other tabs (Power Only, HSID MIV, Relay Card, Dim_Card 0-24v) are never read.

## 3. Source tab structure (verified on Spider Card #1, #2, #3, #4)

- Rows 2 to 5: title block (merged cells B:K): part number, project, "Spider Card No.N - ", IP address. Not data.
- Row 6: header row. Data starts at row 7.
- Source columns (1-based, sheet columns B..K):

| Col | Letter | Header in source |
|---|---|---|
| 2 | B | DISCRETE NAME |
| 3 | C | SIGNAL NAME |
| 4 | D | TYPE |
| 5 | E | CONNECTOR |
| 6 | F | Pin Out |
| 7 | G | FROM |
| 8 | H | PLUG |
| 9 | I | Pin |
| 10 | J | Color |
| 11 | K | AWG |

- A tab is NOT one continuous table. It is several sections stacked vertically. Each section after the first starts with a repeated header row (first cell such as `DISCRETE NAME` or `Analog  NAME`, with the Connector cell equal to `CONNECTOR`). A section usually ends with an empty row.
  - Example, Spider Card #1: discrete I/O at rows 7 to 95, a second header at row 96 followed by outputs at rows 97 to 128, an analog header at row 130 with J1 rows at 131 to 133, and so on.
- Because of this, the same connector appears in several separate blocks of the same tab (J1 on Spider Card #1 is at rows 7 to 24, 25 to 30, 97 to 118, and 131 to 133). **Scan every row from 7 to `ws.max_row`; never stop at the first empty row or at the first block.**
- Spider Card #4 has an extra empty column L; ignore it.
- Card number = the number in the tab name (`Spider Card #3` -> `3`). Parse with regex `#(\d+)`.

## 4. Target file layout (verified from Target_J1.xlsx)

Single sheet named `Sheet`. Row 1 is the header. Header text must be copied exactly, **including the original spelling mistakes** (`Discrete Mame`, `Orignal`), because the example uses them:

| Target col | Header | Filled from |
|---|---|---|
| A | Card | Card number (int) parsed from the tab name |
| B | Discrete Mame | source col B (DISCRETE NAME) |
| C | Signal Name | source col C (SIGNAL NAME) |
| D | Type | source col D (TYPE) |
| E | Connector | source col E (CONNECTOR) |
| F | SPS | source col F (Pin Out) |
| G | Orignal | source col F (Pin Out) |
| H | Pin Out | source col F (Pin Out) |
| I | From | source col G (FROM) |
| J | Plug | source col H (PLUG) |
| K | Pin | source col I (Pin) |
| L | Color | source col J (Color) |
| M | AWG | source col K (AWG) |
| N | Power_Expected | empty |
| O | Power_Input | empty |
| P | PullUp_Expected | empty |
| Q | PullUp_Input | empty |
| R | logic_input | empty |
| S | Logic_Command | empty |
| T | Logic_Expected | empty |
| U | Test_Result | empty |

Verified in the example: for every row, columns F, G and H hold the same value, equal to the source Pin Out. **ASSUMPTION:** SPS and Orignal are meant to start as copies of Pin Out (for later editing/testing). Please confirm.

Rules for values:
- Copy values as they are, with their Python types (ints stay ints, strings stay strings). Do not strip, upper-case or convert.
- Preserve text such as `24V I\O RTN` and `A\C_LEVEL` exactly (the backslash is in the source).
- Empty source cell -> leave the target cell empty (`None`), not `""` and not `0`.
- Columns N to U are always left empty (confirmed by the user, "for now"; keep the header list in one constant so values can be added later).

### Formatting to reproduce (verified)
- Header row 1: no fill, no border, not bold, Calibri 11.
- Data rows (A2 down to the last row, columns A..U): thin border on all four sides, solid white fill (theme color 0).
- Horizontal alignment `center` for columns B to M; vertical `center` for B..I and K..M (column J has no vertical setting in the example; setting it to center is harmless). Columns A and N..U have no alignment.
- Column widths: B = 14.43, C = 40.86, all others default.
- No freeze panes, no autofilter, no conditional formatting, no merged cells.
- **Simplest reliable method:** build the new workbook with openpyxl and apply those styles directly. (Alternative: copy `Target_J1.xlsx` as a template, clear rows 2+, and write rows. Either is fine.)

## 5. Row selection logic (the core of the task)

For each configured tab, walk the rows from 7 to max_row and decide for each row which connector it belongs to.

### 5.1 Normal rows
A row belongs to connector `X` when cell E (Connector), after `str(...).strip()`, matches `CONNECTOR_REGEX` and equals `X`.
- Must be an exact match. `J1` must NOT match `J10`, `J11`, `J13`, etc. (Use equality or the anchored regex, never `in` / `startswith`.)
- Values such as `CONNECTOR`, `CONN.`, `TB7`, `TB8`, `RELAY CARD 8X2A`, `DIMMING CARD 0-24V\nDTYPE 09` and `DIMMING CARD 0-24V POWER INPUT` are not J# connectors and are ignored.

### 5.2 "Orphan" rows with an empty Connector cell
Some real signal rows have an empty Connector (E), empty Pin Out, empty From, and sometimes empty Color/AWG, but do have Discrete Name, Type, Plug and Pin. Example: `DI_13`, plug `1P1`, pin `25`, located between two J1 rows in Spider Card #1 (source row 25).

The example target **includes** this row (target row 20: B=`DI_13`, D=`Gnd/open`, J=`1P1`, K=`25`; E, F, G, H, I, L, M left empty).

But the source also contains long runs of orphan rows that must NOT be attached to J1 (for example `DI_51..DI_64` at rows 80 to 93, and `AI_2..AI_14` / `AOUT_2..` / `INC_ENC..` at rows 134 to 180 on Spider Card #1). The example target does not contain them.

**Rule derived from the example (ASSUMPTION, please confirm):**
A run of consecutive rows with empty Connector cell (and non-empty content) is assigned to connector `X` only if the nearest row above the run AND the nearest row below the run both have connector `X`, with no fully empty row and no section header row in between. Otherwise the run is not assigned to any connector.

Check against the example: row 25 is between row 24 (J1) and row 26 (J1) -> included. Rows 134 to 160: previous row 133 is J1, but the next row is an empty row/section header -> not included. Rows 80 to 93: previous is J4, next is an empty row -> not included. This reproduces exactly the 49 rows of `Target_J1.xlsx` (24 rows from rows 7 to 30 incl. the orphan, 22 rows from rows 97 to 118, 3 rows from rows 131 to 133).

For orphan rows that are included, leave the **Connector** column empty as in the source, to match the example (confirmed: do not fill in the connector name). **Every empty-connector row, included or not, is also written to `Open_Issues.xlsx`** (confirmed by the user), so the included ones get Issue Type `Included in J# file, connector cell empty in source`.

Known ambiguous case: Spider Card #3 row 87 (`DO_3`, `SPARE`, plug `3P1` pin `8`) sits between a `J7` row and a `J3` row. The rule above does not assign it to either. The script must log it as "unassigned orphan" (see section 8).

### 5.3 Row ordering inside a target file
- Order by tab (in `SOURCE_SHEETS` order), then by original source row order within the tab. Do NOT sort by pin number: the example keeps the source order (e.g. pins 7, 9, 11, 13 ... then 43, 29, 31, 34).
- A connector can appear in more than one card, and the **Card** column (A) is what tells them apart. Verified counts of J# rows per tab (strict match, orphans excluded):

| Connector | Card #1 | Card #2 | Card #3 | Card #4 |
|---|---|---|---|---|
| J1 | 48 | | | |
| J2 | 35 | 13 | | |
| J3 | 14 | 19 | 5 | |
| J4 | 10 | | 14 | |
| J5 | 5 | | | |
| J6 | | | 18 | |
| J7 | | | 12 | 7 |
| J8 | | | | 24 |
| J9 | | | 8 | |
| J10 | | 10 | | |
| J11 | | | 8 | |
| J13 | | | 5 | |
| J14 | | 7 | | |
| J15 | | | 10 | |
| J18 | | | 7 | |
| J19 | | | | 9 |
| J20 | | | | 6 |
| J22 | | | | 4 |
| J23 | | | | 36 |
| J26 | | | 7 | |

  (Counts were computed during inspection; the script should print its own counts so they can be compared. Orphan rows are extra.)
- With tabs #1 to #4, the connectors that get files are J1 to J11 (except J12), J13, J14, J15, J18, J19, J20, J22, J23, J26, i.e. the 20 connectors in the table above.
- **Combined file per connector (decision pending, see section 10, question 2):** the Card column separates rows from different cards. This is the default in this spec.

## 6. Algorithm (pseudo-code)

```python
import re
import openpyxl
from openpyxl.styles import Border, Side, Alignment, PatternFill
from collections import OrderedDict

CONN_RE = re.compile(CONNECTOR_REGEX)

def conn_of(ws, r):
    v = ws.cell(r, 5).value
    if isinstance(v, str):
        v = v.strip()
        return v if CONN_RE.match(v) else "OTHER"   # non-J connector text, header, etc.
    return None                                      # empty cell

def row_is_empty(ws, r):
    return all(ws.cell(r, c).value in (None, "") for c in range(2, 12))

def is_header_row(ws, r):
    return str(ws.cell(r, 5).value or "").strip().upper() in ("CONNECTOR", "CONN.") \
        and str(ws.cell(r, 2).value or "").upper().startswith(("DISCRETE", "ANALOG"))

rows_by_conn = OrderedDict()   # "J1" -> list of (card_no, source_row_values)

for sheet_name in SOURCE_SHEETS:
    ws = wb[sheet_name]
    card_no = int(re.search(r"#(\d+)", sheet_name).group(1))
    max_r = ws.max_row
    r = 7
    while r <= max_r:
        c = conn_of(ws, r)
        if c and c != "OTHER":
            add(rows_by_conn, c, card_no, ws, r)
            r += 1
        elif c is None and not row_is_empty(ws, r):
            # orphan run: collect consecutive rows with empty connector and some content
            start = r
            while r <= max_r and conn_of(ws, r) is None and not row_is_empty(ws, r):
                r += 1
            end = r - 1
            above = conn_of(ws, start - 1) if start > 7 else None
            below = conn_of(ws, end + 1) if end + 1 <= max_r else None
            if above and above != "OTHER" and above == below:
                for rr in range(start, end + 1):
                    add(rows_by_conn, above, card_no, ws, rr)
            else:
                log_unassigned(sheet_name, start, end, above, below)
        else:
            r += 1
```

`add(...)` stores: card number, and the values of source columns B, C, D, E, F, G, H, I, J, K.

Output step, for each connector in `rows_by_conn` (sorted numerically by the digits after `J`, filtered by `ONLY_CONNECTORS` if set):
1. Create a new workbook, rename the active sheet to `Sheet`.
2. Write the header row (section 4).
3. For each stored row write:
   `[card, B, C, D, E, F(pin out), F(pin out), F(pin out), G, H, I, J, K, None x 8]`
4. Apply formatting (section 4).
5. Save as `OUTPUT_DIR / FILE_NAME_TEMPLATE.format(conn=conn)`.

## 7. Edge cases the script must handle
- Connector values with stray spaces or different case (`"j1 "`): normalise with `.strip().upper()` for matching, but write the original value to the target. (None were found in the files inspected, but this is cheap protection.)
- Numeric vs text cells: Pin Out is numeric, `Pin` can be numeric (`1`) or text (`TB8`, `CH.1+`). Keep the type as is.
- Multi-line cell values (a `\n` inside the text): connector names containing `\n` are not J# and are ignored; other multi-line text should be copied as is.
- Merged cells: only the title block rows 2 to 5 are merged; data rows are not.
- Formulas: none were seen in the inspected areas, but load with `data_only=False` first and warn if a cell value starts with `=`. If the source has formulas, decide whether to load with `data_only=True` to get cached values.
- Missing tab in `SOURCE_SHEETS`: stop with a clear error message listing the tab names that do exist.
- A connector that exists in no configured tab: nothing is generated, and it is not an error.
- Do not modify the source file (open it read-only; write only to `OUTPUT_DIR`).
- If an output file already exists, overwrite it (log a line), or add a `--no-overwrite` flag.

## 8. Open issues file and run report

### 8.1 `Open_Issues.xlsx` (new, requested by the user)
One extra Excel file, written to `OUTPUT_DIR`, that concentrates everything the script could not place automatically, so the user can review it in one place. One sheet named `Open Issues`, header in row 1, one row per source row (not per run), same formatting style as the target files (thin borders, centered), plus an autofilter on the header row.

| Col | Header | Content |
|---|---|---|
| A | Issue ID | Running number (1, 2, 3 ...) |
| B | Issue Type | Text, see below |
| C | Source Tab | e.g. `Spider Card #3` |
| D | Card | Card number |
| E | Source Row | Excel row number in the source tab |
| F | Connector Above | Nearest connector above the run (or empty) |
| G | Connector Below | Nearest connector below the run (or empty) |
| H | Discrete Name | source col B |
| I | Signal Name | source col C |
| J | Type | source col D |
| K | Connector | source col E |
| L | Pin Out | source col F |
| M | From | source col G |
| N | Plug | source col H |
| O | Pin | source col I |
| P | Color | source col J |
| Q | AWG | source col K |
| R | Notes | Free text column left empty for the user |
| S | Status | Left empty (user fills, e.g. Open / Closed) |

Issue types the script produces (initial list; extend by adding rows to a small table in the code):
- `Included in J# file, connector cell empty in source` (sandwiched rows such as DI_13; put the J# in the Connector Above column). These rows are in BOTH the J file and the issues file.
- `Unassigned row: empty connector, not between two rows of the same J#` (the orphan runs rejected by the rule in 5.2). Covers for example the unused DI/AI/AOUT/INC_ENC channels with only a plug and pin, and Card #3 row 87 (`DO_3`, between J7 and J3).

Size estimate from the inspection (unassigned rows only; add 3 sandwiched rows, one each on Cards #1, #2 and #4) (using the 5.2 rule on tabs #1 to #4): about 281 unassigned rows in 25 runs (Card #1: 51 rows in 4 runs, Card #2: 94 in 6, Card #3: 56 in 8, Card #4: 80 in 7). Many are probably unused or spare channels, but that is an interpretation; the user decides. Please treat these numbers as approximate and let the script print its own.

The file is always created, even when empty (header only).

### 8.2 Console / text run report
Print and also write `output/run_report.txt` containing:
1. Per connector: file name, total rows, rows per card (`J2: card1=35, card2=13, total=48`).
2. Orphan rows that were included in a connector file (tab, source rows, connector).
3. Count of rows written to `Open_Issues.xlsx`, grouped by Issue Type and tab.

## 9. Acceptance test
Run the script with `ONLY_CONNECTORS=["J1"]` on the provided source. The generated `Target_J1.xlsx` must match the example `Target_J1.xlsx` cell for cell for columns A..M over rows 1 to 50 (50 rows, 21 columns, N..U empty), with the same column widths for B and C and the same borders/fill/alignment. Compare programmatically with openpyxl and report any difference.

## 10. Open questions for the user (answers change the logic)
1. ~~Spider Card #4~~ Answered: yes, include it.
2. ~~Combined vs split~~ The answer was "yes", which does not pick between the two options. This spec keeps ONE combined file per connector with a Card column; confirm or ask for one file per connector per card.
3. Is the orphan-row rule in 5.2 right (blank-connector rows included only when the rows directly above and below belong to the same J#)? It reproduces the J1 example exactly, but it is inferred from one example.
4. ~~SPS and Orignal~~ Answered: yes, always plain copies of Pin Out.
5. ~~Fill empty Connector cell~~ Answered: no. Empty-connector rows are NOT given a connector name; they are reported in `Open_Issues.xlsx`. Sandwiched rows such as DI_13 stay in the J file (as in the example, connector cell left empty) AND are also listed in `Open_Issues.xlsx` (confirmed by the user).
6. ~~Test columns N to U~~ Answered: yes, stay empty for now (keep this easy to change later, e.g. a constant list of extra columns).

## 11. Suggested script structure
- `config` section (constants from section 2)
- `load_source()` returns workbook
- `collect_rows()` implements section 5 and returns `rows_by_conn` plus report info
- `write_target(conn, rows)` implements sections 4 and 6
- `main()` ties it together, writes the report, runs the optional self-check from section 9
- Dependencies: Python 3.9+, `openpyxl` only. Verify `openpyxl` API names (`Border`, `Side`, `Alignment`, `PatternFill`, `Workbook`, `column_dimensions`) against the current openpyxl documentation when writing the script.
