"""Two-client real Enhanced Input against mixed targets; runtime-only fixture, no asset changes.
Run in /Game/PureMass/Maps/L_PureMassDungeon with a listen server and one client.
"""
import unreal as u, json, time
from pathlib import Path

_mix = {'phase':'setup', 'started':time.monotonic(), 'checks':{}, 'samples':{}}
_mix_path = Path(u.Paths.project_dir()).resolve()/'Saved/PureMass/MixedCombat/pie.json'
_mix_path.parent.mkdir(parents=True, exist_ok=True)
_mix_perf = u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
_mix_throttle = _mix_perf.get_editor_property('bThrottleCPUWhenNotForeground')
_mix_perf.set_editor_property('bThrottleCPUWhenNotForeground',False)

def _mix_write(): _mix_path.write_text(json.dumps(_mix,indent=2),encoding='utf8')
def _mix_check(name, ok):
    _mix['checks'][name]=bool(ok)
    assert ok,name
def _mix_phase(name):
    _mix.update(phase=name,at=_mix.get('game_time',0)); _mix_write()
def _mix_finish(error=None):
    u.unregister_slate_post_tick_callback(_mix_handle)
    _mix_perf.set_editor_property('bThrottleCPUWhenNotForeground',_mix_throttle)
    _mix.update(passed=error is None and all(_mix['checks'].values()),error=error); _mix_write()
def _mix_attr(asc,name,value=None):
    attrs=asc.get_attribute_set(u.MyAttributeSet);field=attrs.get_editor_property(name)
    if value is None:return field.get_editor_property('current_value')
    field.import_text('(BaseValue='+str(value)+',CurrentValue='+str(value)+')');attrs.set_editor_property(name,field)
def _mix_nodes(world,kind):
    return [a for a in u.GameplayStatics.get_all_actors_of_class(world,u.PureMassRuntime)
        if a.get_editor_property('prototype') and a.get_editor_property('prototype').get_editor_property('kind')==kind]

