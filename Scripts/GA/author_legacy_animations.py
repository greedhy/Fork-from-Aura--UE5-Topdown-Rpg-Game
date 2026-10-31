"""Create isolated Demon attack clips/montages; no gameplay roster changes."""
import unreal as u,json,uuid,hashlib,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world(), 'Stop PIE before authoring'
root=Path(u.Paths.project_dir());out=root/'Saved/GAAuthoring/LegacyMonsterDesign'/uuid.uuid4().hex
out.mkdir(parents=True)
dest='/Game/BluePrints/Characters/LegacyExpansion/Animations'
owner='LegacyMonsterAnimationsV1'
dirty={x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
rows=[]
for short,source in [('Spear','/Game/Assets/Enemies/Goblin/Animations/Spear/Attack_Spear'),('Sling','/Game/Assets/Enemies/Goblin/Animations/Slingshot/Attack_Slingshot'),('GhoulL','/Game/Assets/Enemies/Ghoul/Animations/Attack_L'),('GhoulR','/Game/Assets/Enemies/Ghoul/Animations/Attack_R')]:
 source_file=root/'Content'/(source.removeprefix('/Game/')+'.uasset')
 digest=hashlib.sha256(source_file.read_bytes()).hexdigest()
 source_asset=u.load_asset(source)
 def own(path):
  assert path not in dirty, 'Unsaved target: '+path
  if not u.EditorAssetLibrary.does_asset_exist(path):return None
  asset=u.load_asset(path)
  assert u.EditorAssetLibrary.get_metadata_tag(asset,'AuthoringOwner')==owner,'Unowned target: '+path
  file=root/'Content'/(path.removeprefix('/Game/')+'.uasset')
  shutil.copy2(file,out/file.name)
  return asset
 path=dest+'/AS_Legacy_'+short
 sequence=own(path) or u.EditorAssetLibrary.duplicate_asset(source,path)
 assert sequence
 u.EditorAssetLibrary.set_metadata_tag(sequence,'AuthoringOwner',owner)
 u.EditorAssetLibrary.set_metadata_tag(sequence,'SourceClip',source)
 sequence.set_editor_property('enable_root_motion',False)
 # These clips rotate Root without translating it. Locking Root erases the strike turn.
 sequence.set_editor_property('force_root_lock',False)
 for event in u.AnimationLibrary.get_animation_notify_events(sequence):
  u.AnimationLibrary.remove_animation_notify_events_by_name(sequence,event.get_editor_property('notify_name'))
 assert u.EditorAssetLibrary.save_loaded_asset(sequence,False)
 montage_path=dest+'/AM_Legacy_'+short
 montage=own(montage_path)
 if not montage:
  factory=u.AnimMontageFactory()
  factory.set_editor_property('target_skeleton',sequence.get_editor_property('skeleton'))
  factory.set_editor_property('source_animation',sequence)
  montage=u.AssetToolsHelpers.get_asset_tools().create_asset('AM_Legacy_'+short,dest,u.AnimMontage,factory)
 assert montage
 u.EditorAssetLibrary.set_metadata_tag(montage,'AuthoringOwner',owner)
 for field in ['blend_in','blend_out']:
  blend=montage.get_editor_property(field);blend.set_editor_property('blend_time',.1);montage.set_editor_property(field,blend)
 assert u.EditorAssetLibrary.save_loaded_asset(montage,False)
 tracks=montage.get_editor_property('slot_anim_tracks')
 segments=tracks[0].get_editor_property('anim_track').get_editor_property('anim_segments')
 assert len(tracks)==1 and len(segments)==1
 assert segments[0].get_editor_property('anim_reference')==sequence
 assert abs(sequence.get_play_length()-source_asset.get_play_length())<1.e-5
 assert abs(montage.get_play_length()-sequence.get_play_length())<1.e-5
 assert not u.AnimationLibrary.get_animation_notify_events(sequence)
 assert not u.AnimationLibrary.get_animation_notify_events(montage)
 assert sequence.get_editor_property('skeleton')==source_asset.get_editor_property('skeleton')
 assert hashlib.sha256(source_file.read_bytes()).hexdigest()==digest,'Source changed'
 rows.append({'clip':path,'montage':montage_path,'duration':sequence.get_play_length(),
  'source_sha256':digest,'slot':str(tracks[0].get_editor_property('slot_name')),'source_unchanged':True,
  'frame_interval':u.AnimationLibrary.get_time_at_frame(sequence,1),'no_legacy_notifies':True})
report={'passed':True,'assets':rows,'runtime_verified':False,'backup':str(out)}
(out/'animation-assets.json').write_text(json.dumps(report,indent=2))
(out.parent/'animation-assets.json').write_text(json.dumps(report,indent=2))

for name,source in [('Spear','/Game/BluePrints/Characters/Goblin/ABP_Goblin'),('Sling','/Game/BluePrints/Characters/Goblin/ABP_Goblin_Slinshot'),('Ghoul','/Game/BluePrints/Characters/Ghoul/ABP_Ghoul')]:
 path=dest+'/ABP_Legacy_'+name
 a=own(path) or u.EditorAssetLibrary.duplicate_asset(source,path)
 u.EditorAssetLibrary.set_metadata_tag(a,'AuthoringOwner',owner)
 u.BlueprintEditorLibrary.compile_blueprint(a);assert str(a.get_editor_property('status'))!='BlueprintStatus.BS_ERROR'
 assert u.EditorAssetLibrary.save_loaded_asset(a,False)
