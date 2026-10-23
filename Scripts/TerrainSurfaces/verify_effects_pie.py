"""Listen-server PIE: real floor queries, server GEs, owning/observing client FX.
Only temporary PIE actors and attributes are changed; no saves or input config edits.
"""
import unreal as u
import json, time, uuid
from pathlib import Path
_terrain_qa={'run_id':uuid.uuid4().hex,'phase':'setup','kind':0,'wall':time.monotonic(),'checks':{},'damage':[]}
_terrain_report=Path(u.Paths.project_dir()).resolve()/'Saved/TerrainSurfaces/effect_pie_validation.json'
_terrain_names=['Lava','Frost','Toxic','Vines']
_terrain_types=[u.TerrainSurfaceType.LAVA,u.TerrainSurfaceType.FROST,u.TerrainSurfaceType.TOXIC,u.TerrainSurfaceType.VINES]

def _terrain_check(name,ok):
    _terrain_qa['checks'][name]=bool(ok)
    assert ok,name

def _terrain_pcs():
    return [p for p in u.ObjectIterator(u.MyPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_controlled_pawn()]

def _terrain_asc(pawn):
    state=pawn.get_editor_property('player_state')
    return state.get_component_by_class(u.MyAbilitySystemComponent) if state else pawn.get_component_by_class(u.MyAbilitySystemComponent)

def _terrain_hp(pawn):
    return _terrain_asc(pawn).get_attribute_set(u.MyAttributeSet).get_editor_property('health').get_editor_property('current_value')

def _terrain_setattr(pawn,name,value):
    attrs=_terrain_asc(pawn).get_attribute_set(u.MyAttributeSet)
    data=attrs.get_editor_property(name)
    data.import_text(f'(BaseValue={float(value)},CurrentValue={float(value)})')
    attrs.set_editor_property(name,data)

def _terrain_status(pawn): return pawn.get_component_by_class(u.TerrainStatusComponent)

def _terrain_fx(pawn,name):
    return [c for c in pawn.get_components_by_class(u.NiagaraComponent) if c.get_asset() and c.get_asset().get_name()=='NS_'+name+'_Status' and c.is_active()]

def _terrain_finish(error=None):
    u.unregister_slate_post_tick_callback(_terrain_callback)
    _terrain_qa.update(passed=not error and bool(_terrain_qa['checks']) and all(_terrain_qa['checks'].values()),error=error)
    _terrain_report.write_text(json.dumps(_terrain_qa,indent=2))
    u.log('TERRAIN_PIE_RESULT '+json.dumps(_terrain_qa))

def _terrain_phase(phase,now):
    _terrain_qa.update(phase=phase,at=now)
    _terrain_report.write_text(json.dumps(_terrain_qa,indent=2))

def _terrain_place(pawn,x,y,z):
    half=pawn.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height()
    pawn.teleport(u.Vector(x,y,z+half+2),u.Rotator())
    move=pawn.get_component_by_class(u.CharacterMovementComponent)
    move.stop_movement_immediately(); move.set_movement_mode(u.MovementMode.MOVE_WALKING)

def _terrain_tick(dt):
    try:
        q=_terrain_qa
        if time.monotonic()-q['wall']>100: raise AssertionError('Timeout in '+q['phase'])
        pcs=_terrain_pcs()
        servers=sorted([p for p in pcs if p.get_local_role()==u.NetRole.ROLE_AUTHORITY],key=lambda p:p.get_editor_property('player_state').get_editor_property('travel_player_slot'))
        client=next((p for p in pcs if p.get_local_role()==u.NetRole.ROLE_AUTONOMOUS_PROXY and p.is_local_controller()),None)
        if len(servers)!=2 or not client: return
        sw=servers[0].get_world(); cw=client.get_world()
        now=u.GameplayStatics.get_time_seconds(sw)
        server_pawns=[p.get_controlled_pawn() for p in servers]
        client_pawns=list(u.GameplayStatics.get_all_actors_of_class(cw,u.PlayerCharacter))
        if len(client_pawns)!=2: return
        surfaces=u.GameplayStatics.get_all_actors_of_class(sw,u.TerrainSurface)
        if q['phase']=='setup':
            for old in u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter):
                if old.actor_has_tag('TerrainQADummy'): old.destroy_actor()
            for p in server_pawns: _terrain_status(p).clear_terrain_effects()
            _terrain_check('four_gameplay_surfaces',len(surfaces)==4)
            _terrain_check('both_players_have_terrain_component',all(_terrain_status(p) for p in server_pawns))
            # A real enemy Blueprint with AI disabled by deferring its construction.
            cls=u.load_class(None,'/Game/BluePrints/Characters/Goblin/BP_Goblin.BP_Goblin_C')
            transform=u.Transform(location=u.Vector(0,-500,120))
            lib=u.get_default_object(u.GameplayStatics)
            enemy=lib.call_method('BeginDeferredActorSpawnFromClass',(sw,cls,transform,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            enemy.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
            lib.call_method('FinishSpawningActor',(enemy,transform,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            enemy.tags=list(enemy.tags)+[u.Name('TerrainQADummy')]
            for p in server_pawns+[enemy]:
                _terrain_setattr(p,'max_health',1000); _terrain_setattr(p,'health',1000); _terrain_setattr(p,'health_regeneration',0)
            _terrain_phase('enter',now)
            return
        enemy=next(p for p in u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter) if p.actor_has_tag('TerrainQADummy'))
        name=_terrain_names[q['kind']]; kind=_terrain_types[q['kind']]
        surface=next(s for s in surfaces if s.get_editor_property('config').get_editor_property('surface_type')==kind)
        targets=server_pawns+[enemy]
        if q['phase']=='enter':
            pos=surface.get_actor_location()
            for i,p in enumerate(server_pawns): _terrain_place(p,pos.x+(-90 if i==0 else 90),pos.y-70,pos.z)
            for p in client_pawns:
                slot=p.get_editor_property('player_state').get_editor_property('travel_player_slot')
                _terrain_place(p,pos.x+(-90 if slot==0 else 90),pos.y-70,pos.z)
            _terrain_place(enemy,pos.x,pos.y+100,pos.z)
            q['baseline']=[_terrain_hp(p) for p in targets]
            _terrain_phase('active',now)
        elif q['phase']=='active' and now-q['at']>.7:
            _terrain_check(name+'_server_players_and_enemy_affected',all(_terrain_status(p).is_terrain_status_active(kind) for p in targets))
            _terrain_check(name+'_owner_and_observer_state_replicated',all(_terrain_status(p).is_terrain_status_active(kind) for p in client_pawns))
            _terrain_check(name+'_owner_and_observer_vfx',all(len(_terrain_fx(p,name))==1 for p in client_pawns))
            _terrain_check(name+'_server_vfx',all(len(_terrain_fx(p,name))==1 for p in targets))
            if name=='Frost':
                _terrain_check('frost_remote_movement_multiplier',all(abs(_terrain_status(p).get_terrain_movement_multiplier()-.6)<.001 for p in targets+client_pawns))
                _terrain_check('frost_remote_walk_speed',all(abs(p.get_component_by_class(u.CharacterMovementComponent).max_walk_speed-360)<.1 for p in server_pawns+client_pawns))
            if name=='Vines':
                _terrain_check('vines_stops_movement_on_server_and_client',all(p.get_component_by_class(u.CharacterMovementComponent).max_walk_speed==0 for p in targets+client_pawns))
            _terrain_phase('hold',now)
        elif q['phase']=='hold' and now-q['at']>1.6:
            if name in ['Lava','Toxic']:
                damage=[round(q['baseline'][i]-_terrain_hp(p),3) for i,p in enumerate(targets)]
                q['damage'].append({'kind':name,'elapsed':2.3,'amounts':damage})
                expected=16 if name=='Lava' else 8
                _terrain_check(name+'_exactly_two_authority_ticks',all(abs(x-expected)<.1 for x in damage))
                _terrain_check(name+'_owner_health_replicated',abs(_terrain_hp(client.get_controlled_pawn())-_terrain_hp(server_pawns[1]))<.1)
            if name=='Vines':
                _terrain_check('vines_releases_without_leaving',all(not _terrain_status(p).is_terrain_status_active(kind) for p in targets+client_pawns))
            for i,p in enumerate(server_pawns): _terrain_place(p,-100+i*200,-750,0)
            for p in client_pawns:
                slot=p.get_editor_property('player_state').get_editor_property('travel_player_slot'); _terrain_place(p,-100+slot*200,-750,0)
            _terrain_place(enemy,0,-500,0)
            _terrain_phase('exit',now)
        elif q['phase']=='exit' and now-q['at']>3.7:
            _terrain_check(name+'_server_cleanup',all(not _terrain_status(p).is_terrain_status_active(kind) for p in targets))
            _terrain_check(name+'_remote_cleanup',all(not _terrain_status(p).is_terrain_status_active(kind) and len(_terrain_fx(p,name))==0 for p in client_pawns))
            q['kind']+=1
            if q['kind']==4: _terrain_finish(); return
            _terrain_phase('enter',now)
    except Exception as error:
        _terrain_finish(repr(error))

_terrain_callback=u.register_slate_post_tick_callback(_terrain_tick)
