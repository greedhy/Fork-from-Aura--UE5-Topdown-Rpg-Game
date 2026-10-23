"""Run once inside combat-map PIE. Tests real BP_Player/catalog/visible fireballs.

The check activates the already-granted catalog ability via the ASC, never adds it
to startup or writes a save. It is not a physical menu-click or multiplayer test.
"""
import json
import time
import uuid
from pathlib import Path
import unreal

_orbit_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
assert _orbit_world, 'Start combat-map PIE first'
_orbit_player = unreal.GameplayStatics.get_player_character(_orbit_world, 0)
assert _orbit_player, 'PIE has no player character'
_orbit_pc = unreal.GameplayStatics.get_player_controller(_orbit_world, 0)
_orbit_asc = _orbit_pc.get_editor_property('player_state').get_component_by_class(unreal.MyAbilitySystemComponent)
_orbit_class = unreal.load_class(None,
    '/Game/BluePrints/AbilitySystem/Player/Ability/PassiveSpell/OrbitingFireBolt/GA_OrbitingFireBolt.GA_OrbitingFireBolt_C')
assert _orbit_class, 'Saved GA class did not load'
assert _orbit_asc.try_activate_ability_by_class(_orbit_class), 'Catalog did not grant an activatable passive'
_orbit_started = time.monotonic()
_orbit_started_game = unreal.GameplayStatics.get_time_seconds(_orbit_world)
_orbit_samples = []
_orbit_run = str(uuid.uuid4())
_orbit_out = Path(unreal.Paths.project_dir()).resolve() / 'Saved/GAAuthoring/OrbitingFireBolt' / _orbit_run
_orbit_out.mkdir(parents=True)


def _orbit_smoke_tick(delta_seconds):
    elapsed = unreal.GameplayStatics.get_time_seconds(_orbit_world) - _orbit_started_game
    if elapsed < 9.5 and time.monotonic() - _orbit_started < 60.0:
        return
    unreal.unregister_slate_post_tick_callback(_orbit_callback)
    try:
        balls = unreal.GameplayStatics.get_all_actors_of_class(_orbit_world, unreal.MyOrbitingFireBolt)
        positions = [b.get_actor_location() for b in balls]
        player_position = _orbit_player.get_actor_location()
        checks = {
            'three_live_balls': len(balls) == 3,
            'above_players_head': len(balls) == 3 and all(abs(p.z - player_position.z - 150) < 10 for p in positions),
            'firebolt_niagara_present': len(balls) == 3 and all(b.get_components_by_class(unreal.NiagaraComponent) for b in balls),
        }
        report = {'run_id': _orbit_run, 'passed': all(checks.values()), 'checks': checks,
                  'player': _orbit_player.get_path_name(), 'elapsed': elapsed,
                  'positions': [str(p) for p in positions],
                  'scope': 'Single-player PIE: existing catalog grant, ASC activation, real BP_Player and projectile visuals'}
    except Exception as error:
        report = {'run_id': _orbit_run, 'passed': False, 'error': repr(error)}
    (_orbit_out / 'pie-validation.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    (_orbit_out.parent / 'latest-pie.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    unreal.log('ORBITING_FIRE_BOLT_PIE ' + json.dumps(report))


_orbit_callback = unreal.register_slate_post_tick_callback(_orbit_smoke_tick)
