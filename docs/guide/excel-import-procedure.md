# Excel Import and Transformation Procedure

This procedure describes the Excel-processing utilities in
[`read_excell.py`](../../src/hw_tester/utils/read_excell.py). The module has
three related responsibilities:

1. Transform source wiring workbooks into the column format used by IO Tester.
2. Split a Volcan workbook into one output workbook per connector.
3. Load a prepared workbook into the application's `Connector` and `Pin`
   objects.

The procedure is intended for preparing test data before loading it in the IO
Tester application.

## Prerequisites

- Windows workstation with the IO Tester project available at
  `C:\ArduinoProject\IO_Tester`.
- Python environment with the project dependencies installed.
- Source workbooks in `.xlsx` format. The script searches for `.xls` files in
  its batch mode, but `openpyxl` normally cannot read the older binary `.xls`
  format. Convert those files to `.xlsx` before processing.
- A source workbook whose first row is a header row and whose data starts on
  row 2.

Install the project in editable mode if necessary:

```powershell
cd C:\ArduinoProject\IO_Tester
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## Standard workbook transformation

### What the procedure does

`copy_and_transform_excel()` creates a new workbook in the same directory as
the source workbook. The output name is the source name prefixed with
`IOTester`, for example:

```text
J31_Gunner_Display_Unit.xlsx
IOTesterJ31_Gunner_Display_Unit.xlsx
```

The source workbook is not modified.

For each source data row, the function:

1. Creates a new workbook with the standard IO Tester headers.
2. Copies source columns into the tester layout.
3. Reads the source signal, type, color, and plug fields.
4. Applies the power, pull-up, card, pin, and logic rules.
5. Saves the transformed workbook beside the source workbook.

The selected worksheet is the first worksheet unless `sheet_name` is supplied.

### Standard output columns

The generated workbook has these columns:

| Column | Header | Purpose |
|---|---|---|
| A | `Card` | Spider/card number |
| B | `DISCRETE NAME` | Discrete or source name |
| C | `SIGNAL NAME \ Data` | Signal description |
| D | `TYPE` | Signal type |
| E | `CONNECTOR` | Connector identifier |
| F | `SPS \ Vendor` | Pin/SPS value |
| G | `orignal` | Original pin value |
| H | `Pin Out Final` | Final pin-out value |
| I | `FROM` | Source endpoint |
| J | `PLUG` | Plug description |
| K | `Pin` | Pin number |
| L | `Color` | Wire color |
| M | `AWG` | Wire gauge |
| N | `Power_Expected` | Expected power voltage |
| O | `Power_Input` | Power measurement/input command |
| P | `PullUp_Expected` | Expected pull-up voltage |
| Q | `PullUp_Input` | Pull-up input/command |
| R | `logic_input` | Logic input value or `TBD` |
| S | `Logic_Command` | Logic command |
| T | `Logic_Expected` | Expected logic result |
| U | `Test_Result` | Reserved for test results |

### Source-to-output column mapping

The standard transformation copies source columns as follows:

| Source | Destination |
|---|---|
| B | E |
| C | C |
| D | J |
| E | M |
| F | L |
| G | B |
| H | I |

Source column A is not copied by the ordinary mapping. The `Card` value in
column A is filled or replaced by the card rules described below.

### Select the source format

The `config_name` argument selects which source columns contain the fields used
by the transformation rules:

| Configuration | Signal name | Wire color | Type/associated potential |
|---|---:|---:|---:|
| `DB_Gunner_MK4` | C | E | F |
| `DB_Gunner_MK3` | C | F | G |

The current `main()` procedure is configured for `DB_Gunner_MK3` and processes
files in:

```text
C:\ArduinoProject\IO_Tester\DB_Gunner_MK3
```

To process another source family, change `source_folder` and `config_name` in
`main()` before running the script.

### Row transformation rules

Rules are evaluated for every data row. Text matching is case-insensitive.

| Source condition | Output values |
|---|---|
| Type contains `DI`, but not `DO` or `RTN` | `N = 3.5`, `R = TBD`, `T = C{plug number}_{DI token}_0` |
| Type contains `DO`, but not `DI` or `RTN` | `N = 0`, `P = 4`, `Q = C{plug number}_{DO token}_1` |
| Type contains `RTN` | `N = 0`, `P = 0`, `Q = G` |
| Wire color contains `red` | `N = voltage found in type text`, `O = P` |
| Type contains `INC_ENCY_A` | `N = 3.5`, `R = TBD`, `T = C{plug number}_{IE1/IE2}_1` |
| Type contains `INC_ENCY_B` | `N = 3.5`, `R = TBD`, `T = C{plug number}_{IE1/IE2}_65535` |
| Plug contains `1P`, `2P`, or `3P` | `A = 1`, `2`, or `3` respectively |
| Signal text contains `PIN n` | `F`, `G`, and `H` are all set to `n` |
| Type contains `AI_n` | `N = 0`, `R = TBD`, `T = C{plug number}_AI{n}_10` |

The first number found in the plug text is used as `{plug number}`. For
incremental encoder rows, `P5` in the signal text selects `IE2`; otherwise
`IE1` is used. If a red-wire type does not contain a recognizable number, the
expected voltage becomes `0`.

If multiple rules match the same row, later rules overwrite values written by
earlier rules. This is especially important for rows that are both red and a
logic type.

### Run the current batch procedure

The module does not expose command-line arguments. Running it directly uses the
hard-coded settings in `main()`:

```powershell
cd C:\ArduinoProject\IO_Tester
.\.venv\Scripts\Activate.ps1
python .\src\hw_tester\utils\read_excell.py
```

The batch procedure:

1. Finds `.xlsx` and `.xls` files in the configured source folder.
2. Excludes files whose names already begin with `IOTester`.
3. Processes each remaining file using the configured source format.
4. Prints a success or failure line for each workbook.
5. Prints totals at the end.

If no files are found, the procedure prints the folder path and exits without
creating output files. A failure in one workbook is reported and counted, while
processing continues with the remaining files.

### Run one workbook from Python

For a single workbook, call the function directly. This is also the safest way
to select a non-default worksheet or source format:

```powershell
python -c "from hw_tester.utils.read_excell import copy_and_transform_excel; print(copy_and_transform_excel(r'C:\ArduinoProject\IO_Tester\DB_Gunner_MK3\J31_Gunner_Display_Unit.xlsx', config_name='DB_Gunner_MK3'))"
```

Use `config_name='DB_Gunner_MK4'` for the MK4 source layout. Set
`sheet_name='SheetName'` when the required sheet is not the first sheet.

## Volcan workbook procedure

`copy_and_transform_excel_Volcan()` is a separate workflow for a Volcan source
workbook.

### Input requirements

- Rows begin at row 2.
- The connector value is read from source column E.
- Only connector values `J1` through `J26` are accepted.
- The card number is extracted from each worksheet title. For example,
  `Spider Card #3` produces card value `3`.

