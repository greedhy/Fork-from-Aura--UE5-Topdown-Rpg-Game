"""UE Python: preserve table rows; wire Soul pickups and one entrance sample generator."""
import json
from pathlib import Path
import unreal as u

table = u.load_asset('/Game/Equipment/DT_Equipment')
assert table
rows = json.loads(u.DataTableFunctionLibrary.export_data_table_to_json_string(table))
for row in rows:
    # UE JSON exports FPrimaryAssetType as an empty object; importing it loses the type.
    identity = row['ItemDefinitionId']
    if isinstance(identity, dict):
        type_name = identity.get('PrimaryAssetType', {}).get('Name', 'BackpackItem')
        assert type_name == 'BackpackItem'
        row['ItemDefinitionId'] = type_name + ':' + identity['PrimaryAssetName']
    if row.get('bEquippable', row.get('Equippable', False)):
        row['PickupActorClass'] = '/Script/test_25d.EquipmentSoulPickup'
        row['PickupMode'] = 'Interact'
assert u.DataTableFunctionLibrary.fill_data_table_from_json_string(table, json.dumps(rows, ensure_ascii=False))
assert u.EditorAssetLibrary.save_loaded_asset(table, False)

level = '/Game/RoguelikeGeneration/Maps/L_RoguelikeRun'
subsystem = u.get_editor_subsystem(u.LevelEditorSubsystem)
assert subsystem.load_level(level)
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
existing = [a for a in actors.get_all_level_actors() if isinstance(a, u.EquipmentEntranceSamples)]
assert len(existing) <= 1, 'Duplicate sample generators; inspect before modifying'
stand = existing[0] if existing else actors.spawn_actor_from_class(u.EquipmentEntranceSamples, u.Vector(0,0,0))
stand.set_actor_label('Equipment_Entrance_SoulSamples')
stand.set_editor_property('equipment_names', ['SapphireRing','RubyRing','IronGuardChest','SapphireRing','RubyRing'])
assert subsystem.save_current_level()
# Read mapping assets without changing unrelated controls.
registry = u.AssetRegistryHelpers.get_asset_registry()
inputs = []
for context_path in ['/Game/BluePrints/Input/IMC_PlayerContext']:
    context = u.load_asset(context_path)
    for mapping in context.get_editor_property('default_key_mappings').get_editor_property('mappings'):
        action = mapping.get_editor_property('action')
        key = mapping.get_editor_property('key').export_text()
        if action and ('Pickup' in action.get_name() or 'Backpack' in action.get_name()):
            inputs.append(dict(context=context.get_path_name(), action=action.get_name(), key=key))
report = dict(level=level, generator=stand.get_path_name(), items=list(map(str,stand.get_editor_property('equipment_names'))), input_mappings=inputs)
Path(u.Paths.project_saved_dir(),'Equipment','soul_authored.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('SOUL_PICKUPS_AUTHOR_SUCCESS')
