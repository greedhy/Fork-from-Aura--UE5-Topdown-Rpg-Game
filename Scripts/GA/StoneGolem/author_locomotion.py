import unreal as u
assert not u.EditorLevelLibrary.get_game_world(), 'Stop PIE before authoring locomotion assets'
R='/Game/BluePrints/Characters/StoneGolem/Animations'
for src,name in [('idle1','Idle'),('walkF','Walk'),('jogF','Jog')]:
 p=R+'/AS_SG_'+name
 if not u.EditorAssetLibrary.does_asset_exist(p):
  a=u.EditorAssetLibrary.duplicate_asset('/Game/StoneGolem/Animations/AS_StoneGolem_'+src,p)
  u.EditorAssetLibrary.set_metadata_tag(a,'AuthoringOwner','StoneGolemLocomotionV1')
 else:
  a=u.load_asset(p);assert u.EditorAssetLibrary.get_metadata_tag(a,'AuthoringOwner')=='StoneGolemLocomotionV1'
 a.set_editor_property('enable_root_motion',False);a.set_editor_property('force_root_lock',True);a.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.ZERO)
 assert u.EditorAssetLibrary.save_loaded_asset(a,False)
p=R+'/BS_SG_Locomotion'
if not u.EditorAssetLibrary.does_asset_exist(p):
 f=u.BlendSpaceFactory1D();f.set_editor_property('target_skeleton',a.get_editor_property('skeleton'))
 bs=u.AssetToolsHelpers.get_asset_tools().create_asset('BS_SG_Locomotion',R,u.BlendSpace1D,f)
 u.EditorAssetLibrary.set_metadata_tag(bs,'AuthoringOwner','StoneGolemLocomotionV1');u.EditorAssetLibrary.save_loaded_asset(bs,False)
else:
 bs=u.load_asset(p);assert u.EditorAssetLibrary.get_metadata_tag(bs,'AuthoringOwner')=='StoneGolemLocomotionV1'
bp=u.load_asset(R+'/ABP_SG_Elite')
for cls,key,asset in [(u.AnimGraphNode_SequencePlayer,'sequence',u.load_asset(R+'/AS_SG_Idle')),(u.AnimGraphNode_BlendSpacePlayer,'blend_space',bs)]:
 for n in u.ObjectIterator(cls):
  if bp.get_path_name() in n.get_path_name() and '.Locomotion.' in n.get_path_name():
   data=n.get_editor_property('node');data.set_editor_property(key,asset);n.set_editor_property('node',data)
u.BlueprintEditorLibrary.compile_blueprint(bp);u.EditorAssetLibrary.save_loaded_asset(bp,False)
