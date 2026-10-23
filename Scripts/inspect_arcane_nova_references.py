"""Run inside Unreal via MCP console_exec; read only bounded reference assets."""
import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
report = {}
assets = {
    '/Game/BluePrints/Characters/Player/BP_Player': ['startup_ability', 'startup_passive_ability'],
    '/Game/BluePrints/AbilitySystem/Player/Ability/Arcane/ArcaneChard/GA_ArcaneShards': [
        'ability_tags', 'startup_input_tag', 'damage', 'damage_type', 'cost_gameplay_effect_class',
        'cooldown_gameplay_effect_class', 'net_execution_policy', 'instancing_policy',
        'activation_blocked_tags', 'block_abilities_with_tag'],
    '/Game/BluePrints/AbilitySystem/Player/Ability/Arcane/ArcaneChard/GE_Cost_ArcaneShards': ['modifiers'],
    '/Game/BluePrints/AbilitySystem/Player/Ability/Arcane/ArcaneChard/GE_Cooldown_ArcaneShards': [
        'duration_policy', 'duration_magnitude', 'components'],
    '/Game/BluePrints/AbilitySystem/GameplayCueNotify/GC_ArcaneShards': ['gameplay_cue_tag', 'burst_effects'],
    '/Game/BluePrints/Input/DA_MyInputConfig': ['ability_input_actions'],
}
for path, fields in assets.items():
    cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
    obj = unreal.get_default_object(cls) if cls else unreal.load_asset(path)
    values = {'class': str(obj.get_class().get_path_name())}
    for field in fields:
        try:
            values[field] = str(obj.get_editor_property(field))
        except Exception as error:
            values[field] = str(error)
    report[path] = values
output = ROOT / 'Saved' / 'ArcaneNova' / 'references.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('Saved reference snapshot: ' + str(output))
