@echo off
set "START=%~dp0CurrentSimulation.html"

if not exist "%START%" (
	echo Could not find "%START%".
	pause
	exit /b 1
)

start "" "%START%"
