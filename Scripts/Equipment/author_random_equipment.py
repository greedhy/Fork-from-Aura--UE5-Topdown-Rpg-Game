"""Run ONLY after rebuilding/restarting UE with random equipment reflected types.
Creates missing rows/assets; reruns retain designer edits. Does not run automatically.
"""
import json
from pathlib import Path
import unreal as u

BASE = '/Game/Equipment'
TOOLS = u.AssetToolsHelpers.get_asset_tools()
SAVED = Path(u.Paths.project_saved_dir()) / 'Equipment'
SAVED.mkdir(exist_ok=True)

def merge_table(name, schema, additions):
    path = BASE + '/' + name
    table = u.load_asset(path)
    if table is None:
        factory = u.DataTableFactory()
        factory.set_editor_property('struct', u.load_object(None, '/Script/test_25d.' + schema))
        table = TOOLS.create_asset(name, BASE, u.DataTable, factory)
    assert isinstance(table, u.DataTable), path
    rows = json.loads(u.DataTableFunctionLibrary.export_data_table_to_json_string(table))
    names = {row['Name'] for row in rows}
    missing = [row for row in additions if row['Name'] not in names]
    if missing:
        for row in rows:
            identity = row.get('ItemDefinitionId')
            if isinstance(identity, dict):
                asset_type = identity.get('PrimaryAssetType', {})
                type_name = asset_type.get('Name', 'BackpackItem') if isinstance(asset_type, dict) else asset_type
                assert type_name == 'BackpackItem', identity
                row['ItemDefinitionId'] = 'BackpackItem:' + identity['PrimaryAssetName']
        assert u.DataTableFunctionLibrary.fill_data_table_from_json_string(table, json.dumps(rows + missing, ensure_ascii=False))
        assert u.EditorAssetLibrary.save_loaded_asset(table, False)
    return table

curve_path = BASE + '/CT_RandomEquipmentLevels'
if not u.EditorAssetLibrary.does_asset_exist(curve_path):
    csv = SAVED / 'CT_RandomEquipmentLevels.csv'
    csv.write_text('Name,1,20\nLevelScale,1,2\n', encoding='utf-8')
    settings = u.CSVImportSettings()
    settings.set_editor_property('import_type', u.CSVImportType.ECSV_CURVE_TABLE)
    factory = u.CSVImportFactory()
    factory.set_editor_property('automated_import_settings', settings)
    task = u.AssetImportTask()
    task.filename = str(csv)
    task.destination_path = BASE
    task.destination_name = 'CT_RandomEquipmentLevels'
    task.factory = factory
    task.automated = True
    task.save = True
    TOOLS.import_asset_tasks([task])
assert isinstance(u.load_asset(curve_path), u.CurveTable)

def scalable(value, scaled=False):
    result = dict(Value=value)
    if scaled:
        result['Curve'] = dict(CurveTable=curve_path + '.CT_RandomEquipmentLevels', RowName='LevelScale')
    return result

def stat(attribute, low, high, scaled=False):
    return dict(StatTag=dict(TagName='Equipment.Stat.' + attribute), MinValue=scalable(low, scaled), MaxValue=scalable(high, scaled), DecimalPlaces=0)

examples = [
    ('RolledSapphireRing', '秘铸蓝宝石戒指', '18824_1', 'MaxMana', 12, 25, ['Equipment.Slot.Ring.Left', 'Equipment.Slot.Ring.Right']),
    ('RolledRubyRing', '秘铸红宝石戒指', '19204_1', 'MaxHealth', 25, 50, ['Equipment.Slot.Ring.Left', 'Equipment.Slot.Ring.Right']),
    ('RolledIronGuardChest', '秘铸铁卫胸甲', '24119_1', 'Armor', 4, 8, ['Equipment.Slot.Chest']),
]
profiles = merge_table('DT_EquipmentGenerationProfiles', 'EquipmentGenerationProfileRow', [
    dict(Name=name, DefaultItemLevel=1, BaseStats=[stat(attr, low, high, True)], RarityIds=['Common', 'Magic', 'Rare'])
    for name, label, icon, attr, low, high, slots in examples])
