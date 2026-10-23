"""Read current PIE controllers, replication roles and the real input bindings."""
import json
import unreal
from pathlib import Path
_orbit_net_root = Path(unreal.Paths.project_dir()).resolve() / "Saved/GAAuthoring/OrbitingFireBolt"
_orbit_net_run = _orbit_net_root / json.loads((_orbit_net_root / "latest-network-run.json").read_text())["run_id"]

_orbit_network_controllers = []
_orbit_network_rows = []
for _orbit_pc in unreal.ObjectIterator(unreal.MyPlayerController):
    if 'UEDPIE_' not in _orbit_pc.get_path_name():
        continue
    _orbit_network_controllers.append(_orbit_pc)
    _orbit_pawn = _orbit_pc.call_method('K2_GetPawn')
    _orbit_ps = _orbit_pc.get_editor_property('player_state')
    _orbit_asc = _orbit_ps.get_component_by_class(unreal.MyAbilitySystemComponent) if _orbit_ps else None
    _orbit_network_rows.append({'controller': _orbit_pc.get_path_name(), 'local': _orbit_pc.is_local_controller(),
        'role': str(_orbit_pc.get_local_role()), 'pawn': _orbit_pawn.get_path_name() if _orbit_pawn else None,
        'asc': _orbit_asc.get_path_name() if _orbit_asc else None,
        'abilities': len(_orbit_asc.get_all_abilities()) if _orbit_asc else 0})
_orbit_subsystems = [s.get_path_name() for s in unreal.ObjectIterator(unreal.EnhancedInputLocalPlayerSubsystem)]
_orbit_snapshot = {'controllers': _orbit_network_rows, 'input_subsystems': _orbit_subsystems}
(_orbit_net_run / 'network-state.json').write_text(json.dumps(_orbit_snapshot, indent=2), encoding='utf8')
unreal.log('ORBIT_NETWORK_STATE ' + json.dumps(_orbit_snapshot))
