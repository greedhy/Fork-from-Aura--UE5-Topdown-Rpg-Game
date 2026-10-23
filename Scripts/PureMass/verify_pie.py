"""Two-client test: no enemy Actors; instancing, replication, remote input, removal and authority."""
import unreal as u, json, time, uuid
from pathlib import Path
_pm={'run':uuid.uuid4().hex,'phase':'setup','started':time.monotonic(),'checks':{}}
_pm_path=Path(u.Paths.project_dir()).resolve()/'Saved/PureMass/pie.json'
def _pm_write(): _pm_path.write_text(json.dumps(_pm,indent=2),encoding='utf8')
def _pm_check(name,ok):
    _pm['checks'][name]=bool(ok)
    assert ok,name
def _pm_phase(phase): _pm.update(phase=phase,at=time.monotonic());_pm_write()
def _pm_finish(error=None):
    u.unregister_slate_post_tick_callback(_pm_handle)
    _pm.update(passed=error is None and all(_pm['checks'].values()),error=error);_pm_write()
def _pm_attr(asc,name,value=None):
    attrs=asc.get_attribute_set(u.MyAttributeSet);field=attrs.get_editor_property(name)
    if value is None:return field.get_editor_property('current_value')
    field.import_text('(BaseValue='+str(value)+',CurrentValue='+str(value)+')');attrs.set_editor_property(name,field)
def _pm_damage(amount,source=None):
    d=u.PureMassDamage();d.set_editor_property('amount',amount)
    if source:d.set_editor_property('source',source)
    return d
def _pm_overlays(world):
    return [w.get_path_name() for w in u.ObjectIterator(u.MyUserWidget) if w.get_world()==world and w.get_name().startswith('WBP_Overlay_C') and w.is_in_viewport()]
