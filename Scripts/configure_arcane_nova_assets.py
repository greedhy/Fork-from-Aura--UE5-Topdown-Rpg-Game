"""Run inside Unreal via MCP. Configure only the explicitly named Nova assets."""
import json
from pathlib import Path
import unreal

BASE = '/Game/BluePrints/AbilitySystem/Player/Ability/Arcane/ArcaneNova/'


def cdo(path):
    cls = unreal.EditorAssetLibrary.load_blueprint_class(path)
    assert cls, path
    return unreal.get_default_object(cls)


def struct(cls, text):
    value = cls()
    value.import_text(text)
    return value


def tag(name):
    return struct(unreal.GameplayTag, '(TagName="' + name + '")')


def tags(*names):
    return struct(unreal.GameplayTagContainer,
                  '(GameplayTags=(' + ','.join('(TagName="' + name + '")' for name in names) + '))')


def save_bp(path):
    bp = unreal.load_asset(path)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    assert unreal.EditorAssetLibrary.save_loaded_asset(bp, False), path


cost_path = BASE + 'GE_Cost_ArcaneNova'
cost = cdo(cost_path)
modifiers = list(cost.get_editor_property('modifiers'))
assert len(modifiers) == 1, 'Expected the existing single Mana modifier'
modifier = modifiers[0]
modifier.import_text('(ModifierMagnitude=(MagnitudeCalculationType=ScalableFloat,ScalableFloatMagnitude=(Value=-20.0,Curve=(CurveTable=None,RowName=""))))')
cost.set_editor_property('modifiers', [modifier])
cost.set_editor_property('duration_policy', unreal.GameplayEffectDurationType.INSTANT)
save_bp(cost_path)

cooldown_path = BASE + 'GE_Cooldown_ArcaneNova'
cooldown = cdo(cooldown_path)
cooldown.set_editor_property('duration_policy', unreal.GameplayEffectDurationType.HAS_DURATION)
cooldown.set_editor_property('duration_magnitude', struct(unreal.GameplayEffectModifierMagnitude,
    '(MagnitudeCalculationType=ScalableFloat,ScalableFloatMagnitude=(Value=6.0))'))
components = cooldown.get_editor_property('ge_components')
granted = 0
for component in components:
    if component.get_class().get_name() == 'TargetTagsGameplayEffectComponent':
        component.set_editor_property('InheritableGrantedTagsContainer', struct(unreal.InheritedTagContainer,
            '(CombinedTags=(GameplayTags=((TagName="Cooldown.Arcane.ArcaneNova"))),'
            'Added=(GameplayTags=((TagName="Cooldown.Arcane.ArcaneNova"))),Removed=(GameplayTags=()))'))
        granted += 1
assert granted == 1, 'Expected one Grant Tags to Target Actor component'
save_bp(cooldown_path)

ga_path = BASE + 'GA_ArcaneNova'
ga_class = unreal.EditorAssetLibrary.load_blueprint_class(ga_path)
ga = unreal.get_default_object(ga_class)
ga.set_editor_property('ability_tags', tags('Abilities.Arcane.ArcaneNova'))
ga.set_editor_property('startup_input_tag', tag('InputTag.1'))
ga.set_editor_property('activation_blocked_tags', tags('Debuff.Stun', 'Effects.HitReact', 'Player.Block.InputHeld'))
ga.set_editor_property('damage_type', tag('Damage.Magic'))
ga.set_editor_property('damage_effect_class', unreal.EditorAssetLibrary.load_blueprint_class(
    '/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage'))
ga.set_editor_property('cost_gameplay_effect_class', unreal.EditorAssetLibrary.load_blueprint_class(cost_path))
ga.set_editor_property('cooldown_gameplay_effect_class', unreal.EditorAssetLibrary.load_blueprint_class(cooldown_path))
ga.set_editor_property('nova_radius', 450.0)
ga.set_editor_property('bonus_damage_per_level', 15.0)
ga.set_editor_property('nova_cue_tag', tag('GameplayCue.ArcaneNova'))
save_bp(ga_path)

cue_path = '/Game/BluePrints/AbilitySystem/GameplayCueNotify/GC_ArcaneNova'
cue = cdo(cue_path)
cue.set_editor_property('gameplay_cue_tag', tag('GameplayCue.ArcaneNova'))
cue.set_editor_property('burst_system', unreal.load_asset('/Game/Assets/Effects/ArcaneShards/NS_ArcaneShards'))
cue.set_editor_property('burst_sound', unreal.load_asset('/Game/Assets/Sounds/Abilities/ArcaneShards/sfx_ArcaneShards'))
save_bp(cue_path)

info = unreal.load_asset('/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo')
rows = list(info.get_editor_property('ability_information'))
existing = [row for row in rows if row.get_editor_property('ability') == ga_class]
assert len(existing) <= 1, 'Duplicate Nova definitions'
if not existing:
    row = struct(unreal.MyAbilityInfo,
        '(AbilityTag=(TagName="Abilities.Arcane.ArcaneNova"),'
        'CooldownTag=(TagName="Cooldown.Arcane.ArcaneNova"),'
        'AbilityType=(TagName="Abilities.Type.Offensive"),LevelRequirement=1,'
        'Ability="' + ga_class.get_path_name() + '",'
        'Icon="/Game/Assets/UI/Spells/ArcaneShards2.ArcaneShards2",'
        'BackgroundMaterial="/Game/Assets/UI/Globes/MI_ArcaneSkillBG.MI_ArcaneSkillBG")')
    rows.append(row)
    info.set_editor_property('ability_information', rows)
    assert unreal.EditorAssetLibrary.save_loaded_asset(info, False)

player_path = '/Game/BluePrints/Characters/Player/BP_Player'
player = cdo(player_path)
startup = list(player.get_editor_property('startup_ability'))
if ga_class not in startup:
    # Fail instead of silently binding two startup abilities to the same input.
    for ability in startup:
        assert unreal.get_default_object(ability).get_editor_property('startup_input_tag') != tag('InputTag.1'), 'InputTag.1 occupied'
    startup.append(ga_class)
    player.set_editor_property('startup_ability', startup)
    save_bp(player_path)

output = Path(unreal.Paths.project_dir()) / 'Saved/ArcaneNova/authoring-result.json'
output.write_text(json.dumps({'configured': True, 'ga': ga_path, 'cue': cue_path, 'ability_info_count': len(rows)}, indent=2), encoding='utf-8')
print('ARCANE_NOVA_CONFIGURED')
