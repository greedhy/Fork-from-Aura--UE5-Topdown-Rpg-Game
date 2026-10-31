"""Read-only root rotation/translation comparison, with extraction disabled."""
import unreal as u,json
from pathlib import Path
rows=[]
options=u.AnimPoseEvaluationOptions(evaluation_type=u.AnimDataEvalType.RAW,should_retarget=False,extract_root_motion=False)
for name in ['Demon_Attack_L','Demon_Attack_R','Demon_Red_Tailspin','Demon_Tailspin_left']:
 a=u.load_asset('/Game/Assets/Enemies/Demon/Animations/'+name)
 row={'name':name,'root_motion':a.get_editor_property('enable_root_motion'),'force_lock':a.get_editor_property('force_root_lock'),'samples':[]}
 for t in [0,.1,.2,.3,.4,.5,.6,.7,.8,.9,1.]:
  p=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,options)
  bones={}
  for b in ['Root','Wrist-L','Tail_07']:
   tr=u.AnimPoseExtensions.get_bone_pose(p,b,u.AnimPoseSpaces.WORLD)
   v=tr.translation;r=tr.rotation.rotator()
   bones[b]={'p':[v.x,v.y,v.z],'r':[r.pitch,r.yaw,r.roll]}
  row['samples'].append({'t':t,'bones':bones})
 rows.append(row)
(Path(u.Paths.project_dir())/'Saved/GAAuthoring/MonsterWave1/demon-root-motion.json').write_text(json.dumps(rows,indent=2))
