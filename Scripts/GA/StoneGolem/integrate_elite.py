"""Integrate the tested elite without changing roster, health or pool allocation."""
import unreal as u,json,uuid,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
root=Path(u.Paths.project_dir());out=root/'Saved/GAAuthoring/StoneGolemBuild'
for file in ['combat-probe.json','runtime-regression.json','ai-runtime.json']:
 assert json.loads((out/file).read_text())['passed'],file
native=json.loads((out/'ReviewRegression/index.json').read_text(encoding='utf-8-sig'))
assert len(native['tests'])==10 and all(t['state']=='Success' for t in native['tests'])
p='/Game/RoguelikeGeneration/Gameplay/DA_DungeonGameplay'
assert p not in {x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()},'Profile has unsaved changes'
a=u.load_asset(p);keys=['normal_roster','normal_class','normal_health','normal_pool_capacity','normal_corpse_seconds','elite_health','boss_class','boss_health']
before={k:str(a.get_editor_property(k)) for k in keys}
old=a.get_editor_property('elite_class');new=u.load_class(None,'/Game/BluePrints/Characters/StoneGolem/BP_StoneGolemElite.BP_StoneGolemElite_C');assert new
backup=out/('profile-'+uuid.uuid4().hex+'.uasset');shutil.copy2(root/'Content/RoguelikeGeneration/Gameplay/DA_DungeonGameplay.uasset',backup)
a.set_editor_property('elite_class',new)
assert u.EditorAssetLibrary.save_loaded_asset(a,False)
assert a.get_editor_property('elite_class')==new
assert before=={k:str(a.get_editor_property(k)) for k in keys}
(out/'integration.json').write_text(json.dumps({'profile':p,'old_elite':old.get_path_name() if old else None,'elite':new.get_path_name(),'backup':str(backup),'preserved':before,'passed':True},indent=2))
