"""Read imported Shroom bones, authored poses and motion, without modifying sources."""
import unreal as u,json,uuid
from pathlib import Path
out=Path(u.Paths.project_dir())/'Saved/GAAuthoring/ShroomDesign';out.mkdir(parents=True,exist_ok=True)
base='/Game/Assets/Enemies/Shroom';mesh=u.load_asset(base+'/Mesh/SKM_Shroom')
assert isinstance(mesh,u.SkeletalMesh)
report={'run_id':uuid.uuid4().hex,'mesh':mesh.get_path_name(),'skeleton':mesh.get_editor_property('skeleton').get_path_name(),'animations':[]}
options=u.AnimPoseEvaluationOptions(evaluation_type=u.AnimDataEvalType.RAW,should_retarget=False,extract_root_motion=False)
for name in ['Idle','Bounce','Attack']:
 a=u.load_asset(base+'/Animations/'+name);row={'name':name,'length':a.get_play_length(),'root_motion':a.get_editor_property('enable_root_motion'),'events':[e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(a)],'samples':[]}
 for step in range(21):
  t=a.get_play_length()*step/20;p=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,options);bones={}
  for b in u.AnimPoseExtensions.get_bone_names(p):
   tr=u.AnimPoseExtensions.get_bone_pose(p,b,u.AnimPoseSpaces.WORLD);v=tr.translation;r=tr.rotation.rotator();bones[str(b)]={'p':[v.x,v.y,v.z],'r':[r.pitch,r.yaw,r.roll]}
  row['samples'].append({'t':t,'bones':bones})
 report['animations'].append(row)
(out/'source-audit.json').write_text(json.dumps(report,indent=2))
