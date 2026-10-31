"""Replace only the three validated roster classes; retain IDs, health and pool rules."""
import unreal as u,json,uuid,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
root=Path(u.Paths.project_dir()).resolve();folder=root/'Saved/GAAuthoring/LegacyMonsterDesign'
for name in ['combat-runtime.json','lifecycle-runtime.json','ai-runtime.json','autonomous-runtime.json']:
 assert json.loads((folder/name).read_text()).get('passed'),name
path='/Game/RoguelikeGeneration/Gameplay/DA_DungeonGameplay';profile=u.load_asset(path)
assert path not in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
backup=folder/('integration-'+uuid.uuid4().hex);backup.mkdir();shutil.copy2(root/'Content/RoguelikeGeneration/Gameplay/DA_DungeonGameplay.uasset',backup/'DA_DungeonGameplay.uasset')
rows=list(profile.get_editor_property('normal_roster'));before=[r.export_text() for r in rows]
keep={k:str(profile.get_editor_property(k)) for k in ['normal_pool_capacity','boss_class','boss_health','elite_class','elite_health']}
replaced=[]
for i,row in enumerate(rows):
 name=str(row.get_editor_property('id'))
 if name not in ['GoblinSpear','GoblinSlinger','Ghoul']:continue
 health=row.get_editor_property('health');pool=row.get_editor_property('pool_eligible')
 row.set_editor_property('enemy_class',u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/LegacyExpansion/BP_'+name));rows[i]=row
 assert row.get_editor_property('health')==health and row.get_editor_property('pool_eligible')==pool;replaced.append(name)
assert len(replaced)==3
profile.set_editor_property('normal_roster',rows);assert u.EditorAssetLibrary.save_loaded_asset(profile,False)
after=[r.export_text() for r in profile.get_editor_property('normal_roster')]
assert len(before)==len(after) and all(str(profile.get_editor_property(k))==v for k,v in keep.items())
for i,r in enumerate(rows):
 if str(r.get_editor_property('id')) not in replaced:assert before[i]==after[i]
(folder/'integration.json').write_text(json.dumps({'passed':True,'before':before,'after':after,'preserved':keep,'backup':str(backup)},indent=2))
