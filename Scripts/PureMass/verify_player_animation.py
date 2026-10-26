"""PIE regression: native Character owner, animation bindings, moving/idle poses on all replicas."""
import unreal as u, json, time
from pathlib import Path

_pa={'start':time.monotonic(),'phase':'setup','checks':{},'actors':{}}
_pa_settings=u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
_pa_throttle=_pa_settings.get_editor_property('bThrottleCPUWhenNotForeground')
_pa_settings.set_editor_property('bThrottleCPUWhenNotForeground',False)

def _pa_finish(error=None):
    u.unregister_slate_post_tick_callback(_pa_handle)
    _pa_settings.set_editor_property('bThrottleCPUWhenNotForeground',_pa_throttle)
    _pa['error']=error
    _pa['passed']=error is None and all(_pa['checks'].values())
    Path(u.Paths.project_dir(),'Saved/PureMass/PlayerAnimation/animation-'+str(_pa.get('worlds',0))+'.json').write_text(json.dumps(_pa,indent=2),encoding='utf8')
    u.log('PLAYER_ANIMATION_RESULT '+str(_pa['passed'])+' '+str(error))

def _pa_check(name,value):
    _pa['checks'][name]=bool(value)
    assert value,name

def _pa_pose(mesh):
    # Component-space sockets exclude whole-character translation/rotation.
    return [str(mesh.get_socket_transform(mesh.get_bone_name(i),u.RelativeTransformSpace.RTS_COMPONENT)) for i in range(mesh.get_num_bones())]

def _pa_tick(dt):
    try:
        now=time.monotonic()
        if now-_pa['start']>30:raise AssertionError('Timed out: '+_pa['phase'])
        pcs=[p for p in u.ObjectIterator(u.PureMassPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_controlled_pawn()]
        if not pcs:return
        worlds={p.get_world().get_path_name():p.get_world() for p in pcs}
        pawns=[p for w in worlds.values() for p in u.GameplayStatics.get_all_actors_of_class(w,u.PureMassPlayerCharacter) if p.get_component_by_class(u.SkeletalMeshComponent)]
        if _pa['phase']=='setup':
            if now-_pa['start']<1:return
            _pa['worlds']=len(worlds)
            _pa_check('player_is_character_actor',all(isinstance(p,u.Character) for p in pawns))
            for pawn in pawns:
                mesh=pawn.get_component_by_class(u.SkeletalMeshComponent);anim=mesh.get_anim_instance()
                key=pawn.get_path_name()
                _pa_check(key+'_anim_owner_bound',bool(anim) and anim.get_editor_property('BP_Player_Character')==pawn)
                _pa_check(key+'_movement_bound',anim.get_editor_property('Character Movement')==pawn.get_component_by_class(u.CharacterMovementComponent))
                _pa['actors'][key]={'idle_poses':[],'moving_poses':[],'peak_actor_speed':0,'peak_anim_speed':0,'saw_run':False,'saw_idle_after_move':False}
            _pa.update(phase='idle',at=now,next=now)
            return
        age=now-_pa['at'];phase=_pa['phase']
        if phase=='move':
            for pc in pcs:
                if pc.is_local_controller():pc.get_controlled_pawn().add_movement_input(u.Vector(1,0,0),1,False)
        if now>=_pa['next']:
            for pawn in pawns:
                mesh=pawn.get_component_by_class(u.SkeletalMeshComponent);anim=mesh.get_anim_instance();row=_pa['actors'][pawn.get_path_name()]
                if phase in ['idle','move']:
                    row['idle_poses' if phase=='idle' else 'moving_poses'].append(_pa_pose(mesh))
                if phase=='move':
                    row['peak_actor_speed']=max(row['peak_actor_speed'],pawn.get_velocity().length())
                    row['peak_anim_speed']=max(row['peak_anim_speed'],float(anim.get_editor_property('Ground_speed')))
                    row['saw_run']|=bool(anim.get_editor_property('ShouldRun'))
                if phase=='stop' and age>.7:
                    row['saw_idle_after_move']|=not anim.get_editor_property('ShouldRun') and float(anim.get_editor_property('Ground_speed'))<3
            _pa['next']=now+.12
        if phase=='idle' and age>1.3:_pa.update(phase='move',at=now)
        elif phase=='move' and age>.8:_pa.update(phase='stop',at=now)
        elif phase=='stop' and age>1.8:
            for key,row in _pa['actors'].items():
                for phase_key in ['idle_poses','moving_poses']:
                    poses=row.pop(phase_key)
                    changed=len({tuple(p) for p in poses})>1
                    _pa_check(key+'_'+phase_key+'_advance',changed)
                _pa_check(key+'_run_follows_movement',row['peak_actor_speed']>30 and row['peak_anim_speed']>30 and row['saw_run'])
                _pa_check(key+'_returns_to_idle',row['saw_idle_after_move'])
            _pa_check('200_mass_monsters_preserved',all(len(s.get_snapshots())==200 for s in u.ObjectIterator(u.PureMassSubsystem) if s.get_world() in worlds.values()))
            _pa_finish()
    except Exception as exc:_pa_finish(repr(exc))

_pa_handle=u.register_slate_post_tick_callback(_pa_tick)
