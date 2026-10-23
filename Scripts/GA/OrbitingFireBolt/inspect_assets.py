"""Read-only editor baseline; run through SOMOLMCP console_exec."""
import json
from pathlib import Path
import unreal

def cdo(path):
    return unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class(path))

fire = cdo('/Game/BluePrints/AbilitySystem/Player/Ability/Fire/FireBolt/GA_FireBolt')
report = {
    'catalog': [r.export_text() for r in unreal.load_asset('/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo').get_editor_property('ability_information')],
    'firebolt': {p: str(fire.get_editor_property(p)) for p in (
        'projectile_class', 'damage', 'damage_effect_class', 'damage_type', 'debuff_chance')},
    'dirty_content': [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
    'dirty_maps': [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
}
out = Path(unreal.Paths.project_dir()) / 'Saved/GAAuthoring/OrbitingFireBolt/baseline.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
