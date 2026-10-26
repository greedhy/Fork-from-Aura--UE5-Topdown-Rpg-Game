"""Host Python: copy the player AnimBP and retarget ONLY its player-class references."""
import json, sys, hashlib
from pathlib import Path

root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'skills/build-ga/scripts'))
from mcp_call import MCP
c=MCP(root,'PlayerAnimation')
src='/Game/BluePrints/Characters/Player/ABP_Player'
dst='/Game/PrototypeExtensions/Batch5/ABP_ExtensionPlayer'
old_player='/Game/BluePrints/Characters/Player/BP_Player.BP_Player'
new_player='/Game/PrototypeExtensions/Batch5/BP_ExtensionPlayer.BP_ExtensionPlayer'
out=root/'Saved/GAAuthoring/Batch5/Animation'
out.mkdir(parents=True,exist_ok=True)
original=root/'Content/BluePrints/Characters/Player/ABP_Player.uasset'
before=hashlib.sha256(original.read_bytes()).hexdigest()
export=c.call('blueprint_export_nodes_t3d',{'asset_path':src,'graph_name':'EventGraph','all_nodes':True})
t3d=export['t3d'].replace(old_player,new_player).replace(src+'.ABP_Player',dst+'.ABP_ExtensionPlayer')
assert old_player not in t3d
if not (root/'Content/PrototypeExtensions/Batch5/ABP_ExtensionPlayer.uasset').exists():
    c.call('asset_duplicate',{'source_asset_path':src,'destination_asset_path':dst})
graph=c.call('blueprint_analyze_graph',{'asset_path':dst,'graph_name':'EventGraph'})
nodes=next(g for g in graph['graph_analysis'] if g['name']=='EventGraph')['nodes']
for index,node in enumerate(nodes):
    c.call('blueprint_delete_node',{'asset_path':dst,'node_guid':node['guid']})
    if index%8==0:print('Replacing copied EventGraph',index+1,'/',len(nodes),flush=True)
c.call('blueprint_change_member_variable_type',{'asset_path':dst,'variable_name':'BP_Player_Character',
    'type':'object<'+new_player+'_C>'})
c.call('blueprint_import_nodes_t3d',{'asset_path':dst,'graph_name':'EventGraph','t3d':t3d})
compiled=c.call('blueprint_compile',{'asset_path':dst})
(out/'compile.json').write_text(json.dumps(compiled,indent=2),encoding='utf8')
print('Compile result',json.dumps(compiled),flush=True)
assert hashlib.sha256(original.read_bytes()).hexdigest()==before
(out/'authoring.json').write_text(json.dumps({'original_sha256':before,'original_unchanged':True,'new_anim_blueprint':dst,'event_nodes':len(nodes)},indent=2))
