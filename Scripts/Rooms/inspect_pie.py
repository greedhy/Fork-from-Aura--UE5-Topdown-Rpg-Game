import json
from pathlib import Path
import unreal as u

def inspect():
    result = {'cvar': u.SystemLibrary.get_console_variable_int_value('net.AllowPIESeamlessTravel'), 'rooms': [], 'controllers': []}
    for r in u.ObjectIterator(u.RoomSubsystem):
        if r.get_world() and 'UEDPIE_' in r.get_world().get_path_name():
            result['rooms'].append({'world': r.get_world().get_path_name(), 'state': str(r.get_editor_property('state')), 'error': str(r.get_editor_property('last_error'))})
    for p in u.ObjectIterator(u.PlayerController):
        if 'UEDPIE_' in p.get_path_name():
            result['controllers'].append({'pc': p.get_path_name(), 'local': p.is_local_controller(), 'role': str(p.get_local_role()), 'pawn': p.get_controlled_pawn().get_path_name() if p.get_controlled_pawn() else None})
    (Path(u.Paths.project_dir()).resolve() / 'Saved/Rooms/PIE/inspect.json').write_text(json.dumps(result, indent=2), encoding='utf8')
inspect()
