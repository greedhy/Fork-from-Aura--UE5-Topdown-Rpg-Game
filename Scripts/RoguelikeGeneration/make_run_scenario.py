"""Create an explicit fresh-run PIE request; this script never contacts Unreal.

Example:
  python make_run_scenario.py --capture Saved/RoguelikeGeneration/run-checks/solo-initial.json \
    --party 2 --request-id duo-full-01 --output Saved/RoguelikeGeneration/run-check-request.json

The captured manifest supplies geometry only. The new run must use its seed and
the stage-3 baseline profile (15/30/50 clear coins, first shop offer costs 30).
All branches are visited before the final Boss. Rest requires the driver's real
activate_ability action unless --rest-mode skip is explicitly selected.
"""
import argparse
import json
import math
import re
from collections import deque
from pathlib import Path


BURST = '/Game/PureMass/Abilities/GA_Prototype_Burst.GA_Prototype_Burst_C'
REWARDS = {'Combat': 15, 'Elite': 30, 'Boss': 50}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def authority_snapshot(document):
    snapshots = document.get('latest')
    if snapshots is None and document.get('snapshots'):
        snapshots = document['snapshots'][-1]['worlds']
    if snapshots is None and document.get('authority') is True:
        snapshots = [document]
    selected = [entry for entry in snapshots or [] if entry.get('authority') is True]
    require(len(selected) == 1, 'Capture must contain exactly one authority snapshot')
    return selected[0]


def layout_from_capture(document):
    snapshot = authority_snapshot(document)
    generation, run = snapshot['generation'], snapshot['run']
    rooms = run['rooms']
    require(2 <= len(rooms) <= 64, 'Expected 2 to 64 generated rooms')
    require([room['index'] for room in rooms] == list(range(len(rooms))), 'Room indices must match manifest order')
    require(rooms[0]['role'].split('::')[-1] == 'Entrance', 'Room zero must be the entrance')
    require(len(generation['rooms']) == len(rooms), 'Generation/run room counts differ')
    adjacency = [[] for _ in rooms]
    edge_set = set()
    for edge in run['connections']:
        a, b = edge['from'], edge['to']
        require(isinstance(a, int) and isinstance(b, int) and 0 <= a < len(rooms) and 0 <= b < len(rooms) and a != b,
                'Invalid room connection')
        key = tuple(sorted((a, b)))
        require(key not in edge_set, 'Duplicate room connection')
        edge_set.add(key)
        adjacency[a].append(b)
        adjacency[b].append(a)
        require((rooms[a]['x'] == rooms[b]['x']) != (rooms[a]['y'] == rooms[b]['y']), 'Expected cardinal room connections')
    require(len(edge_set) == len(rooms) - 1, 'Stage-3 scenario expects a tree')
    parent = {0: None}
    queue = deque([0])
    while queue:
        node = queue.popleft()
        for child in sorted(adjacency[node]):
            if child not in parent:
                parent[child] = node
                queue.append(child)
    require(len(parent) == len(rooms), 'Layout must be connected')
    bosses = [r['index'] for r in rooms if r['role'].split('::')[-1] == 'Boss']
    require(len(bosses) == 1 and len(adjacency[bosses[0]]) == 1, 'Expected one leaf Boss room')
    boss_path = set()
    node = bosses[0]
    while node is not None:
        boss_path.add(node)
        node = parent[node]
    route = [0]

    def visit(node):
        if node == bosses[0]:
            return True
        children = [child for child in adjacency[node] if parent.get(child) == node]
        for child in sorted(children, key=lambda value: (value in boss_path, value)):
            route.append(child)
            if visit(child):
                return True
            route.append(node)
        return False

    visit(0)
    require(set(route) == set(range(len(rooms))) and route[-1] == bosses[0], 'Route must cover all rooms and end at Boss')
    return snapshot, rooms, route


def check(path, value, op='eq', scope='authority'):
    return {'scope': scope, 'path': path, 'op': op, 'value': value}


