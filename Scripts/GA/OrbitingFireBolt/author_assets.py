"""Idempotent asset authoring. Run in a freshly built UE editor via MCP."""
import json
import shutil
import uuid
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
RUN = ROOT / 'Saved/GAAuthoring/OrbitingFireBolt' / str(uuid.uuid4())
RUN.mkdir(parents=True)
BASE = '/Game/BluePrints/AbilitySystem/Player/Ability/PassiveSpell/OrbitingFireBolt/'
FIRE = '/Game/BluePrints/AbilitySystem/Player/Ability/Fire/FireBolt/'
TAG = 'Abilities.Passive.OrbitingFireBolt'
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def backup(path):
    source = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    if source.exists():
        target = RUN / 'backup' / source.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def struct(cls, text):
    result = cls()
    result.import_text(text)
    return result


def tag(name):
    return struct(unreal.GameplayTag, '(TagName="' + name + '")')


def bp_class(path):
    result = unreal.EditorAssetLibrary.load_blueprint_class(path)
    assert result, path
    return result


def cdo(path):
    return unreal.get_default_object(bp_class(path))


def save(bp):
    if isinstance(bp, unreal.Blueprint):
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False), bp.get_path_name()


def ensure_bp(name, parent):
    path = BASE + name
    asset = unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
    if asset:
        backup(path)
        assert isinstance(cdo(path), type(unreal.get_default_object(parent))), 'Existing parent conflicts: ' + path
        return asset
    factory = unreal.BlueprintFactory()
    factory.set_editor_property('parent_class', parent)
    return TOOLS.create_asset(name, BASE.rstrip('/'), unreal.Blueprint, factory)


try:
    projectile_path = BASE + 'BP_OrbitingFireBolt'
    projectile = unreal.load_asset(projectile_path) if unreal.EditorAssetLibrary.does_asset_exist(projectile_path) else None
    if not projectile:
        projectile = TOOLS.duplicate_asset('BP_OrbitingFireBolt', BASE.rstrip('/'), unreal.load_asset(FIRE + 'BP_FireBolt'))
        unreal.BlueprintEditorLibrary.reparent_blueprint(projectile, unreal.load_class(None, '/Script/test_25d.MyOrbitingFireBolt'))
    else:
        backup(projectile_path)
    assert projectile
    # BP_FireBolt's stationary-projectile cleanup and delayed collision activation
    # conflict with orbiting actors. Keep SCS/Niagara/audio defaults, remove its logic.
    for graph_name in ('EventGraph', 'DestroyIfTargetDied'):
        graph = unreal.BlueprintEditorLibrary.find_graph(projectile, graph_name)
        if graph:
            unreal.BlueprintEditorLibrary.remove_graph(projectile, graph)
    save(projectile)
    projectile_cdo = cdo(projectile_path)
    projectile_cdo.set_editor_property('replicates', True)
    projectile_cdo.set_editor_property('replicate_movement', True)
    save(projectile)

    config_path = BASE + 'DA_OrbitingFireBolt'
    if unreal.EditorAssetLibrary.does_asset_exist(config_path):
        config = unreal.load_asset(config_path)
        backup(config_path)
        assert isinstance(config, unreal.OrbitingFireBoltConfig)
    else:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property('data_asset_class', unreal.OrbitingFireBoltConfig)
        config = TOOLS.create_asset('DA_OrbitingFireBolt', BASE.rstrip('/'), unreal.OrbitingFireBoltConfig, factory)
    # Preserve user-tuned parameters when this script is rerun.
    config.set_editor_property('fire_bolt_class', bp_class(projectile_path))
    save(config)

    ability = ensure_bp('GA_OrbitingFireBolt', unreal.load_class(None, '/Script/test_25d.MyOrbitingFireBoltAbility'))
    ga = cdo(BASE + 'GA_OrbitingFireBolt')
    original = cdo(FIRE + 'GA_FireBolt')
    ga.set_editor_property('config', config)
    ga.set_editor_property('ability_tags', struct(unreal.GameplayTagContainer, '(GameplayTags=((TagName="' + TAG + '")))'))
    ga.set_editor_property('startup_input_tag', tag(''))
    ga.set_editor_property('cost_gameplay_effect_class', None)
    ga.set_editor_property('cooldown_gameplay_effect_class', None)
    for prop in ('damage', 'damage_type', 'damage_effect_class', 'debuff_chance', 'debuff_damage',
                 'debuff_frequency', 'debuff_duration', 'death_impulse_magnitude', 'knockback_force_magnitude', 'knockback_chance'):
        ga.set_editor_property(prop, original.get_editor_property(prop))
    ga.set_editor_property('projectile_class', bp_class(projectile_path))
    save(ability)

    catalog_path = '/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo'
    backup(catalog_path)
    catalog = unreal.load_asset(catalog_path)
    rows = list(catalog.get_editor_property('ability_information'))
    fire_row = next(row for row in rows if row.get_editor_property('ability_tag').export_text() == tag('Abilities.Fire.FireBolt').export_text())
    matches = [i for i, row in enumerate(rows) if row.get_editor_property('ability_tag').export_text() == tag(TAG).export_text()]
    assert len(matches) <= 1, 'Duplicate identity in catalog'
    row = unreal.MyAbilityInfo()
    # Struct fields are EditDefaultsOnly: use reflected import, not instance setters.
    row.import_text(fire_row.export_text())
    row.import_text('(AbilityTag=(TagName="' + TAG + '"),AbilityType=(TagName="Abilities.Type.Offensive"),'
                    'CooldownTag=(TagName=""),LevelRequirement=1,Ability="/Script/Engine.BlueprintGeneratedClass\''
                    + BASE + 'GA_OrbitingFireBolt.GA_OrbitingFireBolt_C\'")')
    if matches:
        rows[matches[0]] = row
    else:
        rows.append(row)
    catalog.set_editor_property('ability_information', rows)
    save(catalog)
    report = {'run_id': RUN.name, 'success': True, 'ga': ability.get_path_name(), 'config': config.get_path_name(),
              'projectile': projectile.get_path_name(), 'catalog_count': len(rows), 'backups': str(RUN / 'backup')}
except Exception as error:
    report = {'run_id': RUN.name, 'success': False, 'error': repr(error)}
    raise
finally:
    (RUN / 'authoring.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    (ROOT / 'Saved/GAAuthoring/OrbitingFireBolt/latest-authoring.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
