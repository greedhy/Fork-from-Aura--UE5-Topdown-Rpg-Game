import unreal as u,json
from pathlib import Path
tree=u.load_asset('/Game/BluePrints/AI/BehaviorTree/BT_EnemyBehaviorTree');rows=[]
def describe(node):
 d={'path':node.get_path_name(),'class':node.get_class().get_path_name()}
 for key in ['node_name','acceptable_radius','blackboard_key','float_value','int_value','operation_type','arithmetic_operation','notify_observer','flow_abort_mode']:
  try:d[key]=str(node.get_editor_property(key))
  except Exception:pass
 rows.append(d)
def walk(node):
 describe(node)
 for s in node.get_editor_property('services'):describe(s)
 for child in node.get_editor_property('children'):
  for d in child.get_editor_property('decorators'):describe(d)
  t=child.get_editor_property('child_task');c=child.get_editor_property('child_composite')
  if t:describe(t)
  if c:walk(c)
walk(tree.get_editor_property('root_node'))
(Path(u.Paths.project_dir())/'Saved/GAAuthoring/GruxDesign/behavior-audit.json').write_text(json.dumps(rows,indent=2))
