"""Read widget template tags without changing either skill tree. Run in UE."""
import json
import uuid
from pathlib import Path
import unreal

report = {'run_id': str(uuid.uuid4()), 'trees': {}}
for name in ('WBP_OffensiveSpellTree', 'WBP_PassiveSpellTree'):
    bp = unreal.load_asset('/Game/BluePrints/UI/SpellMenu/' + name)
    tree = unreal.find_object(bp, 'WidgetTree')
    tags = {}
    for button in ['WBP_My_SpellGLobeButton'] + ['WBP_My_SpellGLobeButton_' + str(i) for i in range(1, 9)] + ['Button_OrbitingFireBolt']:
        widget = unreal.find_object(tree, button)
        if widget:
            tags[button] = widget.get_editor_property('AbilityTag').export_text()
    report['trees'][name] = tags
root = Path(unreal.Paths.project_dir()).resolve() / 'Saved/GAAuthoring/OrbitingFireBolt'
run = root / report['run_id']
run.mkdir(parents=True)
(run / 'ui-state.json').write_text(json.dumps(report, indent=2), encoding='utf8')
(root / 'latest-ui-state.json').write_text(json.dumps(report, indent=2), encoding='utf8')
