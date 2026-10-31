"""Own the burst system before visual tuning; never edit the imported Free Spells source."""
import unreal as u,json,shutil,uuid
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
root=Path(u.Paths.project_dir());base='/Game/BluePrints/Characters/Goblin/ShamanExpansion'
path=base+'/Effects/NS_Sh_Burst';config_path=base+'/DA_Sh_Burst'
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
assert path not in dirty and config_path not in dirty
backup=root/'Saved/GAAuthoring/MonsterWave1'/uuid.uuid4().hex;backup.mkdir()
shutil.copy2(root/'Content'/(config_path.removeprefix('/Game/')+'.uasset'),backup/'DA_Sh_Burst.uasset')
if u.EditorAssetLibrary.does_asset_exist(path):
 fx=u.load_asset(path);assert u.EditorAssetLibrary.get_metadata_tag(fx,'AuthoringOwner')=='ShamanExpansionV1'
else:
 fx=u.EditorAssetLibrary.duplicate_asset('/Game/Free_Spells/VFX_Niagara/NS_Free_Spells_Explosion',path)
 assert fx;u.EditorAssetLibrary.set_metadata_tag(fx,'AuthoringOwner','ShamanExpansionV1')
assert u.EditorAssetLibrary.save_loaded_asset(fx,False)
config=u.load_asset(config_path);t=config.get_editor_property('tuning');t.set_editor_property('impact_effect',fx)
config.set_editor_property('tuning',t);assert u.EditorAssetLibrary.save_loaded_asset(config,False)
(root/'Saved/GAAuthoring/MonsterWave1/shaman-effect.json').write_text(json.dumps({'asset':fx.get_path_name(),'source_unchanged':True,'backup':str(backup)}))
