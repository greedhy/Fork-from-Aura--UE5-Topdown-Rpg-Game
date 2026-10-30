import sys,json
from pathlib import Path
r=Path.cwd();sys.path.insert(0,str(r/'skills/build-ga/scripts'))
from mcp_call import MCP
c=MCP(r,'StoneGolemBuild');p='/Game/BluePrints/Characters/StoneGolem/Animations/ABP_SG_Elite'
g=c.call('blueprint_analyze_graph',{'asset_path':p,'graph_name':'AnimGraph'})['graph_analysis'][0]
nodes=g['nodes'];root=next(n for n in nodes if n['class'].endswith('.AnimGraphNode_Root'));slot=next(n for n in nodes if n['class'].endswith('.AnimGraphNode_Slot'))
for n in nodes:
 if n['class'].endswith('.AnimGraphNode_ControlRig'):
  print(c.call('blueprint_delete_node',{'asset_path':p,'node_guid':n['guid']}))
print(c.call('blueprint_connect_pins',{'asset_path':p,'from_node_guid':slot['guid'],'from_pin_name':'Pose','to_node_guid':root['guid'],'to_pin_name':'Result'}))
print(c.call('blueprint_compile',{'asset_path':p}))
(r/'Saved/GAAuthoring/StoneGolemBuild/elite-abp-graph.json').write_text(json.dumps(c.call('blueprint_analyze_graph',{'asset_path':p}),ensure_ascii=False,indent=2),encoding='utf-8')
