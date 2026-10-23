"""End-to-end verification against real rendered standalone game processes."""
import json,time,sys,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[2];run=sys.argv[1]
assert run.replace('_','').isalnum()
folder=root/'Saved/Rooms/Network'/run
report={'run_id':run,'checks':{},'evidence':[],'passed':False}
def save(): (folder/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def state(role):
    try:
        raw=(folder/(role+'-state.json')).read_bytes()
        return json.loads(raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'))
    except (OSError,ValueError):return {}
def wait(role,predicate,label,timeout=40):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        s=state(role)
        if s and predicate(s):
            report['checks'][label]=True;report['evidence'].append({'check':label,'state':s});save();print('PASS '+label,flush=True);return s
        time.sleep(.25)
    raise AssertionError(label+': '+json.dumps(state(role),ensure_ascii=False))
def send(role,op,value='',field='',allow_error=False):
    p=folder/(role+'-command.json');old=json.loads(p.read_text()) if p.exists() else {}
    c={'id':old.get('id',0)+1,'op':op,'value':value,'field':field}
    temp=p.with_suffix('.tmp');temp.write_text(json.dumps(c));temp.replace(p)
    until=time.monotonic()+20
    while time.monotonic()<until:
        s=state(role)
        if s.get('last_id',-1)>=c['id']:
            if s.get('command_error') and not allow_error:raise AssertionError(s)
            return s
        time.sleep(.25)
    if op!='quit':raise TimeoutError(c)
def click(role,name,**kw):return send(role,'click',name,**kw)
def join(role,password):
    send(role,'input',password,'JoinPassword');click(role,'JoinRoomButton')
def open_join(role):click(role,'MultiplayerButton');click(role,'OpenJoinButton')
def snapshot(role,name):
    source=folder/(role+'-ui.png');before=source.stat().st_mtime_ns if source.exists() else 0
    send(role,'screenshot');until=time.monotonic()+20
    while time.monotonic()<until:
        if source.exists() and source.stat().st_mtime_ns>before:
            time.sleep(.5);out=root/'SourceArt/Rooms';out.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,out/(name+'.png'));return
        time.sleep(.25)
    raise TimeoutError('Screenshot '+name)
try:
    for role in ['host','guest','solo']:
        wait(role,lambda s:s['world']=='LoadMenu',role+'_loaded_save_page',60)
        send(role,'select','Room'+role.title())
        wait(role,lambda s:s['world']=='LoadMenu' and s['page']==0,role+'_save_opens_mode_without_travel')
    snapshot('host','ModeSelection')
    click('solo','ReturnToSaveButton');wait('solo',lambda s:not s['widget'],'back_returns_to_save_selection')
    send('solo','select','RoomSolo');click('solo','SinglePlayerButton')
    wait('solo',lambda s:s['world']=='Dungeon' and s['net_mode']==0 and s['has_pawn'] and not s['widget'],'single_player_default_map')
    click('host','MultiplayerButton');click('host','CreateRoomButton')
    h=wait('host',lambda s:s['world']=='RoomLobby' and s['is_owner'] and len(s['password'])==6,'host_creates_room_and_password')
    password=h['password'];open_join('guest')
    join('guest','bad');wait('guest',lambda s:bool(s['error']) and not s['busy'],'invalid_password_shows_dialog')
    click('guest','DismissRoomErrorButton');join('guest','Wrong999')
    wait('guest',lambda s:bool(s['error']) and not s['busy'],'wrong_password_search_is_retryable')
    snapshot('guest','JoinFailure');click('guest','DismissRoomErrorButton');join('guest',password)
    wait('guest',lambda s:s['world']=='RoomLobby' and s['players']==['RoomHost','RoomGuest'],'correct_password_joins_real_server')
    wait('host',lambda s:s['players']==['RoomHost','RoomGuest'],'host_roster_replication')
    denied=click('guest','StartRoomButton',allow_error=True);assert denied['command_error']
    report['checks']['guest_start_control_disabled']=True;save()
    snapshot('host','Lobby')
    send('solo','direct_join','127.0.0.1:7777?RoomPassword='+password)
    wait('solo',lambda s:s['world']=='LoadMenu' and '已满' in s['error'],'server_rejects_full_room')
    send('host','input','Room9876','NewRoomPassword');click('host','ChangePasswordButton')
    wait('guest',lambda s:s['password']=='Room9876','password_update_replicates')
    click('guest','LeaveRoomButton');wait('guest',lambda s:s['world']=='LoadMenu' and s['page']==0,'member_leave_returns_to_mode')
    wait('host',lambda s:s['players']==['RoomHost'],'departed_member_removed')
    send('solo','direct_join','127.0.0.1:7777?RoomPassword=Wrong999')
    wait('solo',lambda s:s['world']=='LoadMenu' and '密码错误' in s['error'],'server_rechecks_password_on_direct_connection')
    open_join('guest');join('guest',password)
    wait('guest',lambda s:bool(s['error']) and not s['busy'],'old_password_no_longer_matches')
    click('guest','DismissRoomErrorButton');join('guest','Room9876')
    wait('guest',lambda s:s['world']=='RoomLobby' and len(s['players'])==2,'new_password_allows_rejoin')
    click('host','LeaveRoomButton');wait('host',lambda s:s['world']=='LoadMenu' and s['page']==0,'host_can_close_room')
    wait('guest',lambda s:s['world']=='LoadMenu' and bool(s['error']) and s['page']==0,'host_departure_returns_guest_with_dialog')
    click('guest','DismissRoomErrorButton');click('host','MultiplayerButton');click('host','CreateRoomButton')
    h=wait('host',lambda s:s['world']=='RoomLobby' and bool(s['password']),'host_can_recreate_after_close')
    open_join('guest');join('guest',h['password'])
    wait('guest',lambda s:s['world']=='RoomLobby' and len(s['players'])==2,'guest_can_join_recreated_room')
    click('host','StartRoomButton')
    for role in ['host','guest']:
        wait(role,lambda s:s['world']=='Dungeon' and s['has_pawn'] and not s['widget'] and s['flow']=='Idle' and len(s['players'])==2,role+'_arrives_default_map_without_lobby_ui',60)
    report['passed']=all(report['checks'].values());save();print('NETWORK_VALIDATION_PASSED '+str(len(report['checks'])),flush=True)
except Exception as e:
    report['error']=repr(e);save();print('NETWORK_VALIDATION_FAILED '+repr(e),flush=True);raise
finally:
    for role in ['guest','host','solo']:
        try:send(role,'quit')
        except Exception:pass
