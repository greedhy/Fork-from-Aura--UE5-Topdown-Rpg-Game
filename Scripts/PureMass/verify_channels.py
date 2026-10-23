"""Actual remote input for Beam release and Orbit generation, retargeting and toggle cleanup."""
import unreal as u, json, time
from pathlib import Path
_ch={'phase':'setup','started':time.monotonic(),'checks':{}}
_ch_path=Path(u.Paths.project_dir()).resolve()/'Saved/PureMass/channels.json'
def _ch_write():_ch_path.write_text(json.dumps(_ch,indent=2),encoding='utf8')
def _ch_check(name,ok):_ch['checks'][name]=bool(ok);assert ok,name
def _ch_phase(name):_ch.update(phase=name,at=time.monotonic());_ch_write()
def _ch_finish(error=None):
    u.unregister_slate_post_tick_callback(_ch_handle)
    _ch.update(passed=error is None and all(_ch['checks'].values()),error=error);_ch_write()
def _ch_attr(asc,name,value=None):
    a=asc.get_attribute_set(u.MyAttributeSet);v=a.get_editor_property(name)
    if value is None:return v.get_editor_property('current_value')
    v.import_text('(BaseValue='+str(value)+',CurrentValue='+str(value)+')');a.set_editor_property(name,v)
def _ch_nodes(world,kind):
    return [a for a in u.GameplayStatics.get_all_actors_of_class(world,u.PureMassRuntime) if a.get_editor_property('prototype') and a.get_editor_property('prototype').get_editor_property('kind')==kind]
