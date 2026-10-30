param([string]$EngineRoot = 'C:\Program Files\Epic Games\UE_5.8', [switch]$AllProjectTests)
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$ProjectFile = Join-Path $ProjectRoot 'test_25d.uproject'
$ReportPath = Join-Path $ProjectRoot 'Saved/Automation/Equipment'
$LogPath = Join-Path $ProjectRoot 'Saved/Logs/EquipmentTests.log'
$TestFilter = if ($AllProjectTests) { 'test_25d.' } else { 'test_25d.Equipment+test_25d.Inventory' }
& (Join-Path $EngineRoot 'Engine/Build/BatchFiles/Build.bat') test_25dEditor Win64 Development "-Project=$ProjectFile" -WaitMutex -NoHotReloadFromIDE
if ($LASTEXITCODE -ne 0) { throw 'Equipment build failed; tests were not run against an old DLL.' }
$Started = Get-Date
& (Join-Path $EngineRoot 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe') $ProjectFile `
    -unattended -NullRHI -nosplash -nop4 "-ExecCmds=Automation RunTests $TestFilter" `
    '-TestExit=Automation Test Queue Empty' "-ReportExportPath=$ReportPath" "-abslog=$LogPath"
if ($LASTEXITCODE -ne 0) { throw "Unreal test process failed. See $LogPath" }
$ReportFile = Get-Item -LiteralPath (Join-Path $ReportPath 'index.json')
if ($ReportFile.LastWriteTime -lt $Started) { throw 'Test report was not updated.' }
$Report = Get-Content -Raw -LiteralPath $ReportFile.FullName | ConvertFrom-Json
$Report.tests | Select-Object testDisplayName,state
$EquipmentTests = @($Report.tests | Where-Object fullTestPath -like 'test_25d.Equipment.*')
if ($Report.failed -ne 0 -or $Report.notRun -ne 0 -or $EquipmentTests.Count -lt 7) {
    throw "Tests failed or equipment coverage was not discovered. See $ReportPath"
}
Write-Output "Validated $($Report.tests.Count) tests. Report: $ReportPath"

