import unreal as u,json,time,uuid
from pathlib import Path
root=Path(u.Paths.project_dir())
exec((root/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text().split('sg_path=')[0].replace('sg_source:u.Vector(0,0,89)','sg_source:u.Vector(0,0,57)').replace('sg_outside:u.Vector(700,0,89)','sg_outside:u.Vector(185,0,89)'))
for a in u.GameplayStatics.get_all_actors_of_class(world,u.DefaultPawn):a.set_actor_enable_collision(False)
out=root/'Saved/GAAuthoring/ShroomDesign/combat-runtime.json';report={'run_id':uuid.uuid4().hex,'status':'running','cases':[]};out.write_text(json.dumps(report));index=0;case=None;wall=time.monotonic()
u.GameplayStatics.set_global_time_dilation(world,.5)
def fx():
 return [c for c in u.ObjectIterator(u.NiagaraComponent) if c.get_world()==world and c.get_asset() and '/Shroom/Expansion/NS_Shroom_Spores' in c.get_asset().get_path_name() and c.is_active()]
def tick(dt):
 global index,case
 try:
  now=u.GameplayStatics.get_time_seconds(world)
  if case is None:
   case={'index':index,'start':now,'before':[value(a,'health') for a in [sg_target,sg_friend,sg_outside]],'samples':[]}
   assert sg_source.try_attack_index(index),'Rejected '+str(index)
   case['repeat_rejected']=not sg_source.try_attack_index(index)
  t=now-case['start'];s={'t':t,'hp':[value(a,'health') for a in [sg_target,sg_friend,sg_outside]],'footprint':sg_source.get_component_by_class(u.ProceduralMeshComponent).get_num_sections(),'bang':sg_source.get_component_by_class(u.TextRenderComponent).is_visible(),'root_z':sg_source.get_component_by_class(u.SkeletalMeshComponent).get_socket_location('Root').z,'fx':len(fx())};case['samples'].append(s)
  if t>(5 if index else 2):
   hits=[x for j,x in enumerate(case['samples']) if j and x['hp'][0]<case['samples'][j-1]['hp'][0]-.01]
   case['hits']=[{'t':x['t'],'hp':x['hp'][0],'root_z':x['root_z']} for x in hits]
   case['passed']=len(hits)==(3 if index else 1) and case['repeat_rejected'] and all(x['hp'][1:]==case['before'][1:] for x in case['samples']) and s['footprint']==0 and not s['bang'] and s['fx']==0
   if index:
    case['passed']=case['passed'] and all(abs(hits[n]['t']-hits[n-1]['t']-1)<.06 for n in range(1,len(hits))) and any(x['fx'] for x in case['samples']) and all(x['footprint']>0 for x in case['samples'] if 1.4<x['t']<4.1)
   report['cases'].append(case);case=None;index+=1
  if index==2:report.update(status='complete',passed=all(c['passed'] for c in report['cases']))
  if time.monotonic()-wall>90:raise RuntimeError('timeout')
 except Exception as e:report.update(status='error',passed=False,error=str(e),pending=case)
 if report['status']!='running':u.unregister_slate_post_tick_callback(handle);u.GameplayStatics.set_global_time_dilation(world,1.);out.write_text(json.dumps(report,indent=2))
handle=u.register_slate_post_tick_callback(tick)
