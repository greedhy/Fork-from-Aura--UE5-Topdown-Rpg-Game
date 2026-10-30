"""Generate one fresh-run fault/recovery request; never contact or execute Unreal.

Example:
  python make_run_fault_scenario.py --capture Saved/RoguelikeGeneration/run-checks/solo-initial.json \
    --scenario clear-revive --party 2 --request-id duo-revive-01 --output Saved/RoguelikeGeneration/run-check-request.json

Start each generated request in a new PIE run with the captured seed and matching
ExpectedPlayers. Damage uses the verifier's actual GAS/Mass APIs. No direct revive,
private state edit, inventory edit, automatic editor operation, or exit is emitted.
"""
import argparse
import json
import math
import re
from collections import deque
from pathlib import Path

from make_run_scenario import REWARDS, check, layout_from_capture, require


SCENARIOS = ('gathering-retreat', 'clear-revive', 'all-down', 'required-removal')


def target_route(rooms, connections, role):
    """Choose the shortest deterministic entrance-to-role path without crossing Boss."""
    adjacency = [[] for _ in rooms]
    for edge in connections:
        adjacency[edge['from']].append(edge['to'])
        adjacency[edge['to']].append(edge['from'])
    queue, visited = deque([[0]]), {0}
    while queue:
        route = queue.popleft()
        node = route[-1]
        if rooms[node]['role'].split('::')[-1] == role:
            return route
        for child in sorted(adjacency[node]):
            if child not in visited and rooms[child]['role'].split('::')[-1] != 'Boss':
                visited.add(child)
                queue.append(route + [child])
    raise ValueError('No reachable ' + role + ' room before Boss')


