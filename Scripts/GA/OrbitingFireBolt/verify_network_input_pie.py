"""Two-player Listen Server PIE, real Enhanced Input on the remote client.

Start with MCP pie_start(num_players=2, net_mode=1). Learning/equip is an authority
fixture; activation uses remote IA_Input4 injection on subsequent game ticks, not
ServerToggleAbility. Only the temporary PIE player's regeneration is zeroed to
make resource accounting measurable. Never saves progress or changes assets.
"""
import json
import time
import uuid
from pathlib import Path
import unreal


def _net_tag(name):
    tag = unreal.GameplayTag()
    tag.import_text('(TagName="' + name + '")')
    return tag


def _net_asc(pc):
    return pc.get_editor_property('player_state').get_component_by_class(unreal.MyAbilitySystemComponent)


def _net_ability(asc):
    handles = asc.find_all_abilities_with_tags(_net_tags, True)
    assert len(handles) == 1, 'Existing catalog grant missing or duplicated'
    return unreal.AbilitySystemLibrary.get_gameplay_ability_from_spec_handle(asc, handles[0])[0]


def _net_active():
    return unreal.AbilitySystemLibrary.is_gameplay_ability_active(_net_ability(_net_server_asc))


def _net_mana(asc):
    return asc.get_attribute_set(unreal.MyAttributeSet).get_editor_property('mana').get_editor_property('current_value')


def _net_equipped(asc):
    # Items is protected in Python, but the container's reflected text is readable.
    text = asc.get_editor_property('activatable_abilities').export_text()
    spec = text.split("Default__GA_OrbitingFireBolt_C'")[1].split('NonReplicatedInstances')[0]
    return 'InputTag.4' in spec and 'Abilities.Status.Equipped' in spec


_net_pcs = [pc for pc in unreal.ObjectIterator(unreal.MyPlayerController) if 'UEDPIE_' in pc.get_path_name()]
_net_client = next(pc for pc in _net_pcs if pc.is_local_controller() and pc.get_local_role() == unreal.NetRole.ROLE_AUTONOMOUS_PROXY)
_net_server = next(pc for pc in _net_pcs if not pc.is_local_controller() and pc.get_local_role() == unreal.NetRole.ROLE_AUTHORITY)
_net_client_asc, _net_server_asc = _net_asc(_net_client), _net_asc(_net_server)
_net_server_world, _net_client_world = _net_server.get_world(), _net_client.get_world()
_net_tags = unreal.GameplayTagContainer()
_net_tags.import_text('(GameplayTags=((TagName="Abilities.Passive.OrbitingFireBolt")))')
_net_ability(_net_client_asc)
_net_ability(_net_server_asc)
_net_identity = _net_tag('Abilities.Passive.OrbitingFireBolt')
_net_slot = _net_tag('InputTag.4')

# Suppress only this temporary player's mana regeneration, preserving real costs.
_net_attrs = _net_server_asc.get_attribute_set(unreal.MyAttributeSet)
_net_regen = _net_attrs.get_editor_property('mana_regeneration')
_net_regen.import_text('(BaseValue=0.0,CurrentValue=0.0)')
_net_attrs.set_editor_property('mana_regeneration', _net_regen)
assert _net_attrs.get_editor_property('mana_regeneration').get_editor_property('current_value') == 0

_net_library = unreal.get_default_object(unreal.load_class(None, '/Script/Engine.SubsystemBlueprintLibrary'))
_net_input = _net_library.call_method('GetLocalPlayerSubSystemFromPlayerController', (_net_client, unreal.EnhancedInputLocalPlayerSubsystem.static_class()))
assert _net_input, 'Remote local-player input subsystem missing'
_net_action = unreal.load_asset('/Game/BluePrints/Input/InputActions/IA_Input4')
# The vector wrapper constructs FInputActionValue in C++; its native-only fields
# do not survive all Python reflected struct copies in UE 5.8.
_net_pressed = unreal.Vector(1.0, 0.0, 0.0)
unreal.get_default_object(unreal.load_class(None, '/Script/UMG.WidgetBlueprintLibrary')).call_method(
    'SetInputMode_GameOnly', (_net_client, False))

# Python's FEditorScriptExecutionGuard forces AActor::GetFunctionCallspace local,
# even inside C++ menu methods. Prepare learning/equip on authority; actual input
# is queued for later game ticks, outside that guard, so toggle RPCs traverse the net.
_net_server_asc.call_method('ServerSpendSpellPoint', (_net_identity,))
_net_server_asc.call_method('ServerEquipAbility', (_net_identity, _net_slot))
_net_root = Path(unreal.Paths.project_dir()).resolve() / 'Saved/GAAuthoring/OrbitingFireBolt'
_net_run = _net_root / str(uuid.uuid4())
_net_run.mkdir(parents=True)
_net_checks, _net_cost_steps = {}, []
_net_state = 'equip'
_net_started = unreal.GameplayStatics.get_time_seconds(_net_server_world)
_net_wall = time.monotonic()
_net_last_mana = _net_mana(_net_server_asc)
_net_enabled_at = None
_net_off_at = None
_net_off_mana = None


