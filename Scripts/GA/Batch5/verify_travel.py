def _batch5_travel():
    import unreal as u,json,time,uuid
    from pathlib import Path
    B='/Game/PrototypeExtensions/Batch5/'
    q={'phase':'setup','started':time.monotonic(),'leg':0,'checks':{},'snapshots':[],'saves':[]}
    maps=['L_PrototypeLab','L_PrototypeTravel','L_PrototypeLab','L_PrototypeTravel']
    old_net=u.SystemLibrary.get_console_variable_int_value('net.AllowPIESeamlessTravel')
    old_throttle=u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings')).get_editor_property('bThrottleCPUWhenNotForeground')
    def write(): (Path(u.Paths.project_dir())/'Saved/GAAuthoring/Batch5/travel.json').write_text(json.dumps(q,indent=2),encoding='utf8')
    def phase(p):q.update(phase=p,at=time.monotonic());write()
    def check(n,v):q['checks'][n]=bool(v);assert v,n
    def tag(n):t=u.GameplayTag();t.import_text('(TagName="'+n+'")');return t
    def finish(error=None):
        u.unregister_slate_post_tick_callback(handle)
        ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        u.SystemLibrary.execute_console_command(ew,'net.AllowPIESeamlessTravel '+str(old_net))
        u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings')).set_editor_property('bThrottleCPUWhenNotForeground',old_throttle)
        for name in q['saves']:u.GameplayStatics.delete_game_in_slot(name,0)
        q.update(passed=error is None,error=error);write()
    def slot(p):return p.get_editor_property('player_state').get_editor_property('travel_player_slot')
    def snapshot(pcs):
        u.SystemLibrary.execute_console_command(pcs[0].get_world(),'Extension.QA.SaveSnapshot travel-snapshot')
        saved=json.loads((Path(u.Paths.project_dir())/'Saved/GAAuthoring/Batch5/travel-snapshot.json').read_text(encoding='utf-8-sig'))['players']
        assert len(saved)==2,'Both players must roundtrip through isolated save files'
        rows=[]
        for p in pcs:
            asc=p.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent)
            row={'slot':slot(p),'local':p.is_local_controller(),'points':p.get_controlled_pawn().call_method('GetSpellPoints')}
            row['abilities']=sorted(u.AbilitySystemLibrary.get_gameplay_ability_from_spec_handle(asc,h)[0].get_class().get_path_name() for h in asc.get_all_abilities())
            if p.get_local_role()==u.NetRole.ROLE_AUTHORITY:
                record=next(r for r in saved if r['slot']==slot(p))
                assert record['points']==row['points']
                row['saved']=sorted(record['abilities'])
            if p.is_local_controller():
                overlay=next((w for w in u.ObjectIterator(u.MyUserWidget) if w.get_world()==p.get_world() and w.get_class().get_name()=='WBP_Overlay_C' and w.is_in_viewport()),None)
                assert overlay,'Missing overlay'
                row['icons']={}
                for i in u.ObjectIterator(u.Image):
                    if i.get_name()=='Image_SpellIcon' and i.get_path_name().startswith(overlay.get_path_name()+'.'):
                        resource=i.get_editor_property('brush').get_editor_property('resource_object')
                        row['icons'][i.get_outer().get_outer().get_name()]=resource.get_path_name() if resource else None
            rows.append(row)
        return sorted(rows,key=lambda r:(r['slot'],r['local']))
    def tick(dt):
        try:
            if time.monotonic()-q['started']>180:raise AssertionError('Timeout '+q['phase'])
            expected=maps[q['leg']+1] if q['phase'] in ['travel','settle'] else maps[q['leg']]
            pcs=[p for p in u.ObjectIterator(u.MyPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_world().get_name().endswith(expected) and p.get_controlled_pawn() and p.get_local_role()!=u.NetRole.ROLE_NONE]
            server=sorted([p for p in pcs if p.get_local_role()==u.NetRole.ROLE_AUTHORITY],key=slot)
            if len(pcs)!=3 or len(server)!=2:return
            sw=server[0].get_world()
            if q['phase'] in ['setup','travel']:
                mass=next(s for s in u.ObjectIterator(u.PureMassSubsystem) if s.get_world()==sw)
                for v in mass.get_snapshots():
                    d=u.PureMassDamage();d.set_editor_property('amount',1000000);mass.apply_damage(v.id,d)
                for e in u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter):e.destroy_actor()
            if q['phase']=='setup':
                assert u.load_asset(B+'L_PrototypeTravel'),'Run author_travel_map.py outside PIE first'
                u.SystemLibrary.execute_console_command(sw,'net.AllowPIESeamlessTravel 1')
                u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings')).set_editor_property('bThrottleCPUWhenNotForeground',False)
                u.SystemLibrary.execute_console_command(sw,'Extension.QA.PrepareSaves')
                q['saves']=json.loads((Path(u.Paths.project_dir())/'Saved/GAAuthoring/Batch5/qa-saves.json').read_text(encoding='utf-8-sig'))['saves']
                assert len(q['saves'])==2 and all(n.startswith('PrototypeExtensions_QA_') for n in q['saves'])
                for p in server:
                    p.get_controlled_pawn().call_method('AddToSpellPoints',(-3-slot(p),))
                    asc=p.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent)
                    asc.call_method('ServerSpendSpellPoint',(tag('Abilities.Extension.Attach'),))
                    asc.call_method('ServerEquipAbility',(tag('Abilities.Extension.Attach'),tag('InputTag.3')))
                phase('initial_settle')
            elif q['phase']=='initial_settle':
                if time.monotonic()-q['at']<1:return
                q['snapshots'].append(snapshot(pcs));phase('gather')
            elif q['phase']=='gather':
                portals=u.GameplayStatics.get_all_actors_of_class(sw,u.MapEntrance)
                if not portals:
                    stat=u.get_default_object(u.GameplayStatics.static_class());tf=u.Transform(location=u.Vector(0,-5000,120))
                    portal=stat.call_method('BeginDeferredActorSpawnFromClass',(sw,u.MapEntrance.static_class(),tf,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
                    stat.call_method('FinishSpawningActor',(portal,tf,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
                    portal.get_component_by_class(u.SphereComponent).set_sphere_radius(350,True)
                    portal.set_editor_property('destination_map',u.load_asset(B+maps[q['leg']+1]))
                    starts=u.GameplayStatics.get_all_actors_of_class(sw,u.TravelPlayerStart)
                    group=next(str(s.get_editor_property('player_start_tag')) for s in starts if s.get_editor_property('default_entry_group'))
                    portal.set_editor_property('destination_player_start_tag',group)
                else:portal=portals[0]
                center=portal.get_component_by_class(u.SphereComponent).get_world_location()
                for p in server:
                    pawn=p.get_controlled_pawn();move=pawn.get_component_by_class(u.CharacterMovementComponent)
                    move.set_movement_mode(u.MovementMode.MOVE_FLYING);move.stop_movement_immediately()
                    pawn.set_actor_location(center+u.Vector(0,80*slot(p),0),False,True)
                assert not portal.get_editor_property('travel_error'),portal.get_editor_property('travel_error')
                if portal.get_editor_property('travel_in_progress'):phase('travel')
            elif q['phase']=='travel':phase('settle')
            elif q['phase']=='settle':
                if time.monotonic()-q['at']<2:return
                rows=snapshot(pcs);q['snapshots'].append(rows)
                for row in rows:
                    before=next(r for r in q['snapshots'][0] if r['slot']==row['slot'] and r['local']==row['local'])
                    for field in ['points','abilities']+(['icons'] if row['local'] else [])+(['saved'] if 'saved' in row else []):check(str(q['leg'])+'_'+str(row['slot'])+'_'+str(row['local'])+'_'+field,row[field]==before[field])
                check(str(q['leg'])+'_runtime_cleanup',not u.GameplayStatics.get_all_actors_of_class(sw,u.ExtensionRuntime))
                q['leg']+=1
                if q['leg']==3:finish()
                else:phase('gather')
        except Exception as e:finish(repr(e))
    handle=u.register_slate_post_tick_callback(tick);write()
_batch5_travel()

