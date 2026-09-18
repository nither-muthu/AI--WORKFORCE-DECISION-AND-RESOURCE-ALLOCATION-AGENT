# WorkforceAI Platform Launcher for PowerShell
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path "$scriptDir"
& cmd.exe /c "run_project.bat"
