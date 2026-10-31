"""Own in-place horizontal tracks; retain the imported vertical jump and local poses."""
import unreal as u,json,uuid,hashlib,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
root=Path(u.Paths.project_dir());folder=root/'Saved/GAAuthoring/ShroomDesign';backup=folder/uuid.uuid4().hex;backup.mkdir(parents=True)
R='/Game/BluePrints/Characters/Shroom/Expansion/Animations';owner='ShroomAnimationsV1'
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def own(path):
 assert path not in dirty
 if not u.EditorAssetLibrary.does_asset_exist(path):return None
 a=u.load_asset(path);assert u.EditorAssetLibrary.get_metadata_tag(a,'AuthoringOwner')==owner
 shutil.copy2(root/'Content'/(path.removeprefix('/Game/')+'.uasset'),backup/(path.rsplit('/',1)[1]+'.uasset'));return a
def duplicate(src,name):
 a=own(R+'/'+name) or u.EditorAssetLibrary.duplicate_asset(src,R+'/'+name)
 assert a;u.EditorAssetLibrary.set_metadata_tag(a,'AuthoringOwner',owner);return a
options=u.AnimPoseEvaluationOptions(evaluation_type=u.AnimDataEvalType.RAW,should_retarget=False,extract_root_motion=False)
rows=[];clips={}
for name,source_name,hold in [('Idle','Idle',0),('Move','Bounce',0),('Slam','Bounce',5),('Spore','Attack',0)]:
 src='/Game/Assets/Enemies/Shroom/Animations/'+source_name;source=u.load_asset(src)
 file=root/'Content/Assets/Enemies/Shroom/Animations'/(source_name+'.uasset');digest=hashlib.sha256(file.read_bytes()).hexdigest()
 a=duplicate(src,'AS_Shroom_'+name);step=u.AnimationLibrary.get_time_at_frame(source,1);frames=round(source.get_play_length()/step)
 poses=[u.AnimPoseExtensions.get_anim_pose_at_time(source,min(f,frames)*step,options) for f in range(frames+hold+1)]
 controller=a.get_editor_property('controller');controller.open_bracket('Shroom horizontal in-place copy')
 try:
  controller.set_number_of_frames(u.FrameNumber(frames+hold))
  for bone in u.AnimPoseExtensions.get_bone_names(poses[0]):
   keys=[u.AnimPoseExtensions.get_bone_pose(p,bone,u.AnimPoseSpaces.LOCAL) for p in poses]
   if str(bone)=='Root':
    start_z=keys[0].translation.z;end_z=keys[frames].translation.z
    for i,k in enumerate(keys):
     baseline=start_z+(end_z-start_z)*min(i,frames)/frames
     k.translation=u.Vector(0,0,k.translation.z-baseline)
   assert controller.set_bone_track_keys(bone,[k.translation for k in keys],[k.rotation for k in keys],[k.scale3d for k in keys])
 finally:controller.close_bracket()
 a.set_editor_property('enable_root_motion',False);a.set_editor_property('force_root_lock',False)
 for e in u.AnimationLibrary.get_animation_notify_events(a):u.AnimationLibrary.remove_animation_notify_events_by_name(a,e.get_editor_property('notify_name'))
 assert u.EditorAssetLibrary.save_loaded_asset(a,False);clips[name]=a
 if name in ['Slam','Spore']:
  montage=own(R+'/AM_Shroom_'+name)
  if not montage:
   f=u.AnimMontageFactory();f.set_editor_property('target_skeleton',a.get_editor_property('skeleton'));f.set_editor_property('source_animation',a)
   montage=u.AssetToolsHelpers.get_asset_tools().create_asset('AM_Shroom_'+name,R,u.AnimMontage,f)
  u.EditorAssetLibrary.set_metadata_tag(montage,'AuthoringOwner',owner)
  for key in ['blend_in','blend_out']:
   b=montage.get_editor_property(key);b.set_editor_property('blend_time',.08);montage.set_editor_property(key,b)
  assert u.EditorAssetLibrary.save_loaded_asset(montage,False)
 assert hashlib.sha256(file.read_bytes()).hexdigest()==digest
 rows.append({'name':name,'duration':a.get_play_length(),'source_unchanged':True,'source_hash':digest})
(folder/'animation-assets.json').write_text(json.dumps({'clips':rows,'backup':str(backup)},indent=2))
bs_path=R+'/BS_Shroom_Locomotion';bs=u.load_asset(bs_path) if u.EditorAssetLibrary.does_asset_exist(bs_path) else None
if bs and bs.get_editor_property('skeleton')!=clips['Idle'].get_editor_property('skeleton'):
 assert u.EditorAssetLibrary.get_metadata_tag(bs,'AuthoringOwner')==owner
 assert not (root/'Content'/(bs_path.removeprefix('/Game/')+'.uasset')).exists(),'Do not replace a saved incompatible blendspace'
 assert u.EditorAssetLibrary.delete_asset(bs_path);bs=None
if not bs:
 f=u.BlendSpaceFactory1D();f.set_editor_property('target_skeleton',clips['Idle'].get_editor_property('skeleton'))
 bs=u.AssetToolsHelpers.get_asset_tools().create_asset('BS_Shroom_Locomotion',R,u.BlendSpace1D,f)
assert bs;u.EditorAssetLibrary.set_metadata_tag(bs,'AuthoringOwner',owner)
params=bs.get_editor_property('blend_parameters');axis=params[0];axis.set_editor_property('max',180.);params[0]=axis;bs.set_editor_property('blend_parameters',params)
assert bs.get_editor_property('blend_parameters')[0].get_editor_property('max')==180.
samples=[u.BlendSample(),u.BlendSample()]
for i,s in enumerate(samples):
 s.set_editor_property('animation',clips['Idle' if i==0 else 'Move'])
 s.set_editor_property('sample_value',u.Vector(0 if i==0 else 180,0,0))
bs.set_editor_property('sample_data',samples)
assert u.EditorAssetLibrary.save_loaded_asset(bs,False)
bp=duplicate('/Game/BluePrints/Characters/StoneGolem/Animations/ABP_SG_Elite','ABP_Shroom_Enemy');bp.set_editor_property('target_skeleton',clips['Idle'].get_editor_property('skeleton'))
for cls,key,asset in [(u.AnimGraphNode_SequencePlayer,'sequence',clips['Idle']),(u.AnimGraphNode_BlendSpacePlayer,'blend_space',bs)]:
 for node in u.ObjectIterator(cls):
  if bp.get_path_name() in node.get_path_name():
   v=node.get_editor_property('node');v.set_editor_property(key,asset);node.set_editor_property('node',v)
u.BlueprintEditorLibrary.compile_blueprint(bp);assert str(bp.get_editor_property('status'))!='BlueprintStatus.BS_ERROR'
assert u.EditorAssetLibrary.save_loaded_asset(bp,False)
(folder/'animation-assets.json').write_text(json.dumps({'clips':rows,'backup':str(backup),'anim_blueprint':str(bp.get_editor_property('status')),'blendspace_samples':[s.export_text() for s in bs.get_editor_property('sample_data')]},indent=2))
