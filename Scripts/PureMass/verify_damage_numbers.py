"""Two-client Mass floating-number regression: real skill, owner routing, fatal hit and DOT cleanup."""
import unreal as u, json, time
from pathlib import Path
_dn={'phase':'setup','started':time.monotonic(),'started_wall':time.time(),'checks':{},'seen':{}}
_dn_path=Path(u.Paths.project_dir()).resolve()/'Saved/PureMass/DamageNumbers/pie.json'
_dn_path.parent.mkdir(parents=True,exist_ok=True)
_dn_perf=u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
_dn_throttle=_dn_perf.get_editor_property('bThrottleCPUWhenNotForeground')
_dn_perf.set_editor_property('bThrottleCPUWhenNotForeground',False)
def _dn_write():_dn_path.write_text(json.dumps(_dn,indent=2),encoding='utf8')
def _dn_check(name,ok):_dn['checks'][name]=bool(ok);assert ok,name
def _dn_phase(name):_dn.update(phase=name,at=_dn['game_time']);_dn_write()
def _dn_finish(error=None):
    u.unregister_slate_post_tick_callback(_dn_handle)
    _dn_perf.set_editor_property('bThrottleCPUWhenNotForeground',_dn_throttle)
    _dn.update(passed=error is None,error=error);_dn_write()
def _dn_damage(sim,id,amount,source=None,dot=0):
    damage=u.PureMassDamage();damage.set_editor_property('amount',amount)
    if source:
        damage.import_text('(Source="'+source.get_path_name()+'")')
        assert source.get_path_name() in damage.export_text(),'Fixture source import'
    if dot:
        damage.set_editor_property('status_duration',1.0);damage.set_editor_property('damage_per_second',dot)
    return sim.apply_damage(id,damage)
