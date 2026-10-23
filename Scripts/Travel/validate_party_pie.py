"""Two-player listen PIE regression; uses real portal ticks and Enhanced Input.

Only changes temporary PIE actors. Callback state deliberately keeps no UObject
references: old-world references prevent seamless-travel garbage collection.
"""
import json
import math
import time
from pathlib import Path
import unreal

_party_qa={'phase':'setup','wall':time.monotonic(),'checks':{},'arrivals':[],'leg':0}
_party_maps=['Dungeon','Dungeon2','L_DungeonLabyrinth','Dungeon']
_party_report=Path(unreal.Paths.project_dir()).resolve()/'Saved/TravelValidation/party-pie.json'

def _party_vec(v): return [v.x,v.y,v.z]

def _party_pcs(map_name):
    return [pc for pc in unreal.ObjectIterator(unreal.MyPlayerController)
        if 'UEDPIE_' in pc.get_path_name() and (pc.get_world().get_name()==map_name or pc.get_world().get_name().endswith('_'+map_name))
        and pc.get_controlled_pawn() and pc.get_local_role()!=unreal.NetRole.ROLE_NONE]

def _party_slot(pc): return pc.get_editor_property('player_state').get_editor_property('travel_player_slot')

def _party_check(name,ok):
    _party_qa['checks'][name]=bool(ok)
    assert ok,name

def _party_finish(error=None):
    unreal.unregister_slate_post_tick_callback(_party_callback)
    _party_qa['error']=error
    _party_qa['passed']=not error and bool(_party_qa['checks']) and all(_party_qa['checks'].values())
    _party_report.write_text(json.dumps(_party_qa,indent=2),encoding='utf8')
    unreal.log('PARTY_TRAVEL_RESULT '+json.dumps(_party_qa))

def _party_phase(name,now):
    _party_qa.update(phase=name,at=now)
    _party_report.write_text(json.dumps(_party_qa,indent=2),encoding='utf8')

def _party_place(pc,portal,inside):
    pawn=pc.get_controlled_pawn()
    move=pawn.get_component_by_class(unreal.CharacterMovementComponent)
    move.set_movement_mode(unreal.MovementMode.MOVE_FLYING)
    move.stop_movement_immediately()
    center=portal.get_component_by_class(unreal.SphereComponent).get_world_location()
    pawn.set_actor_location(center+unreal.Vector(0,80*_party_slot(pc) if inside else -700,20),False,True)

def _party_input(pc,pressed):
    lib=unreal.get_default_object(unreal.load_class(None,'/Script/Engine.SubsystemBlueprintLibrary'))
    sub=lib.call_method('GetLocalPlayerSubSystemFromPlayerController',(pc,unreal.EnhancedInputLocalPlayerSubsystem.static_class()))
    assert sub,'Missing input subsystem'
    sub.inject_input_vector_for_action(pc.get_editor_property('move_action'),unreal.Vector(pressed,0,0),[],[])

