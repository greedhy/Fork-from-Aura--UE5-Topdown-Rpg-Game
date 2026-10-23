"""Independent readback of saved asset configuration, without authoring mutations."""
import json
import uuid
from pathlib import Path
import unreal

BASE = '/Game/BluePrints/AbilitySystem/Player/Ability/PassiveSpell/OrbitingFireBolt/'
ROOT = Path(unreal.Paths.project_dir()).resolve()
RUN = ROOT / 'Saved/GAAuthoring/OrbitingFireBolt' / str(uuid.uuid4())
RUN.mkdir(parents=True)
ga_class = unreal.EditorAssetLibrary.load_blueprint_class(BASE + 'GA_OrbitingFireBolt')
ga = unreal.get_default_object(ga_class)
config = unreal.load_asset(BASE + 'DA_OrbitingFireBolt')
projectile = unreal.load_asset(BASE + 'BP_OrbitingFireBolt')
projectile_cdo = unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class(BASE + 'BP_OrbitingFireBolt'))
fire = unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class(
    '/Game/BluePrints/AbilitySystem/Player/Ability/Fire/FireBolt/GA_FireBolt'))
catalog = unreal.load_asset('/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo')
rows = [row for row in catalog.get_editor_property('ability_information')
        if row.get_editor_property('ability_tag').export_text() == '(TagName="Abilities.Passive.OrbitingFireBolt")']
player = unreal.get_default_object(unreal.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/Player/BP_Player'))
checks = {
    'native_ability_parent': isinstance(ga, unreal.MyOrbitingFireBoltAbility),
    'native_projectile_parent': isinstance(projectile_cdo, unreal.MyOrbitingFireBolt),
    'config_linked': ga.get_editor_property('config') == config,
    'cap_3': config.get_editor_property('max_fire_bolts') == 3,
    'spawn_every_3_seconds': abs(config.get_editor_property('spawn_interval') - 3) < .001,
    'launch_every_035_seconds': abs(config.get_editor_property('launch_interval') - .35) < .001,
    'config_projectile_linked': config.get_editor_property('fire_bolt_class') == projectile_cdo.get_class(),
    'damage_curve_reused': ga.get_editor_property('damage').export_text() == fire.get_editor_property('damage').export_text(),
    'damage_ge_reused': ga.get_editor_property('damage_effect_class') == fire.get_editor_property('damage_effect_class'),
    'native_cost_no_duplicate_ge_or_cooldown': not ga.get_editor_property('cost_gameplay_effect_class') and not ga.get_editor_property('cooldown_gameplay_effect_class'),
    'activation_cost_10_mp': config.get_editor_property('activation_mana_cost') == 10,
    'upkeep_1_mp_per_second': config.get_editor_property('mana_per_second') == 1,
    'replicated_projectile': projectile_cdo.get_editor_property('replicates') and projectile_cdo.get_editor_property('replicate_movement'),
    'old_projectile_tick_removed': unreal.BlueprintEditorLibrary.find_event_graph(projectile) is None,
    'unique_active_catalog_row': len(rows) == 1 and rows[0].get_editor_property('ability') == ga_class
        and rows[0].get_editor_property('ability_type').export_text() == '(TagName="Abilities.Type.Offensive")',
    'no_startup_offensive_binding': ga_class not in player.get_editor_property('startup_ability'),
    'no_startup_passive_binding': ga_class not in player.get_editor_property('startup_passive_ability'),
}
report = {'run_id': RUN.name, 'passed': all(checks.values()), 'checks': checks,
          'instancing': str(ga.get_editor_property('instancing_policy')),
          'network_policy': str(ga.get_editor_property('net_execution_policy')),
          'dirty_content': [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
          'dirty_maps': [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]}
(RUN / 'asset-validation.json').write_text(json.dumps(report, indent=2), encoding='utf8')
(ROOT / 'Saved/GAAuthoring/OrbitingFireBolt/latest-validation.json').write_text(json.dumps(report, indent=2), encoding='utf8')
assert report['passed'], report
