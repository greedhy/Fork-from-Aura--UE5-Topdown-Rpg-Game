"""Drive opt-in development game processes, never editor/user saves."""
import argparse,json,time
from pathlib import Path
root=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('run');parser.add_argument('role');parser.add_argument('op',nargs='?',default='state');parser.add_argument('value',nargs='?',default='');parser.add_argument('--field',default='');parser.add_argument('--wait',type=float,default=8)
a=parser.parse_args();folder=root/'Saved/Rooms/Network'/a.run
assert all(s and s.replace('_','').isalnum() for s in [a.run,a.role])
def read():
    try:
        raw=(folder/(a.role+'-state.json')).read_bytes()
        return json.loads(raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'))
    except (OSError,ValueError):return {}
if a.op=='state':print(json.dumps(read(),ensure_ascii=False));raise SystemExit
p=folder/(a.role+'-command.json')
old=json.loads(p.read_text()) if p.exists() else {}
command={'id':old.get('id',0)+1,'op':a.op,'value':a.value,'field':a.field}
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(command),encoding='utf-8');tmp.replace(p)
end=time.monotonic()+a.wait
while time.monotonic()<end:
    state=read()
    if state.get('last_id',-1)>=command['id']:
        print(json.dumps(state,ensure_ascii=False));raise SystemExit(1 if state.get('command_error') else 0)
    time.sleep(.25)
raise TimeoutError(str(command))
