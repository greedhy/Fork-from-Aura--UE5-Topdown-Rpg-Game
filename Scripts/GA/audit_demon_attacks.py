"""Read actual Demon attack curves and existing GAS bindings without saving assets."""
import unreal as u,json,uuid
from pathlib import Path
root=Path(u.Paths.project_dir());out=root/'Saved/GAAuthoring/MonsterWave1'
out.mkdir(parents=True,exist_ok=True)
bp=u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/Demon/BP_Demon_Warrior')
c=u.get_default_object(bp)
r={'run_id':uuid.uuid4().hex,'actor':bp.get_path_name(),'clips':[]}
for key in ['character_class','startup_ability','attack_montage']:
 r[key]=str(c.get_editor_property(key))
info=u.load_asset('/Game/BluePrints/AbilitySystem/Data/DA_CharacterClassInfo')
r['class_defaults']=str(info.get_editor_property('character_class_information'))
options=u.AnimPoseEvaluationOptions(evaluation_type=u.AnimDataEvalType.RAW,should_retarget=False)
for name in ['Demon_Attack_L','Demon_Attack_R','Demon_Red_Tailspin','Demon_Tailspin_left']:
 asset=u.load_asset('/Game/Assets/Enemies/Demon/Animations/'+name)
 pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,0,options)
 bones=[str(b) for b in u.AnimPoseExtensions.get_bone_names(pose)]
 tracked=[b for b in bones if any(t in b.lower() for t in ['wrist','hand','tail','root'])]
 frames=u.AnimationLibrary.get_num_frames(asset)
 row={'name':name,'length':asset.get_play_length(),'frames':frames,'bones':bones,'tracked':tracked,'samples':[]}
 for frame in range(frames+1):
  time=min(u.AnimationLibrary.get_time_at_frame(asset,frame),asset.get_play_length())
  pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,time,options)
  sample={'frame':frame,'time':time,'positions':{}}
  for bone in tracked:
   transform=u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.WORLD)
   v=transform.translation;sample['positions'][bone]=[v.x,v.y,v.z]
  row['samples'].append(sample)
 r['clips'].append(row)
(out/('demon-audit-'+r['run_id']+'.json')).write_text(json.dumps(r,indent=2),encoding='utf8')
(out/'demon-audit-latest.json').write_text(json.dumps(r,indent=2),encoding='utf8')
