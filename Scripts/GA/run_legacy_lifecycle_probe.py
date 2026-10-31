"""Actual GA/ASC damage, warning and projectile travel in an isolated arena."""
import unreal as u,json,time,uuid
from pathlib import Path
w=u.EditorLevelLibrary.get_game_world();assert w and w.get_path_name().startswith('/Temp/')
actors=list(u.GameplayStatics.get_all_actors_of_class(w,u.EnemyCharacter))
sources={n:next(a for a in actors if a.actor_has_tag(n)) for n in ['GoblinSpear','GoblinSlinger','Ghoul']}
targets=[next(a for a in actors if a.actor_has_tag(n)) for n in ['Target','Friend','Outside']]
for a in targets:
 c=a.get_component_by_class(u.CapsuleComponent);c.set_editor_property('generate_overlap_events',True);c.set_collision_response_to_channel(u.CollisionChannel.ECC_PROJECTILE,u.CollisionResponseType.ECR_OVERLAP)
for a in u.GameplayStatics.get_all_actors_of_class(w,u.DefaultPawn):a.set_actor_enable_collision(False)
def attrs(a):return a.get_component_by_class(u.MyAbilitySystemComponent).get_attribute_set(u.MyAttributeSet)
def val(a,n):return attrs(a).get_editor_property(n).get_editor_property('current_value')
def assign(a,n,v):
 f=attrs(a).get_editor_property(n);f.import_text('(BaseValue='+str(v)+',CurrentValue='+str(v)+')');attrs(a).set_editor_property(n,f)
def freeze(a):
 c=a.get_controller();brain=c.get_component_by_class(u.BrainComponent) if c else None
 if brain:brain.stop_logic('Isolated legacy combat')
 a.get_component_by_class(u.CharacterMovementComponent).disable_movement()
def shots():return [a for a in u.GameplayStatics.get_all_actors_of_class(w,u.EnemySlingProjectile)]
for a in sources.values():a.enable_dungeon_pooling(0.)
wall=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.StaticMeshActor) if a.actor_has_tag('LegacyBoundaryWall'))
wall.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE);wall.set_actor_location(u.Vector(50,0,100),False,True);wall.set_actor_scale3d(u.Vector(.1,3,2))
cases=[(n,i,m) for n,i in [('GoblinSpear',0),('GoblinSlinger',0),('Ghoul',0),('Ghoul',1)] for m in ['pre','death','pool','wall','normal']]+[('GoblinSlinger',0,m) for m in ['flight_death','flight_pool','dodge','friend_line','wall_behind']]
report={'run_id':uuid.uuid4().hex,'status':'running','cases':[]};index=0;case=None;source=None;started=time.monotonic()
out=Path(u.Paths.project_dir())/'Saved/GAAuthoring/LegacyMonsterDesign/lifecycle-runtime.json'
u.GameplayStatics.set_global_time_dilation(w,.8)
def tick(dt):
 global index,case,source
 try:
  now=u.GameplayStatics.get_time_seconds(w)
  if case is None:
   name,skill,mode=cases[index]
   for i,a in enumerate(sources.values()):
    a.sleep_for_dungeon_pool(False);h=a.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height()
    assert a.wake_from_dungeon_pool(u.Transform(location=u.Vector(-700,500+i*300,h+2)),'LegacyProbe');freeze(a)
   source=sources[name];h=source.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height();source.set_actor_location(u.Vector(0,0,h+2),False,True)
   distance=400 if name=='GoblinSlinger' else 100
   for a,pos in zip(targets,[u.Vector(distance,0,89),u.Vector(distance,100,89),u.Vector(700,150,89)]):
    freeze(a);a.set_actor_location(pos,False,True)
    for n,v in [('max_health',10000.),('health',10000.),('armor',0.),('block_chance',0.),('critical_hit_chance',0.)]:assign(a,n,v)
   assign(source,'critical_hit_chance',0.);source.set_editor_property('combat_target',targets[0])
   wall.set_actor_enable_collision(False);wall.set_actor_location(u.Vector(50,0,100),False,True)
   case={'name':name,'index':skill,'mode':mode,'acted':False,'start':now,'samples':[],'accepted':source.try_attack_index(skill)}
   case['repeat_rejected']=not source.try_attack_index(skill);assert case['accepted'],'Activation rejected '+name
  t=now-case['start'];mode=case['mode']
  if not case['acted'] and t>(.7 if mode.startswith('flight') else .4):
   case['acted']=True
   if mode=='pre':source.get_component_by_class(u.SkeletalMeshComponent).get_anim_instance().montage_stop(0.)
   elif mode in ['death','flight_death']:
    p=u.DamageEffectParams();tag=u.GameplayTag();tag.import_text('(TagName="Damage.Physics")')
    for k,v in {'source_ability_system_component':targets[0].get_component_by_class(u.MyAbilitySystemComponent),'target_ability_system_component':source.get_component_by_class(u.MyAbilitySystemComponent),'damage_gameplay_effect_class':u.load_class(None,'/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage.GE_Damage_C'),'damage_type':tag,'base_damage':1000000.,'ability_level':1.,'debuff_chance':0.}.items():p.set_editor_property(k,v)
    u.MyAbilitySystemLibrary.apply_damage_effect(p)
   elif mode in ['pool','flight_pool']:source.sleep_for_dungeon_pool(False)
   elif mode=='wall':wall.set_actor_enable_collision(True)
   elif mode=='wall_behind':wall.set_actor_location(u.Vector(460,0,100),False,True);wall.set_actor_enable_collision(True)
   elif mode=='dodge':targets[0].set_actor_location(u.Vector(400,300,89),False,True)
   elif mode=='friend_line':targets[1].set_actor_location(u.Vector(200,0,89),False,True)
  mesh=source.get_component_by_class(u.SkeletalMeshComponent);anim=mesh.get_anim_instance();m=anim.get_current_active_montage()
  case['samples'].append({'t':now-case['start'],'hp':[val(a,'health') for a in targets],'bang':source.get_component_by_class(u.TextRenderComponent).is_visible(),'footprint':source.get_component_by_class(u.ProceduralMeshComponent).get_num_sections(),'montage':m.get_path_name() if m else None,'position':anim.montage_get_position(m) if m else None,'shots':[[p.get_actor_location().x,p.get_actor_location().y,p.get_actor_location().z] for p in shots()]})
  if now-case['start']>3.3:
   s=case['samples'];hits=[x for i,x in enumerate(s) if i and x['hp'][0]<s[i-1]['hp'][0]-.01]
   case['hit_times']=[x['t'] for x in hits]
   expected=1 if case['mode'] in ['normal','friend_line','wall_behind'] else 0
   case['passed']=len(hits)==expected and all(x['hp'][1:]==[10000.,10000.] for x in s) and not s[-1]['bang'] and not shots() and all(x['footprint']==0 for x in s)
   report['cases'].append(case);index+=1;case=None
   if index==len(cases):report.update(status='complete',passed=all(c['passed'] for c in report['cases']))
  if time.monotonic()-started>150:raise RuntimeError('Timeout')
 except Exception as e:report.update(status='error',passed=False,error=str(e))
 if report['status']!='running':u.GameplayStatics.set_global_time_dilation(w,1.);u.unregister_slate_post_tick_callback(handle)
 out.write_text(json.dumps(report,indent=2))
handle=u.register_slate_post_tick_callback(tick)
