"""Append verified Wave 1 types without replacing existing roster or changing pool budget."""
import unreal as u,json,uuid,shutil
from pathlib import Path
root=Path(u.Paths.project_dir());reports=root/'Saved/GAAuthoring/MonsterWave1'
assert not u.EditorLevelLibrary.get_game_world()
for filename in ['demon-combat-probe.json','demon-interrupt-probe.json','demon-pool-runtime.json','demon-boundary-runtime.json','shaman-damage-runtime.json','shaman-summon-runtime.json','shaman-boundary-runtime.json','shaman-interrupt-runtime.json','wave1-ai-runtime.json']:
 assert json.loads((reports/filename).read_text())['passed'],filename
path='/Game/RoguelikeGeneration/Gameplay/DA_DungeonGameplay'
assert path not in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
p=u.load_asset(path);entries=list(p.get_editor_property('normal_roster'))
before=[e.export_text() for e in entries];capacity=p.get_editor_property('normal_pool_capacity')
backup=reports/uuid.uuid4().hex;backup.mkdir();shutil.copy2(root/'Content/RoguelikeGeneration/Gameplay/DA_DungeonGameplay.uasset',backup/'DA_DungeonGameplay.uasset')
for identity,asset in [('DemonWarrior','/Game/BluePrints/Characters/Demon/Expansion/BP_DemonWarrior'),('Shaman','/Game/BluePrints/Characters/Goblin/ShamanExpansion/BP_ShamanExpanded')]:
 cls=u.EditorAssetLibrary.load_blueprint_class(asset);assert cls
 existing=[e for e in entries if str(e.get_editor_property('id'))==identity]
 if existing:
  assert existing[0].get_editor_property('enemy_class')==cls,'Identity already belongs to another class'
  continue
 cdo=u.get_default_object(cls);assert isinstance(cdo,u.TelegraphedEnemyCharacter)
 assert cdo.get_editor_property('auto_possess_ai')==u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED
 entry=u.DungeonNormalEnemy();entry.set_editor_property('id',identity);entry.set_editor_property('enemy_class',cls)
 entry.set_editor_property('health',100.);entry.set_editor_property('pool_eligible',True);entries.append(entry)
p.set_editor_property('normal_roster',entries)
assert p.get_editor_property('normal_pool_capacity')==capacity
assert u.EditorAssetLibrary.save_loaded_asset(p,False)
actual=[e.export_text() for e in p.get_editor_property('normal_roster')]
assert actual[:len(before)]==before
(reports/'roster-integration.json').write_text(json.dumps({'passed':True,'before':before,'after':actual,'pool_capacity_unchanged':capacity,'backup':str(backup),'room_runtime_verified':False},indent=2))
