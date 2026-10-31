"""Real GA, lethal GE, pool retirement and reuse in one isolated PIE actor."""
import unreal as u,json,time,uuid
from pathlib import Path
root=Path(u.Paths.project_dir())
exec((root/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text().split('sg_path=')[0].replace('sg_source:u.Vector(0,0,89)','sg_source:u.Vector(0,0,50)').replace('sg_target:u.Vector(100,0,89)','sg_target:u.Vector(85,0,89)'))
for spectator in u.GameplayStatics.get_all_actors_of_class(world,u.DefaultPawn):
 spectator.set_actor_enable_collision(False)
out=root/'Saved/GAAuthoring/MonsterWave1/demon-pool-runtime.json'
report={'run_id':uuid.uuid4().hex,'status':'running','checks':{},'samples':[]}
sg_source.enable_dungeon_pooling(0.)
lease=sg_source.get_dungeon_pool_lease();before=value(sg_target,'health')
assert sg_source.try_attack_index(1)
start=u.GameplayStatics.get_time_seconds(world);stage=0;stage_start=start;wall=time.monotonic()
out.write_text(json.dumps(report))
def damage_source():
 p=u.DamageEffectParams();tag=u.GameplayTag();tag.import_text('(TagName="Damage.Physics")')
 for k,v in {'source_ability_system_component':sg_target.get_component_by_class(u.MyAbilitySystemComponent),'target_ability_system_component':sg_source.get_component_by_class(u.MyAbilitySystemComponent),'damage_gameplay_effect_class':u.load_class(None,'/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage.GE_Damage_C'),'damage_type':tag,'base_damage':1000000.,'ability_level':1.,'debuff_chance':0.}.items():p.set_editor_property(k,v)
 u.MyAbilitySystemLibrary.apply_damage_effect(p)
def tick(dt):
 global stage,stage_start,before
 try:
  now=u.GameplayStatics.get_time_seconds(world);elapsed=now-stage_start
  hp=value(sg_target,'health')
  report['samples'].append({'t':now-start,'stage':stage,'target_health':hp,'lease':sg_source.get_dungeon_pool_lease()})
  if stage==0 and elapsed>.55:
   damage_source();report['checks']['lethal_before_hit']=value(sg_source,'health')<=0
   stage=1;stage_start=now
  elif stage==1 and elapsed>.1:
   sg_source.sleep_for_dungeon_pool(False)
   report['checks']['hidden_in_pool']=sg_source.get_editor_property('hidden')
   tr=u.Transform(location=u.Vector(0,0,50))
   report['checks']['wake']=sg_source.wake_from_dungeon_pool(tr,'DemonProbeSecondLife')
   # The fixture freezes all actors; Wake correctly restores walking, so freeze again
   # immediately rather than letting collision depenetration move the test source.
   sg_source.get_component_by_class(u.CharacterMovementComponent).disable_movement()
   report['checks']['new_lease']=sg_source.get_dungeon_pool_lease()>lease
   stage=2;stage_start=now
  elif stage==2 and elapsed>1.3:
   report['checks']['old_attack_no_damage']=hp==before
   report['checks']['old_warning_cleared']=sg_source.get_component_by_class(u.ProceduralMeshComponent).get_num_sections()==0 and not sg_source.get_component_by_class(u.TextRenderComponent).is_visible()
   sg_source.set_editor_property('combat_target',sg_target)
   sg_source.get_component_by_class(u.CharacterMovementComponent).disable_movement()
   report['checks']['old_cooldown_cleared']=sg_source.try_attack_index(1)
   report['checks']['duplicate_rejected']=not sg_source.try_attack_index(1)
   stage=3;stage_start=now
  elif stage==3 and elapsed>2.:
   report['checks']['second_life_damage']=hp<before
   values={round(s['target_health'],3) for s in report['samples'] if s['stage']==3}
   report['checks']['second_life_single_hit']=len(values)==2
   damage_source();stage=4;stage_start=now
  elif stage==4 and elapsed>.1:
   sg_source.sleep_for_dungeon_pool(False)
   report['checks']['second_wake']=sg_source.wake_from_dungeon_pool(u.Transform(location=u.Vector(0,0,50)),'DemonProbeThirdLife')
   sg_source.get_component_by_class(u.CharacterMovementComponent).disable_movement()
   report['checks']['third_lease']=sg_source.get_dungeon_pool_lease()==lease+2
   report['checks']['final_warning_cleared']=sg_source.get_component_by_class(u.ProceduralMeshComponent).get_num_sections()==0 and not sg_source.get_component_by_class(u.TextRenderComponent).is_visible()
   report['passed']=all(report['checks'].values());report['status']='complete'
  if time.monotonic()-wall>60:raise RuntimeError('Pool probe timed out')
 except Exception as e:report.update(status='error',passed=False,error=str(e))
 if report['status']!='running':
  u.unregister_slate_post_tick_callback(handle);out.write_text(json.dumps(report,indent=2))
handle=u.register_slate_post_tick_callback(tick)