rarities = merge_table('DT_EquipmentRarities', 'EquipmentRarityRow', [
    dict(Name='Common', DisplayName='普通', Weight=60, MinAffixes=0, MaxAffixes=0, MaxPrefixes=0, MaxSuffixes=0),
    dict(Name='Magic', DisplayName='魔法', Weight=30, MinAffixes=1, MaxAffixes=1, MaxPrefixes=1, MaxSuffixes=1),
    dict(Name='Rare', DisplayName='稀有', Weight=10, MinAffixes=2, MaxAffixes=2, MaxPrefixes=1, MaxSuffixes=1)])
affix_rows = []
for name, label, prefix, attribute, low, high in [
    ('Stalwart', '坚毅的', True, 'Armor', 1, 3), ('Vital', '丰盈的', True, 'MaxHealth', 10, 20),
    ('OfWisdom', '智慧', False, 'MaxMana', 8, 15), ('OfFortitude', '坚韧', False, 'MaxHealth', 10, 20)]:
    affix_rows.append(dict(Name=name, DisplayName=label, bPrefix=prefix, ExclusiveGroup=attribute, Weight=1,
        Profiles=[row[0] for row in examples], Tiers=[
            dict(Tier=1, MinItemLevel=1, MaxItemLevel=9, Stats=[stat(attribute, low, high)]),
            dict(Tier=2, MinItemLevel=10, MaxItemLevel=20, Stats=[stat(attribute, low*2, high*2)])]))
affixes = merge_table('DT_EquipmentAffixes', 'EquipmentAffixRow', affix_rows)

effect_path = BASE + '/Effects/GE_Equipment_Random'
if not u.EditorAssetLibrary.does_asset_exist(effect_path):
    factory = u.BlueprintFactory()
    factory.set_editor_property('parent_class', u.load_class(None, '/Script/test_25d.RandomEquipmentGameplayEffect'))
    bp = TOOLS.create_asset('GE_Equipment_Random', BASE + '/Effects', u.Blueprint, factory)
    assert bp
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    # Native constructor owns all three Channel1 AddBase SetByCaller modifiers.
    assert u.EditorAssetLibrary.save_loaded_asset(bp, False)
rows = []
for name, label, icon, attribute, low, high, slots in examples:
    icon_path = f'/Game/Assets/EquipmentIcon/{icon}.{icon}'
    assert isinstance(u.load_asset(icon_path), u.Texture2D)
    rows.append(dict(Name=name, ItemDefinitionId='BackpackItem:' + name, DisplayName=label,
        Icon=icon_path, WorldMesh='None', PickupActorClass='/Script/test_25d.EquipmentSoulPickup', PickupMode='Interact',
        bStackable=False, MaxStack=1, bEquippable=True, bRandomizedEquipment=True, GenerationProfile=name,
        AllowedEquipmentSlots=dict(GameplayTags=[dict(TagName=tag) for tag in slots]),
        EquipEffect=effect_path + '.GE_Equipment_Random_C', EquipEffectLevel=1, bUsable=False, UseEffect='None'))
table = merge_table('DT_Equipment', 'BackpackItemDefEntry', rows)
catalog = u.load_asset('/Game/BluePrints/DA/DA_BackpackItemDefinitions')
assert catalog
for prop, asset in [('equipment_table', table), ('generation_profiles', profiles), ('rarities', rarities), ('affixes', affixes)]:
    previous = catalog.get_editor_property(prop)
    assert previous is None or previous == asset, 'Refusing to replace designer catalog reference: ' + prop
    catalog.set_editor_property(prop, asset)
assert u.EditorAssetLibrary.save_loaded_asset(catalog, False)

level = u.get_editor_subsystem(u.LevelEditorSubsystem)
assert level.load_level('/Game/RoguelikeGeneration/Maps/L_RoguelikeRun')
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
stands = [a for a in actors.get_all_level_actors() if isinstance(a, u.EquipmentEntranceSamples)]
assert len(stands) == 1, 'Expected existing single entrance sample generator; do not create a duplicate'
stand = stands[0]
names = list(map(str, stand.get_editor_property('equipment_names')))
for row in examples:
    if row[0] not in names:
        names.append(row[0])
stand.set_editor_property('equipment_names', names)
assert level.save_current_level()
report = dict(definitions=[r[0] for r in examples], profiles=profiles.get_path_name(), rarities=rarities.get_path_name(), affixes=affixes.get_path_name(), samples=names)
(SAVED / 'random_equipment_authored.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('RANDOM_EQUIPMENT_AUTHOR_SUCCESS ' + str(report))
