"""Run in UE Python. Creates missing examples; reruns preserve designer-edited tables."""
import json
from pathlib import Path
import unreal as u

BASE = '/Game/Equipment'
EXAMPLES = [
    ('SapphireRing', '蓝宝石戒指', '18824_1', 'MaxMana', 25, ['Equipment.Slot.Ring.Left', 'Equipment.Slot.Ring.Right']),
    ('RubyRing', '红宝石戒指', '19204_1', 'MaxHealth', 50, ['Equipment.Slot.Ring.Left', 'Equipment.Slot.Ring.Right']),
    ('IronGuardChest', '铁卫胸甲', '24119_1', 'Armor', 7, ['Equipment.Slot.Chest']),
]
tools = u.AssetToolsHelpers.get_asset_tools()
saved = Path(u.Paths.project_saved_dir()) / 'Equipment'
saved.mkdir(exist_ok=True)

def struct(cls, text):
    result = cls()
    result.import_text(text)
    return result

curve_path = BASE + '/CT_EquipmentStats'
if not u.EditorAssetLibrary.does_asset_exist(curve_path):
    csv = saved / 'CT_EquipmentStats.csv'
    csv.write_text('Name,1\n' + ''.join(f'{name}_{attribute},{value}\n' for name, _, _, attribute, value, _ in EXAMPLES), encoding='utf-8')
    factory = u.CSVImportFactory()
    settings = u.CSVImportSettings()
    settings.set_editor_property('import_type', u.CSVImportType.ECSV_CURVE_TABLE)
    factory.set_editor_property('automated_import_settings', settings)
    task = u.AssetImportTask()
    task.filename = str(csv)
    task.destination_path = BASE
    task.destination_name = 'CT_EquipmentStats'
    task.factory = factory
    task.automated = True
    task.save = True
    tools.import_asset_tasks([task])
curve = u.load_asset(curve_path)
assert isinstance(curve, u.CurveTable), 'CurveTable import failed'

rows = []
for name, label, icon, attribute, value, slots in EXAMPLES:
    effect_path = BASE + '/Effects/GE_Equipment_' + name
    if not u.EditorAssetLibrary.does_asset_exist(effect_path):
        factory = u.BlueprintFactory()
        factory.set_editor_property('parent_class', u.EquipmentGameplayEffect)
        bp = tools.create_asset('GE_Equipment_' + name, BASE + '/Effects', u.Blueprint, factory)
        assert bp
        u.BlueprintEditorLibrary.compile_blueprint(bp)
        cdo = u.get_default_object(u.EditorAssetLibrary.load_blueprint_class(effect_path))
        modifier = struct(u.GameplayModifierInfo,
            f'(Attribute=(AttributeName="{attribute}",Attribute=/Script/test_25d.MyAttributeSet:{attribute},AttributeOwner="/Script/CoreUObject.Class\'/Script/test_25d.MyAttributeSet\'"),'
            f'ModifierOp=AddBase,ModifierMagnitude=(MagnitudeCalculationType=ScalableFloat,ScalableFloatMagnitude=(Value=1.0,Curve=(CurveTable="/Script/Engine.CurveTable\'{curve_path}.CT_EquipmentStats\'",RowName="{name}_{attribute}"))),EvaluationChannelSettings=(Channel=Channel1))')
        cdo.set_editor_property('modifiers', [modifier])
        u.BlueprintEditorLibrary.compile_blueprint(bp)
        assert u.EditorAssetLibrary.save_loaded_asset(bp, False)
    icon_path = f'/Game/Assets/EquipmentIcon/{icon}.{icon}'
    assert isinstance(u.load_asset(icon_path), u.Texture2D)
    rows.append(dict(Name=name, ItemDefinitionId=f'BackpackItem:{name}', DisplayName=label,
        Icon=icon_path, WorldMesh='None', PickupActorClass='None', PickupMode='Interact',
        bStackable=False, MaxStack=1, bEquippable=True,
        AllowedEquipmentSlots='(GameplayTags=(' + ','.join(f'(TagName="{t}")' for t in slots) + '))',
        EquipEffect=f'{effect_path}.GE_Equipment_{name}_C', EquipEffectLevel=1,
        bUsable=False, UseEffect='None'))

table_path = BASE + '/DT_Equipment'
if not u.EditorAssetLibrary.does_asset_exist(table_path):
    factory = u.DataTableFactory()
    factory.set_editor_property('struct', u.load_object(None, '/Script/test_25d.BackpackItemDefEntry'))
    table = tools.create_asset('DT_Equipment', BASE, u.DataTable, factory)
    assert u.DataTableFunctionLibrary.fill_data_table_from_json_string(table, json.dumps(rows, ensure_ascii=False))
    assert u.EditorAssetLibrary.save_loaded_asset(table, False)
table = u.load_asset(table_path)
assert isinstance(table, u.DataTable)
catalog = u.load_asset('/Game/BluePrints/DA/DA_BackpackItemDefinitions')
previous = catalog.get_editor_property('equipment_table')
assert previous is None or previous == table, 'Do not replace another equipment table'
catalog.set_editor_property('equipment_table', table)
assert u.EditorAssetLibrary.save_loaded_asset(catalog, False)

state_path = '/Game/BluePrints/Player/BP_MyPlayerState'
state = u.get_default_object(u.EditorAssetLibrary.load_blueprint_class(state_path))
equipment = state.get_component_by_class(u.EquipmentComponent)
assert equipment
existing = equipment.get_editor_property('available_slots').export_text()
all_slots = sorted(set(t for row in EXAMPLES for t in row[-1]))
# Preserve existing slots by union through parsed TagName fields.
import re
all_slots = sorted(set(all_slots + re.findall(r'TagName="([^"]+)"', existing)))
equipment.set_editor_property('available_slots', struct(u.GameplayTagContainer,
    '(GameplayTags=(' + ','.join(f'(TagName="{t}")' for t in all_slots) + '))'))
bp = u.load_asset(state_path)
u.BlueprintEditorLibrary.compile_blueprint(bp)
assert u.EditorAssetLibrary.save_loaded_asset(bp, False)
report = dict(table=table_path, curve=curve_path, rows=list(u.DataTableFunctionLibrary.get_data_table_row_names(table)), effects=[BASE+'/Effects/GE_Equipment_'+r[0] for r in EXAMPLES])
(saved/'authored.json').write_text(json.dumps(report, ensure_ascii=False, default=str, indent=2), encoding='utf-8')
u.log('EQUIPMENT_AUTHOR_SUCCESS ' + str(report))
