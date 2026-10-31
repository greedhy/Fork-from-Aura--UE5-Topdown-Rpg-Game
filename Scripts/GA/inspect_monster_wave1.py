"""Read-only first-wave animation metadata; no source assets are saved."""
import json, uuid
from pathlib import Path
import unreal as u

registry = u.AssetRegistryHelpers.get_asset_registry()
report = {'run_id': uuid.uuid4().hex, 'animations': [], 'characters': []}
for root in ['/Game/Assets/Enemies/Demon', '/Game/Assets/Enemies/Shaman']:
    for data in registry.get_assets_by_path(root, recursive=True):
        if str(data.asset_class_path.asset_name) != 'AnimSequence':
            continue
        asset = data.get_asset()
        row = {'path': str(data.package_name)}
        for key in ['sequence_length', 'skeleton', 'enable_root_motion']:
            value = asset.get_editor_property(key)
            row[key] = value.get_path_name() if isinstance(value, u.Object) else value
        report['animations'].append(row)
for path in ['/Game/BluePrints/Characters/Demon/BP_Demon_Warrior', '/Game/BluePrints/Characters/Goblin/BP_Shaman']:
    cls = u.EditorAssetLibrary.load_blueprint_class(path)
    cdo = u.get_default_object(cls)
    mesh = cdo.get_component_by_class(u.SkeletalMeshComponent)
    row = {'path': path, 'native_enemy': isinstance(cdo, u.EnemyCharacter)}
    for key in ['auto_possess_ai', 'ai_controller_class', 'behavior_tree']:
        value = cdo.get_editor_property(key)
        row[key] = value.get_path_name() if isinstance(value, u.Object) else str(value)
    for key in ['skeletal_mesh_asset', 'anim_class']:
        value = mesh.get_editor_property(key)
        row[key] = value.get_path_name() if value else None
    report['characters'].append(row)
out = Path(u.Paths.project_dir())/'Saved/GAAuthoring/MonsterWave1'
out.mkdir(parents=True, exist_ok=True)
(out/(report['run_id']+'.json')).write_text(json.dumps(report, indent=2), encoding='utf8')
(out/'latest.json').write_text(json.dumps(report, indent=2), encoding='utf8')
