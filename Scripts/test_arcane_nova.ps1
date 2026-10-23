param([string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.8')
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$ProjectFile = Join-Path $ProjectRoot 'test_25d.uproject'
$ReportPath = Join-Path $ProjectRoot 'Saved/Automation/ArcaneNova'
$LogPath = Join-Path $ProjectRoot 'Saved/Logs/ArcaneNovaTests.log'
& (Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') $ProjectFile `
    -unattended -NullRHI -nosplash -nop4 `
    '-ExecCmds=Automation RunTests test_25d.Abilities.ArcaneNova' `
    '-TestExit=Automation Test Queue Empty' "-ReportExportPath=$ReportPath" "-abslog=$LogPath"
if ($LASTEXITCODE -ne 0) { throw "Unreal test process failed with exit code $LASTEXITCODE. See $LogPath" }
$Report = Get-Content -Raw -LiteralPath (Join-Path $ReportPath 'index.json') | ConvertFrom-Json
$Report.tests | Select-Object testDisplayName,state
if ($Report.failed -ne 0 -or $Report.notRun -ne 0 -or $Report.tests.Count -ne 4) {
    throw "ArcaneNova tests failed or did not complete. See $ReportPath"
}
Write-Output "All four ArcaneNova tests passed. Report: $ReportPath"
