"""Aggregate only completed reports; a missing/failed run cannot claim completion."""
import json,datetime
from pathlib import Path
root=Path(__file__).resolve().parents[3]
out=root/'Saved/GAAuthoring/Compositions'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
gate=read(out/'stage1-gate.json');assert gate['passed']
native=read(out/'Tests-Completion/index.json')
assert native['failed']==0 and native['notRun']==0 and native['inProcess']==0
report={'completed':True,'timestamp':datetime.datetime.now().isoformat(),'stage1_gate':gate,
        'native_passed':native['succeeded']+native['succeededWithWarnings'],'native_with_fixture_warnings':native['succeededWithWarnings'],'native_failed':native['failed'],'checks':{}}
for name,path,flag in [('compositions',out/'latest-network.json','passed'),('batch2',out/'latest-batch2-network.json','passed'),('assets',out/'latest-assets.json','success'),('menu',root/'Saved/GAAuthoring/Prototypes/latest-menu.json','success'),('travel',out/'Travel/latest.json','passed')]:
    result=read(path);assert result[flag],name
    report['checks'][name]={'run':result.get('run',result.get('run_id')),'passed':len(result['checks']),'file':str(path.relative_to(root))}
editor=read(out/'final-editor-state.json')
assert editor['pie_players']==0 and not editor['dirty_packages'] and 'MainMenu' in editor['map']
report['editor']=editor
(out/'completion.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps(report,indent=2))
