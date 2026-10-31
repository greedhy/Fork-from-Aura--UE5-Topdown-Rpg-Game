"""Reuse the existing tree with a dedicated near-contact MoveTo tolerance."""
import unreal as u,json,uuid,shutil
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
root=Path(u.Paths.project_dir());path='/Game/BluePrints/Characters/Demon/Expansion/BT_DemonWarrior'
assert path not in {x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
tree=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else None
if tree:
 assert u.EditorAssetLibrary.get_metadata_tag(tree,'AuthoringOwner')=='DemonGameplayV1'
 backup=root/'Saved/GAAuthoring/MonsterWave1'/uuid.uuid4().hex;backup.mkdir()
 shutil.copy2(root/'Content/BluePrints/Characters/Demon/Expansion/BT_DemonWarrior.uasset',backup/'BT_DemonWarrior.uasset')
else:tree=u.EditorAssetLibrary.duplicate_asset('/Game/BluePrints/AI/BehaviorTree/BT_EnemyBehaviorTree',path)
assert tree
changed=[]
def walk(node):
 for child in node.get_editor_property('children'):
  task=child.get_editor_property('child_task');composite=child.get_editor_property('child_composite')
  if task and isinstance(task,u.BTTask_MoveTo):
   key=task.get_editor_property('blackboard_key').get_editor_property('selected_key_name')
   if str(key)=='TargetToFollow':
    value=task.get_editor_property('acceptable_radius')
    old=value.get_editor_property('default_value')
    value.set_editor_property('default_value',5.)
    task.set_editor_property('acceptable_radius',value)
    changed.append({'node':task.get_name(),'old':old,'new':value.get_editor_property('default_value')})
  if composite:walk(composite)
walk(tree.get_editor_property('root_node'))
assert changed
u.EditorAssetLibrary.set_metadata_tag(tree,'AuthoringOwner','DemonGameplayV1')
assert u.EditorAssetLibrary.save_loaded_asset(tree,False)
(root/'Saved/GAAuthoring/MonsterWave1/demon-behavior.json').write_text(json.dumps(changed,indent=2))
