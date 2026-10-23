"""Single-player PIE: actual catalog grant, equip-off, toggle RPC, cost and cleanup.

Uses the server endpoint fed by input, not a physical keyboard event. Changes only
the temporary PIE player; does not write save data. Upkeep timing is unit tested
separately because the real player also regenerates mana.
"""
import json
import time
import uuid
from pathlib import Path
import unreal


def _toggle_tag(name):
    value = unreal.GameplayTag()
    value.import_text('(TagName="' + name + '")')
    return value


_toggle_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert _toggle_world, 'Start combat-map PIE'
_toggle_player = unreal.GameplayStatics.get_player_character(_toggle_world, 0)
assert _toggle_player and 'BP_Player' in _toggle_player.get_path_name(), 'Requires the real combat player'
_toggle_pc = unreal.GameplayStatics.get_player_controller(_toggle_world, 0)
_toggle_asc = _toggle_pc.get_editor_property('player_state').get_component_by_class(unreal.MyAbilitySystemComponent)
_toggle_attrs = _toggle_asc.get_attribute_set(unreal.MyAttributeSet)
_toggle_tags = unreal.GameplayTagContainer()
_toggle_tags.import_text('(GameplayTags=((TagName="Abilities.Passive.OrbitingFireBolt")))')
_toggle_handles = _toggle_asc.find_all_abilities_with_tags(_toggle_tags, True)
assert len(_toggle_handles) == 1, 'Catalog must already grant exactly one ability'
_toggle_handle = _toggle_handles[0]
_toggle_identity = _toggle_tag('Abilities.Passive.OrbitingFireBolt')
_toggle_slot = _toggle_tag('InputTag.4')
_toggle_asc.call_method('ServerSpendSpellPoint', (_toggle_identity,))
_toggle_asc.call_method('ServerEquipAbility', (_toggle_identity, _toggle_slot))


def _toggle_ability():
    result = unreal.AbilitySystemLibrary.get_gameplay_ability_from_spec_handle(_toggle_asc, _toggle_handle)
    return result[0] if isinstance(result, tuple) else result


def _toggle_mana():
    return _toggle_attrs.get_editor_property('mana').get_editor_property('current_value')


_toggle_checks = {'equipped_defaults_off': not unreal.AbilitySystemLibrary.is_gameplay_ability_active(_toggle_ability())}
_toggle_before_mana = _toggle_mana()
_toggle_asc.call_method('ServerToggleAbility', (_toggle_handle, _toggle_slot))
_toggle_checks['enable_cost_10_mp'] = abs(_toggle_before_mana - _toggle_mana() - 10) < .01
_toggle_checks['toggle_on_active'] = unreal.AbilitySystemLibrary.is_gameplay_ability_active(_toggle_ability())
_toggle_started = unreal.GameplayStatics.get_time_seconds(_toggle_world)
_toggle_wall = time.monotonic()
_toggle_run = str(uuid.uuid4())
_toggle_root = Path(unreal.Paths.project_dir()).resolve() / 'Saved/GAAuthoring/OrbitingFireBolt'
_toggle_out = _toggle_root / _toggle_run
_toggle_out.mkdir(parents=True)


def _toggle_smoke_tick(delta_seconds):
    elapsed = unreal.GameplayStatics.get_time_seconds(_toggle_world) - _toggle_started
    if elapsed < 9.5 and time.monotonic() - _toggle_wall < 60:
        return
    unreal.unregister_slate_post_tick_callback(_toggle_callback)
    try:
        balls = unreal.GameplayStatics.get_all_actors_of_class(_toggle_world, unreal.MyOrbitingFireBolt)
        _toggle_checks['three_live_balls'] = len(balls) == 3
        _toggle_checks['above_head'] = len(balls) == 3 and all(abs(b.get_actor_location().z - _toggle_player.get_actor_location().z - 150) < 10 for b in balls)
        before_off = _toggle_mana()
        _toggle_asc.call_method('ServerToggleAbility', (_toggle_handle, _toggle_slot))
        _toggle_checks['toggle_off_inactive'] = not unreal.AbilitySystemLibrary.is_gameplay_ability_active(_toggle_ability())
        _toggle_checks['off_is_free'] = abs(_toggle_mana() - before_off) < .01
        _toggle_checks['off_cleans_all_balls'] = len(unreal.GameplayStatics.get_all_actors_of_class(_toggle_world, unreal.MyOrbitingFireBolt)) == 0
        report = {'run_id': _toggle_run, 'passed': all(_toggle_checks.values()), 'checks': _toggle_checks,
                  'player': _toggle_player.get_path_name(), 'elapsed': elapsed,
                  'scope': 'Real BP_Player and catalog grant; server equip/toggle RPC; no physical keyboard, UI clicks or multiplayer verification'}
    except Exception as error:
        report = {'run_id': _toggle_run, 'passed': False, 'error': repr(error), 'checks': _toggle_checks}
    (_toggle_out / 'toggle-pie-validation.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    (_toggle_root / 'latest-toggle-pie.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    unreal.log('ORBITING_FIRE_BOLT_TOGGLE_PIE ' + json.dumps(report))


_toggle_callback = unreal.register_slate_post_tick_callback(_toggle_smoke_tick)
