# Connector Targets (Qt app)

Builds one `Target_J#.xlsx` per connector from the Spider Card tabs of a source workbook,
plus `Open_Issues.xlsx` for rows that need manual review.

## Install and start
    pip install -r requirements.txt
    python app.py

Command line (no window) with the same engine:
    python engine.py source.xlsx -o output --config config.json --only J1 J2

## Pages
- **Run**: choose the source file and output folder, "Load tabs from source" reads the tab names,
  "Preview connector" shows one target file without writing, "Generate files" writes everything.
  The log shows the rows per connector, the issues file and how many rows each rule matched.
- **Source & Tabs**: which tabs are searched (and in which order), first data row, connector pattern,
  card number pattern, file name template (`{conn}`), and which Excel column holds which source field.
- **Column Mapping**: for each target column (A, B, ...), its header text and which source field,
  card number, constant text or nothing feeds it. This is the "routing" of cells from source to target.
- **Fill Rules**: rules that fill the test columns (N to U) after the file is built. See the help text on the page.

## Configuration
Menu *Configuration*: Load config file / Save / Save as / Reset (reload file) / Built-in defaults.
`config.json` next to `app.py` is loaded at start-up when it exists. `default_config.json` is the built-in default (same rules as the original
`generate_targets.py`: AI, red wire with voltage, RTN, CH. minus, red CH. plus, DI, DO).

## Rule syntax
- Conditions look at target columns (letters). Operators: contains, not_contains, equals, not_equals,
  starts_with, regex, is_empty, not_empty. Case is ignored. All conditions of a rule must be true.
- Values: text/number, or a template: `{A}` text of column A, `{A|num}` first number in A,
  `{I|rangemax}` larger number of a range such as `0-24`, `{g1}` group 1 of the regex condition,
  `{H@J=text}` value of column H in the first row of the connector whose column J contains `text`
  (`{H@N==10}` with a double `=` requires column N to equal the text exactly).
- If a placeholder is empty the value is not written. Number-like results are stored as numbers.
- Rules run top to bottom; "Stop after this rule" skips the rest for that row.

## Notes
- The source workbook is never modified.
- Rows with an empty connector cell are kept in a connector file only when the rows directly above and
  below belong to the same connector; all of them are listed in the issues file.
- Validation: if a row did not match any enabled fill rule and all rule-target columns stayed empty,
  the row is added to `Open_Issues.xlsx` as "No fill rule matched; rule target columns stayed empty".
