"""Own isolated spell montages; remove duplicate gameplay events, preserve root rotation."""
import unreal as u,json,uuid,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
root=Path(u.Paths.project_dir());backup=root/'Saved/GAAuthoring/MonsterWave1'/uuid.uuid4().hex;backup.mkdir()
R='/Game/BluePrints/Characters/Goblin/ShamanExpansion/Animations';owner='ShamanExpansionV1'
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
result=[]
def existing(path):
 assert path not in dirty
 if not u.EditorAssetLibrary.does_asset_exist(path):return None
 a=u.load_asset(path);assert u.EditorAssetLibrary.get_metadata_tag(a,'AuthoringOwner')==owner
 shutil.copy2(root/'Content'/(path.removeprefix('/Game/')+'.uasset'),backup/(path.rsplit('/',1)[-1]+'.uasset'))
 return a
for name,source in [('Cast','Shaman_Attack'),('Burst','Shaman_Summon'),('Summon','Shaman_Summon')]:
 src=u.load_asset('/Game/Assets/Enemies/Shaman/Animations/'+source)
 path=R+'/AS_Sh_'+name;a=existing(path) or u.EditorAssetLibrary.duplicate_asset(src.get_path_name().split('.')[0],path)
 u.EditorAssetLibrary.set_metadata_tag(a,'AuthoringOwner',owner)
 a.set_editor_property('enable_root_motion',False);a.set_editor_property('force_root_lock',False)
 opts=u.AnimPoseEvaluationOptions(evaluation_type=u.AnimDataEvalType.RAW,should_retarget=False,extract_root_motion=False)
 pose=u.AnimPoseExtensions.get_anim_pose_at_time(src,0,opts);bone=str(u.AnimPoseExtensions.get_bone_names(pose)[0])
 frames=u.AnimationLibrary.get_num_frames(src)
 keys=[u.AnimPoseExtensions.get_bone_pose(u.AnimPoseExtensions.get_anim_pose_at_time(src,u.AnimationLibrary.get_time_at_frame(src,f),opts),bone,u.AnimPoseSpaces.LOCAL) for f in range(frames+1)]
 drift=max((k.translation-keys[0].translation).length() for k in keys)
 if drift>.001:
  controller=a.get_controller();controller.open_bracket('Stationary Shaman cast',False)
  assert controller.set_bone_track_keys(bone,[keys[0].translation]*len(keys),[k.rotation for k in keys],[k.scale3d for k in keys])
  controller.close_bracket(False)
 for event in u.AnimationLibrary.get_animation_notify_events(a):u.AnimationLibrary.remove_animation_notify_events_by_name(a,event.get_editor_property('notify_name'))
 assert u.EditorAssetLibrary.save_loaded_asset(a,False)
 path=R+'/AM_Sh_'+name;m=existing(path)
 if not m:
  factory=u.AnimMontageFactory();factory.set_editor_property('target_skeleton',a.get_editor_property('skeleton'));factory.set_editor_property('source_animation',a)
  m=u.AssetToolsHelpers.get_asset_tools().create_asset('AM_Sh_'+name,R,u.AnimMontage,factory)
 u.EditorAssetLibrary.set_metadata_tag(m,'AuthoringOwner',owner)
 for key in ['blend_in','blend_out']:
  blend=m.get_editor_property(key);blend.set_editor_property('blend_time',.1);m.set_editor_property(key,blend)
 assert u.EditorAssetLibrary.save_loaded_asset(m,False)
 result.append({'name':name,'source':src.get_path_name(),'length':a.get_play_length(),'root':bone,'source_root_drift':drift,'frames':frames})
(root/'Saved/GAAuthoring/MonsterWave1/shaman-animations.json').write_text(json.dumps(result,indent=2))
