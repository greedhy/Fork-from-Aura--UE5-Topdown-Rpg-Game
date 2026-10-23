"""Project-bound editor bridge for room authoring and validation."""
import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'skills/build-ga/scripts'))
from mcp_call import MCP,check_result
c=MCP(root,'LanRooms')
name=sys.argv[1]
args=json.loads(Path(sys.argv[3]).read_text(encoding='utf-8-sig') if len(sys.argv)>3 and sys.argv[2]=='--file' else sys.argv[2] if len(sys.argv)>2 else '{}')
request={'name':name,'arguments':args,'_project_path':c.project_path,'_instance_uuid':c.instance_uuid,'resource_locks':[{'id':'world:current','mode':'exclusive'}]}
c.record('request',request)
r=check_result(c.rpc('tools/call',request))
j=r.get('structuredContent',{}).get('job_id') or r.get('job_id')
if j:r=c.job(j,25)
c.record('result',r)
print(json.dumps(r,ensure_ascii=True))