def build_request(document, party, request_id, rest_mode='burst', leave=False):
    require(party in (1, 2), 'Only one or two players are supported')
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,100}', request_id) is not None, 'Invalid request id')
    require(rest_mode in ('burst', 'skip'), 'Invalid rest mode')
    snapshot, rooms, route = layout_from_capture(document)
    actions, coins, revisions = [], [0] * party, [0] * party
    visited, claimed, purchased, rested = {0}, set(), set(), set()

    def add(kind, **arguments):
        if kind in ('kill_actor_group', 'damage_actor'):
            actions.append({'action':'wait', 'until':[check('run.pending_enemy_spawns',0)], 'stable_seconds':0})
        action = {'action': kind, 'settle_seconds': .05, 'stable_seconds': 0, **arguments}
        actions.append(action)
        return action

    def room_checks(index, phase):
        return [check('run.rooms.' + str(index) + '.phase', phase, scope='all')]

    def balance_checks():
        return [check('run.players.' + str(player) + '.coins', amount) for player, amount in enumerate(coins)]

    def position(index, player):
        # Separate both axes: a stationary partner must not block the swept path
        # when the route turns from east/west to north/south.
        offset = 0 if party == 1 else (-120 if player == 0 else 120)
        return [rooms[index]['x'] + offset, rooms[index]['y'] + offset, 95]

    def movement(source, target, player, entering):
        start, end = position(source, player), position(target, player)
        distance = math.dist(start, end)
        count = max(1, math.ceil(distance / 450))
        points = [start] + [[round(start[axis] + (end[axis] - start[axis]) * step / count, 4)
                            for axis in range(3)] for step in range(1, count + 1)]
        assertions = [check('run.players.' + str(player) + '.room_index', target)]
        if entering and party == 2 and player == 0 and rooms[target]['role'].split('::')[-1] in REWARDS:
            assertions += room_checks(target, 'Gathering')
            assertions.append(check('run.targets', 0, 'len_eq'))
        add('move_player', player_index=player, waypoints=points, sweep=True, waypoint_interval=.05,
            max_step_cm=600, arrival_tolerance_cm=100, checks=assertions)

    add('wait', until=[check('run.phase', 'Exploring', scope='all'),
                       check('generation.seed', snapshot['generation']['seed'], scope='all'),
                       check('run.rooms', len(rooms), 'len_eq', scope='all'),
                       check('run.targets', 0, 'len_eq')])
    # The authored starts are within 500 cm of these separated entrance points.
    for player in range(party):
        add('move_player', player_index=player, waypoints=[position(0, player)], sweep=True,
            waypoint_interval=.05, max_step_cm=600, checks=[check('run.players.' + str(player) + '.room_index', 0)])

    for previous, index in zip(route, route[1:]):
        entering = index not in visited
        for player in range(party):
            movement(previous, index, player, entering)
        role = rooms[index]['role'].split('::')[-1]
        if not entering:
            add('wait', until=room_checks(index, 'Cleared') + balance_checks()
                + [check('run.targets', 0, 'len_eq'), check('run.phase', 'Exploring', scope='all')])
            continue
        visited.add(index)
        if role in REWARDS:
            first_required = 5 if role == 'Elite' else 3 if role == 'Boss' else 1
            add('wait', until=room_checks(index, 'Active')
                + [check('run.active_room', index, scope='all'), check('run.rooms.' + str(index) + '.wave', 1, scope='all'),
                   check('run.rooms.' + str(index) + '.remaining_required', first_required, 'gte')])
            if role == 'Combat':
                add('kill_actor_group', source_player_index=0)
                add('wait', until=[check('run.rooms.' + str(index) + '.wave', 2, scope='all'),
                                   check('run.rooms.' + str(index) + '.pending_waves', 0, scope='all'),
                                   check('run.rooms.' + str(index) + '.remaining_required', 1, 'gte')])
                add('kill_actor_group', source_player_index=0)
            elif role == 'Elite':
                add('damage_actor', source_player_index=0, target='elite', amount=1000000)
                add('kill_actor_group', source_player_index=0)
            else:
                add('damage_actor', source_player_index=0, target='boss', target_health_fraction=.49)
                add('wait', until=[check('run.rooms.' + str(index) + '.remaining_required', 5),
                                   check('run.targets', 7, 'len_eq')])
                add('damage_actor', source_player_index=0, target='boss', amount=1000000)
                add('wait', until=[check('run.rooms.' + str(index) + '.remaining_required', 4),
                                   check('run.targets', 4, 'len_eq'), check('run.targets.*.required', True)])
                add('kill_actor_group', source_player_index=0)
            coins = [amount + REWARDS[role] for amount in coins]
            add('wait', until=room_checks(index, 'Cleared') + balance_checks()
                + [check('run.phase', 'Victory' if role == 'Boss' else 'Exploring', scope='all'),
                   check('run.targets', 0, 'len_eq')])
        elif role == 'Treasure':
            for player in range(party):
                prefix = 'run.players.' + str(player)
                add('wait', until=[check(prefix + '.can_interact', True), check(prefix + '.chest_remaining', 0, 'gt')])
                revisions[player] += 1
                assertions = [check(prefix + '.chest_remaining', 0), check(prefix + '.backpack.revision', revisions[player])]
                if party == 2 and player == 0:
                    assertions.append(check('run.players.1.chest_remaining', 0, 'gt'))
                add('interact', player_index=player, interaction='CLAIM_TREASURE', repeat=2,
                    checks=assertions + balance_checks())
            claimed.add(index)
        elif role == 'Merchant':
            for player in range(party):
                require(coins[player] >= 30, 'Route reached shop before earning its cheapest offer')
                coins[player] -= 30
                revisions[player] += 1
                prefix = 'run.players.' + str(player)
                add('interact', player_index=player, interaction='PURCHASE', offer_index=0, repeat=2,
                    checks=[check(prefix + '.purchased.0', True), check(prefix + '.coins', coins[player]),
                            check(prefix + '.backpack.revision', revisions[player])])
            purchased.add(index)
        elif role == 'Rest' and rest_mode == 'burst':
            for player in range(party):
                add('activate_ability', player_index=player, ability_class=BURST, world='owner')
                add('interact', player_index=player, interaction='REST', repeat=2,
                    checks=[check('run.players.' + str(player) + '.rested', True)] + balance_checks())
            rested.add(index)

    final_checks = [check('run.phase', 'Victory', scope='all'), check('run.rooms.*.visited', True, scope='all'),
                    check('run.rooms.*.phase', 'Cleared', scope='all'), check('run.targets', 0, 'len_eq'),
                    check('run.players.*.alive', True, scope='all')] + balance_checks()
    # Once both players performed identical transactions, owner-only reports should agree.
    if len(set(coins)) == 1:
        final_checks.append(check('run.players.*.coins', coins[0], scope='all'))
    add('capture', checks=final_checks)
    if leave:
        add('interact', player_index=0, interaction='EXIT', allow_world_exit=True)
    require(len(actions) <= 256, 'Generated request exceeds the verifier action limit')
    return {
        'request_id': request_id, 'expected_worlds': party, 'expected_players': party, 'timeout': 300,
        'scenario': {'name': 'all-rooms-before-boss', 'seed': snapshot['generation']['seed'],
                     'route': route, 'room_count': len(rooms), 'action_count': len(actions),
                     'expected_final_coins': coins, 'expected_backpack_revisions': revisions,
                     'chests_claimed': sorted(claimed), 'shops_purchased': sorted(purchased),
                     'rests_consumed': sorted(rested), 'rest_mode': rest_mode,
                     'assumptions': ['Fresh run at the authored entrance with empty backpack and zero run coins.',
                                     'Baseline clear coins 15/30/50 and offer zero costs30.',
                                     'Driver uses bounded real GE damage to stop the Boss alive below half health.',
                                     'Wall-clock timeout depends on editor frame rate; no editor settings are modified.'],
                     'limitations': ['This request uses sweep-based waypoint movement and actual damage APIs, not keyboard combat.',
                                     'Full inventory, disconnect, death/revival and stale requests require separate scenarios.']
                                    + (['Rest activation/consumption deliberately skipped.'] if rest_mode == 'skip' else [])},
        'actions': actions,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--party', type=int, choices=(1, 2), required=True)
    parser.add_argument('--request-id', required=True)
    parser.add_argument('--output', type=Path, default=Path('Saved/RoguelikeGeneration/run-check-request.json'))
    parser.add_argument('--rest-mode', choices=('burst', 'skip'), default='burst')
    parser.add_argument('--exit', action='store_true', dest='leave')
    parser.add_argument('--dry-run', action='store_true', help='Validate and print summary without writing any file')
    args = parser.parse_args()
    capture = json.loads(args.capture.read_text(encoding='utf-8-sig'))
    request = build_request(capture, args.party, args.request_id, args.rest_mode, args.leave)
    if not args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'request_id': request['request_id'], 'output': None if args.dry_run else str(args.output),
                      **request['scenario']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
