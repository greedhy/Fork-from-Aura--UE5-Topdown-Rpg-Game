"""Read-only Grux source timing, root displacement and weapon bone inventory."""
import unreal as u,json,uuid
from pathlib import Path
root=Path(u.Paths.project_dir());out=root/'Saved/GAAuthoring/GruxDesign';out.mkdir(parents=True,exist_ok=True)
base='/Game/ParagonGrux/Characters/Heroes/Grux';mesh=u.load_asset(base+'/Meshes/Grux')
report={'run_id':uuid.uuid4().hex,'mesh':mesh.get_path_name(),'animations':[]}
sk=mesh.get_editor_property('skeleton');report['skeleton']=sk.get_path_name()
options=u.AnimPoseEvaluationOptions(evaluation_type=u.AnimDataEvalType.RAW,should_retarget=False,extract_root_motion=False)
for name in ['PrimaryAttack_LA','PrimaryAttack_RA','PrimaryAttack_FourStrikes','Stampede','Stampede_Knockup','Ultimate_Roar','Idle','Jog_Fwd','Run_Fwd','Death_A']:
 a=u.load_asset(base+'/Animations/'+name);assert a,name
 row={'name':name,'length':a.get_play_length(),'root_motion':a.get_editor_property('enable_root_motion'),'force_root_lock':a.get_editor_property('force_root_lock'),'events':[e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(a)],'samples':[]}
 for step in range(11):
  t=a.get_play_length()*step/10;p=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,options)
  if step==0:row['bones']=[str(b) for b in u.AnimPoseExtensions.get_bone_names(p)]
  bones={}
  for b in row['bones']:
   if b.lower()=='root' or any(x in b.lower() for x in ['weapon','hand_l','hand_r']):
    tr=u.AnimPoseExtensions.get_bone_pose(p,b,u.AnimPoseSpaces.WORLD);v=tr.translation;r=tr.rotation.rotator();bones[b]={'p':[v.x,v.y,v.z],'r':[r.pitch,r.yaw,r.roll]}
  row['samples'].append({'t':t,'bones':bones})
 report['animations'].append(row)
(out/'source-audit.json').write_text(json.dumps(report,indent=2))
