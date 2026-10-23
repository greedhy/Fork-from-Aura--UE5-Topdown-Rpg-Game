"""Unreal editor acceptance checks, invoked through MCP console_exec."""
import json
from pathlib import Path
import unreal

BASE = '/Game/BluePrints/AbilitySystem/Player/Ability/Arcane/ArcaneNova/'
checks = []


def check(name, condition):
    checks.append({'name': name, 'passed': bool(condition)})


ga = unreal.EditorAssetLibrary.load_blueprint_class(BASE + 'GA_ArcaneNova')
check('GA_ArcaneNova exists and loads', ga is not None)
for name in ['GE_Cost_ArcaneNova', 'GE_Cooldown_ArcaneNova']:
    check(name + ' exists', unreal.EditorAssetLibrary.does_asset_exist(BASE + name))
check('GC_ArcaneNova exists', unreal.EditorAssetLibrary.does_asset_exist(
    '/Game/BluePrints/AbilitySystem/GameplayCueNotify/GC_ArcaneNova'))
if ga:
    cdo = unreal.get_default_object(ga)
    check('Radius is 450', cdo.get_editor_property('nova_radius') == 450.0)
    check('Server authoritative execution', cdo.get_editor_property('net_execution_policy') == unreal.GameplayAbilityNetExecutionPolicy.SERVER_ONLY)
    check('Separate cost GE', 'GE_Cost_ArcaneNova' in cdo.get_editor_property('cost_gameplay_effect_class').get_path_name())
    check('Separate cooldown GE', 'GE_Cooldown_ArcaneNova' in cdo.get_editor_property('cooldown_gameplay_effect_class').get_path_name())
    player = unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/Player/BP_Player'))
    check('Granted to new characters', ga in player.get_editor_property('startup_ability'))
    info = unreal.load_asset('/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo')
    check('Registered exactly once in AbilityInfo', sum(row.get_editor_property('ability') == ga for row in info.get_editor_property('ability_information')) == 1)
result = {'passed': all(c['passed'] for c in checks), 'checks': checks}
output = Path(unreal.Paths.project_dir()) / 'Saved' / 'ArcaneNova' / 'asset-validation.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
