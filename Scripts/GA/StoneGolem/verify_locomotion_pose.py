import unreal as u,json,uuid
from pathlib import Path
root=Path(u.Paths.project_dir());world=u.EditorLevelLibrary.get_game_world()
assert world and world.get_path_name().startswith('/Temp/'), 'Use the isolated combat probe'
assert not globals().get('sg_locomotion_running',False), 'Probe already running'
sg_locomotion_running=True
a=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.StoneGolemCharacter) if a.actor_has_tag('SGSource'))
a.set_actor_location(u.Vector(0,-400,89),False,True)
m=a.get_component_by_class(u.CharacterMovementComponent);m.set_editor_property('gravity_scale',0.);m.set_movement_mode(u.MovementMode.MOVE_FLYING);m.set_editor_property('braking_deceleration_flying',0.);m.set_editor_property('velocity',u.Vector(150,0,0))
mesh=a.get_component_by_class(u.SkeletalMeshComponent);anim=mesh.get_anim_instance()
result={'run_id':uuid.uuid4().hex,'status':'running','samples':[]};started=u.GameplayStatics.get_time_seconds(world);phase=0
out=root/'Saved/GAAuthoring/StoneGolemMovementFix/pose-probe.json'
def tick(dt):
 global phase,sg_locomotion_running
 t=u.GameplayStatics.get_time_seconds(world)-started
 try:
  sample={'time':t,'phase':phase,'speed':a.get_velocity().length(),'feet':{}}
  if phase==0:sample['ground_speed']=anim.get_editor_property('GroundSpeed');sample['should_move']=anim.get_editor_property('ShouldMove')
  for bone in ['foot_l','foot_r','calf_l','calf_r']:
   p=mesh.get_socket_transform(bone,u.RelativeTransformSpace.RTS_COMPONENT).translation;sample['feet'][bone]=[p.x,p.y,p.z]
  result['samples'].append(sample)
  if t>=3 and phase==0:
   phase=1;mesh.play_animation(u.load_asset('/Game/BluePrints/Characters/StoneGolem/Animations/AS_SG_Walk'),True)
  if t>=6:
   mesh.set_animation_mode(u.AnimationMode.ANIMATION_BLUEPRINT);m.stop_movement_immediately();m.set_movement_mode(u.MovementMode.MOVE_NONE)
   steady=[x for x in result['samples'] if x['phase']==0 and x['time']>1]
   travel=[max(x['feet']['foot_l'][i] for x in steady)-min(x['feet']['foot_l'][i] for x in steady) for i in range(3)]
   result['blueprint_foot_travel_cm']=travel;result['passed']=travel[1]>20 and travel[2]>5 and all(x['should_move'] for x in steady)
   result['status']='complete';sg_locomotion_running=False;u.unregister_slate_post_tick_callback(handle)
  out.write_text(json.dumps(result))
 except Exception as e:
  sg_locomotion_running=False;result['status']='error';result['error']=str(e);out.write_text(json.dumps(result));u.unregister_slate_post_tick_callback(handle)
handle=u.register_slate_post_tick_callback(tick)
