"""Cancellation, walls, friendly/outer corridor filtering and lease cleanup with real GA."""
import unreal as u,json,time,uuid
from pathlib import Path
root=Path(u.Paths.project_dir())
exec((root/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text().split('sg_path=')[0].replace('sg_source:u.Vector(0,0,89)','sg_source:u.Vector(0,0,132)').replace('sg_target:u.Vector(100,0,89)','sg_target:u.Vector(170,0,89)'))
for a in u.GameplayStatics.get_all_actors_of_class(world,u.DefaultPawn):a.set_actor_enable_collision(False)
wall=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor) if a.actor_has_tag('GruxBoundaryWall'))
wall.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
wall.set_actor_location(u.Vector(350,0,200),False,True);wall.set_actor_scale3d(u.Vector(.1,12,4));wall.set_actor_enable_collision(False)
sg_source.enable_dungeon_pooling(0.)
caps=sg_source.get_component_by_class(u.CapsuleComponent);old_response=caps.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN)
modes=[(0,'pre',.42,0),(0,'second',1.85,1),(1,'pre',.62,0),(1,'moving',.87,1),(1,'late_pool',1.23,1),(2,'pre',.5,0),(2,'after_buff',.95,0),(2,'late_pool',1.73,0),(2,'pool',.95,0),(0,'death',.42,0),(1,'wall',9,2),(1,'boundary',9,2)]
request=root/'Saved/GAAuthoring/GruxDesign/lifecycle-case-request.json'
selection=json.loads(request.read_text(encoding='utf-8-sig')) if request.exists() else {}
if 'indices' in selection:modes=[modes[i] for i in selection['indices']]
report={'run_id':uuid.uuid4().hex,'status':'running','cases':[]};out=root/'Saved/GAAuthoring/GruxDesign/lifecycle-runtime.json';out.write_text(json.dumps(report));index=0;case=None;started=time.monotonic()
u.GameplayStatics.set_global_time_dilation(world,.5)
def reset():
 sg_source.sleep_for_dungeon_pool(False);assert sg_source.wake_from_dungeon_pool(u.Transform(location=u.Vector(0,0,132)),'GruxRegression')
 sg_source.get_component_by_class(u.CharacterMovementComponent).disable_movement();sg_source.set_editor_property('combat_target',sg_target)
 sg_target.get_component_by_class(u.CharacterMovementComponent).disable_movement();sg_target.get_component_by_class(u.CharacterMovementComponent).stop_movement_immediately()
 sg_target.set_actor_location(u.Vector(300 if modes[index][0]==1 else 170,0,89),False,True)
 sg_friend.set_actor_location(u.Vector(170,100,89),False,True);sg_outside.set_actor_location(u.Vector(150,130,89) if modes[index][1]=='boundary' else u.Vector(700,400,89),False,True)
 caps.set_collision_response_to_channel(u.CollisionChannel.ECC_PAWN,old_response);wall.set_actor_enable_collision(False)
def kill():
 p=u.DamageEffectParams();tag=u.GameplayTag();tag.import_text('(TagName="Damage.Physics")')
 for k,v in {'source_ability_system_component':sg_target.get_component_by_class(u.MyAbilitySystemComponent),'target_ability_system_component':sg_source.get_component_by_class(u.MyAbilitySystemComponent),'damage_gameplay_effect_class':u.load_class(None,'/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage.GE_Damage_C'),'damage_type':tag,'base_damage':1000000.,'ability_level':1.,'debuff_chance':0.}.items():p.set_editor_property(k,v)
 u.MyAbilitySystemLibrary.apply_damage_effect(p)
def tick(dt):
 global index,case
 try:
  now=u.GameplayStatics.get_time_seconds(world);i,mode,at,expected=modes[index]
  if case is None:
   reset()
   if mode=='wall':
    sg_target.set_actor_location(u.Vector(170,0,89),False,True);wall.set_actor_enable_collision(True);caps.set_collision_response_to_channel(u.CollisionChannel.ECC_PAWN,u.CollisionResponseType.ECR_IGNORE)
   case={'index':i,'mode':mode,'start':now,'before':[value(a,'health') for a in [sg_target,sg_friend,sg_outside]],'samples':[],'acted':False,'lease':sg_source.get_dungeon_pool_lease()}
   assert sg_source.try_attack_index(i),'Activation rejected '+mode
  t=now-case['start']
  if t>=at and not case['acted']:
   case['acted']=True;case['health_at_interrupt']=value(sg_target,'health');case['x_at_interrupt']=sg_source.get_actor_location().x
   if mode in ('pool','late_pool'):
    case['buff_before_pool']=sg_source.has_roar_armor();reset();case['new_lease']=sg_source.get_dungeon_pool_lease()>case['lease']
   elif mode=='death':kill()
   else:sg_source.get_component_by_class(u.SkeletalMeshComponent).get_anim_instance().montage_stop(0.)
  s={'t':t,'hp':[value(a,'health') for a in [sg_target,sg_friend,sg_outside]],'x':sg_source.get_actor_location().x,'buff':sg_source.has_roar_armor(),'warning':sg_source.get_component_by_class(u.ProceduralMeshComponent).get_num_sections(),'bang':sg_source.get_component_by_class(u.TextRenderComponent).is_visible()};case['samples'].append(s)
  if t>4:
   changes=[x for j,x in enumerate(case['samples']) if j and x['hp'][0]<case['samples'][j-1]['hp'][0]-.01]
   case['hits']=len(changes);case['max_x']=max(x['x'] for x in case['samples'])
   case['passed']=len(changes)==expected and all(x['hp'][1:]==case['before'][1:] for x in case['samples']) and not s['buff'] and not s['warning'] and not s['bang']
   if mode=='wall':case['passed']=case['passed'] and 250<case['max_x']<300
   if mode=='moving':case['passed']=case['passed'] and abs(s['x']-case['x_at_interrupt'])<1
   if mode in ('pool','late_pool'):case['passed']=case['passed'] and (i!=2 or case['buff_before_pool']) and case['new_lease']
   report['cases'].append(case);case=None;index+=1;out.write_text(json.dumps(report,indent=2))
  if index==len(modes):report.update(status='complete',passed=all(c['passed'] for c in report['cases']))
  if time.monotonic()-started>160:raise RuntimeError('timed out')
 except Exception as e:report.update(status='error',passed=False,error=str(e),pending=case)
 if report['status']!='running':
  wall.set_actor_enable_collision(False);caps.set_collision_response_to_channel(u.CollisionChannel.ECC_PAWN,old_response)
  u.GameplayStatics.set_global_time_dilation(world,1.);u.unregister_slate_post_tick_callback(handle);out.write_text(json.dumps(report,indent=2))
handle=u.register_slate_post_tick_callback(tick)


