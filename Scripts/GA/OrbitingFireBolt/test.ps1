param([string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.8')
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$RunId = [guid]::NewGuid().ToString('N')
$ReportPath = Join-Path $ProjectRoot "Saved/Automation/OrbitingFireBolt/$RunId"
$LogPath = Join-Path $ProjectRoot "Saved/Logs/OrbitingFireBolt-$RunId.log"
& (Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') (Join-Path $ProjectRoot 'test_25d.uproject') `
    -unattended -NullRHI -nosplash -nop4 `
    '-ExecCmds=Automation RunTests test_25d.Abilities.' `
    '-TestExit=Automation Test Queue Empty' "-ReportExportPath=$ReportPath" "-abslog=$LogPath"
if ($LASTEXITCODE -ne 0) { throw "Unreal tests failed: $LogPath" }
$Report = Get-Content -Raw -LiteralPath (Join-Path $ReportPath 'index.json') | ConvertFrom-Json
$Report.tests | Select-Object testDisplayName,state
if ($Report.failed -ne 0 -or $Report.notRun -ne 0 -or $Report.tests.Count -lt 16 -or @($Report.tests | Where-Object { $_.state -ne 'Success' }).Count -gt 0) { throw "Tests incomplete or failed: $ReportPath" }
Write-Output "Ability tests passed. Report: $ReportPath"
