"""Verify persisted roster in real generated encounters, then clear the room."""
import unreal as u,json,time,uuid
from pathlib import Path
w=u.EditorLevelLibrary.get_game_world();assert w and 'L_RoguelikeRun' in w.get_path_name()
d=next(iter(u.GameplayStatics.get_all_actors_of_class(w,u.DungeonRunDirector)))
pc=u.GameplayStatics.get_player_controller(w,0);player=pc.get_controlled_pawn()
initial=json.loads(d.get_run_report());assert initial['phase']=='Exploring'
rooms=[r for r in initial['rooms'] if r['role']=='Combat' and r['phase']=='Discovered'];room=rooms.pop(0)
player.set_actor_location(u.Vector(room['x'],room['y'],110),False,True)
u.GameplayStatics.set_global_time_dilation(w,1.)
out=Path(u.Paths.project_dir())/'Saved/GAAuthoring/ShroomDesign/room-runtime.json'
report={'run_id':uuid.uuid4().hex,'status':'running','checks':{},'ai':{},'snapshots':[],'health':[]}
stage=0;started=time.monotonic();stage_start=0.;source=None;seen=set();required=0
header=(Path(u.Paths.project_dir())/'Scripts/GA/run_wave1_room_probe.py').read_text()
exec(header[header.index('def kill(a):'):header.index('def tick(dt):')])
def tick(dt):
 global stage,stage_start,source,required,room
 try:
  now=u.GameplayStatics.get_time_seconds(w);r=json.loads(d.get_run_report());assert not r['error'],r['error']
  by_path={a.get_path_name():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.EnemyCharacter)}
  active=[by_path[t['path']] for t in r['targets'] if t['kind']=='actor' and t['path'] in by_path]
  for a in active:
   key=a.get_path_name()+':'+str(a.get_dungeon_pool_lease())
   if key not in seen:
    seen.add(key);c=a.get_controller();brain=c.get_component_by_class(u.BrainComponent) if c else None
    report['ai'][key]={'class':a.get_class().get_path_name(),'running':bool(brain and brain.is_running())}
    if brain:brain.stop_logic('Shroom room test')
    anim=a.get_component_by_class(u.SkeletalMeshComponent).get_anim_instance()
    if anim:anim.montage_stop(0.)
   a.get_component_by_class(u.CharacterMovementComponent).disable_movement()
  rr=next(x for x in r['rooms'] if x['index']==room['index'])
  if stage==0 and r['phase']=='Encounter' and r['pending_enemy_spawns']==0 and active:
   candidates=[a for a in active if '/Shroom/Expansion/BP_Shroom' in a.get_class().get_path_name()]
   if not candidates:
    for a in active:kill(a)
   else:
    source=candidates[0];source.set_actor_location(u.Vector(room['x'],room['y'],57),False,True)
    player.set_actor_location(u.Vector(room['x']+100,room['y'],100),False,True)
    source.set_editor_property('combat_target',player);required=sum(t['required'] for t in r['targets'])
    report['checks']['roster_spawned_shroom']=True
    widgets=source.get_components_by_class(u.WidgetComponent)
    report['checks']['health_widget_created']=any(c.get_user_widget_object() is not None for c in widgets)
    report['snapshots'].append(r);stage=1;stage_start=now
  elif stage==0 and rr['phase']=='Cleared':
   assert rooms,'No Shroom in combat rooms';room=rooms.pop(0);player.set_actor_location(u.Vector(room['x'],room['y'],110),False,True)
  elif stage==1 and now-stage_start>10:
   report['checks']['spore_activated']=source.try_attack_index(1);assert report['checks']['spore_activated']
   stage=2;stage_start=now
  elif stage==2:
   # Numeric attributes are read by exported property, matching other runtime probes.
   asc=pc.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent)
   hp=asc.get_attribute_set(u.MyAttributeSet).get_editor_property('health').get_editor_property('current_value')
   report['health'].append({'t':now-stage_start,'hp':hp})
   if now-stage_start>4.6:
    h=report['health'];hits=sum(h[i]['hp']<h[i-1]['hp']-.01 for i in range(1,len(h)))
    report['checks']['three_pulses']=hits==3;report['hits']=hits
    report['checks']['required_count_unchanged']=sum(t['required'] for t in r['targets'])==required
    report['checks']['field_cleaned']=source.get_component_by_class(u.ProceduralMeshComponent).get_num_sections()==0
    stage=3
  elif stage==3:
   for a in active:kill(a)
   if rr['phase']=='Cleared':
    report['checks']['room_clears']=r['phase']=='Exploring' and rr['remaining_required']==0
    report['checks']['spawned_ai_runs']=all(x['running'] for x in report['ai'].values())
    report['snapshots'].append(r);report.update(status='complete',passed=all(report['checks'].values()))
  if time.monotonic()-started>90:raise RuntimeError('Room timeout stage '+str(stage))
 except Exception as e:report.update(status='error',passed=False,error=str(e))
 if report['status']!='running':u.unregister_slate_post_tick_callback(handle)
 out.write_text(json.dumps(report,indent=2))
handle=u.register_slate_post_tick_callback(tick)
