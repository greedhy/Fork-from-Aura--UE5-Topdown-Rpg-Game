"""Two connected PIE players. Real remote Enhanced Input + cursor TargetData.
Authority learning/health fixtures only; never changes content or user saves.
"""
import unreal as u, time, json, uuid
from pathlib import Path

_p = {'run':uuid.uuid4().hex, 'phase':'setup', 'index':0, 'checks':{}, 'samples':[], 'started':time.monotonic()}
_p_names = ['Homing','Piercing','Chain']
_p_out = Path(u.Paths.project_dir()).resolve()/'Saved/GAAuthoring/Compositions'

def _p_write():
    for name in ['latest-batch2-network',_p['run']]: (_p_out/(name+'.json')).write_text(json.dumps(_p,indent=2),encoding='utf8')
def _p_finish(error=None):
    u.unregister_slate_post_tick_callback(_p_handle)
    _p.update(error=error,passed=error is None and all(_p['checks'].values()))
    _p_write()
def _p_tag(name):
    t=u.GameplayTag();t.import_text('(TagName="'+name+'")');return t
def _p_phase(name):
    _p.update(phase=name,at=time.monotonic());_p_write()
def _p_attr(asc,name,value=None):
    attrs=asc.get_attribute_set(u.MyAttributeSet)
    field=attrs.get_editor_property(name)
    if value is None:return field.get_editor_property('current_value')
    field.import_text('(BaseValue='+str(value)+',CurrentValue='+str(value)+')');attrs.set_editor_property(name,field)
def _p_asc(pc):return pc.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent)
def _p_ability(asc,name):
    tags=u.GameplayTagContainer();tags.import_text('(GameplayTags=((TagName="Abilities.Prototype.'+name+'")))')
    handles=asc.find_all_abilities_with_tags(tags,True)
    assert len(handles)==1,(name,len(handles))
    return u.AbilitySystemLibrary.get_gameplay_ability_from_spec_handle(asc,handles[0])[0]
def _p_runtime(world):return u.GameplayStatics.get_all_actors_of_class(world,u.PrototypeRuntime)
def _p_check(name,ok):
    _p['checks'][name]=bool(ok);assert ok,name

