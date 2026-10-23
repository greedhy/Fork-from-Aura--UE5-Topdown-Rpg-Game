"""Read input assets and create a report run before pie_start(num_players=2, net_mode=1).

The MCP pie_start tool uses transient per-session settings. No map, asset,
editor preference or game save is written by this inspection script.
"""
import json
import uuid
from pathlib import Path
import unreal

_orbit_net_root = Path(unreal.Paths.project_dir()).resolve() / 'Saved/GAAuthoring/OrbitingFireBolt'
_orbit_net_run = _orbit_net_root / str(uuid.uuid4())
_orbit_net_run.mkdir(parents=True)
_orbit_input = unreal.load_asset('/Game/BluePrints/Input/DA_MyInputConfig')
_orbit_input_rows = [{'tag': r.get_editor_property('input_tag').export_text(),
                      'action': r.get_editor_property('input_action').get_path_name()}
                     for r in _orbit_input.get_editor_property('ability_input_actions') if r.get_editor_property('input_action')]
(_orbit_net_run / 'input-map.json').write_text(json.dumps(_orbit_input_rows, indent=2), encoding='utf8')
(_orbit_net_root / 'latest-network-run.json').write_text(json.dumps({'run_id': _orbit_net_run.name, 'prepared': True}), encoding='utf8')
unreal.log('ORBIT_NETWORK_READY ' + str(_orbit_net_run))
