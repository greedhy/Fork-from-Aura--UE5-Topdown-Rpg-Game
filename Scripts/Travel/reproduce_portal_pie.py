"""Regression probe: a client overlap must never independently open a map."""
import json
import time
import uuid
from pathlib import Path
import unreal

_travel_probe_root=Path(unreal.Paths.project_dir()).resolve()/'Saved/TravelValidation'
_travel_probe_root.mkdir(parents=True,exist_ok=True)
_travel_probe_id=uuid.uuid4().hex
def _travel_probe_snapshot():
    result=[]
    for pc in unreal.ObjectIterator(unreal.MyPlayerController):
        if 'UEDPIE_' not in pc.get_path_name():
            continue
        pawn=pc.get_controlled_pawn()
        result.append({'pc':pc.get_path_name(),'world':pc.get_world().get_path_name(),
            'local':pc.is_local_controller(),'role':str(pc.get_local_role()),
            'pawn':pawn.get_path_name() if pawn else None,
            'location':str(pawn.get_actor_location()) if pawn else None})
    return result
_travel_probe_before=_travel_probe_snapshot()
_travel_probe_server=next(pc for pc in unreal.ObjectIterator(unreal.MyPlayerController)
    if 'UEDPIE_' in pc.get_path_name() and pc.is_local_controller() and pc.get_local_role()==unreal.NetRole.ROLE_AUTONOMOUS_PROXY)
_travel_probe_world=_travel_probe_server.get_world()
_travel_probe_portal=unreal.GameplayStatics.get_all_actors_of_class(_travel_probe_world,unreal.MapEntrance)[0]
_travel_probe_sphere=_travel_probe_portal.get_component_by_class(unreal.SphereComponent)
_travel_probe_start=time.monotonic()
_travel_probe_portal.call_method('OnSphereOverlap',(_travel_probe_sphere,_travel_probe_server.get_controlled_pawn(),None,0,False,unreal.HitResult()))
def _travel_probe_tick(dt):
    if time.monotonic()-_travel_probe_start<4:
        return
    unreal.unregister_slate_post_tick_callback(_travel_probe_handle)
    after=_travel_probe_snapshot()
    result={'run_id':_travel_probe_id,'before':_travel_probe_before,'after':after,
        'one_player_does_not_travel':bool(after) and all('Dungeon.' in x['world'] for x in after),
        'scope':'Two-player listen PIE; direct remote-client overlap callback; authority cannot save from this callback.'}
    (_travel_probe_root/'baseline.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    unreal.log('PORTAL_BASELINE '+json.dumps(result))
_travel_probe_handle=unreal.register_slate_post_tick_callback(_travel_probe_tick)


