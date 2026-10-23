"""Host-side MCP Niagara authoring/compile pass; source systems stay untouched."""
import json
import sys
import time
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'skills/build-ga/scripts'))
from mcp_call import MCP
c=MCP(root,'TerrainEffects')
plan=json.loads((root/'Saved/TerrainSurfaces/effect_assets.json').read_text())
reports=[]
for variant in plan['variants']:
    for role,data in variant['systems'].items():
        path=data['asset']
        if '--verify-only' not in sys.argv:
            for emitter in data['emitters']:
                c.call('niagara_set_emitter_settings',{'emitter_asset_path':path+'.'+path.rsplit('/',1)[1]+':'+emitter,'local_space':True},wait=25)
            if role=='Surface' or variant['name'] in ['Frost','Vines']:
                c.call('niagara_set_warmup_settings',{'system_asset_path':path,'warmup_time':2.1,'warmup_tick_count':126},wait=25)
            print('Configured '+path,flush=True)
c.call('console_exec',{'command':'py import unreal; print(unreal.EditorAssetLibrary.save_directory("/Game/Art/TerrainSurfaces/Effects",False,True))'},wait=25)
for variant in plan['variants']:
    for role,data in variant['systems'].items():
        path=data['asset']
        for attempt in range(4):
            try:
                result=c.call('niagara_compile_diagnostics',{'system_asset_path':path,'force':False,'wait_for_completion':True,'max_compile_events':20},wait=25)
                break
            except RuntimeError as error:
                if '"has_outstanding_compilation": true' not in str(error) or attempt==3: raise
                # The plugin's "wait" polls once; allow the editor to finish asynchronously.
                time.sleep(1)
        reports.append({'asset':path,'compile':result})
        print(json.dumps({'asset':path,'ready':result.get('ready_to_run'),'errors':result.get('vm_compile_event_error_count')},ensure_ascii=True),flush=True)
(root/'Saved/TerrainSurfaces/effect_compiles.json').write_text(json.dumps(reports,indent=2))
