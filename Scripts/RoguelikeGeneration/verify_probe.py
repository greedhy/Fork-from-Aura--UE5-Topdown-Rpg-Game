"""Observe the real PIE assembly; never save or modify gameplay actors/assets.

Write Saved/RoguelikeGeneration/verify-request.json, execute this script in the
editor, then start PIE. The callback writes <label>.json on success or failure.
The default request expects one world/player. Optional keys: expected_worlds,
expected_players, timeout (seconds), expect_failure (substring), seed.
"""

import builtins
import json
import re
import time
import traceback
import uuid
from pathlib import Path

import unreal as u


class ProbeVerification:
    def __init__(self, request, directory):
        self.request = request
        self.directory = directory
        self.label = request.get('label', 'pie-probe')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', self.label):
            raise ValueError('label must contain 1-80 ASCII letters, digits, _ or -')
        self.expected_worlds = int(request.get('expected_worlds', 1))
        self.expected_players = int(request.get('expected_players', 1))
        self.timeout = float(request.get('timeout', 75))
        self.expected_failure = str(request.get('expect_failure') or '')
        if self.expected_worlds not in (1, 2) or self.expected_players not in (1, 2):
            raise ValueError('This probe supports one or two worlds/players')
        if not 5 <= self.timeout <= 300:
            raise ValueError('timeout must be between 5 and 300 seconds')
        self.started = time.monotonic()
        self.next_sample = 0
        self.ready_since = None
        self.previous_state = None
        self.state_since = self.started
        self.handle = None
        self.finished = False
        self.performance = None
        self.previous_throttle = None
        self.result = {
            'run_id': uuid.uuid4().hex, 'request': request,
            'phase': 'waiting_for_pie', 'checks': {}, 'samples': [],
            'pre_ready_samples': 0, 'world_checks': [],
            'limitations': [
                'Samples editor PIE worlds; packaged builds and separate processes are not covered.',
                'Movement verification reads the input lock; no physical keyboard input is injected.',
                'Early gate observations are sampled, not a continuous frame-by-frame proof.',
            ],
        }
        self.write()

    def write(self):
        self.result['elapsed_seconds'] = round(time.monotonic() - self.started, 3)
        (self.directory / (self.label + '.json')).write_text(
            json.dumps(self.result, ensure_ascii=False, indent=2), encoding='utf-8')

    def start(self):
        try:
            self.performance = u.get_default_object(u.load_class(
                None, '/Script/UnrealEd.EditorPerformanceSettings'))
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
        if self.performance is not None and self.previous_throttle is not None:
            self.performance.set_editor_property('bThrottleCPUWhenNotForeground', self.previous_throttle)
        self.result.update(phase='complete', passed=error is None and bool(self.result['checks'])
                           and all(self.result['checks'].values()), error=error)
        self.write()
        u.log('DUNGEON_PROBE_VERIFICATION ' + self.label + ' passed=' + str(self.result['passed']))

    def check(self, name, condition):
        self.result['checks'][name] = bool(condition)
        if not condition:
            raise AssertionError(name)

    @staticmethod
    def trace(world, start, end, ignored, pawn_channel=False):
        if pawn_channel:
            hit = u.SystemLibrary.line_trace_single_by_profile(
                world, u.Vector(*start), u.Vector(*end), 'Pawn',
                False, ignored, u.DrawDebugTrace.NONE)
        else:
            hit = u.SystemLibrary.line_trace_single(
                world, u.Vector(*start), u.Vector(*end), u.TraceTypeQuery.ECC_VISIBILITY,
                False, ignored, u.DrawDebugTrace.NONE)
        return hit.to_tuple() if hit else None

    @staticmethod
    def local_controllers(world):
        return [pc for pc in u.GameplayStatics.get_all_actors_of_class(world, u.DungeonGenerationController)
                if pc.is_local_controller() and pc.get_controlled_pawn()]

    def validate_world(self, runtime, report):
        world = runtime.get_world()
        name = world.get_path_name()
        rooms = report['rooms']
        checks = {'world': name, 'floor_samples': 0, 'door_samples': 0,
                  'seam_samples': 0, 'routes': []}
        self.result['world_checks'].append(checks)
        ignored = list(u.GameplayStatics.get_all_actors_of_class(world, u.Pawn))
        # UE's generated Python static methods execute through the class default
        # object, whose GetWorld asserts for UCLASS(Within=World). call_method
        # keeps the real navigation instance as the reflected invocation target.
        navigation = next((nav for nav in u.ObjectIterator(u.NavigationSystemV1)
                           if not nav.get_name().startswith('Default__')
                           and nav.get_world() == world), None)
        self.check(name + ':navigation_instance', navigation is not None)
        for room in rooms:
            for dx, dy in ((0, 0), (200, 200), (-200, -200)):
                x, y = room['x'] + dx, room['y'] + dy
                hit = self.trace(world, (x, y, 500), (x, y, -500), ignored)
                self.check(name + ':floor:' + room['id'] + ':' + str((dx, dy)),
                           hit and hit[0] and abs(hit[4].z) < 30)
                checks['floor_samples'] += 1
        spacing = abs(rooms[1]['x'] - rooms[0]['x']) + abs(rooms[1]['y'] - rooms[0]['y'])
        self.check(name + ':spacing', spacing >= 1200)
        # The increment-one contract is the chain R00 -> R01 -> R02.
        edges = ((0, 1), (1, 2))
        for index, room in enumerate(rooms):
            neighbors = [rooms[b if a == index else a] for a, b in edges if index in (a, b)]
            for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                used = any(abs(other['x'] - room['x'] - dx * spacing) < .1
                           and abs(other['y'] - room['y'] - dy * spacing) < .1 for other in neighbors)
                x, y = room['x'] + dx * spacing / 2, room['y'] + dy * spacing / 2
                hit = self.trace(world, (x - dx * 200, y - dy * 200, 140),
                                 (x + dx * 200, y + dy * 200, 140), ignored, True)
                blocked = bool(hit and hit[0])
                self.check(name + ':door:' + room['id'] + ':' + str((dx, dy)),
                           not blocked if used else blocked and hit[9] == runtime)
                checks['door_samples'] += 1
        for first, second in edges:
            a, b = rooms[first], rooms[second]
            x, y = (a['x'] + b['x']) / 2, (a['y'] + b['y']) / 2
            hit = self.trace(world, (x, y, 500), (x, y, -500), ignored, True)
            self.check(name + ':seam:' + a['id'] + ':' + b['id'],
                       hit and hit[0] and abs(hit[4].z) < 30)
            checks['seam_samples'] += 1
        for first, second in (*edges, (0, 2)):
            a, b = rooms[first], rooms[second]
            path = navigation.call_method('FindPathToLocationSynchronously', (
                world, u.Vector(a['x'], a['y'], 30), u.Vector(b['x'], b['y'], 30), None, None))
            complete = bool(path and path.is_valid() and not path.is_partial())
            checks['routes'].append({'from': a['id'], 'to': b['id'], 'complete': complete,
                                     'points': len(path.path_points) if path else 0})
            self.check(name + ':navigation:' + a['id'] + ':' + b['id'], complete)

    def tick(self, delta_seconds):
        try:
            now = time.monotonic()
            if now - self.started > self.timeout:
                raise AssertionError('Timeout during ' + self.result['phase'])
            if now < self.next_sample:
                return
            self.next_sample = now + .1
            runtimes = [actor for actor in u.ObjectIterator(u.DungeonGenerationRuntime)
                        if actor.get_world() and 'UEDPIE_' in actor.get_world().get_path_name()
                        and actor in u.GameplayStatics.get_all_actors_of_class(
                            actor.get_world(), u.DungeonGenerationRuntime)]
            runtimes.sort(key=lambda actor: actor.get_world().get_path_name())
            if not runtimes:
                return
            reports = [json.loads(actor.get_generation_report()) for actor in runtimes]
            self.result['worlds'] = reports
            self.result['phase'] = 'observing_assembly'
            state = [(r['world'], r['phase'], r['error'], r['loaded_rooms'],
                      r['local_ready'], r['ready_players'], r['gate_closed']) for r in reports]
            if state != self.previous_state:
                self.previous_state, self.state_since = state, now
                if len(self.result['samples']) < 200:
                    self.result['samples'].append({'seconds': round(now - self.started, 3), 'states': state})
                self.write()
            # A created safety barrier must stay closed until this endpoint is ready
            # and the server has released the team. Initial missing-manifest state has no gate.
            for runtime, report in zip(runtimes, reports):
                allowed = (report['phase'].endswith('::Ready') and report['local_ready']
                           and not report['error'] and report['ready_players'] >= self.expected_players)
                if not allowed and report['door_barriers']:
                    self.check('sampled_gate_never_released_early:' + report['world'], report['gate_closed'])
                    self.result['pre_ready_samples'] += 1
            if len(runtimes) != self.expected_worlds:
                self.ready_since = None
                return
            self.check('one_runtime_per_world', len({a.get_world().get_path_name() for a in runtimes}) == len(runtimes))
            server = [r for r in reports if r['authority']]
            self.check('one_authority_world', len(server) == 1)
            locals_by_world = [self.local_controllers(actor.get_world()) for actor in runtimes]
            if not all(len(pcs) == 1 for pcs in locals_by_world):
                return
            if self.expected_failure:
                self.check('failure_scenario_never_reaches_ready', not server[0]['phase'].endswith('::Ready'))
                if not server[0]['phase'].endswith('::Failed'):
                    return
                self.check('expected_failure_reason', self.expected_failure in server[0]['error'])
                # Give replication and the controller tick time to settle before reading locks.
                if now - self.state_since < .5:
                    return
                self.check('all_endpoints_failed', all(r['phase'].endswith('::Failed') for r in reports))
                self.check('failed_input_held', all(pc.is_move_input_ignored() for pcs in locals_by_world for pc in pcs))
                self.check('failed_existing_gates_closed', all(not r['door_barriers'] or r['gate_closed'] for r in reports))
                self.result['gate_checks_applicable'] = [bool(r['door_barriers']) for r in reports]
                self.finish()
                return
            if any(r['error'] or r['phase'].endswith('::Failed') for r in reports):
                raise AssertionError('Runtime failure: ' + repr([r['error'] for r in reports]))
            ready = all(r['phase'].endswith('::Ready') and r['local_ready'] and not r['gate_closed']
                        and r['ready_players'] == self.expected_players for r in reports)
            if not ready:
                self.ready_since = None
                return
            if self.ready_since is None:
                self.ready_since = now
                self.result['phase'] = 'waiting_for_stable_ready'
                return
            if now - self.ready_since < 1:
                return
            self.check('expected_player_count', all(r['expected_players'] == self.expected_players for r in reports))
            self.check('two_streamed_rooms_each_world', all(r['loaded_rooms'] == r['streamed_rooms'] == 2 for r in reports))
            self.check('three_manifest_rooms_each_world', all(len(r['rooms']) == 3 for r in reports))
            self.check('eight_unused_doors_and_one_safety_gate', all(r['door_barriers'] == 9 for r in reports))
            self.check('same_generation', len({r['generation_id'] for r in reports}) == 1)
            self.check('same_nonempty_digest', bool(reports[0]['digest']) and len({r['digest'] for r in reports}) == 1)
            self.check('same_room_positions_and_assets', all(r['rooms'] == reports[0]['rooms'] for r in reports))
            self.check('server_received_all_player_acks', server[0]['ready_players'] == self.expected_players)
            self.check('ready_input_released', all(not pc.is_move_input_ignored() for pcs in locals_by_world for pc in pcs))
            if 'seed' in self.request:
                self.check('requested_seed', all(r['seed'] == int(self.request['seed']) for r in reports))
            for runtime, report in zip(runtimes, reports):
                self.validate_world(runtime, report)
            self.finish()
        except Exception:
            self.finish(traceback.format_exc())


_directory = Path(u.Paths.project_dir()).resolve() / 'Saved/RoguelikeGeneration'
_directory.mkdir(parents=True, exist_ok=True)
_request = json.loads((_directory / 'verify-request.json').read_text(encoding='utf-8-sig'))
_previous = getattr(builtins, '_roguelike_probe_verification', None)
if _previous and not _previous.finished:
    _previous.finish('Superseded by another verification request')
_verification = ProbeVerification(_request, _directory)
builtins._roguelike_probe_verification = _verification
_verification.start()
