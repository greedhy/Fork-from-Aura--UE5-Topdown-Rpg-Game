"""Real room roster, optional summon registration, source retirement and wave completion."""
import unreal as u,json,time,uuid
from pathlib import Path
w=u.EditorLevelLibrary.get_game_world();assert w and 'L_RoguelikeRun' in w.get_path_name()
d=next(iter(u.GameplayStatics.get_all_actors_of_class(w,u.DungeonRunDirector)))
pc=u.GameplayStatics.get_player_controller(w,0);player=pc.get_controlled_pawn()
initial=json.loads(d.get_run_report());assert initial['phase']=='Exploring'
room=next(r for r in initial['rooms'] if r['role']=='Combat' and r['phase']=='Discovered')
player.set_actor_location(u.Vector(room['x'],room['y'],110),False,True)
u.GameplayStatics.set_global_time_dilation(w,1.)
out=Path(u.Paths.project_dir())/'Saved/GAAuthoring/MonsterWave1/wave1-room-runtime.json'
report={'run_id':uuid.uuid4().hex,'status':'running','checks':{},'snapshots':[],'ai':{}}
stage=0;started=time.monotonic();stage_start=u.GameplayStatics.get_time_seconds(w);source=None;before_required=None;seen=set();summoned_paths=[]
def kill(a):
 p=u.DamageEffectParams();tag=u.GameplayTag();tag.import_text('(TagName="Damage.Physics")')
 for k,v in {'source_ability_system_component':pc.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent),'target_ability_system_component':a.get_component_by_class(u.MyAbilitySystemComponent),'damage_gameplay_effect_class':u.load_class(None,'/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage.GE_Damage_C'),'damage_type':tag,'base_damage':1000000.,'ability_level':1.,'debuff_chance':0.}.items():p.set_editor_property(k,v)
 u.MyAbilitySystemLibrary.apply_damage_effect(p)
def tick(dt):
 global stage,stage_start,source,before_required,summoned_paths
 try:
  now=u.GameplayStatics.get_time_seconds(w);r=json.loads(d.get_run_report())
  enemies=list(u.GameplayStatics.get_all_actors_of_class(w,u.EnemyCharacter));by_path={a.get_path_name():a for a in enemies}
  active=[by_path[t['path']] for t in r['targets'] if t['kind']=='actor' and t['path'] in by_path]
  for a in active:
   c=a.get_controller();brain=c.get_component_by_class(u.BrainComponent) if c else None
   key=a.get_path_name()+':'+str(a.get_dungeon_pool_lease())
   if key not in seen:
    seen.add(key);report['ai'][key]={'class':a.get_class().get_path_name(),'running':bool(brain and brain.is_running())}
    if brain:brain.stop_logic('Room summon integration probe')
    mesh=a.get_component_by_class(u.SkeletalMeshComponent)
    if mesh.get_anim_instance():mesh.get_anim_instance().montage_stop(0.)
   a.get_component_by_class(u.CharacterMovementComponent).disable_movement()
  if r['error']:raise RuntimeError(r['error'])
  if stage==0 and r['phase']=='Encounter' and r['pending_enemy_spawns']==0 and active:
   candidates=[a for a in active if isinstance(a,u.ShamanEnemyCharacter)]
   if not candidates:
    for a in active:kill(a)
   else:
    source=candidates[0];report['snapshots'].append(r)
    half=source.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height()
    source.set_actor_location(u.Vector(room['x'],room['y'],half+2),False,True)
    player.set_actor_location(u.Vector(room['x']+350,room['y'],100),False,True)
    source.set_editor_property('combat_target',player)
    before_required=sum(t['required'] for t in r['targets'])
    stage=1;stage_start=now
  elif stage==1 and now-stage_start>13:
   report['checks']['summon_activated']=source.try_attack_index(2)
   assert report['checks']['summon_activated'],'Room summon rejected'
   stage=2;stage_start=now
  elif stage==2 and now-stage_start>3:
   owned=[a for a in active if a.get_editor_property('summoning_source')==source]
   summoned_paths=[a.get_path_name() for a in owned]
   report['checks']['summons_registered']=0<len(owned)<=5 and source.get_owned_minion_count()==len(owned)
   report['checks']['summons_optional']=all(not t['required'] for t in r['targets'] if t.get('path') in summoned_paths)
   report['checks']['required_count_unchanged']=sum(t['required'] for t in r['targets'])==before_required
   report['checks']['under_room_cap']=len(r['targets'])+r['pending_enemy_spawns']<=30
   report['snapshots'].append(r);kill(source);stage=3;stage_start=now
  elif stage==3 and now-stage_start>2:
   report['checks']['source_death_retires_summons']=not any(a.get_editor_property('summoning_source')==source for a in enemies)
   report['checks']['ledger_removes_summons']=not any(t.get('path') in summoned_paths for t in r['targets'])
   report['checks']['no_run_failure']=not r['error']
   report['snapshots'].append(r);stage=4;stage_start=now
  elif stage==4:
   for a in active:kill(a)
   rr=next(x for x in r['rooms'] if x['index']==room['index'])
   if rr['phase']=='Cleared':
    report['checks']['room_clears']=r['phase']=='Exploring' and rr['remaining_required']==0
    report['checks']['spawned_ai_runs']=all(x['running'] for x in report['ai'].values())
    report['snapshots'].append(r);report.update(status='complete',passed=all(report['checks'].values()))
  if time.monotonic()-started>90:raise RuntimeError('Room probe timeout: '+str(stage))
 except Exception as e:report.update(status='error',passed=False,error=str(e))
 if report['status']!='running':u.unregister_slate_post_tick_callback(wave1_room_handle)
 out.write_text(json.dumps(report,indent=2))
out.write_text(json.dumps(report));wave1_room_handle=u.register_slate_post_tick_callback(tick)
