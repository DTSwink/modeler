@echo off
set "PAGE=%~dp0CurrentSimulation.html"

if not exist "%PAGE%" (
	echo Could not find "%PAGE%".
	pause
	exit /b 1
)

start "" "%PAGE%"
