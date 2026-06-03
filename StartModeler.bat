@echo off
set "LAUNCHER=%~dp0ModelerLayoutEditorLauncher.exe"

if not exist "%LAUNCHER%" (
	echo Could not find "%LAUNCHER%".
	pause
	exit /b 1
)

start "" "%LAUNCHER%"
