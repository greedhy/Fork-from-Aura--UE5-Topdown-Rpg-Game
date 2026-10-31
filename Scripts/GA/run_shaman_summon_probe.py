"""Exercise actual summon GA and source-owned cleanup through pool reuse."""
import unreal as u,json,time,uuid
from pathlib import Path
root=Path(u.Paths.project_dir())
s=(root/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text().split('sg_path=')[0]
s=s.replace('sg_source:u.Vector(0,0,89)','sg_source:u.Vector(0,0,sg_source.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height())').replace('sg_target:u.Vector(100,0,89)','sg_target:u.Vector(350,0,89)')
exec(compile(s,'shaman_summon_fixture','exec'),globals())
for pawn in u.GameplayStatics.get_all_actors_of_class(world,u.DefaultPawn):pawn.set_actor_enable_collision(False)
u.GameplayStatics.set_global_time_dilation(world,1.)
out=root/'Saved/GAAuthoring/MonsterWave1/shaman-summon-runtime.json'
report={'run_id':uuid.uuid4().hex,'status':'running','checks':{},'samples':[]}
sg_source.enable_dungeon_pooling(0.)
lease=sg_source.get_dungeon_pool_lease();tr=sg_source.get_actor_transform()
report['checks']['activate']=sg_source.try_attack_index(2)
report['checks']['duplicate_rejected']=not sg_source.try_attack_index(2)
start=u.GameplayStatics.get_time_seconds(world);phase=0;phase_start=start;wall=time.monotonic();owned=[]
out.write_text(json.dumps(report))
def damage_source():
 p=u.DamageEffectParams();tag=u.GameplayTag();tag.import_text('(TagName="Damage.Physics")')
 for k,v in {'source_ability_system_component':sg_target.get_component_by_class(u.MyAbilitySystemComponent),'target_ability_system_component':sg_source.get_component_by_class(u.MyAbilitySystemComponent),'damage_gameplay_effect_class':u.load_class(None,'/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage.GE_Damage_C'),'damage_type':tag,'base_damage':1000000.,'ability_level':1.,'debuff_chance':0.}.items():p.set_editor_property(k,v)
 u.MyAbilitySystemLibrary.apply_damage_effect(p)
def tick(dt):
 global phase,phase_start,owned
 try:
  now=u.GameplayStatics.get_time_seconds(world);elapsed=now-phase_start
  count=sg_source.get_owned_minion_count()
  report['samples'].append({'t':now-start,'phase':phase,'count':count})
  for a in u.GameplayStatics.get_all_actors_of_class(world,u.EnemyCharacter):
   if a.get_editor_property('summoning_source')==sg_source:
    if a not in owned:owned.append(a)
    c=a.get_controller()
    if c and c.get_editor_property('brain_component'):c.get_editor_property('brain_component').stop_logic('Isolated summon lifecycle probe')
    a.get_component_by_class(u.CharacterMovementComponent).disable_movement()
  if phase==0 and elapsed>12.5:
   report['checks']['bounded_minions']=1<=count<=5
   report['spawned']=len(owned)
   report['checks']['owned']=len(owned)==count
   report['checks']['at_cap_no_extra']=not sg_source.try_attack_index(2) if count==5 else True
   damage_source();report['checks']['source_dead']=value(sg_source,'health')<=0
   phase=1;phase_start=now
  elif phase==1 and elapsed>.15:
   report['checks']['death_clears_owned']=sg_source.get_owned_minion_count()==0 and not any(a.get_editor_property('summoning_source')==sg_source for a in u.GameplayStatics.get_all_actors_of_class(world,u.EnemyCharacter))
   sg_source.sleep_for_dungeon_pool(False)
   report['checks']['wake']=sg_source.wake_from_dungeon_pool(tr,'ShamanSummonSecondLife')
   sg_source.get_component_by_class(u.CharacterMovementComponent).disable_movement()
   sg_source.set_editor_property('combat_target',sg_target)
   report['checks']['new_lease']=sg_source.get_dungeon_pool_lease()>lease
   report['checks']['new_life_activate']=sg_source.try_attack_index(2)
   owned=[];phase=2;phase_start=now
  elif phase==2 and elapsed>3.:
   report['checks']['new_life_bounded']=1<=count<=5
   sg_source.sleep_for_dungeon_pool(False)
   report['checks']['recycle_clears_owned']=sg_source.get_owned_minion_count()==0 and not any(a.get_editor_property('summoning_source')==sg_source for a in u.GameplayStatics.get_all_actors_of_class(world,u.EnemyCharacter))
   report.update(status='complete',passed=all(report['checks'].values()))
  if time.monotonic()-wall>60:raise RuntimeError('Summon probe timeout')
 except Exception as e:report.update(status='error',passed=False,error=str(e))
 if report['status']!='running':
  u.unregister_slate_post_tick_callback(shaman_summon_handle);out.write_text(json.dumps(report,indent=2))
shaman_summon_handle=u.register_slate_post_tick_callback(tick)
