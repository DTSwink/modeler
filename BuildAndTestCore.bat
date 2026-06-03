@echo off
setlocal

set "ROOT=%~dp0"
set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"

if not exist "%VCVARS%" (
	echo Could not find Visual Studio build tools at:
	echo %VCVARS%
	pause
	exit /b 1
)

call "%VCVARS%" >nul

if not exist "%ROOT%Build" mkdir "%ROOT%Build"
if not exist "%ROOT%Build\Smoke" mkdir "%ROOT%Build\Smoke"

cl /nologo /std:c++20 /EHsc /I"%ROOT%include" ^
	"%ROOT%tests\block0a_smoke.cpp" ^
	"%ROOT%src\modeler\sim\LayoutMarkers.cpp" ^
	/Fo"%ROOT%Build\Smoke\\" ^
	/Fe"%ROOT%Build\Smoke\block0a_smoke.exe"

if errorlevel 1 (
	echo.
	echo Build failed.
	pause
	exit /b 1
)

echo.
"%ROOT%Build\Smoke\block0a_smoke.exe"

echo.
pause
