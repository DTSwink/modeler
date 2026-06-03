@echo off
set "PROJECT=%~dp0Modeler.uproject"

if not exist "%PROJECT%" (
	echo Could not find "%PROJECT%".
	pause
	exit /b 1
)

start "" "%PROJECT%"
