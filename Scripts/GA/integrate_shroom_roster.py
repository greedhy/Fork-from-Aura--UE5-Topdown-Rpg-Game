"""Add validated Shroom without replacing other roster entries or boss tuning."""
import unreal as u,json,uuid,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
root=Path(u.Paths.project_dir());folder=root/'Saved/GAAuthoring/ShroomDesign'
for name in ['combat-runtime.json','lifecycle-runtime.json','ai-runtime.json']:
 assert json.loads((folder/name).read_text()).get('passed'),name
p='/Game/RoguelikeGeneration/Gameplay/DA_DungeonGameplay';a=u.load_asset(p)
assert p not in {x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
backup=folder/('integration-'+uuid.uuid4().hex);backup.mkdir()
shutil.copy2(root/'Content/RoguelikeGeneration/Gameplay/DA_DungeonGameplay.uasset',backup/'DA_DungeonGameplay.uasset')
rows=list(a.get_editor_property('normal_roster'));before=[r.export_text() for r in rows]
keep={k:str(a.get_editor_property(k)) for k in ['normal_pool_capacity','boss_class','boss_health','normal_health','elite_health']}
if not any(str(r.get_editor_property('id'))=='Shroom' for r in rows):
 r=u.DungeonNormalEnemy();r.import_text('(Id="Shroom",EnemyClass="/Game/BluePrints/Characters/Shroom/Expansion/BP_Shroom.BP_Shroom_C",Health=100.000000,bPoolEligible=True)');rows.append(r)
a.set_editor_property('normal_roster',rows);assert u.EditorAssetLibrary.save_loaded_asset(a,False)
after=[r.export_text() for r in a.get_editor_property('normal_roster')]
assert all(v in after for v in before)
assert all(str(a.get_editor_property(k))==v for k,v in keep.items())
(folder/'integration.json').write_text(json.dumps({'before':before,'after':after,'preserved':keep,'backup':str(backup),'passed':True},indent=2))