def _dn_tick(dt):
    try:
        if time.monotonic()-_dn['started']>90:raise AssertionError('Timeout '+_dn['phase'])
        pcs=[p for p in u.ObjectIterator(u.PureMassPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_controlled_pawn()]
        if len(pcs)!=3:return
        remote=next(p for p in pcs if not p.is_local_controller())
        client=next(p for p in pcs if p.is_local_controller() and p.get_local_role()==u.NetRole.ROLE_AUTONOMOUS_PROXY)
        host=next(p for p in pcs if p.is_local_controller() and p.get_local_role()==u.NetRole.ROLE_AUTHORITY)
        sw,cw=remote.get_world(),client.get_world()
        sm=next(m for m in u.ObjectIterator(u.PureMassSubsystem) if m.get_world()==sw)
        cm=next(m for m in u.ObjectIterator(u.PureMassSubsystem) if m.get_world()==cw)
        _dn['game_time']=u.GameplayStatics.get_time_seconds(sw)
        age=_dn['game_time']-_dn.get('at',_dn['game_time']);phase=_dn['phase']
        def numbers(pc):
            return [c for c in u.ObjectIterator(u.DamageTextComponent) if c.get_world()==pc.get_world()
                and c.get_owner() and (c.get_owner()==pc or (c.get_owner().get_owner()==pc and c.get_owner().get_class()==u.Actor.static_class()))
                and c in c.get_owner().get_components_by_class(u.DamageTextComponent)]
        texts=numbers(client)
        host_texts=numbers(host)
        for c in texts:
            p=c.get_world_location()
            widget=c.get_user_widget_object()
            if widget and phase=='hit':_dn.setdefault('first_number_at',_dn['game_time'])
            if widget and phase=='hit' and _dn['game_time']-_dn['first_number_at']>.15 and not _dn.get('remote_screenshot_requested'):
                u.SystemLibrary.execute_console_command(cw,'PureMass.QA.CaptureUI 1 mass-remote-hit',client)
                _dn['remote_screenshot_requested']=True
            _dn['seen'][c.get_path_name()]={'phase':phase,'position':[p.x,p.y,p.z],'widget':bool(widget),
                'owner_hidden':bool(c.get_owner().get_editor_property('hidden')),
                'text':str(widget.get_editor_property('Text_Damage').get_text()) if widget else ''}
        if phase=='setup':
            for v in sm.get_snapshots():_dn_damage(sm,v.id,1000000)
            for pc,pos in [(remote,u.Vector(70,740,110)),(host,u.Vector(1500,-1500,110))]:
                pawn=pc.get_controlled_pawn();mv=pawn.get_component_by_class(u.CharacterMovementComponent)
                mv.set_movement_mode(u.MovementMode.MOVE_FLYING);mv.stop_movement_immediately();pawn.set_actor_location(pos,False,True)
            _dn['target']=sm.spawn_monster(u.load_asset('/Game/PureMass/DA_MassQAGoblin'),u.Vector(-10,940,60),'DamageNumberQA')
            u.get_default_object(u.load_class(None,'/Script/UMG.WidgetBlueprintLibrary')).call_method('SetInputMode_GameOnly',(client,False))
            _dn_phase('settle');return
        views=list(sm.get_snapshots());v=next((v for v in views if v.id==_dn['target']),None)
        cv=next((v for v in cm.get_snapshots() if v.id==_dn['target']),None)
        if phase=='settle':
            if age<1 or not cv:return
            _dn['before']=v.health;_dn_phase('press');return
        if phase=='press':
            screen=client.project_world_location_to_screen(cv.location)
            client.set_mouse_location(int(screen.x),int(screen.y))
            lib=u.get_default_object(u.load_class(None,'/Script/Engine.SubsystemBlueprintLibrary'))
            inp=lib.call_method('GetLocalPlayerSubSystemFromPlayerController',(client,u.EnhancedInputLocalPlayerSubsystem.static_class()))
            inp.inject_input_vector_for_action(u.load_asset('/Game/BluePrints/Input/InputActions/IA_Input2'),u.Vector(1,0,0),[],[])
            if age>.1:_dn_phase('hit')
            return
        if phase=='hit':
            _dn_check('remote_hit_not_broadcast_to_host',not host_texts)
            if age<1.2:return
            _dn_check('real_remote_skill_decreased_mass_hp',v and v.health<_dn['before'])
            _dn_check('remote_attacker_received_damage_widget',bool(_dn['seen']))
            _dn_check('screen_widget_owner_is_visible',all(not s['owner_hidden'] for s in _dn['seen'].values()))
            capture=_dn_path.parents[1]/'FeedbackUI/mass-remote-hit.json'
            _dn_check('fresh_remote_screen_capture',capture.exists() and capture.stat().st_mtime>=_dn['started_wall'])
            screen_report=json.loads(capture.read_text(encoding='utf8'))
            _dn_check('remote_number_reached_screen_layer',any(n['added_to_screen'] and not n['owner_hidden'] and n.get('text') for n in screen_report['numbers']))
            _dn_check('widget_created_at_target',all(abs(s['position'][0]+10)<100 and abs(s['position'][1]-940)<100 and s['widget'] for s in _dn['seen'].values()))
            _dn['applied_damage']=_dn['before']-v.health
            # Existing WBP_DamageText rounds its numeric label to whole numbers.
            _dn_check('widget_displays_applied_damage',any(abs(float(s['text'].replace(',',''))-_dn['applied_damage'])<=.51 for s in _dn['seen'].values()))
            _dn['hit_count']=len(_dn['seen']);_dn_phase('fatal');return
        if phase=='fatal':
            _dn_damage(sm,_dn['target'],1000000,remote.get_controlled_pawn());_dn_phase('fatal_wait');return
        if phase=='fatal_wait':
            if age<.5:return
            _dn_check('fatal_entity_removed_both_worlds',not v and not cv)
            _dn_check('fatal_hit_still_has_number',len(_dn['seen'])>_dn['hit_count'])
            _dn['target']=sm.spawn_monster(u.load_asset('/Game/PureMass/DA_MassQAGoblin'),u.Vector(-10,940,60),'DotQA')
            _dn_damage(sm,_dn['target'],0,remote.get_controlled_pawn(),20)
            _dn['before_dot_count']=len(_dn['seen']);_dn_phase('dot');return
        if phase=='dot':
            if age<1.5:return
            _dn_check('dot_reduces_hp',v.health<100000)
            _dn_check('dot_numbers_batched',0<len(_dn['seen'])-_dn['before_dot_count']<=12)
            _dn_phase('cleanup');return
        if phase=='cleanup':
            if age<3:return
            _dn_check('damage_components_cleaned_up',not texts)
            _dn_check('no_enemy_proxy_actors',not u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter))
            _dn['before_host_count']=len(_dn['seen'])
            host.get_controlled_pawn().set_actor_location(u.Vector(70,740,110),False,True)
            _dn_damage(sm,_dn['target'],10,host.get_controlled_pawn());_dn_phase('host_hit');return
        if phase=='host_hit':
            if age<.3:return
            _dn_check('listen_host_sees_own_damage',bool(host_texts))
            u.SystemLibrary.execute_console_command(sw,'Shot SHOWUI filename="'+str(_dn_path.parent/'host-visible.png').replace('\\','/')+'" -nosuffix',host)
            _dn_check('host_hit_not_sent_to_other_client',len(_dn['seen'])==_dn['before_host_count'])
            _dn_phase('host_cleanup');return
        if phase=='host_cleanup':
            if age<3:return
            _dn_check('host_components_cleaned_up',not host_texts)
            _dn_finish()
    except Exception as error:_dn_finish(repr(error));u.log_error('DAMAGE_NUMBER_QA '+repr(error))
_dn_handle=u.register_slate_post_tick_callback(_dn_tick)
_dn_write()
