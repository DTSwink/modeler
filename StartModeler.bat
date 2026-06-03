@echo off
set "SCRIPT=%~dp0ModelerLayoutEditor.pyw"
set "PYTHONW=C:\Users\singerie\Documents\Cursor\stepper\.tools\python310\pythonw.exe"

if not exist "%SCRIPT%" (
	echo Could not find "%SCRIPT%".
	pause
	exit /b 1
)

if not exist "%PYTHONW%" (
	echo Could not find "%PYTHONW%".
	pause
	exit /b 1
)

start "" "%PYTHONW%" "%SCRIPT%"
