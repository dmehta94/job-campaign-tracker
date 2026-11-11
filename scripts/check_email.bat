@echo off
rem Checks Gmail for application confirmations and rejections and logs them in the tracker.
rem A shortcut to this file in your Startup folder runs it each time you sign in to Windows
rem (see "Check email automatically" in the README). You can also double-click it.
cd /d "%~dp0.."
if not exist logs mkdir logs
"venv\Scripts\python.exe" scripts\import_from_gmail.py >> logs\gmail_import.log 2>&1