def build_fault_request(document, scenario, party, request_id):
    require(scenario in SCENARIOS, 'Unknown fault scenario')
    require(party in (1, 2), 'Only one or two players are supported')
    require(party == 2 or scenario not in ('gathering-retreat', 'clear-revive'),
            'Gathering/partner revival requires two players')
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,100}', request_id) is not None, 'Invalid request id')
    snapshot, rooms, _ = layout_from_capture(document)
    role = 'Elite' if scenario in ('clear-revive', 'all-down') else 'Combat'
    route = target_route(rooms, snapshot['run']['connections'], role)
    target, actions, coins = route[-1], [], 0

    def add(kind, **arguments):
        if kind in ('kill_actor_group','damage_actor','down_player','destroy_actor'):
            actions.append({'action':'wait','until':[check('run.pending_enemy_spawns',0)],'stable_seconds':0})
        actions.append({'action': kind, 'settle_seconds': .05, 'stable_seconds': 0, **arguments})

    def room_phase(index, phase):
        return check('run.rooms.' + str(index) + '.phase', phase, scope='all')

    def balance(amount):
        return check('run.players.*.coins', amount, scope='all')

    def position(index, player):
        offset = 0 if party == 1 else (-120 if player == 0 else 120)
        return [rooms[index]['x'] + offset, rooms[index]['y'] + offset, 95]

    def move(source, destination, player, assertions=()):
        start, end = position(source, player), position(destination, player)
        count = max(1, math.ceil(math.dist(start, end) / 450))
        points = [start] + [[round(start[axis] + (end[axis] - start[axis]) * step / count, 4)
                            for axis in range(3)] for step in range(1, count + 1)]
        add('move_player', player_index=player, waypoints=points, sweep=True,
            waypoint_interval=.05, max_step_cm=600, arrival_tolerance_cm=100,
            checks=[check('run.players.' + str(player) + '.room_index', destination)] + list(assertions))

    def active(index):
        required = 5 if rooms[index]['role'].split('::')[-1] == 'Elite' else 1
        add('wait', until=[check('run.phase', 'Encounter', scope='all'), room_phase(index, 'Active'),
                           check('run.active_room', index, scope='all'),
                           check('run.rooms.' + str(index) + '.remaining_required', required, 'gte')])

    def clear(index, source_player=0, extra=()):
        nonlocal coins
        current_role = rooms[index]['role'].split('::')[-1]
        require(current_role in ('Combat', 'Elite'), 'Unexpected encounter before fault target')
        if current_role == 'Elite':
            add('damage_actor', source_player_index=source_player, target='elite', amount=1000000)
        add('kill_actor_group', source_player_index=source_player)
        if current_role == 'Combat':
            add('wait', until=[check('run.rooms.' + str(index) + '.wave', 2, scope='all'),
                               check('run.rooms.' + str(index) + '.pending_waves', 0, scope='all'),
                               check('run.rooms.' + str(index) + '.remaining_required', 1, 'gte')])
            add('kill_actor_group', source_player_index=source_player)
        coins += REWARDS[current_role]
        add('wait', until=[room_phase(index, 'Cleared'), check('run.phase', 'Exploring', scope='all'),
                           check('run.targets', 0, 'len_eq'), balance(coins)] + list(extra))

    add('wait', until=[check('run.phase', 'Exploring', scope='all'),
                       check('generation.seed', snapshot['generation']['seed'], scope='all'),
                       check('run.rooms', len(rooms), 'len_eq', scope='all'),
                       check('run.players.*.alive', True, scope='all'), balance(0),
                       check('run.targets', 0, 'len_eq')])
    for player in range(party):
        add('move_player', player_index=player, waypoints=[position(0, player)], sweep=True,
            waypoint_interval=.05, max_step_cm=600,
            checks=[check('run.players.' + str(player) + '.room_index', 0)])

    for previous, index in zip(route, route[1:]):
        combat = rooms[index]['role'].split('::')[-1] in REWARDS
        for player in range(party):
            assertions = [room_phase(index, 'Gathering'), check('run.targets', 0, 'len_eq')]
            move(previous, index, player, assertions if combat and party == 2 and player == 0 else [])
            if scenario == 'gathering-retreat' and index == target and player == 0:
                move(index, previous, player, [room_phase(index, 'Discovered'),
                     check('run.gathering_room', -1, scope='all'), check('run.active_room', -1, scope='all'),
                     check('run.phase', 'Exploring', scope='all'), check('run.targets', 0, 'len_eq'), balance(coins)])
                move(previous, index, player, assertions)
        if combat:
            active(index)
            if index != target:
                clear(index)
        else:
            add('wait', until=[room_phase(index, 'Cleared'), check('run.targets', 0, 'len_eq')])

    if scenario == 'gathering-retreat':
        clear(target)
        previous = route[-2]
        for player in range(party):
            move(target, previous, player)
        for player in range(party):
            move(previous, target, player)
        add('capture', checks=[room_phase(target, 'Cleared'), check('run.targets', 0, 'len_eq'),
                              check('run.phase', 'Exploring', scope='all'), balance(coins)], stable_seconds=.3)
    elif scenario == 'clear-revive':
        add('down_player', target='elite', player_index=0,
            checks=[check('run.players.0.alive', False), check('run.players.1.alive', True),
                    check('players.0.downed', True), room_phase(target, 'Active')])
        # Only a living partner deals the remaining real damage. CompleteEncounter must revive player 0.
        clear(target, source_player=1, extra=[check('run.players.*.alive', True, scope='all'),
              check('players.*.downed', False, scope='all'), check('run.players.0.health', 0, 'gt'),
              check('run.players.0.mana', 0, 'gt')])
        add('capture', checks=[room_phase(target, 'Cleared'), balance(coins),
                              check('players.*.downed', False, scope='all'), check('run.targets', 0, 'len_eq')])
    elif scenario == 'all-down':
        for player in range(party):
            add('down_player', target='elite', player_index=player)
        add('wait', until=[check('run.phase', 'Failed', scope='all'),
                           check('run.error', 'AllPlayersDown', scope='all'), room_phase(target, 'Failed'),
                           check('run.players.*.alive', False, scope='all'),
                           check('players.*.downed', True, scope='all'), check('run.targets', 0, 'len_eq'),
                           check('mass', 0, 'len_eq'), check('run.pending_enemy_spawns',0), balance(coins)])
        add('capture', checks=[check('run.phase', 'Failed', scope='all'), balance(coins)], stable_seconds=.3)
    else:
        add('destroy_actor', target='first_required')
        add('wait', until=[check('run.phase', 'Failed', scope='all'),
                           check('run.error', 'TargetRemovedWithoutKill:', 'contains', scope='all'),
                           room_phase(target, 'Failed'), check('run.targets', 0, 'len_eq'),
                           check('mass', 0, 'len_eq'), check('run.pending_enemy_spawns',0), balance(coins)])
        add('capture', checks=[check('run.phase', 'Failed', scope='all'), balance(coins)], stable_seconds=.3)

    require(len(actions) <= 256, 'Generated request exceeds verifier action limit')
    return {
        'request_id': request_id, 'expected_worlds': party, 'expected_players': party, 'timeout': 300,
        'scenario': {'name': scenario, 'seed': snapshot['generation']['seed'], 'route': route,
                     'target_room': target, 'action_count': len(actions), 'expected_final_coins': coins,
                     'expected_final_phase': 'Failed' if scenario in ('all-down', 'required-removal') else 'Exploring',
                     'assumptions': ['Fresh PIE at authored entrance with matching ExpectedPlayers and zero run coins.',
                                     'Baseline two-wave Combat rooms, one elite Actor plus four normal Actors in Elite rooms.',
                                     'Each request has a new request_id; start a new Run for each scenario.'],
                     'limitations': ['Sweep movement and real damage/removal APIs do not verify keyboard combat.',
                                     'Automatic revival checks observable recovery; exact 30% and preserved loadout are covered by native tests.',
                                     'No merchant/treasure RPC, editor operation, direct revival, save mutation, or exit is requested.']},
        'actions': actions,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--scenario', choices=SCENARIOS, required=True)
    parser.add_argument('--party', type=int, choices=(1, 2), required=True)
    parser.add_argument('--request-id', required=True)
    parser.add_argument('--output', type=Path, default=Path('Saved/RoguelikeGeneration/run-check-request.json'))
    parser.add_argument('--dry-run', action='store_true', help='Validate and summarize without writing a request')
    args = parser.parse_args()
    capture = json.loads(args.capture.read_text(encoding='utf-8-sig'))
    request = build_fault_request(capture, args.scenario, args.party, args.request_id)
    if not args.dry_run:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'request_id': request['request_id'], 'output': None if args.dry_run else str(args.output),
                      **request['scenario']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
