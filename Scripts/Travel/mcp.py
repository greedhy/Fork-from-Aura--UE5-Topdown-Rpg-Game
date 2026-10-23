"""Small project-bound CLI for portal editor validation (including world locks)."""
import json
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'skills/build-ga/scripts'))
from mcp_call import MCP, check_result

c=MCP(root,'PortalTravel')
name=sys.argv[1]
args=json.loads(sys.argv[2])
request={'name':name,'arguments':args,'_project_path':c.project_path,
         '_instance_uuid':c.instance_uuid,'resource_locks':[{'id':'world:current','mode':'exclusive'}]}
c.record('request',request)
r=check_result(c.rpc('tools/call',request))
j=r.get('structuredContent',{}).get('job_id') or r.get('job_id')
if j: r=c.job(j,25)
c.record('result',r)
print(json.dumps(r,ensure_ascii=True))