def _mix_tick(dt):
    try:
        if time.monotonic()-_mix['started']>180:raise AssertionError('Timeout '+_mix['phase'])
        pcs=[p for p in u.ObjectIterator(u.PureMassPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_controlled_pawn()]
        if len(pcs)!=3:return
        server=next(p for p in pcs if not p.is_local_controller())
        client=next(p for p in pcs if p.is_local_controller() and p.get_local_role()==u.NetRole.ROLE_AUTONOMOUS_PROXY)
        host=next(p for p in pcs if p.is_local_controller() and p.get_local_role()==u.NetRole.ROLE_AUTHORITY)
        sw,cw=server.get_world(),client.get_world()
        sm=next(m for m in u.ObjectIterator(u.PureMassSubsystem) if m.get_world()==sw)
        cm=next(m for m in u.ObjectIterator(u.PureMassSubsystem) if m.get_world()==cw)
        sa=server.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent)
        _mix['game_time']=u.GameplayStatics.get_time_seconds(sw)
        phase=_mix['phase'];age=_mix['game_time']-_mix.get('at',_mix['game_time'])
        if phase=='setup':
            for v in sm.get_snapshots():
                damage=u.PureMassDamage();damage.set_editor_property('amount',1000000.0);sm.apply_damage(v.id,damage)
            for pc,pos in [(server,u.Vector(70,740,110)),(host,u.Vector(1500,-1500,110))]:
                pawn=pc.get_controlled_pawn();mv=pawn.get_component_by_class(u.CharacterMovementComponent)
                mv.set_movement_mode(u.MovementMode.MOVE_FLYING);mv.stop_movement_immediately();pawn.set_actor_location(pos,False,True)
            _mix['entity']=sm.spawn_monster(u.load_asset('/Game/PureMass/DA_MassQAGoblin'),u.Vector(-10,940,60),'MixedQA')
            actor_class=u.load_class(None,'/Game/BluePrints/Characters/Goblin/BP_GoblinSpear.BP_GoblinSpear_C')
            transform=u.Transform(location=u.Vector(180,940,60))
            statics=u.get_default_object(u.GameplayStatics.static_class())
            actor=statics.call_method('BeginDeferredActorSpawnFromClass',(sw,actor_class,transform,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            actor.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
            statics.call_method('FinishSpawningActor',(actor,transform,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
            actor.get_component_by_class(u.CharacterMovementComponent).disable_movement()
            ea=actor.get_component_by_class(u.MyAbilitySystemComponent)
            for key,value in [('max_health',100000),('health',100000),('health_regeneration',0),('block_chance',0)]:_mix_attr(ea,key,value)
            _mix['actor']=actor.get_name()
            for key,value in [('max_mana',1000),('mana',1000),('mana_regeneration',0),('critical_hit_chance',0)]:_mix_attr(sa,key,value)
            u.get_default_object(u.load_class(None,'/Script/UMG.WidgetBlueprintLibrary')).call_method('SetInputMode_GameOnly',(client,False))
            _mix_phase('settle');return
        actors=u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter)
        actor=next((a for a in actors if a.get_name()==_mix['actor']),None)
        ca=next((a for a in u.GameplayStatics.get_all_actors_of_class(cw,u.EnemyCharacter) if a.get_name()==_mix['actor']),None)
        v=next((v for v in sm.get_snapshots() if v.id==_mix['entity']),None)
        cv=next((v for v in cm.get_snapshots() if v.id==_mix['entity']),None)
        if not actor or not ca or not v or not cv:return
        ea=actor.get_component_by_class(u.MyAbilitySystemComponent)
        cea=ca.get_component_by_class(u.MyAbilitySystemComponent)
        sample=lambda:{'actor':_mix_attr(ea,'health'),'mass':v.health,'mana':_mix_attr(sa,'mana')}
        lib=u.get_default_object(u.load_class(None,'/Script/Engine.SubsystemBlueprintLibrary'))
        inp=lib.call_method('GetLocalPlayerSubSystemFromPlayerController',(client,u.EnhancedInputLocalPlayerSubsystem.static_class()))
        target=cv.location if phase.startswith('mass_') else ca.get_actor_location()
        screen=client.project_world_location_to_screen(target)
        if screen:client.set_mouse_location(int(screen.x),int(screen.y))
        def press(name):inp.inject_input_vector_for_action(u.load_asset('/Game/BluePrints/Input/InputActions/'+name),u.Vector(1,0,0),[],[])
        def begin(name):_mix['before']=sample();_mix_phase(name)
        def cost_once(kind):
            proto=u.get_default_object(u.load_class(None,'/Game/PureMass/Abilities/GA_Prototype_'+kind+'.GA_Prototype_'+kind+'_C')).get_editor_property('prototype')
            _mix_check(phase+'_cost_once',abs(_mix['before']['mana']-_mix_attr(sa,'mana')-proto.get_editor_property('mana_cost'))<.01)
        def synced():
            _mix_check(phase+'_actor_health_replicated',abs(_mix_attr(cea,'health')-_mix_attr(ea,'health'))<.01)
            _mix_check(phase+'_mass_health_replicated',abs(cv.health-v.health)<.01)
        if phase=='settle':
            if age<1.5:return
            _mix_check('one_actor_enemy_per_world',len(actors)==1 and len(u.GameplayStatics.get_all_actors_of_class(cw,u.EnemyCharacter))==1)
            _mix_check('mass_monster_has_no_actor',len(sm.get_snapshots())==1 and len(cm.get_snapshots())==1)
            begin('actor_press');return
        presses={'actor_press':'IA_Input2','mass_press':'IA_Input2','burst_press':'IA_Input1','chain_press':'IA_Input3','lmb_press':'IA_LMB'}
        if phase in presses:
            press(presses[phase])
            if age>.10:_mix_phase(phase.replace('_press','_wait'))
            return
        if phase in ['actor_wait','mass_wait','burst_wait','chain_wait','lmb_wait']:
            if age<3.5:return
            current=sample();_mix['samples'][phase]={'before':_mix['before'],'after':current}
            if phase!='mass_wait':_mix_check(phase+'_actor_hit',current['actor']<_mix['before']['actor'])
            if phase in ['mass_wait','burst_wait','chain_wait']:_mix_check(phase+'_mass_hit',current['mass']<_mix['before']['mass'])
            if phase in ['actor_wait','lmb_wait']:_mix_check(phase+'_mass_not_spuriously_hit',current['mass']==_mix['before']['mass'])
            cost_once({'actor_wait':'Homing','mass_wait':'Homing','burst_wait':'Burst','chain_wait':'Chain','lmb_wait':'Projectile'}[phase]);synced()
            begin({'actor_wait':'mass_press','mass_wait':'burst_press','burst_wait':'chain_press','chain_wait':'lmb_press','lmb_wait':'beam'}[phase]);return
        if phase=='beam':
            press('IA_RMB')
            if age<1.3:return
            _mix_check('beam_actor_damage',_mix_attr(ea,'health')<_mix['before']['actor'])
            _mix_check('beam_replicates',len(_mix_nodes(sw,u.AbilityPrototypeKind.BEAM))==1 and len(_mix_nodes(cw,u.AbilityPrototypeKind.BEAM))==1)
            _mix_phase('beam_release');return
        if phase=='beam_release':
            if age<1.8:return
            _mix_check('beam_release_cleanup',not _mix_nodes(sw,u.AbilityPrototypeKind.BEAM) and not _mix_nodes(cw,u.AbilityPrototypeKind.BEAM))
            begin('orbit_on');return
        if phase=='orbit_on':
            press('IA_Input4')
            if age>.10:_mix_phase('orbit_wait')
            return
        if phase=='orbit_wait':
            if age<3.7:return
            sr=_mix_nodes(sw,u.AbilityPrototypeKind.ORBIT);cr=_mix_nodes(cw,u.AbilityPrototypeKind.ORBIT)
            _mix_check('orbit_bolt_exists_both_worlds',len(sr)==1 and len(cr)==1 and len(sr[0].get_editor_property('orbit_bolts'))>0 and len(cr[0].get_editor_property('orbit_bolts'))>0)
            begin('orbit_trigger');return
        if phase=='orbit_trigger':
            press('IA_Input2')
            if age>.10:_mix_phase('orbit_attack')
            return
        if phase=='orbit_attack':
            if age<2:return
            solo=_mix['samples']['actor_wait']['before']['actor']-_mix['samples']['actor_wait']['after']['actor']
            _mix_check('committed_actor_attack_launches_orbit',_mix['before']['actor']-_mix_attr(ea,'health')>solo+.01)
            _mix_phase('orbit_off');return
        if phase=='orbit_off':
            press('IA_Input4')
            if age>.10:_mix_phase('cleanup')
            return
        if phase=='cleanup':
            if age<1.5:return
            _mix_check('orbit_cleanup_both_worlds',not _mix_nodes(sw,u.AbilityPrototypeKind.ORBIT) and not _mix_nodes(cw,u.AbilityPrototypeKind.ORBIT))
            synced();_mix['final_mana']=_mix_attr(sa,'mana');_mix_phase('stable');return
        if phase=='stable':
            if age<1.5:return
            _mix_check('mana_stops_after_toggle_off',abs(_mix_attr(sa,'mana')-_mix['final_mana'])<.01)
            _mix_finish()
    except Exception as error:
        _mix_finish(repr(error));u.log_error('MIXED_COMBAT_QA '+repr(error))
_mix_handle=u.register_slate_post_tick_callback(_mix_tick)
_mix_write()