def _ch_tick(dt):
    try:
        if time.monotonic()-_ch['started']>80:raise AssertionError('Timeout '+_ch['phase'])
        pcs=[p for p in u.ObjectIterator(u.PureMassPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_controlled_pawn()]
        if len(pcs)!=3:return
        server=next(p for p in pcs if not p.is_local_controller())
        client=next(p for p in pcs if p.is_local_controller() and p.get_local_role()==u.NetRole.ROLE_AUTONOMOUS_PROXY)
        host=next(p for p in pcs if p.is_local_controller() and p.get_local_role()==u.NetRole.ROLE_AUTHORITY)
        sw,cw=server.get_world(),client.get_world()
        sm=next(m for m in u.ObjectIterator(u.PureMassSubsystem) if m.get_world()==sw)
        cm=next(m for m in u.ObjectIterator(u.PureMassSubsystem) if m.get_world()==cw)
        sa=server.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent)
        phase=_ch['phase'];age=time.monotonic()-_ch.get('at',_ch['started'])
        if phase=='setup':
            for v in sm.get_snapshots():
                d=u.PureMassDamage();d.set_editor_property('amount',1000000.0);sm.apply_damage(v.id,d)
            pawn=server.get_controlled_pawn();mv=pawn.get_component_by_class(u.CharacterMovementComponent)
            mv.set_movement_mode(u.MovementMode.MOVE_FLYING);mv.stop_movement_immediately()
            pawn.set_actor_location(u.Vector(70,740,110),False,True)
            hp=host.get_controlled_pawn();hp.get_component_by_class(u.CharacterMovementComponent).set_movement_mode(u.MovementMode.MOVE_FLYING)
            hp.set_actor_location(u.Vector(1500,-1500,110),False,True)
            _ch['id']=sm.spawn_monster(u.load_asset('/Game/PureMass/DA_MassQAGoblin'),u.Vector(-10,940,60),'ChannelQA')
            for k,v in [('max_mana',1000),('mana',1000),('mana_regeneration',0)]:_ch_attr(sa,k,v)
            u.get_default_object(u.load_class(None,'/Script/UMG.WidgetBlueprintLibrary')).call_method('SetInputMode_GameOnly',(client,False))
            _ch_phase('settle');return
        v=next((v for v in sm.get_snapshots() if v.id==_ch['id']),None)
        cv=next((v for v in cm.get_snapshots() if v.id==_ch['id']),None)
        if not v or not cv:return
        screen=client.project_world_location_to_screen(cv.location)
        if screen:client.set_mouse_location(int(screen.x),int(screen.y))
        lib=u.get_default_object(u.load_class(None,'/Script/Engine.SubsystemBlueprintLibrary'))
        inp=lib.call_method('GetLocalPlayerSubSystemFromPlayerController',(client,u.EnhancedInputLocalPlayerSubsystem.static_class()))
        def press(name):inp.inject_input_vector_for_action(u.load_asset('/Game/BluePrints/Input/InputActions/'+name),u.Vector(1,0,0),[],[])
        if phase=='settle':
            if age<.7:return
            _ch['beam_health']=v.health;_ch['beam_mana']=_ch_attr(sa,'mana')
            _ch_phase('beam');return
        if phase=='beam':
            press('IA_RMB')
            if age<2.5:return
            _ch_check('beam_runtime_server',len(_ch_nodes(sw,u.AbilityPrototypeKind.BEAM))==1)
            _ch_check('beam_runtime_client',len(_ch_nodes(cw,u.AbilityPrototypeKind.BEAM))==1)
            _ch_check('beam_damages_entity',v.health<_ch['beam_health'])
            _ch_check('beam_spends_mana',_ch_attr(sa,'mana')<_ch['beam_mana'])
            _ch_phase('beam_release');return
        if phase=='beam_release':
            if age<2.0:return
            _ch_check('beam_release_cleans_server',not _ch_nodes(sw,u.AbilityPrototypeKind.BEAM))
            _ch_check('beam_release_cleans_client',not _ch_nodes(cw,u.AbilityPrototypeKind.BEAM))
            _ch['orbit_mana']=_ch_attr(sa,'mana')
            _ch_phase('orbit_on');return
        if phase=='orbit_on':
            press('IA_Input4')
            if age>.12:_ch_phase('orbit_wait')
            return
        if phase=='orbit_wait':
            if age<3.7:return
            sr=_ch_nodes(sw,u.AbilityPrototypeKind.ORBIT);cr=_ch_nodes(cw,u.AbilityPrototypeKind.ORBIT)
            _ch_check('orbit_toggle_started',len(sr)==1 and len(cr)==1)
            _ch_check('orbit_generated_data_bolt',len(sr[0].get_editor_property('orbit_bolts'))>=1)
            _ch_check('orbit_bolt_replicated',len(cr[0].get_editor_property('orbit_bolts'))>=1)
            _ch_check('orbit_initial_and_running_cost',_ch['orbit_mana']-_ch_attr(sa,'mana')>=12)
            _ch['health_before_trigger']=v.health
            _ch_phase('trigger');return
        if phase=='trigger':
            press('IA_Input2')
            if age>.12:_ch_phase('orbit_attack')
            return
        if phase=='orbit_attack':
            if age<1.8:return
            _ch_check('committed_attack_triggers_orbit',_ch['health_before_trigger']-v.health>25.01)
            _ch_phase('orbit_off');return
        if phase=='orbit_off':
            press('IA_Input4')
            if age>.12:_ch_phase('off_wait')
            return
        if phase=='off_wait':
            if age<2:return
            _ch_check('orbit_toggle_cleans_server',not _ch_nodes(sw,u.AbilityPrototypeKind.ORBIT))
            _ch_check('orbit_toggle_cleans_client',not _ch_nodes(cw,u.AbilityPrototypeKind.ORBIT))
            _ch['mana_after_off']=_ch_attr(sa,'mana')
            _ch_phase('off_stable');return
        if phase=='off_stable':
            if age<1.5:return
            _ch_check('off_stops_mana_drain',abs(_ch_attr(sa,'mana')-_ch['mana_after_off'])<.01)
            _ch_finish()
    except Exception as e:_ch_finish(repr(e));u.log_error('PURE_MASS_CHANNELS '+repr(e))
_ch_handle=u.register_slate_post_tick_callback(_ch_tick)
_ch_write()
