"""Reuse tested generic velocity/state/slot structure with Grux-only animation assets."""
import unreal as u,json,uuid,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
root=Path(u.Paths.project_dir());out=root/'Saved/GAAuthoring/GruxDesign'/uuid.uuid4().hex;out.mkdir(parents=True)
base='/Game/ParagonGrux/Characters/Heroes/Grux';dest='/Game/BluePrints/Characters/Grux/Expansion/Animations';owner='GruxAnimBPV1'
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def duplicate(src,name):
 path=dest+'/'+name;assert path not in dirty
 if u.EditorAssetLibrary.does_asset_exist(path):
  a=u.load_asset(path);assert u.EditorAssetLibrary.get_metadata_tag(a,'AuthoringOwner')==owner
  shutil.copy2(root/'Content'/(path.removeprefix('/Game/')+'.uasset'),out/(name+'.uasset'))
 else:a=u.EditorAssetLibrary.duplicate_asset(src,path)
 assert a;u.EditorAssetLibrary.set_metadata_tag(a,'AuthoringOwner',owner);return a
idle=duplicate(base+'/Animations/Idle','AS_Grux_Idle')
bs=duplicate(base+'/Animations/Blendspaces/Idle2Run','BS_Grux_Locomotion')
bp=duplicate('/Game/BluePrints/Characters/StoneGolem/Animations/ABP_SG_Elite','ABP_Grux_Enemy')
bp.set_editor_property('target_skeleton',idle.get_editor_property('skeleton'))
nodes=[]
for cls,key,asset in [(u.AnimGraphNode_SequencePlayer,'sequence',idle),(u.AnimGraphNode_BlendSpacePlayer,'blend_space',bs)]:
 for n in u.ObjectIterator(cls):
  if bp.get_path_name() in n.get_path_name():
   data=n.get_editor_property('node');data.set_editor_property(key,asset);n.set_editor_property('node',data);nodes.append(n.get_path_name())
u.BlueprintEditorLibrary.compile_blueprint(bp)
assert str(bp.get_editor_property('status'))!='BlueprintStatus.BS_ERROR'
for a in [idle,bs,bp]:assert u.EditorAssetLibrary.save_loaded_asset(a,False)
report={'status':str(bp.get_editor_property('status')),'nodes':nodes,'blendspace_samples':[x.export_text() for x in bs.get_editor_property('sample_data')],'blueprint':bp.get_path_name()}
(out.parent/'anim-blueprint.json').write_text(json.dumps(report,indent=2))
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
 if isinstance(a,u.Character) and a.actor_has_tag('GruxAnimationProbe'):a.get_component_by_class(u.SkeletalMeshComponent).set_anim_instance_class(bp.generated_class())
