"""Verify runtime possession/BT, then measure real locomotion output on nav movement."""
import unreal as u,json,time,uuid
from pathlib import Path
w=u.EditorLevelLibrary.get_game_world();assert w and w.get_path_name().startswith('/Temp/')
u.GameplayStatics.set_global_time_dilation(w,1.)
pc=u.GameplayStatics.get_player_controller(w,0);pawn=pc.get_controlled_pawn();pawn.set_actor_enable_collision(False)
u.SystemLibrary.execute_console_command(w,'EnableCheats',pc)
paths=['/Game/BluePrints/Characters/Demon/Expansion/BP_DemonWarrior','/Game/BluePrints/Characters/Goblin/ShamanExpansion/BP_ShamanExpanded']
report={'run_id':uuid.uuid4().hex,'status':'running','cases':[]};entries=[]
for i,p in enumerate(paths):
 cls=u.load_class(None,p+'.'+p.rsplit('/',1)[1]+'_C');before={a.get_path_name() for a in u.GameplayStatics.get_all_actors_of_class(w,cls)}
 pawn.set_actor_location(u.Vector(-600,-550+i*450,250),False,True)
 u.SystemLibrary.execute_console_command(w,'Summon '+cls.get_path_name(),pc)
 actors=[a for a in u.GameplayStatics.get_all_actors_of_class(w,cls) if a.get_path_name() not in before];assert len(actors)==1,p
 a=actors[0];ctrl=a.get_controller();brain=ctrl.get_component_by_class(u.BrainComponent) if ctrl else None
 r={'class':p,'brain_running':bool(brain and brain.is_running()),'samples':[]}
 assert ctrl and brain,p+' no runtime controller'
 brain.stop_logic('Isolated navigation locomotion measurement')
 z=a.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height()+2
 a.set_actor_location(u.Vector(-600,-550+i*450,z),False,True)
 mesh=a.get_component_by_class(u.SkeletalMeshComponent);anim=mesh.get_anim_instance()
 r['anim_class']=anim.get_class().get_path_name();r['bone_names']=[str(mesh.get_bone_name(b)) for b in range(mesh.get_num_bones()) if any(x in str(mesh.get_bone_name(b)).lower() for x in ['foot','ankle'])]
 r['move_result']=str(ctrl.move_to_location(u.Vector(400,-550+i*450,z),10.,False,True,False,False,None,False))
 report['cases'].append(r);entries.append((a,mesh,anim,r))
out=Path(u.Paths.project_dir())/'Saved/GAAuthoring/MonsterWave1/wave1-ai-runtime.json';out.write_text(json.dumps(report));started=time.monotonic()
def tick(dt):
 try:
  for a,mesh,anim,r in entries:
   pos=a.get_actor_location();sample={'speed':a.get_velocity().length(),'location':[pos.x,pos.y,pos.z],'bones':{}}
   try:sample['ground_speed']=anim.get_editor_property('GroundSpeed');sample['should_move']=anim.get_editor_property('ShouldMove')
   except Exception:pass
   for bone in r['bone_names']:
    v=a.get_actor_transform().inverse_transform_location(mesh.get_socket_location(bone));sample['bones'][bone]=[v.x,v.y,v.z]
   r['samples'].append(sample)
  if time.monotonic()-started<4:return
  for a,mesh,anim,r in entries:
   moving=[s for s in r['samples'] if s['speed']>50]
   varied=any(len({tuple(round(x,1) for x in s['bones'][b]) for s in moving})>3 for b in r['bone_names'])
   r['passed']=r['brain_running'] and len(moving)>5 and varied
   a.destroy_actor()
  report.update(status='complete',passed=all(r['passed'] for r in report['cases']))
 except Exception as e:report.update(status='error',passed=False,error=str(e))
 u.unregister_slate_post_tick_callback(wave1_ai_handle);out.write_text(json.dumps(report,indent=2))
wave1_ai_handle=u.register_slate_post_tick_callback(tick)
