"""Run after Rooms/verify_pie_travel.py has created two players with QA saves.
Read the actual rendered spell icon brushes before/after every map transition.
No UObject is retained across frames, so seamless travel can collect old worlds.
"""
import json
import time
import uuid
from pathlib import Path
import unreal as u

_sb = {'run': uuid.uuid4().hex, 'phase': 'setup', 'leg': 0, 'started': time.monotonic(), 'checks': {}, 'snapshots': []}
_sb_maps = ['Dungeon', 'Dungeon2', 'L_DungeonLabyrinth', 'Dungeon']
_sb_dir = Path(u.Paths.project_dir()).resolve() / 'Saved/GAAuthoring/Compositions/Travel'
_sb_dir.mkdir(parents=True, exist_ok=True)
_sb['saves'] = json.loads((Path(u.Paths.project_dir()).resolve()/'Saved/Rooms/PIE/latest.json').read_text())['saves']
assert all(n.startswith('RoomPIE_') for n in _sb['saves'])

def _sb_write():
    for name in [_sb['run'], 'latest']:
        (_sb_dir/(name+'.json')).write_text(json.dumps(_sb, indent=2), encoding='utf8')

def _sb_finish(error=None):
    u.unregister_slate_post_tick_callback(_sb_handle)
    _sb.update(error=error, passed=error is None)
    for name in _sb['saves']: u.GameplayStatics.delete_game_in_slot(name,0)
    _sb_write()

def _sb_phase(name):
    _sb.update(phase=name, at=time.monotonic())
    _sb_write()

def _sb_slot(pc): return pc.get_editor_property('player_state').get_editor_property('travel_player_slot')

def _sb_pcs(name):
    return [p for p in u.ObjectIterator(u.MyPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_world().get_name().endswith(name) and p.get_controlled_pawn() and p.get_local_role()!=u.NetRole.ROLE_NONE]

def _sb_snapshot(pcs, name):
    rows = []
    for pc in pcs:
        asc = pc.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent)
        row = {'slot': _sb_slot(pc), 'local': pc.is_local_controller(), 'role': str(pc.get_local_role()), 'abilities': len(asc.get_all_abilities())}
        row['ability_classes']=sorted(u.AbilitySystemLibrary.get_gameplay_ability_from_spec_handle(asc,h)[0].get_class().get_path_name() for h in asc.get_all_abilities())
        if pc.is_local_controller():
            overlay = next((w for w in u.ObjectIterator(u.MyUserWidget) if w.get_world()==pc.get_world() and w.get_class().get_name()=='WBP_Overlay_C' and w.is_in_viewport()), None)
            assert overlay and overlay.is_in_viewport(), 'Missing overlay'
            row['icons'] = {}
            for i in u.ObjectIterator(u.Image):
                if i.get_name() == 'Image_SpellIcon' and i.get_path_name().startswith(overlay.get_path_name()+'.'):
                    globe = i.get_outer().get_outer()
                    resource = i.get_editor_property('brush').get_editor_property('resource_object')
                    row['icons'][globe.get_name()] = resource.get_path_name() if resource else None
        rows.append(row)
    return {'map': name, 'players': sorted(rows, key=lambda r: (r['slot'],r['local']))}

def _sb_tick(dt):
    try:
        if time.monotonic()-_sb['started'] > 100: raise AssertionError('Timeout: '+_sb['phase'])
        leg = _sb['leg']
        name = _sb_maps[leg+1] if _sb['phase'] in ['travel','settle'] else _sb_maps[leg]
        pcs = _sb_pcs(name)
        server = sorted([p for p in pcs if p.get_local_role()==u.NetRole.ROLE_AUTHORITY], key=_sb_slot)
        if len(server)!=2 or len(pcs)!=3: return
        if _sb['phase'] in ['setup','travel']:
            for e in u.GameplayStatics.get_all_actors_of_class(server[0].get_world(),u.EnemyCharacter): e.destroy_actor()
        if _sb['phase']=='setup':
            snap=_sb_snapshot(pcs,name)
            _sb['snapshots'].append(snap)
            assert all(sum(bool(v) for v in r['icons'].values())>=2 for r in snap['players'] if r['local']), 'Initial icons missing'
            _sb_phase('gather')
        elif _sb['phase']=='gather':
            portal=u.GameplayStatics.get_all_actors_of_class(server[0].get_world(),u.MapEntrance)[0]
            center=portal.get_component_by_class(u.SphereComponent).get_world_location()
            for p in server:
                pawn=p.get_controlled_pawn()
                move=pawn.get_component_by_class(u.CharacterMovementComponent)
                move.set_movement_mode(u.MovementMode.MOVE_FLYING)
                move.stop_movement_immediately()
                pawn.set_actor_location(center+u.Vector(0,80*_sb_slot(p),20),False,True)
            if portal.get_editor_property('travel_error'): raise AssertionError(str(portal.get_editor_property('travel_error')))
            if portal.get_editor_property('travel_in_progress'): _sb_phase('travel')
        elif _sb['phase']=='travel': _sb_phase('settle')
        elif _sb['phase']=='settle' and time.monotonic()-_sb['at']>2:
            snap=_sb_snapshot(pcs,name)
            _sb['snapshots'].append(snap)
            initial=_sb['snapshots'][0]['players']
            for row in snap['players']:
                before=next(r for r in initial if r['slot']==row['slot'] and r['local']==row['local'])
                key=name+'_'+str(row['slot'])+'_'+str(row['local'])
                _sb['checks'][key+'_ability_count']=row['abilities']==before['abilities']
                _sb['checks'][key+'_ability_classes']=row['ability_classes']==before['ability_classes']
                if row['local']: _sb['checks'][key+'_icons']=row['icons']==before['icons']
            _sb_write()
            assert all(_sb['checks'].values()), 'Abilities or displayed icons changed across travel'
            _sb['leg']+=1
            if _sb['leg']==3: _sb_finish()
            else: _sb_phase('gather')
    except Exception as error: _sb_finish(repr(error))

_sb_handle=u.register_slate_post_tick_callback(_sb_tick)
