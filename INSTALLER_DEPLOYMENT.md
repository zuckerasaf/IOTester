# IO Tester Deployment Manual

## Build the installer

Build the installer on the development computer:

1. Make sure the project virtual environment and its dependencies are installed.
2. Install Inno Setup 6. The build script must be able to find `ISCC.exe` in `PATH` or in its default installation folder.
3. From the repository root, run:

   ```powershell
   .\build_installer.bat
   ```

The script runs `build_exe.bat` to build IO Tester, DB Creator, and the documentation site, then uses Inno Setup to create the installer. The current output is:

```text
installer_output\IOTester_Setup_v1.0.0.exe
```

## Install on the remote computer

1. Copy the installer `.exe` to the remote Windows 10/11 64-bit computer using an approved USB drive or file-transfer method.
2. Before upgrading an existing installation, back up its configuration files.
3. Run the installer and follow its prompts. Approve the Windows permission prompt if required.
4. Start **IO Tester** from the Start menu.
5. Configure the COM port and other hardware settings for that computer.

The remote computer does not need Python, PyInstaller, Inno Setup, or the project `.bat` files. DB Creator is included in the installer.

## Portable alternative

To make a ZIP instead of an installer, run `.\build_exe.bat`, then `.\build_portable_zip.bat`. Copy the generated ZIP to the remote computer, extract it, and run `IOTester.exe`. This option does not use Inno Setup.
