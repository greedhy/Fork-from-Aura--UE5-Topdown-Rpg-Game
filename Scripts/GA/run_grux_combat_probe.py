"""Actual montage-clock combo, swept charge and timed self-buff in an isolated PIE world."""
import unreal as u,json,time,uuid
from pathlib import Path
root=Path(u.Paths.project_dir())
exec((root/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text().split('sg_path=')[0].replace('sg_source:u.Vector(0,0,89)','sg_source:u.Vector(0,0,132)').replace('sg_target:u.Vector(100,0,89)','sg_target:u.Vector(170,0,89)'))
for spectator in u.GameplayStatics.get_all_actors_of_class(world,u.DefaultPawn):spectator.set_actor_enable_collision(False)
u.GameplayStatics.set_global_time_dilation(world,.5)
path=root/'Saved/GAAuthoring/GruxDesign/combat-runtime.json'
report={'run_id':uuid.uuid4().hex,'status':'running','cases':[]};path.write_text(json.dumps(report))
index=0;case=None;wall_start=time.monotonic();handle=None
def sample(t):
 return {'t':round(t,4),'health':[value(a,'health') for a in [sg_target,sg_friend,sg_outside]],'armor':value(sg_source,'armor'),'buff':sg_source.has_roar_armor(),'x':sg_source.get_actor_location().x,'warning':sg_source.get_component_by_class(u.ProceduralMeshComponent).get_num_sections(),'bang':sg_source.get_component_by_class(u.TextRenderComponent).is_visible(),'montage':str(sg_source.get_component_by_class(u.SkeletalMeshComponent).get_anim_instance().get_current_active_montage())}
def tick(delta):
 global index,case
 try:
  now=u.GameplayStatics.get_time_seconds(world)
  if case is None:
   sg_source.set_actor_location(u.Vector(0,0,132),False,True);sg_source.set_actor_rotation(u.Rotator(),True)
   sg_target.set_actor_location(u.Vector(300 if index==1 else 170,0,89),False,True)
   sg_friend.set_actor_location(u.Vector(170,100,89),False,True)
   sg_outside.set_actor_location(u.Vector(700,400,89),False,True)
   case={'index':index,'start':now,'before':sample(0),'samples':[],'accepted':sg_source.try_attack_index(index)}
   case['repeat_rejected']=not sg_source.try_attack_index(index)
   assert case['accepted'],'activation refused '+str(index)
  t=now-case['start'];s=sample(t);case['samples'].append(s)
  if t> (8 if index==2 else 4):
   samples=case['samples'];hp=[round(x['health'][0],3) for x in samples]
   changes=[x for j,x in enumerate(samples) if j and x['health'][0]<samples[j-1]['health'][0]-.01]
   rising=[x['t'] for j,x in enumerate(samples) if x['bang'] and (j==0 or not samples[j-1]['bang'])]
   case['damage_events']=[{'t':x['t'],'health':x['health'][0],'x':x['x']} for x in changes];case['warning_starts']=rising
   common=case['repeat_rejected'] and all(x['health'][1:]==case['before']['health'][1:] for x in samples) and not s['bang'] and s['warning']==0
   if index<2:case['passed']=common and len(changes)==2 and len(rising)==2 and (index==0 or max(x['x'] for x in samples)>100)
   else:
    # Direct fixture attribute edits do not change GAS aggregator bases; compare
    # the real GE's active delta against its post-expiry base, not that fixture edit.
    case['passed']=common and not changes and any(x['buff'] and abs(x['armor']-s['armor']-25)<.01 for x in samples) and not s['buff']
   report['cases'].append(case);case=None;index+=1
  if index==3 or time.monotonic()-wall_start>180:
   report['status']='complete';report['passed']=index==3 and all(c['passed'] for c in report['cases']);path.write_text(json.dumps(report,indent=2))
   u.GameplayStatics.set_global_time_dilation(world,1.);u.unregister_slate_post_tick_callback(handle)
 except Exception as e:
  report['status']='error';report['error']=str(e);report['pending_case']=case;path.write_text(json.dumps(report,indent=2));u.GameplayStatics.set_global_time_dilation(world,1.);u.unregister_slate_post_tick_callback(handle)
handle=u.register_slate_post_tick_callback(tick)