def _pm_tick(dt):
    try:
        if time.monotonic()-_pm['started']>80:raise AssertionError('Timeout '+_pm['phase'])
        pcs=[p for p in u.ObjectIterator(u.PureMassPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_controlled_pawn()]
        if len(pcs)!=3:return
        remote=next(p for p in pcs if not p.is_local_controller())
        client=next(p for p in pcs if p.is_local_controller() and p.get_local_role()==u.NetRole.ROLE_AUTONOMOUS_PROXY)
        host=next(p for p in pcs if p.is_local_controller() and p.get_local_role()==u.NetRole.ROLE_AUTHORITY)
        sw,cw=remote.get_world(),client.get_world()
        sm=next(m for m in u.ObjectIterator(u.PureMassSubsystem) if m.get_world()==sw)
        cm=next(m for m in u.ObjectIterator(u.PureMassSubsystem) if m.get_world()==cw)
        sc=u.GameplayStatics.get_all_actors_of_class(sw,u.PureMassCrowd)
        cc=u.GameplayStatics.get_all_actors_of_class(cw,u.PureMassCrowd)
        if len(sc)!=1 or len(cc)!=1:return
        sa=remote.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent)
        phase=_pm['phase'];age=time.monotonic()-_pm.get('at',_pm['started'])
        snapshots=list(sm.get_snapshots())
        if phase=='setup':
            if not snapshots or cc[0].get_rendered_instance_count()!=len(snapshots):return
            _pm_check('server_zero_enemy_actors',not u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter))
            _pm_check('client_zero_enemy_actors',not u.GameplayStatics.get_all_actors_of_class(cw,u.EnemyCharacter))
            _pm_check('one_shared_crowd_per_world',len(sc)==1 and len(cc)==1)
            _pm_check('server_rendered_all_entities',sc[0].get_rendered_instance_count()==len(snapshots))
            _pm_check('one_component_per_type',sc[0].get_render_component_count()==1 and cc[0].get_render_component_count()==1)
            _pm_check('client_has_independent_tracks',cc[0].get_animation_track_count()==len(snapshots))
            _pm_check('client_query_registry',len(cm.get_snapshots())==len(snapshots))
            _pm['initial']={str(v.id):[v.location.x,v.location.y,v.location.z] for v in snapshots}
            for pc in [remote,host]:
                pawn=pc.get_controlled_pawn()
                movement=pawn.get_component_by_class(u.CharacterMovementComponent)
                movement.set_movement_mode(u.MovementMode.MOVE_FLYING);movement.stop_movement_immediately()
                pawn.set_actor_location(u.Vector(70,740,pawn.get_actor_location().z),False,True)
            _pm_phase('motion');return
        if phase=='motion':
            if age<2:return
            _pm_check('mass_navigation_moves_entities',any((v.location-u.Vector(*_pm['initial'][str(v.id)])).length()>1 for v in snapshots if str(v.id) in _pm['initial']))
            for v in snapshots:sm.apply_damage(v.id,_pm_damage(1000000))
            _pm_phase('remove');return
        if phase=='remove':
            if age<.7:return
            _pm_check('dead_entities_removed_server',not sm.get_snapshots())
            _pm_check('death_replication_removes_instances',cc[0].get_rendered_instance_count()==0 and cc[0].get_animation_track_count()==0)
            _pm_check('death_removes_client_targets',not cm.get_snapshots())
            player=remote.get_controlled_pawn()
            hp=host.get_controlled_pawn();hp.get_component_by_class(u.CharacterMovementComponent).set_movement_mode(u.MovementMode.MOVE_FLYING)
            hp.set_actor_location(player.get_actor_location()+u.Vector(1500,-1500,100),False,True)
            entity=sm.spawn_monster(u.load_asset('/Game/PureMass/DA_MassQAGoblin'),player.get_actor_location()+u.Vector(-80,200,0),'NetworkQA')
            _pm_check('spawn_entity_has_valid_id',entity>0)
            _pm['target']=entity
            for key,value in [('max_mana',1000),('mana',1000),('mana_regeneration',0)]:_pm_attr(sa,key,value)
            u.get_default_object(u.load_class(None,'/Script/UMG.WidgetBlueprintLibrary')).call_method('SetInputMode_GameOnly',(client,False))
            _pm_phase('target');return
        entity=_pm['target']
        view=next((v for v in snapshots if v.id==entity),None)
        cv=next((v for v in cm.get_snapshots() if v.id==entity),None)
        if phase=='target':
            if not cv:return
            _pm_check('client_cannot_damage',cm.apply_damage(entity,_pm_damage(1000))==0)
            _pm['before_health']=view.health;_pm['before_mana']=_pm_attr(sa,'mana')
            _pm_phase('press');return
        if phase=='press':
            screen=client.project_world_location_to_screen(cv.location)
            if screen:client.set_mouse_location(int(screen.x),int(screen.y))
            lib=u.get_default_object(u.load_class(None,'/Script/Engine.SubsystemBlueprintLibrary'))
            inputs=lib.call_method('GetLocalPlayerSubSystemFromPlayerController',(client,u.EnhancedInputLocalPlayerSubsystem.static_class()))
            inputs.inject_input_vector_for_action(u.load_asset('/Game/BluePrints/Input/InputActions/IA_Input2'),u.Vector(1,0,0),[],[])
            if age>.15:_pm_phase('hit')
            return
        if phase=='hit':
            if age<1.4:return
            _pm_check('remote_ga_hits_entity',view.health<_pm['before_health'])
            proto=u.get_default_object(u.load_class(None,'/Game/PureMass/Abilities/GA_Prototype_Homing.GA_Prototype_Homing_C')).get_editor_property('prototype')
            _pm_check('remote_ga_cost_once',abs(_pm['before_mana']-_pm_attr(sa,'mana')-proto.get_editor_property('mana_cost'))<.01)
            _pm_check('health_snapshot_replicated',abs(cv.health-view.health)<.01)
            _pm_check('still_no_enemy_actors',not u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter))
            _pm['damage']=_pm['before_health']-view.health
            sm.apply_damage(entity,_pm_damage(1000000))
            _pm_phase('final_remove');return
        if phase=='final_remove':
            if age<.5:return
            _pm_check('combat_death_removed_client',not cm.get_snapshots() and cc[0].get_rendered_instance_count()==0)
            _pm['old_pawn']=remote.get_controlled_pawn().get_path_name()
            _pm['old_overlay']=_pm_overlays(cw)
            _pm_check('one_overlay_before_death',len(_pm['old_overlay'])==1)
            params=u.DamageEffectParams()
            params.set_editor_property('world_context_object',remote.get_controlled_pawn())
            params.set_editor_property('source_ability_system_component',host.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent))
            params.set_editor_property('target_ability_system_component',sa)
            params.set_editor_property('damage_gameplay_effect_class',u.load_class(None,'/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage.GE_Damage_C'))
            params.set_editor_property('base_damage',1000000.0)
            tag=u.GameplayTag();tag.import_text('(TagName="Damage.Physics")');params.set_editor_property('damage_type',tag)
            params.set_editor_property('debuff_chance',0.0)
            u.MyAbilitySystemLibrary.apply_damage_effect(params)
            _pm_phase('respawn');return
        if phase=='respawn':
            if age<7:return
            _pm_check('respawn_stays_in_mass_map','L_PureMassDungeon' in sw.get_path_name())
            _pm_check('new_mass_pawn_after_death',remote.get_controlled_pawn().get_path_name()!=_pm['old_pawn'] and isinstance(remote.get_controlled_pawn(),u.PureMassPlayerCharacter))
            _pm_check('respawn_reuses_single_overlay',_pm_overlays(cw)==_pm['old_overlay'])
            _pm_check('respawn_has_positive_health',_pm_attr(sa,'health')>0)
            _pm_finish()
    except Exception as e:
        _pm_finish(repr(e));u.log_error('PURE_MASS_QA '+repr(e))
_pm_handle=u.register_slate_post_tick_callback(_pm_tick)
_pm_write()
