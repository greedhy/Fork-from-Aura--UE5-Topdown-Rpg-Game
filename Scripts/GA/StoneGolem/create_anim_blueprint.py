import unreal as u
source='/Game/StoneGolem/Demo/ABP_StoneGolem';target='/Game/BluePrints/Characters/StoneGolem/Animations/ABP_SG_Elite'
assert not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'Unsaved content: inspect before authoring'
if u.EditorAssetLibrary.does_asset_exist(target):
 a=u.load_asset(target);assert u.EditorAssetLibrary.get_metadata_tag(a,'AuthoringOwner')=='StoneGolemAnimBPV1'
else:
 a=u.EditorAssetLibrary.duplicate_asset(source,target);assert a
 u.EditorAssetLibrary.set_metadata_tag(a,'AuthoringOwner','StoneGolemAnimBPV1');u.EditorAssetLibrary.save_loaded_asset(a,False)
