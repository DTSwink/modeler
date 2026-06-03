@echo off
set "START=%~dp0START_HERE.html"

if not exist "%START%" (
	echo Could not find "%START%".
	pause
	exit /b 1
)

start "" "%START%"
