"""Real GAS target selection, sector edges and occlusion, not geometry-only assertions."""
import unreal as u,json,time,uuid
from pathlib import Path
root=Path(u.Paths.project_dir())
exec((root/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text().split('sg_path=')[0].replace('sg_source:u.Vector(0,0,89)','sg_source:u.Vector(0,0,50)').replace('sg_target:u.Vector(100,0,89)','sg_target:u.Vector(85,0,89)'))
for p in u.GameplayStatics.get_all_actors_of_class(world,u.DefaultPawn):p.set_actor_enable_collision(False)
wall=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor) if a.actor_has_tag('DemonBoundaryWall'))
cases=[('selected_only',0,(80,15,89),False,(True,False)),('sector_two_targets',1,(70,40,89),False,(True,True)),('outside_radius',1,(101,0,89),False,(True,False)),('safe_rear',1,(-85,0,89),False,(True,False)),('wall_blocks',1,(80,15,89),True,(False,False))]
out=root/'Saved/GAAuthoring/MonsterWave1/demon-boundary-runtime.json'
report={'run_id':uuid.uuid4().hex,'status':'running','cases':[]};idx=0;current=None;next_time=0;started=time.monotonic()
def hp():return [value(sg_target,'health'),value(sg_friend,'health')]
def tick(dt):
 global idx,current,next_time
 try:
  now=u.GameplayStatics.get_time_seconds(world)
  if current is None and now>=next_time:
   name,attack,pos,blocked,expected=cases[idx]
   sg_source.set_actor_location(u.Vector(0,0,50),False,True)
   sg_source.get_component_by_class(u.CharacterMovementComponent).disable_movement()
   sg_friend.set_editor_property('tags',['Player','SGCombatProbe','Friend'])
   sg_friend.set_actor_location(u.Vector(*pos),False,True)
   wall.set_actor_enable_collision(blocked)
   current={'name':name,'before':hp(),'start':now,'expected':expected,'samples':[]}
   current['activated']=sg_source.try_attack_index(attack)
   assert current['activated'],name+' activation failed'
  if current:
   current['samples'].append(hp())
   if now-current['start']>2:
    current['after']=hp();actual=tuple(a<b for a,b in zip(current['after'],current['before']))
    current['passed']=actual==tuple(current['expected'])
    report['cases'].append(current);current=None;idx+=1;next_time=now+5.5
    out.write_text(json.dumps(report,indent=2))
  if idx==len(cases):report.update(status='complete',passed=all(c['passed'] for c in report['cases']))
  if time.monotonic()-started>90:raise RuntimeError('Boundary probe timeout')
 except Exception as e:report.update(status='error',passed=False,error=str(e))
 if report['status']!='running':
  wall.set_actor_enable_collision(False);u.unregister_slate_post_tick_callback(handle);out.write_text(json.dumps(report,indent=2))
out.write_text(json.dumps(report));handle=u.register_slate_post_tick_callback(tick)
