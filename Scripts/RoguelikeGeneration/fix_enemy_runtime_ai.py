"""Enable runtime AI possession for the three actor/GAS room-roster enemies."""
import unreal as u,json,uuid,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
root=Path(u.Paths.project_dir()).resolve();out=root/'Saved/GAAuthoring/EnemyAIRegression';backup=out/uuid.uuid4().hex;backup.mkdir(parents=True)
paths=['/Game/BluePrints/Characters/Goblin/BP_GoblinSpear','/Game/BluePrints/Characters/Goblin/BP_Goblin_Slinshot','/Game/BluePrints/Characters/Ghoul/BP_Ghoul']
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()};report=[]
for p in paths:
 assert p not in dirty,'Unsaved target: '+p
 bp=u.load_asset(p);c=u.get_default_object(bp.generated_class());before=str(c.get_editor_property('auto_possess_ai'))
 assert c.get_editor_property('behavior_tree') and c.get_editor_property('ai_controller_class')
 shutil.copy2((root/'Content'/p.removeprefix('/Game/')).with_suffix('.uasset'),backup/(p.rsplit('/',1)[1]+'.uasset'))
 c.set_editor_property('auto_possess_ai',u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
 u.BlueprintEditorLibrary.compile_blueprint(bp);assert u.EditorAssetLibrary.save_loaded_asset(bp,False)
 assert u.get_default_object(bp.generated_class()).get_editor_property('auto_possess_ai')==u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED
 report.append({'asset':p,'before':before,'after':str(u.get_default_object(bp.generated_class()).get_editor_property('auto_possess_ai'))})
(out/'asset-fix.json').write_text(json.dumps({'backup':str(backup),'changes':report},indent=2))
