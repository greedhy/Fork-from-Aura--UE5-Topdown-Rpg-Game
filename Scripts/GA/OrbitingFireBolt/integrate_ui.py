"""Move the toggle's menu entry into an inspected empty active skill-tree slot."""
import json
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'skills/build-ga/scripts'))
from mcp_call import MCP

ACTIVE = '/Game/BluePrints/UI/SpellMenu/WBP_OffensiveSpellTree'
PASSIVE = '/Game/BluePrints/UI/SpellMenu/WBP_PassiveSpellTree'
BUTTON = 'WBP_My_SpellGLobeButton_1'  # Inspected empty slot directly above FireBolt.
OLD_BUTTON = 'Button_OrbitingFireBolt'
TAG = 'Abilities.Passive.OrbitingFireBolt'  # Stable save identity; catalog type is Offensive.
RUN = ROOT / 'Saved/GAAuthoring/OrbitingFireBolt' / str(uuid.uuid4())
RUN.mkdir(parents=True)
for asset in (ACTIVE, PASSIVE):
    source = ROOT / 'Content' / (asset.removeprefix('/Game/') + '.uasset')
    shutil.copy2(source, RUN / source.name)
client = MCP(ROOT, 'OrbitingFireBolt')


def call(name, **args):
    return client.call(name, args, wait=10)


def graph(asset, name):
    return call('blueprint_analyze_graph', asset_path=asset, graph_name=name)['graph_analysis'][0]['nodes']


def read_tags():
    output = ROOT / 'Saved/GAAuthoring/OrbitingFireBolt/latest-ui-state.json'
    old = json.loads(output.read_text())['run_id'] if output.exists() else None
    call('console_exec', command='py "' + (ROOT / 'Scripts/GA/OrbitingFireBolt/inspect_ui.py').as_posix() + '"')
    report = json.loads(output.read_text())
    assert report['run_id'] != old, 'UI readback did not finish'
    return report


baseline = read_tags()
(RUN / 'ui-before.json').write_text(json.dumps(baseline, indent=2), encoding='utf8')
assert baseline['trees']['WBP_OffensiveSpellTree'][BUTTON] in ('(TagName="")', '(TagName="' + TAG + '")'), 'Active slot is occupied'
call('umg_widget_tree_set_widget_properties', asset_path=ACTIVE, widget_name=BUTTON,
     properties={'AbilityTag': {'TagName': TAG}})

for name in ('EventGraph', 'PassiveClearAll'):
    for node in graph(PASSIVE, name):
        if node['class'].endswith('K2Node_VariableGet') and any(p['name'] == OLD_BUTTON for p in node['pins']):
            call('blueprint_delete_node', asset_path=PASSIVE, node_guid=node['guid'])
names = {w['name'] for w in call('umg_widget_tree_list', asset_path=PASSIVE)['widgets']}
for name in (OLD_BUTTON, 'Spacer_OrbitingFireBolt'):
    if name in names:
        call('umg_widget_tree_remove_widget', asset_path=PASSIVE, widget_name=name)
for name in ('Spacer_91', 'Spacer_191'):
    call('umg_widget_tree_set_widget_properties', asset_path=PASSIVE, widget_name=name,
         properties={'Size': {'X': 100.0, 'Y': 60.0}})

compiles = {}
for asset, clear, count in ((ACTIVE, 'OffensiveClearAll', 9), (PASSIVE, 'PassiveClearAll', 3)):
    for name, targets in (('EventGraph', ['SetWidgetController', 'Assign On Spell Button Selected']), (clear, ['Deselect'])):
        nodes = graph(asset, name)
        for title in targets:
            target = next(n for n in nodes if n['title'] == title)
            links = next(p for p in target['pins'] if p['name'] == 'self')['linkedTo']
            assert len(links) == count, (asset, title, len(links))
            if asset == ACTIVE:
                getter = next(n for n in nodes if n['class'].endswith('K2Node_VariableGet') and any(p['name'] == BUTTON for p in n['pins']))
                assert any(link['nodeGuid'] == getter['guid'] for link in links), title
    diagnostics = call('blueprint_compile_diagnostics', asset_path=asset, compile=True)
    assert diagnostics.get('compile_ok') and diagnostics.get('compiler_error_count') == 0, diagnostics
    compiles[asset] = diagnostics
    call('asset_save', asset_path=asset, only_if_dirty=False)

after = read_tags()
for tree, buttons in baseline['trees'].items():
    for button, tag in buttons.items():
        if (tree == 'WBP_OffensiveSpellTree' and button == BUTTON) or button == OLD_BUTTON:
            continue
        assert after['trees'][tree][button] == tag, (tree, button)
assert after['trees']['WBP_OffensiveSpellTree'][BUTTON] == '(TagName="' + TAG + '")'
assert OLD_BUTTON not in after['trees']['WBP_PassiveSpellTree']
result = {'success': True, 'run_id': RUN.name, 'active_button': BUTTON, 'compile': compiles, 'readback': after}
(RUN / 'ui-result.json').write_text(json.dumps(result, indent=2), encoding='utf8')
(RUN.parent / 'latest-ui.json').write_text(json.dumps(result, indent=2), encoding='utf8')
print(json.dumps({'success': True, 'run_id': RUN.name, 'active_button': BUTTON}))
