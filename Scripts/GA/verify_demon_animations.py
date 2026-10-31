"""Independent saved-asset checks for the Demon animation preparation stage."""
import unreal as u,json
from pathlib import Path
root='/Game/BluePrints/Characters/Demon/Expansion/Animations/'
results=[]
options=u.AnimPoseEvaluationOptions(evaluation_type=u.AnimDataEvalType.RAW,should_retarget=False)
for short,source in [('ClawL','Demon_Attack_L'),('ClawR','Demon_Attack_R'),('Tailspin','Demon_Red_Tailspin')]:
 a=u.load_asset(root+'AS_Demon_'+short)
 m=u.load_asset(root+'AM_Demon_'+short)
 s=u.load_asset('/Game/Assets/Enemies/Demon/Animations/'+source)
 assert a and m and s
 assert not a.get_editor_property('enable_root_motion') and not a.get_editor_property('force_root_lock'), 'Do not erase authored root rotation'
 assert not u.AnimationLibrary.get_animation_notify_events(a)
 assert not u.AnimationLibrary.get_animation_notify_events(m)
 assert a.get_editor_property('skeleton')==m.get_editor_property('skeleton')==s.get_editor_property('skeleton')
 frames=u.AnimationLibrary.get_num_frames(s)
 assert u.AnimationLibrary.get_num_frames(a)==frames
 max_error=0.
 for frame in range(frames+1):
  t=u.AnimationLibrary.get_time_at_frame(s,frame)
  ap=u.AnimPoseExtensions.get_anim_pose_at_time(a,t,options)
  sp=u.AnimPoseExtensions.get_anim_pose_at_time(s,t,options)
  for bone in ['Wrist-L','Wrist-R','Tail_07']:
   av=u.AnimPoseExtensions.get_bone_pose(ap,bone,u.AnimPoseSpaces.LOCAL)
   sv=u.AnimPoseExtensions.get_bone_pose(sp,bone,u.AnimPoseSpaces.LOCAL)
   max_error=max(max_error,(av.translation-sv.translation).length())
 assert max_error<.001
 results.append({'clip':short,'frames':frames,'local_pose_translation_error_cm':max_error,'passed':True})
(Path(u.Paths.project_dir())/'Saved/GAAuthoring/MonsterWave1/demon-animation-verification.json').write_text(json.dumps({'passed':True,'cases':results,'contact_window_verified':False},indent=2))