def _net_finish(error=None):
    unreal.unregister_slate_post_tick_callback(_net_callback)
    result = {'run_id': _net_run.name, 'passed': not error and bool(_net_checks) and all(_net_checks.values()),
              'checks': _net_checks, 'cost_steps': _net_cost_steps, 'error': error,
              'client': _net_client.get_path_name(), 'server': _net_server.get_path_name(),
              'client_role': str(_net_client.get_local_role()), 'server_role': str(_net_server.get_local_role()),
              'scope': 'Two-player Listen Server; authority learning/equip fixture; remote Enhanced Input action injection, real toggle RPC, authority costs, actor replication and teardown. No OS keyboard or menu clicks.'}
    (_net_run / 'network-input-validation.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    (_net_root / 'latest-network-input.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    unreal.log('ORBIT_NETWORK_INPUT_RESULT ' + json.dumps(result))


def _net_input_tick(delta_seconds):
    global _net_state, _net_last_mana, _net_enabled_at, _net_off_at, _net_off_mana
    try:
        now = unreal.GameplayStatics.get_time_seconds(_net_server_world)
        if time.monotonic() - _net_wall > 75:
            _net_finish('Timed out in phase ' + _net_state)
            return
        mana = _net_mana(_net_server_asc)
        if _net_state != 'equip' and mana < _net_last_mana - .01:
            _net_cost_steps.append(round(_net_last_mana - mana, 4))
        _net_last_mana = mana
        if _net_state == 'equip' and now - _net_started >= 1.0:
            _net_checks['authority_equip_fixture'] = _net_equipped(_net_server_asc)
            _net_checks['equipped_slot_replicated'] = _net_equipped(_net_client_asc)
            assert all(_net_checks.values()), 'Authority equip or slot replication failed'
            _net_checks['equip_defaults_off'] = not _net_active()
            _net_state = 'press_on'
            _net_enabled_at = now
        if _net_state == 'press_on':
            _net_input.inject_input_vector_for_action(_net_action, _net_pressed, [], [])
            if now - _net_enabled_at >= 1.5:
                _net_checks['remote_input_activates_server'] = _net_active()
                _net_checks['hold_does_not_toggle_off'] = _net_active()
                _net_state = 'orbit'
        elif _net_state == 'orbit' and now - _net_enabled_at >= 10.0:
            server_balls = unreal.GameplayStatics.get_all_actors_of_class(_net_server_world, unreal.MyOrbitingFireBolt)
            client_balls = unreal.GameplayStatics.get_all_actors_of_class(_net_client_world, unreal.MyOrbitingFireBolt)
            _net_checks['server_three_balls'] = len(server_balls) == 3
            _net_checks['client_three_replicated_balls'] = len(client_balls) == 3
            _net_checks['release_keeps_enabled'] = _net_active()
            _net_checks['one_startup_payment'] = _net_cost_steps.count(10.0) == 1
            _net_checks['upkeep_single_mp'] = len(_net_cost_steps) >= 9 and all(x == 1.0 for x in _net_cost_steps[1:])
            _net_checks['owner_mana_replication'] = abs(_net_mana(_net_client_asc) - mana) <= 1.01
            _net_state = 'press_off'
            _net_off_at = now
        elif _net_state == 'press_off':
            _net_input.inject_input_vector_for_action(_net_action, _net_pressed, [], [])
            if now - _net_off_at >= 1.5:
                _net_checks['second_press_turns_off'] = not _net_active()
                _net_checks['held_after_off_does_not_restart'] = not _net_active()
                _net_off_mana = mana
                _net_state = 'cleanup'
        elif _net_state == 'cleanup' and now - _net_off_at >= 4.0:
            _net_checks['server_cleanup'] = len(unreal.GameplayStatics.get_all_actors_of_class(_net_server_world, unreal.MyOrbitingFireBolt)) == 0
            _net_checks['client_cleanup'] = len(unreal.GameplayStatics.get_all_actors_of_class(_net_client_world, unreal.MyOrbitingFireBolt)) == 0
            _net_checks['no_off_state_drain'] = abs(mana - _net_off_mana) < .01
            _net_finish()
    except Exception as error:
        _net_finish(repr(error))


_net_callback = unreal.register_slate_post_tick_callback(_net_input_tick)
