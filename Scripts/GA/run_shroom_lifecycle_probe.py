import unreal as u,json,time,uuid
from pathlib import Path
root=Path(u.Paths.project_dir())
exec((root/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text().split('sg_path=')[0].replace('sg_source:u.Vector(0,0,89)','sg_source:u.Vector(0,0,57)').replace('sg_outside:u.Vector(700,0,89)','sg_outside:u.Vector(185,0,89)'))
for a in u.GameplayStatics.get_all_actors_of_class(world,u.DefaultPawn):a.set_actor_enable_collision(False)
wall=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor) if a.actor_has_tag('ShroomBoundaryWall'))
wall.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE);wall.set_actor_location(u.Vector(50,0,100),False,True);wall.set_actor_scale3d(u.Vector(.1,5,2));wall.set_actor_enable_collision(False)
sg_source.enable_dungeon_pooling(0.)
modes=[(0,'pre',.45,0),(1,'pre',.6,0),(1,'interrupt_field',1.4,1),(1,'pool_field',2.1,1),(1,'death_field',2.4,2),(1,'wall_field',1.6,1),(1,'second_life_normal',9,3),(0,'third_life_normal',9,1)]
report={'run_id':uuid.uuid4().hex,'status':'running','cases':[]};out=root/'Saved/GAAuthoring/ShroomDesign/lifecycle-runtime.json';out.write_text(json.dumps(report));index=0;case=None;started=time.monotonic()
u.GameplayStatics.set_global_time_dilation(world,.7)
def reset():
 wall.set_actor_enable_collision(False);sg_source.sleep_for_dungeon_pool(False)
 assert sg_source.wake_from_dungeon_pool(u.Transform(location=u.Vector(0,0,57)),'ShroomRegression')
 sg_source.get_component_by_class(u.CharacterMovementComponent).disable_movement();sg_source.set_editor_property('combat_target',sg_target)
 for a,p in [(sg_target,u.Vector(100,0,89)),(sg_friend,u.Vector(100,40,89)),(sg_outside,u.Vector(185,0,89))]:
  a.get_component_by_class(u.CharacterMovementComponent).stop_movement_immediately();a.get_component_by_class(u.CharacterMovementComponent).disable_movement();a.set_actor_location(p,False,True)
def kill():
 p=u.DamageEffectParams();tag=u.GameplayTag();tag.import_text('(TagName="Damage.Physics")')
 for k,v in {'source_ability_system_component':sg_target.get_component_by_class(u.MyAbilitySystemComponent),'target_ability_system_component':sg_source.get_component_by_class(u.MyAbilitySystemComponent),'damage_gameplay_effect_class':u.load_class(None,'/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage.GE_Damage_C'),'damage_type':tag,'base_damage':1000000.,'ability_level':1.,'debuff_chance':0.}.items():p.set_editor_property(k,v)
 u.MyAbilitySystemLibrary.apply_damage_effect(p)
def fx():return [c for c in u.ObjectIterator(u.NiagaraComponent) if c.get_world()==world and c.get_asset() and '/Shroom/Expansion/NS_Shroom_Spores' in c.get_asset().get_path_name() and c.is_active()]
def tick(dt):
 global index,case
 try:
  now=u.GameplayStatics.get_time_seconds(world);i,mode,at,expected=modes[index]
  if case is None:
   reset();case={'index':i,'mode':mode,'start':now,'before':[value(a,'health') for a in [sg_target,sg_friend,sg_outside]],'samples':[],'acted':False,'lease':sg_source.get_dungeon_pool_lease()};assert sg_source.try_attack_index(i)
  t=now-case['start']
  if t>=at and not case['acted']:
   case['acted']=True
   if mode=='pool_field':reset();case['new_lease']=sg_source.get_dungeon_pool_lease()>case['lease']
   elif mode=='death_field':kill();case['killed']=value(sg_source,'health')<=0
   elif mode=='wall_field':wall.set_actor_enable_collision(True)
   else:sg_source.get_component_by_class(u.SkeletalMeshComponent).get_anim_instance().montage_stop(0.)
  m=sg_source.get_component_by_class(u.SkeletalMeshComponent)
  s={'t':t,'hp':[value(a,'health') for a in [sg_target,sg_friend,sg_outside]],'footprint':sg_source.get_component_by_class(u.ProceduralMeshComponent).get_num_sections(),'bang':sg_source.get_component_by_class(u.TextRenderComponent).is_visible(),'fx':len(fx()),'root_z':m.get_socket_location('Root').z,'physics':m.is_simulating_physics()};case['samples'].append(s)
  if t>5:
   hits=[x for j,x in enumerate(case['samples']) if j and x['hp'][0]<case['samples'][j-1]['hp'][0]-.01];case['hits']=len(hits)
   case['passed']=len(hits)==expected and all(x['hp'][1:]==case['before'][1:] for x in case['samples']) and not s['footprint'] and not s['bang'] and not s['fx']
   if mode=='pool_field':case['passed']=case['passed'] and case['new_lease']
   if mode=='death_field':case['passed']=case['passed'] and case['killed']
   if 'life_normal' in mode:case['passed']=case['passed'] and not s['physics'] and abs(s['root_z']-2)<5
   report['cases'].append(case);case=None;index+=1;out.write_text(json.dumps(report,indent=2))
  if index==len(modes):
   reset();sg_source.set_editor_property('combat_target',sg_friend);report['friendly_target_rejected']=not sg_source.try_attack_index(0)
   report.update(status='complete',passed=all(c['passed'] for c in report['cases']) and report['friendly_target_rejected'])
  if time.monotonic()-started>120:raise RuntimeError('timeout')
 except Exception as e:report.update(status='error',passed=False,error=str(e),pending=case)
 if report['status']!='running':
  wall.set_actor_enable_collision(False);u.GameplayStatics.set_global_time_dilation(world,1.);u.unregister_slate_post_tick_callback(handle);out.write_text(json.dumps(report,indent=2))
handle=u.register_slate_post_tick_callback(tick)
