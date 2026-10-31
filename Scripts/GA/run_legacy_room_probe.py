"""Persisted roster, autonomous GAS damage to the real room player, and wave completion."""
import unreal as u,json,time,uuid
from pathlib import Path
w=u.EditorLevelLibrary.get_game_world();assert w and 'L_RoguelikeRun' in w.get_path_name()
d=next(iter(u.GameplayStatics.get_all_actors_of_class(w,u.DungeonRunDirector)));initial=json.loads(d.get_run_report());assert initial['phase']=='Exploring'
pc=u.GameplayStatics.get_player_controller(w,0);player=pc.get_controlled_pawn();asc=pc.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent);attrs=asc.get_attribute_set(u.MyAttributeSet)
for k in ['max_health','health']:
 v=attrs.get_editor_property(k);v.import_text('(BaseValue=100000,CurrentValue=100000)');attrs.set_editor_property(k,v)
rooms=[r for r in initial['rooms'] if r['role']=='Combat' and r['phase']=='Discovered'];room=rooms.pop(0)
player.set_actor_location(u.Vector(room['x'],room['y'],110),False,True);u.GameplayStatics.set_global_time_dilation(w,1.)
header=(Path(u.Paths.project_dir())/'Scripts/GA/run_wave1_room_probe.py').read_text();exec(header[header.index('def kill(a):'):header.index('def tick(dt):')])
needed={'GoblinSpear','GoblinSlinger','Ghoul'};seen=set();checked=set();source=None;case=None;started=time.monotonic();cleared=[]
report={'run_id':uuid.uuid4().hex,'status':'running','cases':[],'ai':{},'checks':{}};out=Path(u.Paths.project_dir())/'Saved/GAAuthoring/LegacyMonsterDesign/room-runtime.json'
def hp():return attrs.get_editor_property('health').get_editor_property('current_value')
def tick(dt):
 global room,source,case
 try:
  now=u.GameplayStatics.get_time_seconds(w);r=json.loads(d.get_run_report());assert not r['error'],r['error']
  by_path={a.get_path_name():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.EnemyCharacter)}
  active=[by_path[t['path']] for t in r['targets'] if t['kind']=='actor' and t['path'] in by_path]
  for a in active:
   key=a.get_path_name()+':'+str(a.get_dungeon_pool_lease());ctrl=a.get_controller();brain=ctrl.get_component_by_class(u.BrainComponent) if ctrl else None
   if key not in seen:
    seen.add(key);report['ai'][key]=bool(brain and brain.is_running())
    if brain:brain.stop_logic('Isolate one roster type')
    anim=a.get_component_by_class(u.SkeletalMeshComponent).get_anim_instance()
    if anim:anim.montage_stop(0.)
   if a!=source:a.get_component_by_class(u.CharacterMovementComponent).disable_movement()
  rr=next(x for x in r['rooms'] if x['index']==room['index'])
  if case is None and r['phase']=='Encounter' and r['pending_enemy_spawns']==0:
   candidates=[(n,a) for a in active for n in needed-checked if '/LegacyExpansion/BP_'+n+'.' in a.get_class().get_path_name()]
   if candidates:
    n,source=candidates[0];h=source.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height()
    source.set_actor_location(u.Vector(room['x'],room['y'],h+2),False,True)
    player.set_actor_location(u.Vector(room['x']+(400 if n=='GoblinSlinger' else 100),room['y'],100),False,True)
    source.set_editor_property('combat_target',player);source.get_component_by_class(u.CharacterMovementComponent).set_movement_mode(u.MovementMode.MOVE_WALKING)
    brain=source.get_controller().get_component_by_class(u.BrainComponent);brain.restart_logic()
    case={'name':n,'start':now,'before':hp(),'healthbar':source.get_editor_property('health_bar').get_user_widget_object() is not None,'samples':[]}
   else:
    for a in active:kill(a)
  elif case:
   mesh=source.get_component_by_class(u.SkeletalMeshComponent);anim=mesh.get_anim_instance();m=anim.get_current_active_montage()
   case['samples'].append({'t':now-case['start'],'hp':hp(),'montage':m.get_name() if m else None,'bang':source.get_component_by_class(u.TextRenderComponent).is_visible()})
   if now-case['start']>7:
    case['passed']=case['healthbar'] and hp()<case['before'] and any(s['bang'] for s in case['samples']) and any(s['montage'] and 'AM_Legacy_' in s['montage'] for s in case['samples'])
    checked.add(case['name']);report['cases'].append(case);kill(source);source=None;case=None
  if rr['phase']=='Cleared' and case is None:
   if room['index'] not in cleared:cleared.append(room['index'])
   if checked==needed:
    report['checks']={'all_three_real_player_hits':all(c['passed'] for c in report['cases']),'all_spawned_ai_started':all(report['ai'].values()),'room_cleared':r['phase']=='Exploring' and rr['remaining_required']==0,'no_remaining_targets':not r['targets'] and r['pending_enemy_spawns']==0}
    report.update(status='complete',passed=all(report['checks'].values()),cleared_rooms=cleared,final=r)
   else:
    assert rooms,'Did not spawn all three types';room=rooms.pop(0);player.set_actor_location(u.Vector(room['x'],room['y'],110),False,True)
  if time.monotonic()-started>120:raise RuntimeError('Room timeout')
 except Exception as e:report.update(status='error',passed=False,error=str(e))
 if report['status']!='running':u.unregister_slate_post_tick_callback(handle)
 out.write_text(json.dumps(report,indent=2))
handle=u.register_slate_post_tick_callback(tick)
