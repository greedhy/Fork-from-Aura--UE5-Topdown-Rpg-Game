"""Run with the editor closed using the newly built commandlet. Preserve existing affix rows."""
import json
from pathlib import Path
import unreal as u
attributes = [('Strength', '力量'), ('Intelligence', '智力'), ('Resilience', '韧性'), ('Vigor', '活力'), ('Armor', '护甲'), ('ArmorPene', '护甲穿透'), ('BlockChance', '格挡率'), ('CriticalHitChance', '暴击率'), ('CriticalHitDamage', '暴击伤害'), ('CriticalHitResistence', '暴击抗性'), ('HealthRegeneration', '生命恢复'), ('ManaRegeneration', '法力恢复'), ('MaxHealth', '最大生命'), ('MaxMana', '最大法力'), ('FireResistance', '火焰抗性'), ('ThunderResistance', '雷电抗性'), ('WaterResistance', '水系抗性'), ('MagicResistance', '魔法抗性'), ('PhysicsResistance', '物理抗性'), ('PureResistance', '纯粹抗性')]
path = '/Game/Equipment/DT_EquipmentAffixes'
table = u.load_asset(path)
assert table
rows = json.loads(u.DataTableFunctionLibrary.export_data_table_to_json_string(table))
names = {r['Name'] for r in rows}
for attribute, label in attributes:
    name = 'Of' + attribute
    if name in names:
        continue
    low, high = (10, 20) if attribute in ('MaxHealth', 'MaxMana') else (1, 3)
    if attribute in ('HealthRegeneration', 'ManaRegeneration'):
        low, high = 0.2, 0.5
    tiers = []
    for tier, minimum, maximum in [(1, 1, 9), (2, 10, 20)]:
        tiers.append(dict(Tier=tier, MinItemLevel=minimum, MaxItemLevel=maximum, Stats=[dict(
            StatTag=dict(TagName='Equipment.Stat.' + attribute),
            MinValue=dict(Value=low*tier), MaxValue=dict(Value=high*tier),
            DecimalPlaces=1 if attribute.endswith('Regeneration') else 0)]))
    rows.append(dict(Name=name, DisplayName='之' + label, bPrefix=False,
                     ExclusiveGroup=attribute, Weight=1, Profiles=[], Tiers=tiers))
assert u.DataTableFunctionLibrary.fill_data_table_from_json_string(table, json.dumps(rows, ensure_ascii=False))
assert u.EditorAssetLibrary.save_loaded_asset(table, False)
# Explicitly migrate only the shared random GE's modifiers; native constructor is authoritative.
bp = u.load_asset('/Game/Equipment/Effects/GE_Equipment_Random')
assert bp
u.BlueprintEditorLibrary.compile_blueprint(bp)
native = u.get_default_object(u.load_class(None, '/Script/test_25d.RandomEquipmentGameplayEffect'))
cdo = u.get_default_object(bp.generated_class())
cdo.set_editor_property('modifiers', native.get_editor_property('modifiers'))
assert len(cdo.get_editor_property('modifiers')) == len(attributes)
assert u.EditorAssetLibrary.save_loaded_asset(bp, False)
result = dict(attributes=[a for a, _ in attributes], suffixes=['Of'+a for a,_ in attributes], modifiers=len(cdo.get_editor_property('modifiers')))
(Path(u.Paths.project_saved_dir())/'Equipment'/'all_attributes_authored.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('ALL_EQUIPMENT_ATTRIBUTES_SUCCESS ' + str(result))
