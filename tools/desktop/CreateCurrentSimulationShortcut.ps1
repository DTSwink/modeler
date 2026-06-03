$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$target = Join-Path $repoRoot "CurrentSimulation.html"
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Modeler Current Simulation.lnk"

if (-not (Test-Path -LiteralPath $target)) {
    Write-Error "Could not find CurrentSimulation.html at $target"
    exit 1
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $repoRoot
$shortcut.Description = "Open the latest local Modeler simulation snapshot"
$shortcut.Save()

Write-Output "Created shortcut: $shortcutPath"
