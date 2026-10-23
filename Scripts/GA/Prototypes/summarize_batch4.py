"""Aggregate fresh fourth-batch validation artifacts after review."""
import json,datetime
from pathlib import Path
root=Path(__file__).resolve().parents[3];out=root/'Saved/GAAuthoring/Batch4'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
native_path=out/('Tests-Final' if (out/'Tests-Final/index.json').exists() else 'Tests-Assets')/'index.json'
native=read(native_path)
assert native['failed']==0 and native['notRun']==0 and native['inProcess']==0
report={'complete':True,'timestamp':datetime.datetime.now().isoformat(),'native_passed':native['succeeded']+native['succeededWithWarnings'],
        'native_passed_with_warnings':native['succeededWithWarnings'],'native_failed':native['failed'],'checks':{}}
for name,file,flag in [('network','latest-network.json','passed'),('assets','latest-assets.json','success'),('menu','latest-menu.json','success'),('travel','Travel/latest.json','passed')]:
    r=read(out/file);assert r[flag],name
    report['checks'][name]={'run':r.get('run',r.get('run_id')),'passed':len(r['checks']),'file':file}
editor=read(out/'final-editor-state.json');assert not editor['dirty_packages'] and editor['pie_players']==0 and 'MainMenu' in editor['map']
report['editor']=editor
(out/'completion.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