### Processing steps

1. Read the selected worksheet, or all worksheets when `sheet_name` is omitted.
2. Read the card number from each worksheet title.
3. Keep only rows whose column E value is a valid `J1`-`J26` connector.
4. Group rows by connector.
5. Create one standardized workbook for each connector.
6. Apply the Volcan-specific DI, DO, RTN, red terminal-block, and `INC_ENCY`
   rules.
7. Save each workbook beside the source file.

Output files use this naming convention:

```text
Volcan_J1.xlsx
Volcan_J2.xlsx
```

The Volcan output uses the same 21-column tester layout. Columns F (`SPS`) and
G (`Orignal`) are intentionally blank in the generated rows. Volcan rules are:

| Source condition | Output values |
|---|---|
| `DI_n` in the discrete-name field | `N = 3.5`, `R = TBD`, `T = C{card}_{DI n}_0` |
| `DO_n` in the discrete-name field | `N = 0`, `P = 4`, `Q = C{card}_{DO n}_1` |
| `RTN` in the plug field | `N = 0`, `P = 0`, `Q = G` |
| `RED` in Color and `TERMINAL BLOCK` in From | `N = voltage from plug`, `O = P` |
| `INC_ENCY` in Signal Name | `N = 3.5`, `R = TBD`, `T = C{card}_{IE1/IE2}_{1/65535}` |

For `INC_ENCY`, `P5` in the plug selects `IE2`; otherwise `IE1` is used. The
signal text suffix `A+` selects `1`; all other suffixes select `65535`.

Example:

```powershell
python -c "from hw_tester.utils.read_excell import copy_and_transform_excel_Volcan; print(copy_and_transform_excel_Volcan(r'C:\ArduinoProject\IO_Tester\DB_Volcan\HSID Volcan V8 REV03.xlsx'))"
```

## Loading a prepared workbook into IO Tester

`load_connector_from_excel()` is used by the application after a workbook has
been prepared. It:

1. Loads `settings.yaml` and reads the `ExcelColumns` section.
2. Resolves configured Excel letters such as `H` or `T` to zero-based indexes.
3. Opens the selected workbook and worksheet.
4. Skips row 1 as the header.
5. Skips rows without an ID.
6. Converts expected power and pull-up values to numbers, using `0.0` when
   empty or non-numeric.
7. Converts other fields to trimmed strings.
8. Creates a `Pin` with all test values initialized to `NO_RESULT`.
9. Adds each pin to a `Connector`.

The default arguments are:

```text
file_name = J17_Armant.xlsx
db_path = tests/DB
connector_id = J17
```

The configured columns must match the generated workbook, especially `ID`,
`Connect`, `Signal_Name`, `Plug`, `Type`, `Pin`, `Power_Expected`,
`Power_Input`, `PullUp_Expected`, `PullUp_Input`, `Logic_Pin_Input`,
`Logic_Command`, and `Logic_Expected`.

## Verification checklist

After processing a workbook:

- Confirm an `IOTester*.xlsx` or `Volcan_J*.xlsx` file was created beside the
  source file.
- Open the output and verify row 1 contains the expected tester headers.
- Check that the connector, plug, pin, color, and type values are in the
  expected columns.
- Spot-check DI, DO, RTN, red-wire, AI, and encoder rows.
- Verify generated logic strings use the expected card and channel numbers.
- Confirm the output file can be loaded by IO Tester and that pins appear in
  the pin table.
- Keep the original source workbook as a backup; the script does not overwrite
  it, but a rerun can replace an existing output with the same name.

## Common problems

| Symptom | Likely cause | Action |
|---|---|---|
| `Source Excel file not found` | Incorrect path or filename | Use an absolute path or a path relative to the project root. |
| `Unknown config_name` | Unsupported configuration name | Use `DB_Gunner_MK3` or `DB_Gunner_MK4`. |
| No output files are created | Folder contains no eligible files, or all files begin with `IOTester` | Check `source_folder` and the input filenames. |
| Output has unexpected values | Source columns do not match the selected configuration | Confirm the source layout and select the matching config. |
| Volcan output is empty | Connector values are not `J1`-`J26` in column E | Correct the connector column or source data. |
| Pins do not load in the application | Missing IDs or incorrect `ExcelColumns` settings | Check the ID column and `settings.yaml`. |

