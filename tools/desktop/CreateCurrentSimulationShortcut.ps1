$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$target = Join-Path $repoRoot "ModelerLayoutEditor.pyw"
$pythonw = Join-Path (Split-Path $repoRoot -Parent) "stepper\.tools\python310\pythonw.exe"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Modeler Current Simulation.lnk"

if (-not (Test-Path -LiteralPath $target)) {
    Write-Error "Could not find ModelerLayoutEditor.pyw at $target"
    exit 1
}

if (-not (Test-Path -LiteralPath $pythonw)) {
    Write-Error "Could not find pythonw.exe at $pythonw"
    exit 1
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = '"' + $target + '"'
$shortcut.WorkingDirectory = $repoRoot
$shortcut.Description = "Open the latest local Modeler layout editor"
$shortcut.IconLocation = "$env:SystemRoot\System32\imageres.dll,67"
$shortcut.Save()

Write-Output "Created shortcut: $shortcutPath"
