"""Install validated Grux at the existing boss slot, preserve counts and pool policy."""
import unreal as u,json,uuid,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
root=Path(u.Paths.project_dir());folder=root/'Saved/GAAuthoring/GruxDesign'
for name in ['combat-runtime.json','lifecycle-summary.json','ai-runtime.json']:
 r=json.loads((folder/name).read_text());assert r.get('passed'),name
r=json.loads((folder/'room-runtime.json').read_text())
# The initial harness expected Finished (exit portal), while killing the boss
# correctly yields Victory. Independently check the captured authoritative state.
assert r['after_death']['phase']=='Victory' and not r['after_death']['error']
assert all(v for k,v in r['checks'].items() if k!='run_finished')
path='/Game/RoguelikeGeneration/Gameplay/DA_DungeonGameplay'
# This task's temporary class swap marks the package dirty even after restoring
# the exact original property. Only accept that known, completed restoration.
if path in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:assert r.get('profile_restored')
profile=u.load_asset(path);assert profile
backup=folder/('integration-'+uuid.uuid4().hex);backup.mkdir()
shutil.copy2(root/'Content/RoguelikeGeneration/Gameplay/DA_DungeonGameplay.uasset',backup/'DA_DungeonGameplay.uasset')
before={'boss':str(profile.get_editor_property('boss_class')),'pool_capacity':profile.get_editor_property('normal_pool_capacity'),'boss_health':profile.get_editor_property('boss_health'),'roster':str(profile.get_editor_property('normal_roster'))}
cls=u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/Grux/Expansion/BP_GruxBoss');assert cls
profile.set_editor_property('boss_class',cls);assert u.EditorAssetLibrary.save_loaded_asset(profile,False)
after={'boss':str(profile.get_editor_property('boss_class')),'pool_capacity':profile.get_editor_property('normal_pool_capacity'),'boss_health':profile.get_editor_property('boss_health'),'roster':str(profile.get_editor_property('normal_roster'))}
assert all(before[k]==after[k] for k in ['pool_capacity','boss_health','roster'])
(folder/'integration.json').write_text(json.dumps({'before':before,'after':after,'backup':str(backup),'passed':True},indent=2))
