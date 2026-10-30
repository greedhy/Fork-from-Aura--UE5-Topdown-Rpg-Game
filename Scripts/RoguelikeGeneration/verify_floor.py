"""Bounded read-only PIE checks; request floor-request.json, result <label>.json.

Developer validation only: does not implement a player map or room gameplay.
"""
import builtins
import json
import re
import time
import traceback
import uuid
from pathlib import Path
import unreal as u


class FloorVerification:
    def __init__(self, request, directory):
        self.request, self.directory = request, directory
        self.label = request.get('label', 'floor-verification')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', self.label):
            raise ValueError('Invalid report label')
        self.worlds = int(request.get('expected_worlds', 1))
        self.players = int(request.get('expected_players', 1))
        self.timeout = float(request.get('timeout', 90))
        if self.worlds not in (1, 2) or self.players not in (1, 2) or not 5 <= self.timeout <= 120:
            raise ValueError('Expected one/two players/worlds and timeout 5..120 seconds')
        self.failure = str(request.get('expect_failure') or '')
        self.started, self.next_sample = time.monotonic(), 0
        self.stable_since, self.state_since, self.previous = None, self.started, None
        self.handle, self.performance, self.previous_throttle = None, None, None
        self.finished = False
        self.result = {'run_id': uuid.uuid4().hex, 'request': request, 'phase': 'waiting_for_pie',
                       'checks': {}, 'samples': [], 'world_checks': [], 'pre_ready_samples': 0,
                       'limitations': ['Editor PIE; no packaged/separate-process networking.',
                                       'Room roles do not prove encounters/rewards/merchant gameplay.',
                                       'Input locks inspected; use verify_movement.py for actual action injection.',
                                       'Early gate state sampled, not observed every game frame.']}
        self.write()

    def write(self):
        self.result['elapsed_seconds'] = round(time.monotonic() - self.started, 3)
        destination = self.directory / (self.label + '.json')
        temporary = destination.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(self.result, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(destination)

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
        cleanup_errors = []
        if self.handle is not None:
            try:
                u.unregister_slate_post_tick_callback(self.handle)
                self.handle = None
            except Exception:
                cleanup_errors.append(traceback.format_exc())
        if self.performance is not None and self.previous_throttle is not None:
            try:
                self.performance.set_editor_property('bThrottleCPUWhenNotForeground', self.previous_throttle)
            except Exception:
                cleanup_errors.append(traceback.format_exc())
        if cleanup_errors:
            error = '\n'.join(([error] if error else []) + cleanup_errors)
        self.result.update(phase='complete', passed=error is None and bool(self.result['checks'])
                           and all(self.result['checks'].values()), error=error)
        self.write()
        u.log('DUNGEON_FLOOR_VERIFICATION ' + self.label + ' passed=' + str(self.result['passed']))

    def check(self, name, condition):
        self.result['checks'][name] = bool(condition)
        if not condition:
            raise AssertionError(name)

    @staticmethod
    def role(room):
        return room['role'].split('::')[-1]

    @staticmethod
    def trace(world, start, end, ignored):
        hit = u.SystemLibrary.line_trace_single_by_profile(world, u.Vector(*start), u.Vector(*end),
                                                          'Pawn', False, ignored, u.DrawDebugTrace.NONE)
        return hit.to_tuple() if hit else None

    def validate_graph(self, report):
        rooms, edges, count = report['rooms'], report['connections'], report['main_path_length']
        self.check('version_and_room_counts', report['layout_version'] == 2 and 14 <= len(rooms) <= 18
                   and 10 <= count <= 12 and 4 <= len(rooms) - count <= 6)
        self.check('unique_room_ids_and_cells', len({r['id'] for r in rooms}) == len(rooms)
                   and len({(r['cell_x'], r['cell_y']) for r in rooms}) == len(rooms))
        links = {tuple(sorted((int(e['from']), int(e['to'])))) for e in edges}
        self.check('tree_edge_count', len(edges) == len(links) == len(rooms) - 1)
        adjacent = {i: [] for i in range(len(rooms))}
        for a, b in links:
            self.check('edge_indices:' + str((a, b)), 0 <= a < b < len(rooms))
            adjacent[a].append(b)
            adjacent[b].append(a)
            self.check('edge_adjacency:' + str((a, b)), abs(rooms[a]['cell_x'] - rooms[b]['cell_x'])
                       + abs(rooms[a]['cell_y'] - rooms[b]['cell_y']) == 1)
        reached, pending = {0}, [0]
        while pending:
            for neighbor in adjacent[pending.pop()]:
                if neighbor not in reached:
                    reached.add(neighbor)
                    pending.append(neighbor)
        self.check('all_rooms_reachable', len(reached) == len(rooms))
        main = sorted((i for i, r in enumerate(rooms) if r['main_index'] >= 0), key=lambda i: rooms[i]['main_index'])
        self.check('main_metadata', len(main) == count and [rooms[i]['main_index'] for i in main] == list(range(count))
                   and all(rooms[i]['branch_id'] == -1 for i in main) and main[0] == 0)
        roles = [self.role(rooms[i]) for i in main]
        self.check('main_role_quota', roles.count('Combat') == count - 6
                   and all(roles.count(role) == 1 for role in ('Entrance', 'Treasure', 'Elite', 'Merchant', 'Rest', 'Boss')))
        self.check('main_role_order', roles[0] == 'Entrance' and roles[1:3] == ['Combat', 'Combat']
                   and roles[-2:] == ['Rest', 'Boss'] and roles.index('Treasure') < roles.index('Elite')
                   < roles.index('Merchant') < roles.index('Rest') and roles[:roles.index('Elite')].count('Combat') >= 3)
        streak = 0
        for role in roles:
            streak = streak + 1 if role in ('Combat', 'Elite') else 0
            self.check('main_combat_streak', streak <= 3)
        self.check('main_chain', all(tuple(sorted((a, b))) in links for a, b in zip(main, main[1:])))
        branches = sorted({r['branch_id'] for r in rooms if r['main_index'] < 0})
        self.check('branch_count_and_ids', len(branches) in (2, 3) and branches == list(range(len(branches))))
        all_roles = [self.role(r) for r in rooms]
        self.check('global_special_quotas', 2 <= all_roles.count('Treasure') <= 3 and 1 <= all_roles.count('Elite') <= 2
                   and all(all_roles.count(role) == 1 for role in ('Entrance', 'Merchant', 'Rest', 'Boss')))
        for branch in branches:
            nodes = {i for i, r in enumerate(rooms) if r['branch_id'] == branch}
            boundary = [(i, j) for i in nodes for j in adjacent[i] if j not in nodes]
            leaves = [i for i in nodes if len(adjacent[i]) == 1]
            self.check('branch_shape:' + str(branch), 1 <= len(nodes) <= 3 and len(boundary) == 1
                       and boundary[0][1] in main and len(leaves) == 1 and all(len(adjacent[i]) <= 2 for i in nodes)
                       and all(rooms[i]['main_index'] == -1 for i in nodes))
            self.check('branch_attachment:' + str(branch), self.role(rooms[boundary[0][1]]) not in ('Entrance', 'Rest', 'Boss'))
            self.check('branch_reward:' + str(branch), self.role(rooms[leaves[0]]) in ('Treasure', 'Elite')
                       and all(self.role(rooms[i]) == 'Combat' for i in nodes if i != leaves[0]))
        self.check('fixed_persistent_entrance', rooms[0]['persistent'] and rooms[0]['cell_x'] == rooms[0]['cell_y'] == 0
                   and rooms[0]['yaw'] == 0 and not any(r['persistent'] for r in rooms[1:]))

    def validate_world(self, runtime, report):
        world, rooms, name = runtime.get_world(), report['rooms'], report['world']
        adjacent = {i: [] for i in range(len(rooms))}
        for edge in report['connections']:
            adjacent[edge['from']].append(edge['to'])
            adjacent[edge['to']].append(edge['from'])
        ignored = list(u.GameplayStatics.get_all_actors_of_class(world, u.Pawn))
        # Class-bound static calls use the CDO, whose Within=World GetWorld ensures.
        navigation = next((nav for nav in u.ObjectIterator(u.NavigationSystemV1)
                           if not nav.get_name().startswith('Default__') and nav.get_world() == world), None)
        self.check(name + ':navigation_instance', navigation is not None)
        detail = {'world': name, 'floor_samples': 0, 'door_samples': 0, 'seam_samples': 0, 'routes': []}
        self.result['world_checks'].append(detail)
        for room in rooms:
            for dx, dy in ((0, 0), (200, 200), (-200, -200)):
                x, y = room['x'] + dx, room['y'] + dy
                hit = self.trace(world, (x, y, 500), (x, y, -500), ignored)
                self.check(name + ':floor:' + room['id'] + ':' + str((dx, dy)), hit and hit[0] and abs(hit[4].z) < 30)
                detail['floor_samples'] += 1
        first = report['connections'][0]
        a, b = rooms[first['from']], rooms[first['to']]
        spacing = abs(a['x'] - b['x']) + abs(a['y'] - b['y'])
        self.check(name + ':shared_footprint', abs(spacing - 2400) < .1 and all(
            abs(r['x'] - r['cell_x'] * spacing) < .1 and abs(r['y'] - r['cell_y'] * spacing) < .1 for r in rooms))
        for index, room in enumerate(rooms):
            for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                used = any(rooms[j]['cell_x'] - room['cell_x'] == dx
                           and rooms[j]['cell_y'] - room['cell_y'] == dy for j in adjacent[index])
                x, y = room['x'] + dx * spacing / 2, room['y'] + dy * spacing / 2
                hit = self.trace(world, (x - dx * 200, y - dy * 200, 140), (x + dx * 200, y + dy * 200, 140), ignored)
                self.check(name + ':door:' + room['id'] + ':' + str((dx, dy)), bool(hit and hit[0]) != used)
                detail['door_samples'] += 1
        routes = set()
        for edge in report['connections']:
            first, second = edge['from'], edge['to']
            a, b = rooms[first], rooms[second]
            x, y = (a['x'] + b['x']) / 2, (a['y'] + b['y']) / 2
            hit = self.trace(world, (x, y, 500), (x, y, -500), ignored)
            self.check(name + ':seam:' + a['id'] + ':' + b['id'], hit and hit[0] and abs(hit[4].z) < 30)
            detail['seam_samples'] += 1
            routes.add((first, second))
        routes.update((0, i) for i, room in enumerate(rooms)
                      if self.role(room) == 'Boss' or (room['branch_id'] >= 0 and len(adjacent[i]) == 1))
        for first, second in sorted(routes):
            a, b = rooms[first], rooms[second]
            path = navigation.call_method('FindPathToLocationSynchronously', (
                world, u.Vector(a['x'], a['y'], 30), u.Vector(b['x'], b['y'], 30), None, None))
            complete = bool(path and path.is_valid() and not path.is_partial())
            detail['routes'].append({'from': a['id'], 'to': b['id'], 'complete': complete,
                                     'points': len(path.path_points) if path else 0})
            self.check(name + ':route:' + a['id'] + ':' + b['id'], complete)

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
                        and actor in u.GameplayStatics.get_all_actors_of_class(actor.get_world(), u.DungeonGenerationRuntime)]
            runtimes.sort(key=lambda actor: actor.get_world().get_path_name())
            if not runtimes:
                return
            reports = [json.loads(actor.get_generation_report()) for actor in runtimes]
            self.result.update(worlds=reports, phase='observing_assembly')
            state = [(r['world'], r['phase'], r['error'], r['loaded_rooms'], r['local_ready'], r['ready_players'], r['gate_closed']) for r in reports]
            if state != self.previous:
                self.previous, self.state_since = state, now
                if len(self.result['samples']) < 300:
                    self.result['samples'].append({'seconds': round(now - self.started, 3), 'states': state})
                self.write()
            for report in reports:
                allowed = report['phase'].endswith('::Ready') and report['local_ready'] and not report['error'] and report['ready_players'] >= self.players
                if not allowed and report['door_barriers']:
                    self.check('gate_not_early:' + report['world'], report['gate_closed'])
                    self.result['pre_ready_samples'] += 1
            if len(reports) != self.worlds:
                self.stable_since = None
                return
            self.check('one_runtime_per_world', len({a.get_world().get_path_name() for a in runtimes}) == self.worlds)
            authorities = [r for r in reports if r['authority']]
            self.check('one_authority_world', len(authorities) == 1)
            controllers = [[pc for pc in u.GameplayStatics.get_all_actors_of_class(a.get_world(), u.DungeonGenerationController)
                            if pc.is_local_controller() and pc.get_controlled_pawn()] for a in runtimes]
            if not all(len(items) == 1 for items in controllers):
                return
            if self.failure:
                self.check('failure_never_ready', not authorities[0]['phase'].endswith('::Ready'))
                if not authorities[0]['phase'].endswith('::Failed') or now - self.state_since < .5:
                    return
                self.check('expected_failure', self.failure in authorities[0]['error'])
                self.check('all_failed', all(r['phase'].endswith('::Failed') for r in reports))
                self.check('failed_input_held', all(pc.is_move_input_ignored() for items in controllers for pc in items))
                self.check('failed_gates_closed', all(not r['door_barriers'] or r['gate_closed'] for r in reports))
                self.finish()
                return
            if any(r['error'] or r['phase'].endswith('::Failed') for r in reports):
                raise AssertionError('Runtime failure: ' + repr([r['error'] for r in reports]))
            if not all(r['phase'].endswith('::Ready') and r['local_ready'] and not r['gate_closed']
                       and r['ready_players'] == self.players for r in reports):
                self.stable_since = None
                return
            if self.stable_since is None:
                self.stable_since = now
                return
            if now - self.stable_since < 1:
                return
            self.validate_graph(reports[0])
            self.check('same_generation_and_digest', len({r['generation_id'] for r in reports}) == 1
                       and bool(reports[0]['digest']) and len({r['digest'] for r in reports}) == 1)
            fields = ('layout_version', 'main_path_length', 'used_fallback', 'diversity_relaxed',
                      'placement_attempts', 'search_steps', 'rooms', 'connections')
            self.check('same_manifest', all(all(r[k] == reports[0][k] for k in fields) for r in reports))
            self.check('all_rooms_loaded', all(r['loaded_rooms'] == r['streamed_rooms'] == len(r['rooms']) - 1 for r in reports))
            self.check('all_unused_doors_and_safety_gate', all(r['door_barriers'] == 4 * len(r['rooms']) - 2 * len(r['connections']) + 1 for r in reports))
            self.check('expected_player_count', all(r['expected_players'] == self.players for r in reports))
            self.check('requested_seed', all(r['seed'] == int(self.request.get('seed', r['seed'])) for r in reports))
            self.check('ready_input_released', all(not pc.is_move_input_ignored() for items in controllers for pc in items))
            if 'expected_fallback' in self.request:
                self.check('expected_fallback', all(r['used_fallback'] == bool(self.request['expected_fallback']) for r in reports))
            for runtime, report in zip(runtimes, reports):
                self.validate_world(runtime, report)
            self.finish()
        except Exception:
            self.finish(traceback.format_exc())


_directory = Path(u.Paths.project_dir()).resolve() / 'Saved/RoguelikeGeneration'
_directory.mkdir(parents=True, exist_ok=True)
_request = json.loads((_directory / 'floor-request.json').read_text(encoding='utf-8-sig'))
_previous = getattr(builtins, '_roguelike_floor_verification', None)
if _previous and not _previous.finished:
    _previous.finish('Superseded by another floor verification')
_verification = FloorVerification(_request, _directory)
builtins._roguelike_floor_verification = _verification
_verification.start()