def _party_tick(dt):
    try:
        q=_party_qa
        if time.monotonic()-q['wall']>150:
            raise AssertionError('Timeout in '+q['phase'])
        leg=q['leg']
        if q['phase']=='wait_depart' and len(_party_pcs(_party_maps[leg+1]))>=3:
            q['phase']='travel'
        name=_party_maps[leg]
        if q['phase']=='travel': name=_party_maps[leg+1]
        pcs=_party_pcs(name)
        server=sorted([p for p in pcs if p.get_local_role()==unreal.NetRole.ROLE_AUTHORITY],key=_party_slot)
        remote=next((p for p in pcs if p.get_local_role()==unreal.NetRole.ROLE_AUTONOMOUS_PROXY and p.is_local_controller()),None)
        if len(server)!=2 or not remote: return
        world=server[0].get_world()
        now=unreal.GameplayStatics.get_time_seconds(world)
        portal=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.MapEntrance)[0]
        phase=q['phase']
        if phase in ['setup','travel']:
            # Isolate transport/input from combat and death reloads in this PIE run.
            for enemy in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.EnemyCharacter):
                enemy.destroy_actor()
        if phase=='setup':
            _party_check('initial_unique_slots',[_party_slot(p) for p in server]==[0,1])
            q['initial']=[{'slot':_party_slot(p),'pos':_party_vec(p.get_controlled_pawn().get_actor_location())} for p in server]
            for p in server:
                state=p.get_editor_property('player_state')
                p.get_controlled_pawn().call_method('AddToXP',(111+222*_party_slot(p)-state.get_editor_property('xp'),))
                p.get_controlled_pawn().call_method('AddToSpellPoints',(7+_party_slot(p)-state.get_editor_property('spell_points'),))
            client_portal=unreal.GameplayStatics.get_all_actors_of_class(remote.get_world(),unreal.MapEntrance)[0]
            client_portal.call_method('OnSphereOverlap',(client_portal.get_component_by_class(unreal.SphereComponent),remote.get_controlled_pawn(),None,0,False,unreal.HitResult()))
            _party_phase('single',now)
        elif phase=='single':
            for p in server: _party_place(p,portal,_party_slot(p)==0)
            if now-q['at']>4:
                _party_check('single_player_and_client_overlap_do_not_travel',True)
                _party_check('one_ready_of_two',portal.get_editor_property('ready_players')==1 and portal.get_editor_property('required_players')==2)
                _party_phase('cancel_start',now)
        elif phase=='cancel_start':
            for p in server: _party_place(p,portal,True)
            if now-q['at']>1.5:
                _party_check('countdown_started',portal.get_editor_property('countdown_end_server_time')>now)
                _party_phase('leave',now)
        elif phase=='leave':
            for p in server: _party_place(p,portal,_party_slot(p)==0)
            if now-q['at']>1:
                _party_check('leaving_resets_countdown',portal.get_editor_property('countdown_end_server_time')<0)
                _party_phase('gather',now)
        elif phase=='gather':
            for p in server: _party_place(p,portal,True)
            if portal.get_editor_property('travel_error'):
                raise AssertionError(str(portal.get_editor_property('travel_error')))
            if now-q['at']>2.5:
                _party_check('leg_'+str(leg)+'_still_here_before_3_seconds',not portal.get_editor_property('travel_in_progress'))
                _party_phase('wait_depart',now)
        elif phase=='wait_depart':
            for p in server: _party_place(p,portal,True)
            if portal.get_editor_property('travel_error'):
                raise AssertionError(str(portal.get_editor_property('travel_error')))
            if portal.get_editor_property('travel_in_progress'):
                _party_phase('travel',now)
        elif phase=='travel':
            q['leg']+=1
            _party_phase('settle',now)
        elif phase=='settle' and now-q['at']>1:
            label='arrival_'+str(leg)
            starts=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.PlayerStart)
            entries=[]
            for p in server:
                slot=_party_slot(p)
                start=next(a for a in starts if not isinstance(a,unreal.CheckPoint) and
                    ((isinstance(a,unreal.TravelPlayerStart) and a.get_editor_property('player_slot')==slot) or
                     (not isinstance(a,unreal.TravelPlayerStart) and slot==0)))
                pos=p.get_controlled_pawn().get_actor_location()
                expected=start.get_actor_location()
                _party_check(label+'_slot_'+str(slot)+'_position',math.hypot(pos.x-expected.x,pos.y-expected.y)<10)
                state=p.get_editor_property('player_state')
                _party_check(label+'_slot_'+str(slot)+'_progress',state.get_editor_property('xp')==111+222*slot and state.get_editor_property('spell_points')==7+slot)
                entries.append({'slot':slot,'pos':_party_vec(pos),'expected':_party_vec(expected)})
            _party_check(label+'_remote_autonomous',remote.get_local_role()==unreal.NetRole.ROLE_AUTONOMOUS_PROXY)
            q['arrivals'].append({'map':name,'players':entries})
            q['move_start']={str(_party_slot(p)):_party_vec(p.get_controlled_pawn().get_actor_location()) for p in server}
            _party_phase('move',now)
        elif phase=='move':
            for pc in [remote,next(p for p in server if p.is_local_controller())]:
                unreal.get_default_object(unreal.load_class(None,'/Script/UMG.WidgetBlueprintLibrary')).call_method('SetInputMode_GameOnly',(pc,False))
                _party_input(pc,1)
            if now-q['at']>0.7:
                _party_phase('move_settle',now)
        elif phase=='move_settle':
            for pc in [remote,next(p for p in server if p.is_local_controller())]: _party_input(pc,0)
            if now-q['at']>0.5:
                for p in server:
                    slot=_party_slot(p)
                    pos=p.get_controlled_pawn().get_actor_location()
                    before=q['move_start'][str(slot)]
                    _party_check('leg_'+str(leg)+'_slot_'+str(slot)+'_input_moves_on_server',math.hypot(pos.x-before[0],pos.y-before[1])>20)
                remote_pos=remote.get_controlled_pawn().get_actor_location()
                server_pos=next(p for p in server if _party_slot(p)==_party_slot(remote)).get_controlled_pawn().get_actor_location()
                _party_check('leg_'+str(leg)+'_remote_movement_replication',(remote_pos-server_pos).length()<30)
                if leg==3: _party_finish()
                else: _party_phase('gather',now)
    except Exception as error:
        _party_finish(repr(error))

_party_callback=unreal.register_slate_post_tick_callback(_party_tick)
