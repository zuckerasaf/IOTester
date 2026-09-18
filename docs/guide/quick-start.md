# Quick Start Guide

**Version 2.0 | September 2026 | UI: Qt / PySide6**

---

## Before you begin - checklist

- [ ] Controllino Mega is powered on and connected via USB (default: COM5) green and red light on the Controlino + Green LED on the MUX card 
- [ ] IO Box is powered and connected to the test network
- [ ] The Unit Under Test (UUT) is connected to the test fixture
- [ ] The correct Excel test file (`.xlsx`) for this connector is available

---

## Step 1 - Launch the application

Double-click `IO_Tester.exe`.

The application opens with a dark-themed window containing:

- Pin table (top, most of the screen)
- Run Controls bar (middle)
- Operational Log (bottom)

At startup the application will attempt to connect to the Controllino. Watch the Operational Log - you should see:

```
[INFO]  Hardware initialized on COM5
```

or in local host mode

```
[INFO] [ControllinoIO] Running in no-connection mode (operations will be no-ops)
```

If you see a WARNING about connection, see [Troubleshooting](#troubleshooting) below.

---

## Step 2 - Verify communication

Click **[ Comm Check ]** (bottom-right panel, "Test/Debug" group).

- Green flash on the controlino DI LED  =  Controllino responding correctly, Ping Test will be run with the predefine IO Cards 
- the Comm Check  button turns **GREEN** (all pass) or **RED** (failures detected) 
- status of the porcedure will be present in the log =  for cable or COM port issue (see Troubleshooting).

---

## Step 3 - Load a test file

Click **[ Load ]** (bottom-left panel).

Select the Excel file (`.xlsx`) for the connector you are testing. The pin table will populate with all pins and their expected values. The connector name appears in the "Connector:" field.

The **[ Test ]** and **[ Test_All ]** buttons become active.

---

## Step 4 - Run the tests

### To test all pins

Click **[ Test_All ]**.

The tester will work through every pin automatically:

- The currently-tested row turns **YELLOW**
- Pass results turn **GREEN** | Fail results turn **PINK**
- The "Testing Pin / Power / Pullup / Logic" status bar updates live

### To test selected pins only

Click one or more rows in the pin table (`Ctrl+click` for multi-select), then click **[ Test ]**.

### To stop early

Click **[ Stop ]** at any time - the current pin finishes and then stops.

---

## Step 5 - Read the results

Pin currently being tested raw will bw marked with yellow  

Key columns to check:

- `Power_Result` / `Power_Result_Reason (with present all mode)`
- `PullUp_Result` / `PullUp_Result_Reason (with present all mode)`
- `Logic_DI_Result` / `Logic_DI_Result_Reason (with present all mode)`

Values are **Pass** or **Fail**. Hover over any cell to see the full text.

---

## Step 6 - Save a report

Upon the completion ofof the test run or on Click **[ Report ]**.

Choose a file name and location. An Excel file is saved containing all pin data and test results for this session.

---

## Running the I-BIT test (built-in test)

The I-BIT test checks all 50 pins on both connector systems (A and B) for short-circuit / open-circuit faults without using the test file.

1. Click **[ IBIT ]** (Test/Debug group)
2. The test runs automatically for approximately 100 pins; watch the log for progress
3. The IBIT button turns **GREEN** (all pass) or **RED** (failures detected)
4. Click **[ Stop IBIT ]** to abort early if needed

---

## Troubleshooting

**"No communication" / hardware warning at startup**

- Check USB cable to Controllino is seated
- Verify COM port: open Settings and confirm `Board.Port` = correct COM
- Try Comm Check button - if it fails, restart the Controllino

**"UDP binding error" on startup**

- Another instance of IO Tester may already be running - close it
- Check that no other program is using the card network ports

**All pins reporting FAIL**

- Check that "Simulation: Off" is shown (not On) in Test/Debug group
- Confirm the correct connector map Excel file was loaded
- Verify UUT is fully seated in the fixture

**Test button stays greyed out**

- No file has been loaded - click Load first

**Need to run without hardware (demo / office use)**

- Ensure the button reads **Simulation: On** to enable simulation mode
- If it reads Simulation: Off, click it once to switch to simulation mode
- Tests will run with simulated voltages - no hardware required

---

For full reference see the [User Manual](user-manual.md).
