param([Parameter(Mandatory=$true)][string]$Run, [string[]]$Roles=@('host','guest','solo'))
$ErrorActionPreference='Stop'
if ($Run -notmatch '^[A-Za-z0-9_]{1,64}$') { throw 'Invalid run identifier' }
$roomProject=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$roomFolder=Join-Path $roomProject "Saved/Rooms/Network/$Run"
New-Item -ItemType Directory -Path $roomFolder -Force | Out-Null
foreach ($roomRole in $Roles) {
    if ($roomRole -notmatch '^[A-Za-z0-9_]{1,64}$') { throw 'Invalid role' }
    $roomArgs=@(('"'+$roomProject+'/test_25d.uproject"'),'/Game/levels/LoadMenu','-game','-windowed','-ResX=1280','-ResY=900','-RenderOffscreen','-unattended','-nosplash','-nosound','-NoLiveCoding','-DisablePlugins=SOMOLMCP','-NoScreenMessages',"-RoomProbe=$roomRole","-RoomProbeRun=$Run",('"-abslog='+$roomFolder+'/'+$roomRole+'.log"'),'-ExecCmds="t.MaxFPS 30"')
    $roomProc=Start-Process -FilePath 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $roomArgs -WindowStyle Hidden -PassThru
    [pscustomobject]@{role=$roomRole;id=$roomProc.Id;run=$Run} | ConvertTo-Json -Compress | Add-Content -LiteralPath (Join-Path $roomFolder 'processes.jsonl')
}
Get-Content -LiteralPath (Join-Path $roomFolder 'processes.jsonl')
