"""Inject a brief movement action in an already-ready PIE probe, then read back
the local and authority pawns. Does not teleport, navigate, or edit/save assets.
Results: Saved/RoguelikeGeneration/movement.json.
"""

import builtins
import json
import math
import time
import traceback
import uuid
from pathlib import Path

import unreal as u


class MovementVerification:
    def __init__(self):
        self.started = time.monotonic()
        self.phase_started = self.started
        self.handle = None
        self.finished = False
        self.players = []
        self.performance = None
        self.previous_throttle = None
        self.path = Path(u.Paths.project_dir()).resolve() / 'Saved/RoguelikeGeneration/movement.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.result = {'run_id': uuid.uuid4().hex, 'phase': 'waiting_for_ready',
                       'checks': {}, 'players': [], 'injection_duration_seconds': .5,
                       'limitations': ['Enhanced Input action injection covers the existing action binding and movement replication, not physical keyboard focus.',
                                       'Runs in PIE and does not test crossing doors or packaged networking.']}
        self.write()

    def write(self):
        self.result['elapsed_seconds'] = round(time.monotonic() - self.started, 3)
        self.path.write_text(json.dumps(self.result, indent=2), encoding='utf-8')

    def start(self):
        try:
            self.performance = u.get_default_object(u.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings'))
            self.previous_throttle = self.performance.get_editor_property('bThrottleCPUWhenNotForeground')
            self.performance.set_editor_property('bThrottleCPUWhenNotForeground', False)
            self.handle = u.register_slate_post_tick_callback(self.tick)
        except Exception:
            self.finish(traceback.format_exc())
            raise

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        if self.handle is not None:
            u.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        # Injection is frame-scoped. A final zero also releases any Triggered action.
        for player in self.players:
            try:
                player['input'].inject_input_vector_for_action(player['action'], u.Vector(0, 0, 0), [], [])
            except Exception:
                pass  # PIE may have ended while the verification was running.
        if self.performance is not None and self.previous_throttle is not None:
            self.performance.set_editor_property('bThrottleCPUWhenNotForeground', self.previous_throttle)
        self.result.update(phase='complete', passed=error is None and bool(self.result['checks'])
                           and all(self.result['checks'].values()), error=error)
        self.write()
        u.log('DUNGEON_MOVEMENT_VERIFICATION passed=' + str(self.result['passed']))

    def check(self, name, condition):
        self.result['checks'][name] = bool(condition)
        if not condition:
            raise AssertionError(name)

    @staticmethod
    def position(pawn):
        value = pawn.get_actor_location()
        return [value.x, value.y, value.z]

    @staticmethod
    def distance_xy(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @staticmethod
    def player_id(controller):
        state = controller.get_editor_property('player_state')
        return state.get_editor_property('player_id') if state else None

    def setup(self):
        runtimes = [actor for actor in u.ObjectIterator(u.DungeonGenerationRuntime)
                    if actor.get_world() and 'UEDPIE_' in actor.get_world().get_path_name()
                    and actor in u.GameplayStatics.get_all_actors_of_class(actor.get_world(), u.DungeonGenerationRuntime)]
        reports = [json.loads(actor.get_generation_report()) for actor in runtimes]
        self.result['worlds'] = reports
        if not reports or not all(r['phase'].endswith('::Ready') and r['local_ready']
                                  and not r['error'] and not r['gate_closed'] for r in reports):
            return False
        authority = [actor for actor, report in zip(runtimes, reports) if report['authority']]
        self.check('one_authority_world', len(authority) == 1)
        expected = reports[0]['expected_players']
        if len(runtimes) != expected:
            return False
        controllers = [pc for actor in runtimes for pc in u.GameplayStatics.get_all_actors_of_class(
            actor.get_world(), u.DungeonGenerationController) if pc.is_local_controller() and pc.get_controlled_pawn()]
        if len(controllers) != expected or any(self.player_id(pc) is None for pc in controllers):
            return False
        server_controllers = u.GameplayStatics.get_all_actors_of_class(authority[0].get_world(), u.DungeonGenerationController)
        server_by_id = {self.player_id(pc): pc for pc in server_controllers if pc.get_controlled_pawn()}
        if len(server_by_id) != expected:
            return False
        self.check('distinct_local_players', len({self.player_id(pc) for pc in controllers}) == expected)
        library = u.get_default_object(u.load_class(None, '/Script/Engine.SubsystemBlueprintLibrary'))
        for pc in controllers:
            identity = self.player_id(pc)
            server = server_by_id.get(identity)
            self.check('authority_player_' + str(identity), server is not None)
            action = pc.get_editor_property('mass_move_action')
            inputs = library.call_method('GetLocalPlayerSubSystemFromPlayerController',
                                         (pc, u.EnhancedInputLocalPlayerSubsystem.static_class()))
            self.check('movement_action_' + str(identity), action is not None and inputs is not None)
            self.check('input_unlocked_' + str(identity), not pc.is_move_input_ignored())
            initial = self.position(pc.get_controlled_pawn())
            self.check('safe_central_start_' + str(identity), abs(initial[0]) < 600 and abs(initial[1]) < 600)
            record = {'player_id': identity, 'world': pc.get_world().get_path_name(),
                      'server_remote_controller': not server.is_local_controller(),
                      'action': action.get_path_name(), 'initial_local_cm': initial,
                      'initial_server_cm': self.position(server.get_controlled_pawn()), 'injected_frames': 0}
            self.result['players'].append(record)
            self.players.append({'controller': pc, 'server': server, 'action': action, 'input': inputs, 'record': record})
        self.result['expected_players'] = expected
        self.result['phase'] = 'injecting_movement'
        self.phase_started = time.monotonic()
        self.write()
        return True

    def tick(self, delta_seconds):
        try:
            now = time.monotonic()
            if now - self.started > 20:
                raise AssertionError('Timeout during ' + self.result['phase'])
            if self.result['phase'] == 'waiting_for_ready':
                if not self.setup():
                    return
                now = time.monotonic()
            if self.result['phase'] == 'injecting_movement':
                if now - self.phase_started < .5:
                    for player in self.players:
                        player['input'].inject_input_vector_for_action(player['action'], u.Vector(0, 1, 0), [], [])
                        player['record']['injected_frames'] += 1
                    return
                self.result['actual_injection_wall_seconds'] = now - self.phase_started
                self.result['phase'] = 'waiting_for_replication'
                self.phase_started = now
                self.write()
            # Release input while ordinary braking and client movement replication settle.
            for player in self.players:
                player['input'].inject_input_vector_for_action(player['action'], u.Vector(0, 0, 0), [], [])
            if now - self.phase_started < 1:
                return
            for player in self.players:
                record = player['record']
                local = self.position(player['controller'].get_controlled_pawn())
                server = self.position(player['server'].get_controlled_pawn())
                record.update(final_local_cm=local, final_server_cm=server,
                              local_distance_cm=self.distance_xy(local, record['initial_local_cm']),
                              server_distance_cm=self.distance_xy(server, record['initial_server_cm']),
                              replication_error_cm=self.distance_xy(local, server))
                suffix = '_' + str(record['player_id'])
                self.check('action_was_injected' + suffix, record['injected_frames'] > 0)
                self.check('local_pawn_moved' + suffix, record['local_distance_cm'] > 30)
                self.check('authority_pawn_moved' + suffix, record['server_distance_cm'] > 30)
                self.check('authority_position_matches' + suffix, record['replication_error_cm'] < 25)
                self.check('input_remains_unlocked' + suffix, not player['controller'].is_move_input_ignored())
            if self.result['expected_players'] == 2:
                self.check('remote_client_movement_observed_on_server', any(
                    record['server_remote_controller'] and record['server_distance_cm'] > 30 for record in self.result['players']))
            self.finish()
        except Exception:
            self.finish(traceback.format_exc())


_previous = getattr(builtins, '_roguelike_movement_verification', None)
if _previous and not _previous.finished:
    _previous.finish('Superseded by another movement verification')
_movement = MovementVerification()
builtins._roguelike_movement_verification = _movement
_movement.start()
