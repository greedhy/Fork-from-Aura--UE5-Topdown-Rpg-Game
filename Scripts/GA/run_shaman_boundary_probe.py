"""Actual ranged GA boundary, selected-only, occlusion and locked-ground checks."""
import unreal as u,json,time,uuid
from pathlib import Path
root=Path(u.Paths.project_dir())
s=(root/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text().split('sg_path=')[0]
s=s.replace('sg_source:u.Vector(0,0,89)','sg_source:u.Vector(0,0,sg_source.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height())').replace('sg_target:u.Vector(100,0,89)','sg_target:u.Vector(350,0,89)')
exec(compile(s,'shaman_boundary_fixture','exec'),globals())
u.GameplayStatics.set_global_time_dilation(world,1.)
for p in u.GameplayStatics.get_all_actors_of_class(world,u.DefaultPawn):p.set_actor_enable_collision(False)
wall=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor) if a.actor_has_tag('DemonBoundaryWall'))
wall.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
wall.set_actor_location(u.Vector(175,0,100),False,True);wall.set_actor_scale3d(u.Vector(.1,4,2))
cases=[('selected_only',0,(350,70,89),False,False,(True,False)),('burst_two',1,(350,100,89),False,False,(True,True)),('burst_outside',1,(350,171,89),False,False,(True,False)),('ground_locks',1,(350,0,89),False,True,(False,True)),('wall_rejects',0,(350,70,89),True,False,(False,False))]
out=root/'Saved/GAAuthoring/MonsterWave1/shaman-boundary-runtime.json'
report={'run_id':uuid.uuid4().hex,'status':'running','cases':[]};idx=0;current=None;next_time=0;started=time.monotonic()
def hp():return [value(sg_target,'health'),value(sg_friend,'health')]
def tick(dt):
 global idx,current,next_time
 try:
  now=u.GameplayStatics.get_time_seconds(world)
  if current is None and now>=next_time:
   name,attack,pos,blocked,move,expected=cases[idx]
   sg_target.set_actor_location(u.Vector(350,0,89),False,True)
   sg_friend.set_editor_property('tags',['Player','SGCombatProbe','Friend']);sg_friend.set_actor_location(u.Vector(*pos),False,True)
   sg_source.set_editor_property('combat_target',sg_target);wall.set_actor_enable_collision(blocked)
   current={'name':name,'before':hp(),'start':now,'expected':expected,'moved':False,'activation_expected':not blocked}
   current['activated']=sg_source.try_attack_index(attack)
  if current:
   if cases[idx][4] and now-current['start']>.5 and not current['moved']:
    sg_target.set_actor_location(u.Vector(600,0,89),False,True);current['moved']=True
   if now-current['start']>2.6:
    current['after']=hp();actual=tuple(a<b for a,b in zip(current['after'],current['before']))
    current['passed']=actual==tuple(current['expected']) and current['activated']==current['activation_expected']
    report['cases'].append(current);current=None;idx+=1;next_time=now+4.6
    out.write_text(json.dumps(report,indent=2))
  if idx==len(cases):report.update(status='complete',passed=all(c['passed'] for c in report['cases']))
  if time.monotonic()-started>90:raise RuntimeError('Shaman boundary timeout')
 except Exception as e:report.update(status='error',passed=False,error=str(e))
 if report['status']!='running':
  wall.set_actor_enable_collision(False);u.unregister_slate_post_tick_callback(shaman_boundary_handle);out.write_text(json.dumps(report,indent=2))
out.write_text(json.dumps(report));shaman_boundary_handle=u.register_slate_post_tick_callback(tick)
