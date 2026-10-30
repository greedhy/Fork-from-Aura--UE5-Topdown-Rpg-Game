"""Bounded request-driven PIE verifier; no editor operations or asset/savegame writes.

Run with console ``py <absolute path to this script>`` after starting PIE. Input:
Saved/RoguelikeGeneration/run-check-request.json. Atomic output: run-check-response.json.
Receipts are also retained in run-checks/<request_id>.json to prevent replay.
expected_map defaults to /Game/RoguelikeGeneration/Maps/L_RoguelikeRun (package
path, not object path). A different active PIE map fails before gameplay actions.
This guard is not an editor lock: coordinate exclusive use before starting PIE.

Example (one request_id must identify exactly one immutable request):
{
  "request_id": "solo-first-room", "expected_worlds": 1, "expected_players": 1,
  "timeout": 60, "actions": [
    {"action": "capture"},
    {"action": "move_player", "player_index": 0,
     "waypoints": [[0,0,110],[500,0,110],[1000,0,110]], "sweep": true},
    {"action": "wait", "until": [{"scope":"authority", "path":"run.phase",
      "op":"endswith", "value":"Encounter"}]},
    {"action": "kill_mass", "source_player_index": 0},
    {"action": "capture"}
  ]
}

Player indices always refer to authority controllers ordered by PlayerState.player_id.
interact selects that player's owning local controller, including the remote client.
Checks address each world snapshot (run, generation, players, actors, mass) with dot
paths and optional * array expansion. Supported scopes: authority, client, all, or
an exact PIE world path. Explicit wait/check steps are required to prove business
outcomes; a successful action receipt alone does not prove a completed run.
"""

import builtins
import hashlib
import json
import math
import os
import re
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

import unreal as u


