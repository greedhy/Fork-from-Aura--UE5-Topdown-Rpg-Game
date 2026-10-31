"""Spawned controllers must navigate and invoke the new GAs without manual activation."""
import unreal as u,json,time,uuid
from pathlib import Path
w=u.EditorLevelLibrary.get_game_world();assert w and w.get_path_name().startswith('/Temp/')
actors=list(u.GameplayStatics.get_all_actors_of_class(w,u.EnemyCharacter));target=next(a for a in actors if a.actor_has_tag('Target'))
for a in actors:
 if isinstance(a,u.TelegraphedEnemyCharacter):a.enable_dungeon_pooling(0.);a.sleep_for_dungeon_pool(False)
 if a!=target and a.actor_has_tag('Player'):a.set_editor_property('tags',['Outside'])
target.set_actor_location(u.Vector(0,0,89),False,True);target.get_component_by_class(u.CharacterMovementComponent).disable_movement()
c=target.get_component_by_class(u.CapsuleComponent);c.set_editor_property('generate_overlap_events',True);c.set_collision_response_to_channel(u.CollisionChannel.ECC_PROJECTILE,u.CollisionResponseType.ECR_OVERLAP)
at=target.get_component_by_class(u.MyAbilitySystemComponent).get_attribute_set(u.MyAttributeSet)
for k in ['max_health','health']:
 v=at.get_editor_property(k);v.import_text('(BaseValue=100000,CurrentValue=100000)');at.set_editor_property(k,v)
pc=u.GameplayStatics.get_player_controller(w,0);pawn=pc.get_controlled_pawn();pawn.set_actor_enable_collision(False)
u.SystemLibrary.execute_console_command(w,'EnableCheats',pc);u.GameplayStatics.set_global_time_dilation(w,1.)
names=['GoblinSpear','GoblinSlinger','Ghoul'];index=0;case=None;source=None;started=time.monotonic()
report={'run_id':uuid.uuid4().hex,'status':'running','cases':[]};out=Path(u.Paths.project_dir())/'Saved/GAAuthoring/LegacyMonsterDesign/autonomous-runtime.json'
def hp():return at.get_editor_property('health').get_editor_property('current_value')
def tick(dt):
 global index,case,source
 try:
  now=u.GameplayStatics.get_time_seconds(w)
  if case is None:
   n=names[index];p='/Game/BluePrints/Characters/LegacyExpansion/BP_'+n;cls=u.load_class(None,p+'.BP_'+n+'_C')
   before={a.get_path_name() for a in u.GameplayStatics.get_all_actors_of_class(w,cls)};pawn.set_actor_location(u.Vector(-550,0,150),False,True)
   u.SystemLibrary.execute_console_command(w,'Summon '+cls.get_path_name(),pc)
   source=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,cls) if a.get_path_name() not in before)
   h=source.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height();source.set_actor_location(u.Vector(-450,0,h+2),False,True)
   controller=source.get_controller();brain=controller.get_component_by_class(u.BrainComponent) if controller else None
   case={'name':n,'start':now,'hp_before':hp(),'brain':bool(brain and brain.is_running()),'samples':[]}
  mesh=source.get_component_by_class(u.SkeletalMeshComponent);anim=mesh.get_anim_instance();m=anim.get_current_active_montage();foot=source.get_actor_transform().inverse_transform_location(mesh.get_socket_location('Foot-L'))
  case['samples'].append({'t':now-case['start'],'speed':source.get_velocity().length(),'hp':hp(),'montage':m.get_name() if m else None,'bang':source.get_component_by_class(u.TextRenderComponent).is_visible(),'foot':[round(foot.x,1),round(foot.y,1),round(foot.z,1)]})
  if now-case['start']>9:
   s=case['samples'];case['passed']=case['brain'] and s[-1]['hp']<case['hp_before'] and any(x['bang'] for x in s) and any(x['montage'] and 'AM_Legacy_' in x['montage'] for x in s)
   # Ranged AI may already be in range and intentionally remain stationary.
   case['navigation_observed']=any(x['speed']>50 for x in s);case['pose_varied']=len({tuple(x['foot']) for x in s if x['speed']>50})>3
   report['cases'].append(case);source.destroy_actor();index+=1;case=None
   if index==len(names):report.update(status='complete',passed=all(c['passed'] for c in report['cases']))
  if time.monotonic()-started>60:raise RuntimeError('AI timeout')
 except Exception as e:report.update(status='error',passed=False,error=str(e))
 if report['status']!='running':u.unregister_slate_post_tick_callback(handle)
 out.write_text(json.dumps(report,indent=2))
handle=u.register_slate_post_tick_callback(tick)
