"""Record real AnimInstance montage playback in the isolated simulation world."""
import json
import time
import uuid
from pathlib import Path
import unreal as u

world=u.EditorLevelLibrary.get_game_world()
assert world and '/Temp/' in world.get_path_name(), 'Probe requires its isolated unsaved simulation world'
actors=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Character) if a.actor_has_tag('SGAnimationProbe')]
assert len(actors)==2
R='/Game/BluePrints/Characters/StoneGolem/Animations/'
assert not (globals().get('probe_handle') and globals().get('probe',{}).get('status')=='running'), 'A probe is already running'
probe_handle=None
original_time_dilation=u.GameplayStatics.get_global_time_dilation(world)
probe={'run_id':uuid.uuid4().hex,'passed':False,'samples':{},'started':{},'status':'running'}
hammer=u.load_asset('/Game/StoneGolem/Mesh/SM_StoneGolem_Hammer')
hammer_vertices=[]
for section in range(hammer.get_num_sections(0)):
    hammer_vertices.extend(u.ProceduralMeshLibrary.get_section_from_static_mesh(hammer,0,section)[0])
assert hammer_vertices
probe['slam_montage']=R+'AM_SG_Slam_Contact'
path=Path(u.Paths.project_dir())/'Saved/GAAuthoring/StoneGolemBuild/runtime-animation-probe.json'
path.write_text(json.dumps(probe),encoding='utf-8')
entries=[]
for actor in actors:
    kind='Slam' if actor.actor_has_tag('Slam') else 'ShieldBash'
    movement=actor.get_component_by_class(u.CharacterMovementComponent)
    movement.stop_movement_immediately()
    movement.set_movement_mode(u.MovementMode.MOVE_NONE)
    movement.set_editor_property('gravity_scale',0.)
    actor.set_actor_location(u.Vector(0,0 if kind=='Slam' else 350,89),False,True)
    mesh=actor.get_component_by_class(u.SkeletalMeshComponent)
    instance=mesh.get_anim_instance()
    assert instance and 'ABP_SG_Elite' in instance.get_class().get_name()
    montage=u.load_asset(R+'AM_SG_'+kind+('_Contact' if kind=='Slam' else ''))
    probe['started'][kind]=instance.montage_play(montage,1.)
    assert probe['started'][kind]>0
    entries.append((kind,actor,mesh,instance,montage,actor.get_actor_location()))
    probe['samples'][kind]=[]
start=u.GameplayStatics.get_time_seconds(world)
wall_start=time.monotonic()

def record(delta):
    try:
        elapsed=u.GameplayStatics.get_time_seconds(world)-start
        for kind,actor,mesh,instance,montage,origin in entries:
            pos=instance.montage_get_position(montage)
            socket=mesh.get_socket_location('weapon_rSocket' if kind=='Slam' else 'weapon_lSocket')
            root=mesh.get_socket_location('root')
            location=actor.get_actor_location()
            sequence=u.load_asset(R+'AS_SG_'+kind+('_Contact' if kind=='Slam' else ''))
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(sequence,pos,u.AnimPoseEvaluationOptions(evaluation_type=u.AnimDataEvalType.COMPRESSED,should_retarget=False))
            expected=u.AnimPoseExtensions.get_socket_pose(pose,'weapon_rSocket' if kind=='Slam' else 'weapon_lSocket',u.AnimPoseSpaces.WORLD)
            expected_world=mesh.get_world_transform().transform_location(expected.translation)
            probe['samples'][kind].append({'elapsed':elapsed,'position':pos,
                'active':instance.montage_is_active(montage),'playing':instance.montage_is_playing(montage),
                'weapon':[socket.x,socket.y,socket.z],'root':[root.x,root.y,root.z],
                'actor_drift':(location-origin).length(),'pose_error_cm':(socket-expected_world).length()})
            if kind=='Slam' and instance.montage_is_active(montage) and abs(pos-.7)<.05:
                actual_transform=mesh.get_socket_transform('weapon_rSocket',u.RelativeTransformSpace.RTS_WORLD)
                probe['samples'][kind][-1]['actual_hammer_min_z']=min(actual_transform.transform_location(v).z for v in hammer_vertices)
        if elapsed>2.2 or time.monotonic()-wall_start>60:
            probe['checks']={}
            for kind,_,_,instance,montage,_ in entries:
                samples=probe['samples'][kind]
                planned=.7 if kind=='Slam' else 25/30
                near=[s for s in samples if s['active'] and abs(s['position']-planned)<.05]
                probe['checks'][kind]={'observed_playback':any(s['active'] and s['position']>.2 for s in samples),
                    'contact_window_sampled':bool(near),'max_actor_drift':max(s['actor_drift'] for s in samples),
                    'maximum_contact_pose_error_cm':max((s['pose_error_cm'] for s in near),default=1.e9),
                    'ended':not instance.montage_is_active(montage),'actual_contact_verified':False}
                if kind=='Slam':
                    gap=min((s['actual_hammer_min_z'] for s in near if 'actual_hammer_min_z' in s),default=1.e9)
                    probe['checks'][kind]['runtime_hammer_floor_gap_cm']=gap
                    probe['checks'][kind]['actual_contact_verified']=-.5<=gap<=2.
            probe['passed']=all(c['observed_playback'] and c['contact_window_sampled'] and c['max_actor_drift']<.1 and c['ended'] and c['maximum_contact_pose_error_cm']<2 for c in probe['checks'].values())
            probe['passed']=probe['passed'] and probe['checks']['Slam']['actual_contact_verified']
            probe['status']='complete'
            path.write_text(json.dumps(probe,indent=2),encoding='utf-8')
            u.GameplayStatics.set_global_time_dilation(world,original_time_dilation)
            u.unregister_slate_post_tick_callback(probe_handle)
    except Exception as error:
        probe['status']='error';probe['error']=str(error)
        path.write_text(json.dumps(probe,indent=2),encoding='utf-8')
        u.GameplayStatics.set_global_time_dilation(world,original_time_dilation)
        u.unregister_slate_post_tick_callback(probe_handle)

probe_handle=u.register_slate_post_tick_callback(record)
u.GameplayStatics.set_global_time_dilation(world,.1)
