"""Run through MCP in a fresh single-player Dungeon PIE; does not save game progress.

Exercises the actual startup-granted ability on BP_Player. This is an ASC smoke
test, not proof of physical keyboard input, UI clicks, or multiplayer rendering.
"""
import json
from pathlib import Path
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert world, 'Start Dungeon PIE before running this check'
player = unreal.GameplayStatics.get_player_character(world, 0)
assert player, 'PIE must use the combat GameMode and BP_Player'
controller = unreal.GameplayStatics.get_player_controller(world, 0)
asc = controller.get_editor_property('player_state').get_component_by_class(unreal.MyAbilitySystemComponent)
attributes = asc.get_attribute_set(unreal.MyAttributeSet)
ability = unreal.load_class(None,
    '/Game/BluePrints/AbilitySystem/Player/Ability/Arcane/ArcaneNova/GA_ArcaneNova.GA_ArcaneNova_C')
cooldown = unreal.GameplayTag()
cooldown.import_text('(TagName="Cooldown.Arcane.ArcaneNova")')


def mana():
    return attributes.get_editor_property('mana').get_editor_property('current_value')


def burst_components():
    return {component.get_path_name() for component in unreal.ObjectIterator(unreal.NiagaraComponent)
            if component.get_world() == world and component.get_asset()
            and component.get_asset().get_path_name() ==
            '/Game/Assets/Effects/ArcaneShards/NS_ArcaneShards.NS_ArcaneShards'}


before_mana = mana()
before_components = burst_components()
activated = asc.try_activate_ability_by_class(ability)
after_mana = mana()
cooldown_count = asc.get_gameplay_tag_count(cooldown)
new_components = burst_components() - before_components
repeat_activated = asc.try_activate_ability_by_class(ability)
checks = {
    'startup_ability_activated': activated,
    'mana_decreased_by_20': abs(before_mana - after_mana - 20.0) < 0.001,
    'cooldown_tag_present': cooldown_count == 1,
    'cue_spawned_center_and_eight_ring_bursts': len(new_components) == 9,
    'repeat_rejected_without_cost': not repeat_activated and mana() == after_mana,
}
result = {'passed': all(checks.values()), 'checks': checks, 'player': player.get_path_name(),
          'mana_before': before_mana, 'mana_after': after_mana,
          'new_cue_components': sorted(new_components),
          'scope': 'Actual BP_Player startup grant and ASC activation in single-player PIE'}
output = Path(unreal.Paths.project_dir()) / 'Saved/ArcaneNova/pie-validation.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
assert result['passed'], 'Arcane Nova PIE smoke check failed; see pie-validation.json'
