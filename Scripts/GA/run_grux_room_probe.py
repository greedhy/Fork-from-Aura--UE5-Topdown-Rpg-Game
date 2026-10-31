"""Temporary in-memory boss class override, real room spawning/AI/ledger, restored on exit."""
import unreal as u,json,time,uuid
from pathlib import Path
w=u.EditorLevelLibrary.get_game_world();assert w and 'L_RoguelikeRun' in w.get_path_name()
d=next(iter(u.GameplayStatics.get_all_actors_of_class(w,u.DungeonRunDirector)));initial=json.loads(d.get_run_report());assert initial['phase']=='Exploring'
profile=d.get_editor_property('profile');old_boss=profile.get_editor_property('boss_class')
cls=u.load_class(None,'/Game/BluePrints/Characters/Grux/Expansion/BP_GruxBoss.BP_GruxBoss_C');assert cls
profile.set_editor_property('boss_class',cls)
pc=u.GameplayStatics.get_player_controller(w,0);player=pc.get_controlled_pawn();asc=pc.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent)
attrs=asc.get_attribute_set(u.MyAttributeSet)
for key in ['max_health','health']:
 v=attrs.get_editor_property(key);v.import_text('(BaseValue=100000,CurrentValue=100000)');attrs.set_editor_property(key,v)
rooms=initial['rooms'];boss_room=next(r['index'] for r in rooms if r['role']=='Boss');parents={0:None};queue=[0]
while queue:
 a=queue.pop(0)
 for e in initial['connections']:
  b=e['to'] if e['from']==a else e['from'] if e['to']==a else None
  if b is not None and b not in parents:parents[b]=a;queue.append(b)
route=[];n=boss_room
while n is not None:route.append(n);n=parents[n]
route.reverse();cursor=1;stage=0;boss=None;boss_start=0.;seen_montages=set();max_speed=0.;foot_poses=set();initial_count=0
report={'run_id':uuid.uuid4().hex,'status':'running','checks':{},'route':route,'samples':[]};out=Path(u.Paths.project_dir())/'Saved/GAAuthoring/GruxDesign/room-runtime.json';started=time.monotonic()
def kill(a):
 p=u.DamageEffectParams();tag=u.GameplayTag();tag.import_text('(TagName="Damage.Physics")')
 for k,v in {'source_ability_system_component':asc,'target_ability_system_component':a.get_component_by_class(u.MyAbilitySystemComponent),'damage_gameplay_effect_class':u.load_class(None,'/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage.GE_Damage_C'),'damage_type':tag,'base_damage':1000000.,'ability_level':1.,'debuff_chance':0.}.items():p.set_editor_property(k,v)
 u.MyAbilitySystemLibrary.apply_damage_effect(p)
def tick(dt):
 global cursor,stage,boss,boss_start,max_speed,initial_count
 try:
  now=u.GameplayStatics.get_time_seconds(w);r=json.loads(d.get_run_report());assert not r['error'],r['error']
  if r['phase']=='Failed':raise RuntimeError(str(r))
  enemies={a.get_path_name():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.EnemyCharacter)}
  active=[enemies[t['path']] for t in r['targets'] if t['kind']=='actor' and t['path'] in enemies]
  target_room=rooms[route[cursor]]
  if stage==0:
   if r['phase']=='Exploring':player.set_actor_location(u.Vector(target_room['x'],target_room['y'],100),False,True)
   if target_room['index']!=boss_room:
    for a in active:kill(a)
    if r['rooms'][target_room['index']]['phase']=='Cleared':cursor+=1
   elif r['phase']=='Encounter' and r['pending_enemy_spawns']==0 and active:
    boss=d.get_editor_property('boss');assert boss and isinstance(boss,u.GruxEnemyCharacter),'Wrong boss class'
    ctrl=boss.get_controller();brain=ctrl.get_component_by_class(u.BrainComponent) if ctrl else None
    report['checks']['dynamic_ai_running']=bool(brain and brain.is_running())
    report['checks']['not_ordinary_pool']=boss.get_dungeon_pool_lease()==0
    report['checks']['healthbar_created']=boss.get_editor_property('health_bar').get_user_widget_object() is not None
    for a in active:
     if a!=boss:
      c=a.get_controller();b=c.get_component_by_class(u.BrainComponent) if c else None
      if b:b.stop_logic('Boss isolation')
      a.get_component_by_class(u.CharacterMovementComponent).disable_movement()
    boss.set_actor_location(u.Vector(target_room['x']-450,target_room['y'],132),False,True)
    player.set_actor_location(u.Vector(target_room['x'],target_room['y'],100),False,True)
    # Real below-half health condition must not trigger the legacy director summon.
    at=boss.get_component_by_class(u.MyAbilitySystemComponent).get_attribute_set(u.MyAttributeSet);v=at.get_editor_property('health');v.import_text('(BaseValue=500,CurrentValue=500)');at.set_editor_property('health',v)
    initial_count=len(r['targets']);stage=1;boss_start=now
  elif stage==1:
   mesh=boss.get_component_by_class(u.SkeletalMeshComponent);anim=mesh.get_anim_instance();m=anim.get_current_active_montage()
   if m:seen_montages.add(m.get_path_name())
   speed=boss.get_velocity().length();max_speed=max(max_speed,speed)
   if speed>50:
    foot=boss.get_actor_transform().inverse_transform_location(mesh.get_socket_location('foot_l'));foot_poses.add((round(foot.x,1),round(foot.y,1),round(foot.z,1)))
   report['samples'].append({'t':now-boss_start,'targets':len(r['targets']),'pulse':d.get_editor_property('pulse_warning'),'speed':speed,'montage':m.get_name() if m else None})
   if now-boss_start>12:
    report['checks']['ai_attacks']=bool(seen_montages);report['checks']['locomotion_pose_changes']=max_speed>50 and len(foot_poses)>3
    report['checks']['no_legacy_pulse']=not any(s['pulse'] for s in report['samples'])
    report['checks']['no_legacy_half_health_summon']=all(s['targets']<=initial_count for s in report['samples'])
    report['before_death']=r
    for t in r['targets']:
     if t['kind']=='actor' and t['required'] and t['path'] in enemies:kill(enemies[t['path']])
    stage=2;boss_start=now
  elif stage==2 and now-boss_start>1:
   report['after_death']=r;report['montages']=sorted(seen_montages)
   report['checks']['boss_room_cleared']=r['rooms'][boss_room]['phase']=='Cleared'
   report['checks']['optional_targets_cleaned']=not r['targets'] and r['pending_enemy_spawns']==0
   report['checks']['run_victory']=r['phase']=='Victory'
   report.update(status='complete',passed=all(report['checks'].values()))
  if time.monotonic()-started>120:raise RuntimeError('Boss room timeout stage '+str(stage))
 except Exception as e:report.update(status='error',passed=False,error=str(e))
 if report['status']!='running':
  profile.set_editor_property('boss_class',old_boss);report['profile_restored']=str(profile.get_editor_property('boss_class'))==str(old_boss);u.unregister_slate_post_tick_callback(handle)
 out.write_text(json.dumps(report,indent=2))
handle=u.register_slate_post_tick_callback(tick)

