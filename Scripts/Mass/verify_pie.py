"""Run in two-player listen-server PIE on L_MassDungeonTest. Only PIE fixtures are changed."""
import unreal as u, json, time, uuid
from pathlib import Path

_mm = {'run': uuid.uuid4().hex, 'phase': 'setup', 'started': time.monotonic(), 'checks': {}}
_mm_out = Path(u.Paths.project_dir()).resolve()/'Saved/MassMonsters/pie.json'
def _mm_check(key, value):
    _mm['checks'][key] = bool(value)
    assert value, key
def _mm_write(): _mm_out.write_text(json.dumps(_mm, indent=2), encoding='utf8')
def _mm_phase(phase):
    _mm.update(phase=phase, at=time.monotonic()); _mm_write()
def _mm_finish(error=None):
    u.unregister_slate_post_tick_callback(_mm_handle)
    _mm.update(passed=error is None and all(_mm['checks'].values()), error=error); _mm_write()
def _mm_enemies(w): return u.GameplayStatics.get_all_actors_of_class(w, u.EnemyCharacter)
def _mm_move(pawn, pos):
    move = pawn.get_component_by_class(u.CharacterMovementComponent)
    move.set_movement_mode(u.MovementMode.MOVE_FLYING); move.stop_movement_immediately()
    pawn.set_actor_location(pos, False, True)
def _mm_damage(pc, enemy, amount):
    params = u.DamageEffectParams()
    params.set_editor_property('world_context_object', enemy)
    params.set_editor_property('source_ability_system_component', pc.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent))
    params.set_editor_property('target_ability_system_component', enemy.get_component_by_class(u.MyAbilitySystemComponent))
    params.set_editor_property('damage_gameplay_effect_class', u.load_class(None, '/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage.GE_Damage_C'))
    params.set_editor_property('base_damage', amount)
    tag = u.GameplayTag(); tag.import_text('(TagName="Damage.Fire")')
    params.set_editor_property('damage_type', tag)
    u.MyAbilitySystemLibrary.apply_damage_effect(params)
def _mm_tick(dt):
    try:
        if time.monotonic()-_mm['started'] > 45: raise AssertionError('Timeout '+_mm['phase'])
        managers = [m for m in u.ObjectIterator(u.MonsterManagementSubsystem) if m.get_world() and 'UEDPIE_' in m.get_world().get_path_name()]
        if len(managers) != 2: return
        manager = next(m for m in managers if m.get_stats().enabled)
        client_manager = next(m for m in managers if not m.get_stats().enabled)
        world = manager.get_world(); client_world = client_manager.get_world()
        pcs = [p for p in u.GameplayStatics.get_all_actors_of_class(world, u.MyPlayerController) if p.get_controlled_pawn()]
        if len(pcs) != 2: return
        host = next(p for p in pcs if p.is_local_controller())
        remote = next(p for p in pcs if not p.is_local_controller())
        phase = _mm['phase']; age = time.monotonic()-_mm.get('at', _mm['started'])
        enemy = next((e for e in _mm_enemies(world) if 'MassQA' in [str(t) for t in e.tags]), None)
        if phase == 'setup':
            _mm_check('server_processor_automatic', manager.get_stats().update_count > 0)
            _mm_check('client_no_entities_or_processing', client_manager.get_stats().registered == 0 and client_manager.get_stats().update_count == 0)
            for e in _mm_enemies(world): e.destroy_actor()
            origin = host.get_controlled_pawn().get_actor_location()+u.Vector(0,0,200)
            _mm['origin'] = [origin.x, origin.y, origin.z]
            _mm_move(host.get_controlled_pawn(), origin)
            _mm_move(remote.get_controlled_pawn(), origin+u.Vector(0,600,0))
            cls = u.load_class(None, '/Game/BluePrints/Characters/Goblin/BP_Goblin.BP_Goblin_C')
            transform = u.Transform(location=origin+u.Vector(6000,0,0))
            lib = u.get_default_object(u.GameplayStatics)
            enemy = lib.call_method('BeginDeferredActorSpawnFromClass', (world,cls,transform,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            enemy.set_editor_property('monster_room_id', 'MassQARoom')
            lib.call_method('FinishSpawningActor', (enemy,transform,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            enemy.tags = list(enemy.tags)+['MassQA']
            enemy.spawn_default_controller(); _mm_move(enemy, transform.translation)
            _mm_check('spawn_registered_once', manager.get_stats().registered == 1)
            _mm_phase('far'); return
        assert enemy, 'QA enemy missing'
        brain = enemy.get_controller().get_component_by_class(u.BrainComponent)
        if age < .8: return
        if phase == 'far':
            _mm_check('far_enemy_sleeps', not manager.is_monster_active(enemy))
            _mm_check('behavior_tree_paused', brain.is_paused())
            _mm_check('one_owned_pause', manager.get_stats().paused_brains == 1)
            _mm_check('room_query', len(manager.find_monsters_in_radius(enemy.get_actor_location(), 100, 'MassQARoom')) == 1)
            _mm_check('different_room_excluded', not manager.find_monsters_in_radius(enemy.get_actor_location(), 100, 'OtherRoom'))
            _mm_move(remote.get_controlled_pawn(), enemy.get_actor_location()+u.Vector(2000,0,0))
            _mm_phase('remote_wake')
        elif phase == 'remote_wake':
            _mm_check('remote_player_wakes', manager.is_monster_active(enemy))
            _mm_check('behavior_tree_resumes', brain.is_running() and not brain.is_paused())
            _mm_check('enemy_replicated_to_client', len(_mm_enemies(client_world)) == 1)
            old = enemy.get_actor_location(); _mm['old'] = [old.x,old.y,old.z]
            _mm_move(enemy, old+u.Vector(-12000,-4000,0))
            _mm_phase('moved')
        elif phase == 'moved':
            _mm_check('old_grid_cell_empty', not manager.find_monsters_in_radius(u.Vector(*_mm['old']),100,'MassQARoom'))
            _mm_check('new_grid_cell_found', len(manager.find_monsters_in_radius(enemy.get_actor_location(),100,'MassQARoom'))==1)
            _mm_check('distant_again_sleeps', not manager.is_monster_active(enemy))
            _mm_damage(host, enemy, 1.0)
            _mm_check('real_health_damage_immediate_wake', manager.is_monster_active(enemy))
            _mm_phase('damage')
        elif phase == 'damage':
            if age < 4.0: _mm_check('damage_grace_keeps_active', manager.is_monster_active(enemy))
            if age < 6.0: return
            _mm_phase('after_grace')
        elif phase == 'after_grace':
            _mm_check('sleeps_after_damage_grace', not manager.is_monster_active(enemy))
            _mm_move(remote.get_controlled_pawn(), enemy.get_actor_location()+u.Vector(2000,0,0))
            _mm_phase('external_pause')
        elif phase == 'external_pause':
            _mm_check('resumes_after_damage_sleep', brain.is_running())
            # External pause ownership is tested natively: PauseLogic is not reflected to Python.
            _mm_damage(host, enemy, 1000000.0)
            _mm_check('death_unregisters_immediately', manager.get_stats().registered == 0)
            _mm_check('death_removed_from_queries', not manager.find_monsters_in_radius(enemy.get_actor_location(),100,'MassQARoom'))
            _mm_check('client_stays_authority_free', client_manager.get_stats().registered == 0)
            _mm_finish()
    except Exception as exc:
        _mm_finish(str(exc)); u.log_error('MASS_QA '+str(exc))
_mm_handle = u.register_slate_post_tick_callback(_mm_tick)
_mm_write()
