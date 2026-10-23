"""Collect fresh completed reports; run with normal Python after editor validation."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[3]
folder=root/'Saved/GAAuthoring/Prototypes'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
tests=read(folder/'Tests-Completion/index.json')
network=read(folder/'latest-network.json')
menu=read(folder/'latest-menu.json')
assets=read(folder/'latest-validation.json')
travel=read(root/'Saved/TravelValidation/SkillBar/latest.json')
editor=read(folder/'final-editor-state.json')
assert tests['failed']==0 and tests['succeeded']+tests['succeededWithWarnings']==71
assert network['passed'] and all(network['checks'].values())
assert menu['success'] and assets['success'] and travel['passed'] and all(travel['checks'].values())
assert not editor['dirty_packages'] and editor['pie_players']==0
assert 'Result: Succeeded' in (folder/'build-final.log').read_text(encoding='utf-8',errors='replace')
summary={'success':True,'native_tests':71,'native_test_warnings':tests['succeededWithWarnings'],
         'network_checks':len(network['checks']),'network_run':network['run'],
         'menu_checks':len(menu['checks']),'menu_run':menu['run_id'],
         'asset_checks':len(assets['checks']),'asset_run':assets['run_id'],
         'travel_checks':len(travel['checks']),'travel_run':travel['run'],
         'editor':editor,
         'network_scope':'Two connected PIE windows; authority learning fixtures, remote Enhanced Input and cursor TargetData, authority damage and replicated actors. Final description-only change covered by native tests.'}
(folder/'completion.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
print(json.dumps(summary,indent=2))
