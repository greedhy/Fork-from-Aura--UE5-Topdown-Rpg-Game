"""Run in UE; acceptance contract for the first eight prototypes."""
import json, uuid
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir())
out = root / 'Saved/GAAuthoring/Prototypes'
out.mkdir(parents=True, exist_ok=True)
names = ['Projectile', 'Multishot', 'Burst', 'Beam', 'Surface', 'Orbit', 'Field', 'Trap']
base = '/Game/BluePrints/AbilitySystem/Player/Ability/Prototypes/'
checks = []
for name in names:
    path = base + 'GA_Prototype_' + name
    exists = unreal.EditorAssetLibrary.does_asset_exist(path)
    checks.append({'name': name, 'exists': exists})
    if exists:
        ga = unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class(path))
        config = ga.get_editor_property('prototype')
        checks[-1]['config'] = bool(config)
        checks[-1]['valid'] = bool(config and config.is_valid_configuration())
        checks[-1]['no_startup_slot'] = ga.get_editor_property('startup_input_tag').export_text() == '(TagName="")'
report = {'run_id': str(uuid.uuid4()), 'checks': checks,
          'success': all(c['exists'] and c.get('valid') and c.get('no_startup_slot') for c in checks)}
(out / 'latest-validation.json').write_text(json.dumps(report, indent=2), encoding='utf8')
assert report['success'], report
