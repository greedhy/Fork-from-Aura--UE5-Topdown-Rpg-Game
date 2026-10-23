"""Run after two standalone PIE instances start on LoadMenu.

Exercises real save selection, LAN discovery, joining and host start. Never
changes travel CVars; the editor must load the project's configuration itself.
Only unique QA saves and temporary PIE actors are changed. No UObject survives
in callback state across travel (which would prevent old-world collection).
"""
import json
import math
import time
import uuid
from pathlib import Path
import unreal as u

_rp = {'run': uuid.uuid4().hex, 'phase': 'select', 'started': time.monotonic(), 'checks': {}, 'saves': []}
_rp_dir = Path(u.Paths.project_dir()).resolve() / 'Saved/Rooms/PIE'
_rp_dir.mkdir(parents=True, exist_ok=True)

def _rp_write():
    (_rp_dir / (_rp['run'] + '.json')).write_text(json.dumps(_rp, indent=2), encoding='utf8')
    (_rp_dir / 'latest.json').write_text(json.dumps(_rp, indent=2), encoding='utf8')

def _rp_phase(phase):
    _rp.update(phase=phase, at=time.monotonic())
    _rp_write()

def _rp_check(name, ok):
    _rp['checks'][name] = bool(ok)
    assert ok, name

def _rp_finish(error=None):
    u.unregister_slate_post_tick_callback(_rp_handle)
    _rp.update(error=error, passed=error is None)
    for name in _rp['saves']:
        u.GameplayStatics.delete_game_in_slot(name, 0)
    _rp_write()

def _rp_rooms():
    return sorted([r for r in u.ObjectIterator(u.RoomSubsystem) if r.get_world() and 'UEDPIE_' in r.get_world().get_path_name()], key=lambda r: r.get_path_name())

def _rp_pcs():
    return [p for p in u.ObjectIterator(u.MyPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_controlled_pawn() and 'Dungeon.' in p.get_world().get_path_name()]

def _rp_input(pc, value):
    lib = u.get_default_object(u.load_class(None, '/Script/Engine.SubsystemBlueprintLibrary'))
    sub = lib.call_method('GetLocalPlayerSubSystemFromPlayerController', (pc, u.EnhancedInputLocalPlayerSubsystem.static_class()))
    assert sub, 'Missing local input subsystem'
    sub.inject_input_vector_for_action(pc.get_editor_property('move_action'), u.Vector(value, 0, 0), [], [])

def _rp_tick(dt):
    try:
        if time.monotonic() - _rp['started'] > 55:
            _rp['worlds'] = [r.get_world().get_path_name() for r in _rp_rooms()]
            raise AssertionError('Timeout in ' + _rp['phase'])
        rooms = _rp_rooms()
        if len(rooms) != 2:
            return
        phase = _rp['phase']
        if phase == 'select':
            huds = [h for h in u.ObjectIterator(u.LoadScreenHUD) if 'UEDPIE_' in h.get_path_name()]
            if len(huds) != 2: return
            _rp['pie_seamless_enabled'] = u.SystemLibrary.get_console_variable_int_value('net.AllowPIESeamlessTravel')
            for i, hud in enumerate(huds):
                vm = hud.get_editor_property('load_screen_view_model')
                slot = vm.get_load_slot_view_model_by_index(0)
                name = 'RoomPIE_' + _rp['run'] + '_' + str(i)
                _rp['saves'].append(name)
                slot.set_editor_property('load_slot_name', name)
                vm.new_slot_button_pressed(0, 'PIEPlayer' + str(i))
                vm.select_slot_button_pressed(0)
                vm.play_button_pressed()
            _rp_check('both_selected_save', all(r.has_selection() for r in rooms))
            rooms[0].create_room()
            _rp_phase('create')
        elif phase == 'create':
            host = next((r for r in rooms if r.is_hosting()), None)
            if not host: return
            gs = u.GameplayStatics.get_game_state(host.get_world())
            if not isinstance(gs, u.RoomLobbyGameState): return
            password = gs.get_editor_property('room_password')
            if not password: return
            next(r for r in rooms if not r.is_hosting()).join_room(password)
            _rp_phase('join')
        elif phase == 'join':
            states = [u.GameplayStatics.get_game_state(r.get_world()) for r in rooms]
            if not all(isinstance(s, u.RoomLobbyGameState) and len(s.get_editor_property('player_array')) == 2 for s in states): return
            _rp_check('both_in_lobby_with_two_players', True)
            # Python's FEditorScriptExecutionGuard forces Actor RPCs to execute
            # locally. Start on the game timer after that guard has unwound so
            # ProcessClientTravel actually sends its RPC to the remote player.
            host = next(r for r in rooms if r.is_hosting())
            u.get_default_object(u.SystemLibrary).call_method('K2_SetTimer', (host, 'StartRoomGame', 0.2, False, False, 0.0, 0.0))
            _rp_phase('travel')
        elif phase == 'travel':
            pcs = _rp_pcs()
            if len(pcs) != 3 or sum(p.is_local_controller() for p in pcs) != 2: return
            if any(u.GameplayStatics.get_game_state(r.get_world()) is None for r in rooms): return
            _rp_check('both_arrived_and_possessed', True)
            _rp_check('no_lobby_ui', not any(w.is_in_viewport() for w in u.ObjectIterator(u.RoomMenuWidget) if 'UEDPIE_' in w.get_path_name()))
            _rp_check('two_players_per_world', all(len(u.GameplayStatics.get_game_state(r.get_world()).get_editor_property('player_array')) == 2 for r in rooms))
            for r in rooms:
                for e in u.GameplayStatics.get_all_actors_of_class(r.get_world(), u.EnemyCharacter): e.destroy_actor()
            _rp_phase('settle')
        elif phase == 'settle' and time.monotonic() - _rp['at'] > 1:
            _rp['before'] = {p.get_path_name(): [p.get_controlled_pawn().get_actor_location().x, p.get_controlled_pawn().get_actor_location().y] for p in _rp_pcs()}
            _rp_phase('move')
        elif phase == 'move':
            for p in _rp_pcs():
                if p.is_local_controller(): _rp_input(p, 1)
            if time.monotonic() - _rp['at'] > 0.7: _rp_phase('movement_settle')
        elif phase == 'movement_settle':
            pcs = _rp_pcs()
            for p in pcs:
                if p.is_local_controller(): _rp_input(p, 0)
            if time.monotonic() - _rp['at'] < 0.6: return
            _rp['players'] = []
            for p in pcs:
                pos = p.get_controlled_pawn().get_actor_location()
                before = _rp['before'][p.get_path_name()]
                _rp_check('movement_' + p.get_name(), math.hypot(pos.x-before[0], pos.y-before[1]) > 20)
                _rp['players'].append({'pc': p.get_path_name(), 'local': p.is_local_controller(), 'role': str(p.get_local_role()), 'pos': [pos.x, pos.y, pos.z]})
            guest = next(p for p in pcs if p.get_local_role() == u.NetRole.ROLE_AUTONOMOUS_PROXY)
            server_guest = next(p for p in pcs if not p.is_local_controller())
            _rp_check('guest_movement_replicates', (guest.get_controlled_pawn().get_actor_location()-server_guest.get_controlled_pawn().get_actor_location()).length() < 30)
            _rp_finish()
    except Exception as error:
        _rp_finish(repr(error))

_rp_handle = u.register_slate_post_tick_callback(_rp_tick)