class RunVerification:
    ACTIONS = {'kill_actor_group', 'capture', 'wait', 'move_player', 'kill_mass', 'damage_actor', 'damage_player', 'activate_ability',
               'down_player', 'revive_player', 'interact', 'remove_mass', 'destroy_actor'}
    MUTATIONS = ACTIONS - {'capture', 'wait'}
    EFFECT = '/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage.GE_Damage_C'

    def __init__(self, request, directory):
        self.request, self.directory = request, directory
        self.request_id = request.get('request_id', '')
        self.require(isinstance(self.request_id, str) and
                     re.fullmatch(r'[A-Za-z0-9_-]{1,100}', self.request_id), 'InvalidRequestId')
        self.actions = request.get('actions', [request] if 'action' in request else [])
        self.require(isinstance(self.actions, list) and 1 <= len(self.actions) <= 256, 'Expected1To256Actions')
        for action in self.actions:
            self.require(isinstance(action, dict) and action.get('action') in self.ACTIONS, 'UnknownAction')
            for key in ('until', 'checks'):
                self.require(isinstance(action.get(key, []), list), 'CheckListMustBeAnArray')
        self.expected_worlds = int(request.get('expected_worlds', 1))
        self.expected_players = int(request.get('expected_players', 1))
        self.expected_map = request.get('expected_map', '/Game/RoguelikeGeneration/Maps/L_RoguelikeRun')
        self.require(isinstance(self.expected_map, str) and self.expected_map.startswith('/Game/')
                     and '.' not in self.expected_map, 'ExpectedMapMustBeGamePackagePath')
        self.timeout = self.number(request.get('timeout', 90), 1, 300, 'timeout')
        self.require(self.expected_worlds in (1, 2) and self.expected_players in (1, 2), 'OnlySingleOrDuoPIE')
        self.started = time.monotonic()
        self.next_sample = 0
        self.index = 0
        self.step = None
        self.bound_generation = None
        self.bound_run = None
        self.finished = False
        self.handle = None
        self.last_write = 0
        self.fingerprint = self.request_hash(request)
        self.result = {
            'schema': 'roguelike-run-check-v1', 'request_id': self.request_id,
            'request_sha256': self.fingerprint, 'execution_id': uuid.uuid4().hex,
            'started_utc': datetime.now(timezone.utc).isoformat(), 'request': request,
            'runtime': {'editor_pid': os.getpid(), 'engine_version': u.SystemLibrary.get_engine_version(),
                        'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            'phase': 'waiting_for_pie', 'passed': False, 'receipts': [], 'snapshots': [],
            'checks': [], 'limitations': [
                'Editor PIE only; no packaged or separate-process networking evidence.',
                'Movement uses Actor SetActorLocation waypoints, not physical input or a movement ability.',
                'Damage actions use real Mass damage / GE_Damage, not player ability activation or attack animation.',
                'Interact calls the owning controller request API; this does not prove keyboard/UI focus.',
                'Direct revive is an explicit fixture action, not evidence of automatic clear-room revival.',
                'No private backpack fields are read or modified; inventory checks require native run-report fields.',
                'No full-pack fixture or disconnect fixture is implemented by this public-API driver.',
            ],
            'api_evidence': {
                'mass': 'PureMassSubsystem.h: ApplyDamage/GetSnapshots/RemoveMonster UFUNCTIONs; Scripts/PureMass/verify_pie.py',
                'gas': 'MyAbilitySystemLibrary.h: ApplyDamageEffect; Scripts/Mass/verify_pie.py and PureMass/verify_pie.py',
                'interaction': 'DungeonRunController.h: RequestRoomInteraction/ServerRoomInteraction UFUNCTIONs',
                'revive': 'DungeonPlayerCharacter.h: ReviveForDungeon/IsDungeonDowned UFUNCTIONs',
                'capture': 'DungeonRunDirector.h: GetRunReport/GetGeneration; public reflected RunView',
            },
        }

    @staticmethod
    def require(condition, message):
        if not condition:
            raise RuntimeError(message)

    @staticmethod
    def request_hash(request):
        return hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()

    @staticmethod
    def number(value, lower, upper, name):
        value = float(value)
        RunVerification.require(math.isfinite(value) and lower <= value <= upper, 'InvalidNumber: ' + name)
        return value

    @staticmethod
    def vector(value):
        RunVerification.require(isinstance(value, (list, tuple)) and len(value) == 3, 'ExpectedXYZVector')
        return u.Vector(*(RunVerification.number(part, -1000000, 1000000, 'vector') for part in value))

    @staticmethod
    def xyz(value):
        return [value.x, value.y, value.z]

    @staticmethod
    def player_id(controller):
        state = controller.get_editor_property('player_state')
        return state.get_editor_property('player_id') if state else None

    @staticmethod
    def asc(actor):
        # Player ASC lives on PlayerState; both lookups are public reflected APIs.
        if isinstance(actor, u.DungeonPlayerCharacter):
            controller = actor.get_controller()
            state = controller.get_editor_property('player_state') if controller else None
            return state.get_component_by_class(u.MyAbilitySystemComponent) if state else None
        return actor.get_component_by_class(u.MyAbilitySystemComponent)

    @staticmethod
    def attributes(actor):
        asc = RunVerification.asc(actor)
        attributes = asc.get_attribute_set(u.MyAttributeSet) if asc else None
        if not attributes:
            return {'health': None, 'max_health': None, 'mana': None, 'max_mana': None}
        return {key: attributes.get_editor_property(key).get_editor_property('current_value')
                for key in ('health', 'max_health', 'mana', 'max_mana')}

    def write(self):
        self.result['elapsed_seconds'] = round(time.monotonic() - self.started, 3)
        history = self.directory / 'run-checks'
        history.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(self.result, ensure_ascii=False, indent=2)
        # Write immutable identity history first. A process interruption between
        # files must never make an already-dispatched request eligible for replay.
        for destination in (history / (self.request_id + '.json'), self.directory / 'run-check-response.json'):
            temporary = destination.with_suffix('.json.tmp')
            temporary.write_text(encoded, encoding='utf-8')
            for attempt in range(5):
                try:
                    temporary.replace(destination)
                    break
                except PermissionError:
                    # Windows readers can briefly deny replacement. Retry only I/O,
                    # never the gameplay action; extra wait is at most 100 ms per file.
                    if attempt < 4:
                        time.sleep(.01 * (attempt + 1))
                        continue
                    if destination.parent == history:
                        raise  # Durable identity receipt must succeed before mutations.
                    # Identity history is authoritative; retry the mirror next write.
        self.last_write = time.monotonic()

    def start(self):
        self.write()
        try:
            self.handle = u.register_slate_post_tick_callback(self.tick)
        except Exception:
            self.finish(traceback.format_exc())
            raise

    def finish(self, error=None):
        if self.finished:
            return
        self.finished = True
        if self.handle is not None:
            try:
                u.unregister_slate_post_tick_callback(self.handle)
            except Exception:
                error = (error or '') + '\nCallbackCleanupFailed: ' + traceback.format_exc()
            self.handle = None
        self.result.update(phase='complete', passed=error is None and self.index == len(self.actions),
                           error=error, finished_utc=datetime.now(timezone.utc).isoformat())
        if self.step and self.step.get('status') != 'complete':
            self.step['status'] = 'failed'
            self.step['mutation_may_have_occurred'] = self.step.get('dispatched', False)
        self.write()
        u.log('ROGUELIKE_RUN_CHECK ' + self.request_id + ' passed=' + str(self.result['passed']))

    @staticmethod
    def parse_run_report(payload):
        run = json.loads(payload)
        RunVerification.require(isinstance(run, dict), 'NativeRunReportMustBeJSONObject')
        # Each action retains before/after state. Repeating the rolling sample history
        # in every state makes receipt I/O grow quadratically with run duration.
        # Native ExportPerformanceReport (also called on EndPlay) keeps those samples.
        performance = run.get('performance', {})
        run['receipt_omitted_performance_samples'] = len(performance.pop('samples', []))
        return run

    @staticmethod
    def validate_pie_maps(paths, expected_map):
        for path in paths:
            package = re.sub(r'/UEDPIE_\d+_', '/', path.split('.', 1)[0])
            RunVerification.require(package == expected_map,
                                    'UnexpectedPIEMap: expected=' + expected_map + ', actual=' + path)

    def collect(self):
        contexts = []
        seen = set()
        for director in u.ObjectIterator(u.DungeonRunDirector):
            world = director.get_world()
            if not world or 'UEDPIE_' not in world.get_path_name():
                continue
            if director not in u.GameplayStatics.get_all_actors_of_class(world, u.DungeonRunDirector):
                continue
            path = world.get_path_name()
            self.require(path not in seen, 'MultipleDirectorsInWorld: ' + path)
            seen.add(path)
            generation = director.get_generation()
            run = self.parse_run_report(director.get_run_report())
            controllers = sorted((pc for pc in u.GameplayStatics.get_all_actors_of_class(world, u.DungeonRunController)
                                  if pc.get_controlled_pawn() and self.player_id(pc) is not None),
                                 key=self.player_id)
            mass = [subsystem for subsystem in u.ObjectIterator(u.PureMassSubsystem) if subsystem.get_world() == world]
            self.require(len(mass) <= 1, 'MultipleMassSubsystemsInWorld')
            enemies = sorted(u.GameplayStatics.get_all_actors_of_class(world, u.EnemyCharacter),
                             key=lambda actor: actor.get_path_name())
            snapshot = {'world': path, 'authority': director.get_local_role() == u.NetRole.ROLE_AUTHORITY,
                        'director': director.get_path_name(), 'run': run,
                        'generation': json.loads(generation.get_generation_report()) if generation else {},
                        'game_seconds': u.GameplayStatics.get_time_seconds(world),
                        'players': [], 'actors': [], 'mass': []}
            for pc in controllers:
                pawn = pc.get_controlled_pawn()
                self.require(isinstance(pawn, u.DungeonPlayerCharacter), 'UnexpectedPawnClassInRun')
                view = pc.get_editor_property('run_view')
                snapshot['players'].append({
                    'player_id': self.player_id(pc), 'controller': pc.get_path_name(),
                    'pawn': pawn.get_path_name(), 'asc': self.asc(pawn).get_path_name(), 'local': pc.is_local_controller(),
                    'position': self.xyz(pawn.get_actor_location()), 'downed': pawn.is_dungeon_downed(),
                    'movement_ignored': pc.is_move_input_ignored(), **self.attributes(pawn),
                    'view': {**{key: view.get_editor_property(key) for key in
                               ('coins', 'can_interact', 'chest_remaining', 'rested', 'message')},
                             'current_room': str(view.get_editor_property('current_room')),
                             'purchased': list(view.get_editor_property('purchased'))}})
            snapshot['pool_actors'] = []
            for enemy in enemies:
                life = enemy.get_dungeon_pool_lease()
                if life:
                    mesh = enemy.get_editor_property('mesh')
                    weapon = enemy.get_editor_property('weapon')
                    snapshot['pool_actors'].append({
                        'path': enemy.get_path_name(), 'class': enemy.get_class().get_path_name(), 'life': life,
                        'hidden': enemy.get_editor_property('hidden'), 'actor_tick': enemy.is_actor_tick_enabled(),
                        'mesh_tick': mesh.is_component_tick_enabled(),
                        'ragdoll': mesh.is_simulating_physics(),
                        'weapon_attached': weapon.get_attach_parent() == mesh,
                        'weapon_simulating': weapon.is_simulating_physics(),
                        'collision': enemy.get_actor_enable_collision(),
                        'health': self.attributes(enemy)['health']})
                ai = enemy.get_controller()
                brain = ai.get_editor_property('brain_component') if isinstance(ai, u.AIController) else None
                snapshot['actors'].append({'path': enemy.get_path_name(), 'class': enemy.get_class().get_path_name(),
                                           'ai_controller': ai.get_path_name() if ai else None,
                                           'brain_running': brain.is_running() if brain else False,
                                           'position': self.xyz(enemy.get_actor_location()),
                                           'room_id': str(enemy.get_editor_property('monster_room_id')),
                                           **self.attributes(enemy)})
            snapshot['pool_actor_count'] = len(snapshot['pool_actors'])
            if mass:
                snapshot['mass_death_count'] = mass[0].get_death_count()
                snapshot['mass'] = [{'id': view.id, 'health': view.health, 'max_health': view.max_health,
                                     'position': self.xyz(view.location), 'state': view.state}
                                    for view in mass[0].get_snapshots()]
            contexts.append({'director': director, 'world': world, 'controllers': controllers,
                             'enemies': enemies, 'mass': mass[0] if mass else None, 'snapshot': snapshot})
        return sorted(contexts, key=lambda context: context['snapshot']['world'])

    def select_world(self, contexts, scope='authority'):
        if scope in ('authority', 'client'):
            selected = [item for item in contexts if item['snapshot']['authority'] == (scope == 'authority')]
        else:
            selected = [item for item in contexts if item['snapshot']['world'] == scope]
        self.require(len(selected) == 1, 'WorldSelectionMustBeUnique: ' + scope)
        return selected[0]

    def player(self, contexts, index, context=None):
        authority = self.select_world(contexts)
        self.require(isinstance(index, int) and 0 <= index < len(authority['controllers']), 'InvalidAuthorityPlayerIndex')
        server = authority['controllers'][index]
        if context is None or context is authority:
            return server
        selected = [pc for pc in context['controllers'] if self.player_id(pc) == self.player_id(server)]
        self.require(len(selected) == 1, 'SelectedPlayerNotPresentInWorld')
        return selected[0]

    def actor(self, context, action, key='actor_path'):
        path = action.get(key)
        if path:
            selected = [enemy for enemy in context['enemies'] if enemy.get_path_name() == path]
        elif key == 'actor_path' and action.get('target') == 'boss':
            boss = context['director'].get_editor_property('boss')
            selected = [enemy for enemy in context['enemies'] if enemy == boss]
        else:
            selected = [enemy for enemy in context['enemies'] if (self.attributes(enemy)['health'] or 0) > 0]
            if action.get('target') == 'first_required':
                paths = {t['path'] for t in context['snapshot']['run']['targets'] if t['kind']=='actor' and t['required']}
                selected = sorted((e for e in selected if e.get_path_name() in paths),key=lambda e:e.get_path_name())[:1]
            if action.get('target') == 'elite':
                selected = [e for e in selected if self.attributes(e)['max_health'] == 450]
            self.require(len(selected) == 1, 'SpecifyExactEnemyActorPathWhenNotUnique')
        self.require(len(selected) == 1, 'EnemyActorNotFoundInSelectedPIEWorld')
        return selected[0]

    @staticmethod
    def path_values(value, tokens):
        if not tokens:
            return [value]
        key, rest = tokens[0], tokens[1:]
        if key == '*' and isinstance(value, (list, dict)):
            values = value.values() if isinstance(value, dict) else value
            return [found for child in values for found in RunVerification.path_values(child, rest)]
        if isinstance(value, dict) and key in value:
            return RunVerification.path_values(value[key], rest)
        if isinstance(value, list) and key.isdigit() and int(key) < len(value):
            return RunVerification.path_values(value[int(key)], rest)
        return []

    def evaluate_checks(self, snapshots, checks):
        self.require(isinstance(checks, list) and len(checks) <= 100, 'InvalidCheckList')
        results = []
        for check in checks:
            scope = check.get('scope', 'authority')
            selected = [snapshot for snapshot in snapshots if scope == 'all' or
                        (scope == 'authority' and snapshot['authority']) or
                        (scope == 'client' and not snapshot['authority']) or snapshot['world'] == scope]
            path = check.get('path', '')
            self.require(isinstance(path, str) and path, 'CheckPathMissing')
            actual = [self.path_values(snapshot, path.split('.')) for snapshot in selected]
            expected = check.get('value')
            operation = check.get('op', 'eq')
            def test(value):
                if operation == 'eq': return value == expected
                if operation == 'ne': return value != expected
                if operation == 'truthy': return bool(value)
                if operation == 'falsy': return not value
                if operation == 'gt': return value > expected
                if operation == 'gte': return value >= expected
                if operation == 'lt': return value < expected
                if operation == 'lte': return value <= expected
                if operation == 'contains': return expected in value
                if operation == 'not_contains': return expected not in value
                if operation == 'endswith': return str(value).endswith(str(expected))
                if operation == 'len_eq': return len(value) == expected
                raise RuntimeError('UnsupportedCheckOperation: ' + operation)
            passed = bool(selected) and all(values and all(test(value) for value in values) for values in actual)
            results.append({'check': check, 'passed': bool(passed), 'actual': actual})
        return results

    def gas_damage(self, source, target, amount):
        source_asc, target_asc = self.asc(source), self.asc(target)
        self.require(source_asc is not None and target_asc is not None, 'GASDamageRequiresSourceAndTargetASC')
        effect = u.load_class(None, self.EFFECT)
        self.require(effect is not None, 'DamageGameplayEffectMissing')
        params = u.DamageEffectParams()
        for key, value in (
                ('world_context_object', target), ('source_ability_system_component', source_asc),
                ('target_ability_system_component', target_asc), ('damage_gameplay_effect_class', effect),
                ('base_damage', amount), ('debuff_chance', 0.0), ('knockback_chance', 0.0)):
            params.set_editor_property(key, value)
        tag = u.GameplayTag()
        tag.import_text('(TagName="Damage.Physics")')
        params.set_editor_property('damage_type', tag)
        before = self.attributes(target)
        self.step['dispatched'] = True
        self.write()
        u.MyAbilitySystemLibrary.apply_damage_effect(params)
        return {'source': source.get_path_name(), 'target': target.get_path_name(), 'amount': amount,
                'before': before, 'after_immediate': self.attributes(target), 'effect': self.EFFECT}

    def dispatch(self, action, contexts):
        kind = action['action']
        if kind in ('capture', 'wait'):
            return {}
        authority = self.select_world(contexts)
        if kind == 'kill_actor_group':
            source = self.player(contexts, action.get('source_player_index', 0)).get_controlled_pawn()
            self.require(not source.is_dungeon_downed(), 'LivingSourceRequired')
            self.require(authority['snapshot']['run']['pending_enemy_spawns'] == 0, 'WaitForQueuedEnemiesFirst')
            paths = {t['path'] for t in authority['snapshot']['run']['targets'] if t['kind'] == 'actor'}
            targets = [e for e in authority['enemies'] if e.get_path_name() in paths and self.attributes(e)['health'] > 0]
            self.require(0 < len(targets) <= 30, 'ExpectedLivingActorTargets')
            self.step['dispatched'] = True
            self.write()
            hits = [self.gas_damage(source, target, 1000000) for target in targets]
            self.step['detail'] = {'hits': hits}
            self.write()
            self.require(all(hit['after_immediate']['health'] <= 0 for hit in hits), 'ActorGroupNotKilled')
            return {'hits': hits}
        if kind == 'activate_ability':
            server = self.player(contexts, action.get('player_index', 0))
            scope = action.get('world', 'owner')
            candidates = [(context, pc) for context in contexts for pc in context['controllers']
                          if pc.is_local_controller() and self.player_id(pc) == self.player_id(server)
                          and (scope == 'owner' or context is self.select_world(contexts, scope))]
            self.require(len(candidates) == 1, 'ActivationMustUseOwningLocalController')
            context, pc = candidates[0]
            path = action['ability_class']
            self.require(path.startswith('/Game/PureMass/Abilities/GA_Prototype_'), 'ExpectedExistingPrototypeAbility')
            cls = u.load_class(None, path)
            self.require(cls is not None, 'AbilityClassMissing')
            before = self.attributes(server.get_controlled_pawn())
            self.step['dispatched'] = True
            self.write()
            accepted = u.DungeonRunAutomationLibrary.queue_ability_activation(pc, cls)
            self.require(accepted, 'AbilityActivationNotQueued')
            return {'ability': path, 'world': context['snapshot']['world'], 'origin_authority': context['snapshot']['authority'],
                    'before': before, 'queued': accepted}
        if kind == 'move_player':
            waypoints = action.get('waypoints')
            self.require(isinstance(waypoints, list) and 1 <= len(waypoints) <= 256, 'Expected1To256Waypoints')
            points = [self.vector(point) for point in waypoints]
            pawn = self.player(contexts, action.get('player_index', 0)).get_controlled_pawn()
            self.require(not pawn.is_dungeon_downed(), 'CannotMoveDownedPlayer')
            maximum = self.number(action.get('max_step_cm', 600), 1, 2400, 'max_step_cm')
            previous = pawn.get_actor_location()
            for point in points:
                self.require((point - previous).length() <= maximum + .1, 'WaypointStepTooLarge')
                previous = point
            return {'waypoints': [self.xyz(point) for point in points], 'moves': [], 'next_waypoint': 0}
        if kind in ('kill_mass', 'remove_mass'):
            context = self.select_world(contexts, action.get('world', 'authority'))
            rejected = bool(action.get('expect_rejected', False))
            self.require(context['snapshot']['authority'] or (kind == 'kill_mass' and rejected),
                         'ClientMassMutationOnlyAllowedForExplicitRejectionCheck')
            mass = context['mass']
            self.require(mass is not None, 'MassSubsystemMissing')
            existing = {view.id: view for view in mass.get_snapshots()}
            ids = action.get('ids', sorted(existing))
            self.require(isinstance(ids, list) and 1 <= len(ids) <= 64 and
                         len(set(ids)) == len(ids) and all(isinstance(i, int) and i in existing for i in ids),
                         'InvalidOrMissingMassTargetIds')
            results = []
            if kind == 'kill_mass':
                source = self.player(contexts, action.get('source_player_index', 0), context).get_controlled_pawn()
                self.require(not source.is_dungeon_downed(), 'MassDamageRequiresLivingDungeonPawn')
                damage = u.PureMassDamage()
                # Source is reflected but has no Edit flag. Use the struct's supported
                # text importer, as the existing damage-number integration probe does.
                damage.import_text('(Source="' + source.get_path_name() + '")')
                damage.set_editor_property('amount', self.number(action.get('amount', 1000000), .01, 100000000, 'amount'))
                self.require(source.get_path_name() in damage.export_text(), 'MassDamageSourceReadbackMismatch')
            else:
                reason = str(action.get('reason', 'unexpected')).upper()
                self.require(reason in ('RECYCLED', 'UNEXPECTED'), 'RemovalCannotForgeKilledReason')
                reason = getattr(u.PureMassRemovalReason, reason)
            self.step['dispatched'] = True
            self.write()
            for identity in ids:
                result = mass.apply_damage(identity, damage) if kind == 'kill_mass' else mass.remove_monster(identity, reason)
                results.append({'id': identity, 'health_before': existing[identity].health, 'result': result})
            self.require(all((row['result'] == 0 if rejected else row['result'] > 0) for row in results),
                         'MassMutationResultUnexpected')
            return {'world': context['snapshot']['world'], 'targets': results, 'expect_rejected': rejected,
                    'require_killed': kind == 'kill_mass' and not rejected and action.get('require_killed', True)}
        if kind in ('damage_actor', 'damage_player', 'down_player'):
            if kind in ('damage_player', 'down_player'):
                target = self.player(contexts, action.get('player_index', 0)).get_controlled_pawn()
                self.require(not target.is_dungeon_downed(), 'PlayerAlreadyDowned')
                source = self.actor(authority, action, 'source_actor_path')
            else:
                target = self.actor(authority, action)
                source = self.player(contexts, action.get('source_player_index', 0)).get_controlled_pawn()
                self.require(not source.is_dungeon_downed(), 'ActorDamageRequiresLivingSource')
            fraction = action.get('target_health_fraction') if kind == 'damage_actor' else None
            if fraction is not None:
                fraction = self.number(fraction, .1, .9, 'target_health_fraction')
                maximum = self.attributes(target)['max_health']
                goal = maximum * fraction
                hits = []
                for _ in range(64):
                    health = self.attributes(target)['health']
                    if health <= goal:
                        break
                    hit = self.gas_damage(source, target, maximum * .04)
                    self.require(0 < hit['after_immediate']['health'] < health, 'FractionDamageMustBeNonlethalAndEffective')
                    hits.append(hit)
                self.require(hits and 0 < self.attributes(target)['health'] <= goal, 'TargetHealthFractionNotReached')
                return {'target': target.get_path_name(), 'target_health_fraction': fraction, 'hits': hits}
            detail = self.gas_damage(source, target, self.number(action.get('amount', 1000000), .01, 100000000, 'amount'))
            before, after = detail['before']['health'], detail['after_immediate']['health']
            self.require(before is not None and after is not None, 'DamageHealthObservationUnavailable')
            self.require(after >= before if action.get('expect_rejected', False) else after < before,
                         'GASDamageHealthDeltaUnexpected')
            return detail
        if kind == 'revive_player':
            pawn = self.player(contexts, action.get('player_index', 0)).get_controlled_pawn()
            self.require(pawn.is_dungeon_downed(), 'DirectReviveRequiresDownedPlayer')
            position = self.vector(action['location']) if 'location' in action else pawn.get_actor_location()
            fraction = self.number(action.get('fraction', .3), .01, 1, 'fraction')
            self.step['dispatched'] = True
            self.write()
            success = pawn.revive_for_dungeon(position, fraction)
            self.require(success, 'DirectReviveRejected')
            return {'pawn': pawn.get_path_name(), 'success': success,
                    'fixture_only': 'Direct revive does not verify automatic clear-room revival'}
        if kind == 'destroy_actor':
            target = self.actor(authority, action)
            path = target.get_path_name()
            self.step['dispatched'] = True
            self.write()
            target.destroy_actor()
            return {'target': path, 'fault': 'external actor destruction, never a forged death notification'}
        if kind == 'interact':
            server = self.player(contexts, action.get('player_index', 0))
            scope = action.get('world', 'owner')
            candidates = [(context, pc) for context in contexts for pc in context['controllers']
                          if pc.is_local_controller() and self.player_id(pc) == self.player_id(server)
                          and (scope == 'owner' or context is self.select_world(contexts, scope))]
            self.require(len(candidates) == 1, 'InteractionMustUseUniqueOwningLocalController')
            context, controller = candidates[0]
            room = str(action.get('room_id') or controller.get_editor_property('run_view').get_editor_property('current_room'))
            self.require(room and room != 'None', 'InteractionRoomIdMissing')
            name = str(action.get('interaction', '')).upper()
            self.require(name in ('CLAIM_TREASURE', 'PURCHASE', 'REST', 'EXIT'), 'InvalidInteraction')
            interaction = getattr(u.DungeonInteraction, name)
            offer = int(action.get('offer_index', -1))
            self.require(-1 <= offer <= 100, 'InvalidOfferIndex')
            repeat = int(action.get('repeat', 1))
            self.require(1 <= repeat <= 8, 'InteractionRepeatMustBe1To8')
            override = action.get('run_id_override')
            if override is not None:
                digits = uuid.UUID(str(override)).hex
                override = u.Guid(*(int(digits[offset:offset + 8], 16) for offset in (0, 8, 16, 24)))
            self.step['dispatched'] = True
            self.write()
            for _ in range(repeat):
                request_run = override if override is not None else controller.get_editor_property('run_view').get_editor_property('run_id')
                # Python's FEditorScriptExecutionGuard makes Actor RPCs local. The PIE-only
                # bridge queues the normal RPC on a gameplay tick; business checks below
                # still wait for the actual server mutation and client replication.
                queued = u.DungeonRunAutomationLibrary.queue_interaction(controller, request_run, u.Name(room), interaction, offer)
                self.require(queued, 'RoomInteractionNotQueued')
            return {'player_id': self.player_id(controller), 'world': context['snapshot']['world'],
                    'origin_authority': context['snapshot']['authority'], 'room_id': room,
                    'interaction': name, 'offer_index': offer, 'repeat': repeat,
                    'run_id_override': action.get('run_id_override')}
        raise RuntimeError('UnhandledAction: ' + kind)

    def tick(self, delta_seconds):
        try:
            now = time.monotonic()
            self.require(now - self.started <= self.timeout, 'RequestTimeout')
            if now < self.next_sample:
                return
            self.next_sample = now + .05
            contexts = self.collect()
            snapshots = [context['snapshot'] for context in contexts]
            self.result['latest'] = snapshots
            if now - self.last_write >= .5:
                self.write()
            if (not contexts and self.step and self.step.get('dispatched') and
                    self.index == len(self.actions) - 1 and self.actions[self.index].get('allow_world_exit') and
                    self.step.get('detail', {}).get('interaction') == 'EXIT'):
                self.step.update(status='complete', after=[], world_exit_observed=True,
                                 finished_seconds=now - self.started)
                self.index += 1
                self.step = None
                self.finish()
                return
            self.validate_pie_maps([world.get_path_name() for world in u.EditorLevelLibrary.get_pie_worlds(False)],
                                   self.expected_map)
            if len(contexts) != self.expected_worlds:
                return
            authority = self.select_world(contexts)
            if len(authority['controllers']) != self.expected_players:
                return
            action = self.actions[self.index]
            generation = authority['snapshot']['generation']
            if self.bound_generation is not None:
                self.require(generation.get('generation_id') == self.bound_generation and
                             authority['snapshot']['run'].get('run_id') == self.bound_run,
                             'RunChangedDuringRequest')
            if action['action'] in self.MUTATIONS:
                if not all(context['snapshot']['generation'].get('phase', '').endswith('Ready')
                           for context in contexts):
                    return
                identity = generation.get('generation_id')
                run_id = authority['snapshot']['run'].get('run_id')
                self.require(identity and run_id, 'NativeReportsMissingGenerationOrRunId')
                # Geometry Ready can precede the director's first gameplay tick and
                # client replication. Do not bind the all-zero loading run identity.
                if any(context['snapshot']['run'].get('phase') == 'Loading' or
                       uuid.UUID(context['snapshot']['run'].get('run_id')).int == 0
                       for context in contexts):
                    return
                if self.bound_generation is None:
                    self.bound_generation, self.bound_run = identity, run_id
                self.require(identity == self.bound_generation and run_id == self.bound_run, 'RunChangedDuringRequest')
                if self.request.get('expected_run_id') is not None:
                    self.require(run_id == self.request['expected_run_id'], 'RequestRunIdMismatch')
            if self.step is None:
                self.step = {'index': self.index, 'action': action, 'status': 'started', 'dispatched': False,
                             'started_seconds': now - self.started, 'started_at': now,
                             'before': snapshots, 'stable_since': None}
                self.result['receipts'].append(self.step)
                self.result.update(phase='executing', action_index=self.index)
                self.write()
                self.step['detail'] = self.dispatch(action, contexts)
                self.step['dispatch_finished_at'] = time.monotonic()
                self.write()
                return
            self.require(now - self.step['started_at'] <= self.number(action.get('timeout', 30), .1, 120, 'step timeout'),
                         'ActionTimeout: ' + action['action'])
            if action['action'] == 'move_player':
                detail = self.step['detail']
                point_index = detail['next_waypoint']
                if point_index < len(detail['waypoints']):
                    interval = self.number(action.get('waypoint_interval', .1), .05, 5, 'waypoint_interval')
                    if now - detail.get('last_move_at', 0) < interval:
                        return
                    pawn = self.player(contexts, action.get('player_index', 0)).get_controlled_pawn()
                    point = self.vector(detail['waypoints'][point_index])
                    before = self.xyz(pawn.get_actor_location())
                    movement = pawn.get_component_by_class(u.CharacterMovementComponent)
                    if movement:
                        movement.stop_movement_immediately()
                    self.step['dispatched'] = True
                    self.write()
                    pawn.set_actor_location(point, bool(action.get('sweep', True)), False)
                    detail['moves'].append({'requested': self.xyz(point), 'before': before,
                                            'after_immediate': self.xyz(pawn.get_actor_location())})
                    detail['next_waypoint'] += 1
                    detail['last_move_at'] = now
                    self.step['dispatch_finished_at'] = now
                    self.write()
                    return
            settle = self.number(action.get('settle_seconds', .3), 0, 30, 'settle_seconds')
            if now - self.step['dispatch_finished_at'] < settle:
                return
            checks = action.get('until', []) + action.get('checks', [])
            evaluated = self.evaluate_checks(snapshots, checks)
            self.step['check_results'] = evaluated
            if not all(item['passed'] for item in evaluated):
                self.step['stable_since'] = None
                return
            detail = self.step['detail']
            kind = action['action']
            if kind == 'activate_ability' and action.get('require_mana_spent', True):
                after = self.attributes(self.player(contexts, action.get('player_index', 0)).get_controlled_pawn())
                if after['mana'] >= detail['before']['mana']:
                    return  # Await the real server Commit/replication, bounded by step timeout.
            if kind == 'move_player' and action.get('require_arrival', True):
                pawn = self.player(contexts, action.get('player_index', 0)).get_controlled_pawn()
                tolerance = self.number(action.get('arrival_tolerance_cm', 45), 1, 200, 'arrival_tolerance_cm')
                self.require((pawn.get_actor_location() - self.vector(detail['waypoints'][-1])).length() <= tolerance,
                             'MovementDidNotReachFinalWaypoint')
            if kind == 'kill_mass' and detail['require_killed']:
                context = self.select_world(contexts, detail['world'])
                remaining = {view.id for view in context['mass'].get_snapshots()}
                self.require(all(target['id'] not in remaining for target in detail['targets']), 'MassTargetsNotKilled')
            if kind in ('down_player', 'revive_player'):
                pawn = self.player(contexts, action.get('player_index', 0)).get_controlled_pawn()
                expected_downed = kind == 'down_player' and not action.get('expect_rejected', False)
                self.require(pawn.is_dungeon_downed() == expected_downed, 'PlayerDownedStateUnexpected')
            if self.step['stable_since'] is None:
                self.step['stable_since'] = now
            stable = self.number(action.get('stable_seconds', .15), 0, 10, 'stable_seconds')
            if now - self.step['stable_since'] < stable:
                return
            self.step.update(status='complete', after=snapshots, finished_seconds=now - self.started)
            self.result['checks'].extend(evaluated)
            if kind == 'capture':
                self.result['snapshots'].append({'action_index': self.index, 'worlds': snapshots})
            self.index += 1
            self.step = None
            if self.index == len(self.actions):
                self.finish()
            else:
                self.write()
        except Exception:
            self.finish(traceback.format_exc())


def main():
    directory = Path(u.Paths.project_dir()).resolve() / 'Saved/RoguelikeGeneration'
    directory.mkdir(parents=True, exist_ok=True)
    request = json.loads((directory / 'run-check-request.json').read_text(encoding='utf-8-sig'))
    fingerprint = RunVerification.request_hash(request)
    previous = getattr(builtins, '_roguelike_run_verification', None)
    if previous and not previous.finished:
        if previous.request_id == request.get('request_id') and previous.fingerprint == fingerprint:
            u.log('ROGUELIKE_RUN_CHECK already running; no action resubmitted')
        else:
            u.log_error('ROGUELIKE_RUN_CHECK another request is active; wait for its bounded receipt')
        return
    response = directory / 'run-check-response.json'
    request_id = request.get('request_id', '')
    RunVerification.require(isinstance(request_id, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', request_id),
                            'InvalidRequestId')
    history = directory / 'run-checks' / (request_id + '.json')
    for receipt in (history, response):
        if not receipt.exists():
            continue
        saved = json.loads(receipt.read_text(encoding='utf-8-sig'))
        if saved.get('request_id') == request.get('request_id'):
            RunVerification.require(saved.get('request_sha256') == fingerprint,
                                    'RequestIdReusedWithDifferentPayload')
            if receipt == history:
                temporary = response.with_suffix('.json.tmp')
                temporary.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding='utf-8')
                temporary.replace(response)
            u.log('ROGUELIKE_RUN_CHECK request already has a receipt; never replaying possible mutations')
            return
    try:
        verifier = RunVerification(request, directory)
    except Exception:
        rejected = {'schema': 'roguelike-run-check-v1', 'request_id': request.get('request_id'),
                    'request_sha256': fingerprint, 'passed': False, 'phase': 'rejected',
                    'error': traceback.format_exc(), 'mutation_may_have_occurred': False}
        temporary = response.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(rejected, indent=2), encoding='utf-8')
        temporary.replace(response)
        raise
    builtins._roguelike_run_verification = verifier
    verifier.start()


if __name__ == '__main__':
    main()
