"""Build the editor-generated interpolation data after native sample authoring."""
import unreal as u,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
p='/Game/BluePrints/Characters/StoneGolem/Animations/BS_SG_Locomotion'
a=u.load_asset(p)
assert u.EditorAssetLibrary.get_metadata_tag(a,'AuthoringOwner')=='StoneGolemLocomotionV1'
assert p not in {x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
root=Path(u.Paths.project_dir()).resolve()
backup=root/'Saved/GAAuthoring/StoneGolemMovementFix/BS_SG_Locomotion-before-resample.uasset'
if not backup.exists():shutil.copy2(root/'Content/BluePrints/Characters/StoneGolem/Animations/BS_SG_Locomotion.uasset',backup)
editors=u.get_editor_subsystem(u.AssetEditorSubsystem)
# SBlendSpaceEditor::Construct calls ResampleData; AddSample alone does not.
assert editors.open_editor_for_assets([a])
assert u.EditorAssetLibrary.save_loaded_asset(a,False)