def _p_tick(dt):
    try:
        if time.monotonic()-_p['started']>110:raise AssertionError('Timeout '+_p['phase'])
        pcs=[pc for pc in u.ObjectIterator(u.MyPlayerController) if 'UEDPIE_' in pc.get_path_name() and pc.get_controlled_pawn()]
        if len(pcs)!=3:return
        server=next(pc for pc in pcs if not pc.is_local_controller() and pc.get_local_role()==u.NetRole.ROLE_AUTHORITY)
        client=next(pc for pc in pcs if pc.is_local_controller() and pc.get_local_role()==u.NetRole.ROLE_AUTONOMOUS_PROXY)
        sa,ca=_p_asc(server),_p_asc(client)
        sw,cw=server.get_world(),client.get_world()
        enemy=next((e for e in u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter) if 'PrototypeQA' in [str(t) for t in e.tags]),None)
        if _p['phase']=='setup':
            room_report=json.loads((Path(u.Paths.project_dir())/'Saved/Rooms/PIE/latest.json').read_text())
            if not room_report.get('passed'):return
            for e in u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter):e.destroy_actor()
            cls=u.load_class(None,'/Game/BluePrints/Characters/Goblin/BP_Goblin.BP_Goblin_C')
            assert cls,'QA enemy class failed to load'
            # The spawn corridor has a wall at +X; keep the target in the visible aisle.
            transform=u.Transform(location=server.get_controlled_pawn().get_actor_location()+u.Vector(-80,200,0))
            enemy=u.get_default_object(u.GameplayStatics).call_method('BeginDeferredActorSpawnFromClass',(sw,cls,transform,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,server.get_controlled_pawn(),u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            u.get_default_object(u.GameplayStatics).call_method('FinishSpawningActor',(enemy,transform,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            enemy.tags=list(enemy.tags)+['PrototypeQA']
            enemy.spawn_default_controller()
            feet=server.get_controlled_pawn().get_actor_location().z-server.get_controlled_pawn().get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height()
            pos=enemy.get_actor_location();pos.z=feet+enemy.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height()+1
            enemy.set_actor_location(pos,False,True)
            enemy.get_component_by_class(u.CharacterMovementComponent).set_movement_mode(u.MovementMode.MOVE_WALKING)
            if enemy.get_controller():
                brain=enemy.get_controller().get_component_by_class(u.BrainComponent)
                if brain:brain.stop_logic('Prototype QA fixture')
            server.get_controlled_pawn().call_method('AddToSpellPoints',(20,))
            for name in _p_names:
                _p_ability(sa,name)
                sa.call_method('ServerSpendSpellPoint',(_p_tag('Abilities.Prototype.'+name),))
            for attr,value in [('max_mana',1000.0),('mana',1000.0),('mana_regeneration',0.0)]:_p_attr(sa,attr,value)
            ea=enemy.get_component_by_class(u.MyAbilitySystemComponent)
            for attr,value in [('max_health',10000.0),('health',10000.0),('block_chance',0.0),('armor',0.0)]:_p_attr(ea,attr,value)
            u.get_default_object(u.load_class(None,'/Script/UMG.WidgetBlueprintLibrary')).call_method('SetInputMode_GameOnly',(client,False))
            _p_phase('equip');return
        assert enemy,'Test target missing'
        ea=enemy.get_component_by_class(u.MyAbilitySystemComponent)
        if _p['phase']=='cleanup':
            if time.monotonic()-_p['at']<1.5:return
            _p_check('all_nodes_removed_server',not _p_runtime(sw))
            _p_check('all_nodes_removed_client',not _p_runtime(cw))
            _p_finish();return
        name=_p_names[_p['index']]
        age=time.monotonic()-_p['at']
        if _p['phase']=='equip':
            if name=='Chain':
                for number in (1,2):
                    cls=u.load_class(None,'/Game/BluePrints/Characters/Goblin/BP_Goblin.BP_Goblin_C')
                    transform=u.Transform(location=enemy.get_actor_location()+u.Vector(0,110*number,0))
                    extra=u.get_default_object(u.GameplayStatics).call_method('BeginDeferredActorSpawnFromClass',(sw,cls,transform,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,server.get_controlled_pawn(),u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
                    u.get_default_object(u.GameplayStatics).call_method('FinishSpawningActor',(extra,transform,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
                    extra.tags=list(extra.tags)+['ChainQA'];extra.spawn_default_controller()
                    if extra.get_controller():
                        brain=extra.get_controller().get_component_by_class(u.BrainComponent)
                        if brain:brain.stop_logic('Chain QA fixture')
                    for attr,value in [('max_health',10000.0),('health',10000.0),('block_chance',0.0),('armor',0.0)]:_p_attr(extra.get_component_by_class(u.MyAbilitySystemComponent),attr,value)
            sa.call_method('ServerEquipAbility',(_p_tag('Abilities.Prototype.'+name),_p_tag('InputTag.4')))
            _p.update(beam_ends=[],before_mana=_p_attr(sa,'mana'),before_health=_p_attr(ea,'health'),server_peak=0,client_peak=0,orbit_peak=0)
            _p_phase('settle');return
        if _p['phase']=='settle':
            if age<.6:return
            _p_check(name+'_replicated_catalog',bool(_p_ability(ca,name)))
            _p_phase('press');return
        lib=u.get_default_object(u.load_class(None,'/Script/Engine.SubsystemBlueprintLibrary'))
        inputs=lib.call_method('GetLocalPlayerSubSystemFromPlayerController',(client,u.EnhancedInputLocalPlayerSubsystem.static_class()))
        # Keep the cursor over the remote world's replica of the same target.
        ce=next((e for e in u.GameplayStatics.get_all_actors_of_class(cw,u.EnemyCharacter) if e.get_name()==enemy.get_name()),None)
        if ce:
            screen=client.project_world_location_to_screen(ce.get_actor_location()+u.Vector(0,0,-20))
            if screen:client.set_mouse_location(int(screen.x),int(screen.y))
        if _p['phase']=='press':
            inputs.inject_input_vector_for_action(u.load_asset('/Game/BluePrints/Input/InputActions/IA_Input4'),u.Vector(1,0,0),[],[])
            if age>(4.0 if name=='Beam' else .2):
                _p_phase('observe');return
        elif _p['phase']=='off':
            inputs.inject_input_vector_for_action(u.load_asset('/Game/BluePrints/Input/InputActions/IA_Input4'),u.Vector(1,0,0),[],[])
            if age>.2:_p_phase('off_wait')
        _p['server_peak']=max(_p['server_peak'],len(_p_runtime(sw)))
        _p['client_peak']=max(_p['client_peak'],len(_p_runtime(cw)))
        if name=='Chain':
            for actor in _p_runtime(cw):
                point=actor.get_editor_property('beam_end')
                end=[round(point.x,2),round(point.y,2),round(point.z,2)]
                if end not in _p['beam_ends']:_p['beam_ends'].append(end)
        if _p['phase']=='observe':
            if age<2.0:return
            _p_check(name+'_authority_cast',_p['server_peak']>0)
            _p_check(name+'_replicated_actor',_p['client_peak']>0)
            config=u.get_default_object(_p_ability(sa,name).get_class()).get_editor_property('prototype')
            _p_check(name+'_paid_once',abs((_p['before_mana']-_p_attr(sa,'mana'))-config.get_editor_property('mana_cost'))<.01)
            _p_check(name+'_damaged_enemy',_p_attr(ea,'health')<_p['before_health'])
            _p_check(name+'_ability_ended',not u.AbilitySystemLibrary.is_gameplay_ability_active(_p_ability(sa,name)))
            if name=='Chain':
                extras=[a for a in u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter) if 'ChainQA' in [str(t) for t in a.tags]]
                _p_check('chain_hits_three_enemies',len(extras)==2 and all(_p_attr(a.get_component_by_class(u.MyAbilitySystemComponent),'health')<10000 for a in extras))
                _p_check('chain_endpoint_replicated',len(_p['beam_ends'])>=2)
            _p['samples'].append({'name':name,'server_peak':_p['server_peak'],'client_peak':_p['client_peak'],'mana_spent':_p['before_mana']-_p_attr(sa,'mana'),'damage':_p['before_health']-_p_attr(ea,'health')})
            for actor in _p_runtime(sw):actor.cancel_cast()
            _p['index']+=1;_p_phase('cleanup' if _p['index']==len(_p_names) else 'equip')
    except Exception as error:_p_finish(repr(error))

_p_handle=u.register_slate_post_tick_callback(_p_tick)
