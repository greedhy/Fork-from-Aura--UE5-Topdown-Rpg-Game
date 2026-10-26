def _batch5_start(start_index=0,report_name='pie.json'):
    """Two-player PIE integration: real remote Enhanced Input, isolated transient combat fixtures."""
    import unreal as u,json,time
    from pathlib import Path
    B='/Game/PrototypeExtensions/Batch5/'
    OUT=Path(u.Paths.project_dir()).resolve()/'Saved/GAAuthoring/Batch5'/report_name
    q={'phase':'setup','started':time.monotonic(),'index':start_index,'checks':{},'samples':[]}
    cases=[(n,t) for n in ['StormBrand','FrostParasite','EmberBrand','StormConvergence','GravityWell','BrambleRepulse'] for t in ['mass','actor']]
    perf=u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
    old_throttle=perf.get_editor_property('bThrottleCPUWhenNotForeground');perf.set_editor_property('bThrottleCPUWhenNotForeground',False)
    def write():OUT.write_text(json.dumps(q,indent=2,ensure_ascii=False),encoding='utf-8')
    def phase(p):q.update(phase=p,at=q['time']);write()
    def check(n,v):q['checks'][n]=bool(v);assert v,n
    def tag(n):t=u.GameplayTag();t.import_text('(TagName="'+n+'")');return t
    def attr(asc,n,v=None):
     a=asc.get_attribute_set(u.MyAttributeSet);f=a.get_editor_property(n)
     if v is None:return f.get_editor_property('current_value')
     f.import_text('(BaseValue='+str(v)+',CurrentValue='+str(v)+')');a.set_editor_property(n,f)
    def finish(error=None):
     u.unregister_slate_post_tick_callback(handle);perf.set_editor_property('bThrottleCPUWhenNotForeground',old_throttle)
     q.update(passed=error is None and all(q['checks'].values()),error=error);write()
    def nodes(w):return u.GameplayStatics.get_all_actors_of_class(w,u.ExtensionRuntime)
    def tick(dt):
     try:
      if time.monotonic()-q['started']>240:raise AssertionError('Timeout '+q['phase'])
      pcs=[p for p in u.ObjectIterator(u.PureMassPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_controlled_pawn()]
      if len(pcs)!=3:return
      sp=next(p for p in pcs if not p.is_local_controller());cp=next(p for p in pcs if p.is_local_controller() and p.get_local_role()==u.NetRole.ROLE_AUTONOMOUS_PROXY)
      hp=next(p for p in pcs if p.is_local_controller() and p.get_local_role()==u.NetRole.ROLE_AUTHORITY)
      sw,cw=sp.get_world(),cp.get_world();q['time']=u.GameplayStatics.get_time_seconds(sw);age=q['time']-q.get('at',q['time'])
      sm=next(s for s in u.ObjectIterator(u.PureMassSubsystem) if s.get_world()==sw);cm=next(s for s in u.ObjectIterator(u.PureMassSubsystem) if s.get_world()==cw)
      sa=sp.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent)
      if q['phase']=='setup':
       check('initial_200_mass',len(sm.get_snapshots())==200)
       check('initial_no_enemy_actors',len(u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter))==0)
       check('extension_player',isinstance(sp.get_controlled_pawn(),u.ExtensionPlayerCharacter))
       check('host_starting_skill_points_999',hp.get_controlled_pawn().call_method('GetSpellPoints')==999)
       check('remote_starting_skill_points_999',sp.get_controlled_pawn().call_method('GetSpellPoints')==999)
       check('client_starting_skill_points_999',cp.get_controlled_pawn().call_method('GetSpellPoints')==999)
       for n in ['Attach','Stack','Displace']+[v[0] for v in cases[::2]]:sa.call_method('ServerSpendSpellPoint',(tag('Abilities.Extension.'+n),))
       for pc,pos in [(sp,u.Vector(0,-5030,120)),(hp,u.Vector(700,-5400,120))]:
        pawn=pc.get_controlled_pawn();pawn.get_component_by_class(u.CharacterMovementComponent).set_movement_mode(u.MovementMode.MOVE_FLYING)
        pawn.set_actor_location(pos,False,True)
       for key,val in [('max_mana',10000),('mana',10000),('mana_regeneration',0),('critical_hit_chance',0),('max_health',100000),('health',100000)]:attr(sa,key,val)
       u.get_default_object(u.load_class(None,'/Script/UMG.WidgetBlueprintLibrary')).call_method('SetInputMode_GameOnly',(cp,False))
       phase('prepare');return
      if q['phase']=='prepare':
       for a in nodes(sw):a.destroy_actor()
       for a in u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter):a.destroy_actor()
       for v in sm.get_snapshots():
        d=u.PureMassDamage();d.set_editor_property('amount',1000000);sm.apply_damage(v.id,d)
       q['entity']=sm.spawn_monster(u.load_asset('/Game/PureMass/DA_MassQAGoblin'),u.Vector(-100,-4800,61),'Batch5QA')
       cls=u.load_class(None,'/Game/BluePrints/Characters/Goblin/BP_GoblinSpear.BP_GoblinSpear_C');tf=u.Transform(location=u.Vector(100,-4800,61))
       stat=u.get_default_object(u.GameplayStatics.static_class())
       enemy=stat.call_method('BeginDeferredActorSpawnFromClass',(sw,cls,tf,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
       enemy.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
       enemy.get_component_by_class(u.CapsuleComponent).set_capsule_size(32,60,True)
       stat.call_method('FinishSpawningActor',(enemy,tf,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
       enemy.get_component_by_class(u.CharacterMovementComponent).set_editor_property('max_walk_speed',0.0)
       enemy.get_component_by_class(u.CharacterMovementComponent).set_editor_property('run_physics_with_no_controller',True)
       enemy.get_component_by_class(u.CharacterMovementComponent).set_movement_mode(u.MovementMode.MOVE_WALKING)
       ea=enemy.get_component_by_class(u.MyAbilitySystemComponent)
       for key,val in [('max_health',100000),('health',100000),('armor',0),('block_chance',0),('health_regeneration',0)]:attr(ea,key,val)
       name,target=cases[q['index']];q.update(name=name,target=target,server_nodes=[],client_nodes=[],node_positions={},actor_motion=[],max_layers=0,numbers=[],shots=0,actor_start=[100,-4800,61],mass_start=[-100,-4800,61])
       sa.call_method('ServerEquipAbility',(tag('Abilities.Extension.'+name),tag('InputTag.4')))
       phase('settle');return
      enemy=next(iter(u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter)),None)
      ce=next(iter(u.GameplayStatics.get_all_actors_of_class(cw,u.EnemyCharacter)),None)
      v=next((x for x in sm.get_snapshots() if x.id==q['entity']),None);cv=next((x for x in cm.get_snapshots() if x.id==q['entity']),None)
      if not enemy or not ce or not v or not cv:return
      ea=enemy.get_component_by_class(u.MyAbilitySystemComponent);name=q['name'];key=name+'_'+q['target']
      for w,label in [(sw,'server_nodes'),(cw,'client_nodes')]:
       for a in nodes(w):
        n=a.get_editor_property('node')
        if n and n.get_name() not in q[label]:
         q[label].append(n.get_name());pos=a.get_actor_location();q['node_positions'][label+'_'+n.get_name()]=[pos.x,pos.y,pos.z]
      for a in u.GameplayStatics.get_all_actors_of_class(cw,u.ExtensionPresentation):
       for m in a.get_editor_property('marks'):q['max_layers']=max(q['max_layers'],m.layers)
      for c in u.ObjectIterator(u.DamageTextComponent):
       if c.get_world()!=cw or not c.get_owner() or (c.get_owner().get_owner()!=cp and c.get_owner()!=ce):continue
       widget=c.get_user_widget_object()
       if widget:
        val=str(widget.get_editor_property('Text_Damage').get_text())
        if val not in q['numbers']:q['numbers'].append(val)
      if q['phase']=='settle':
       if age<3.0:return
       q['mana_before']=attr(sa,'mana');q['actor_before']=attr(ea,'health');q['mass_before']=v.health
       phase('cast');return
      if q['phase']=='cast':
       if name in ['GravityWell','BrambleRepulse'] and age<1 and len(q['actor_motion'])<40:
        ws=next(s for s in u.ObjectIterator(u.ExtensionWorldSubsystem) if s.get_world()==sw)
        loc=enemy.get_actor_location();q['actor_motion'].append({'t':age,'anim_root':enemy.is_playing_root_motion(),'any_root':enemy.has_any_root_motion(),'position':[loc.x,loc.y,loc.z]})
       if name=='EmberBrand' and q['max_layers']>=2 and not q.get('captured_layers'):
        u.SystemLibrary.execute_console_command(cw,'PureMass.QA.CaptureUI 1 Batch5_EmberBrand',cp);q['captured_layers']=True
       aim=cv.location if q['target']=='mass' else ce.get_actor_location()
       if name=='GravityWell':aim=u.Vector(0,-4900,0)
       screen=cp.project_world_location_to_screen(aim)
       if screen:cp.set_mouse_location(int(screen.x),int(screen.y))
       repetitions=3 if name in ['EmberBrand','StormConvergence'] else 1
       gap=.95 if name=='EmberBrand' else 2.15
       if q['shots']<repetitions and age>=q['shots']*gap:
        lib=u.get_default_object(u.load_class(None,'/Script/Engine.SubsystemBlueprintLibrary'))
        inp=lib.call_method('GetLocalPlayerSubSystemFromPlayerController',(cp,u.EnhancedInputLocalPlayerSubsystem.static_class()))
        inp.inject_input_vector_for_action(u.load_asset('/Game/BluePrints/Input/InputActions/IA_Input4'),u.Vector(1,0,0),[],[])
        q['shots']+=1
       duration=8.3 if name=='FrostParasite' else 6.0 if name in ['StormBrand','StormConvergence'] else 4.5
       if age<duration:return
       config=u.get_default_object(u.load_class(None,B+'GA_'+name+'.GA_'+name+'_C')).get_editor_property('prototype')
       expected=config.get_editor_property('mana_cost')*repetitions
       actual=q['mana_before']-attr(sa,'mana')
       q['actual_cost']=actual;q['damage']={'mass':q['mass_before']-v.health,'actor':q['actor_before']-attr(ea,'health')}
       apos=enemy.get_actor_location();q['positions_after']={'mass':[v.location.x,v.location.y,v.location.z],'actor':[apos.x,apos.y,apos.z]}
       check(key+'_cost_once_per_cast',abs(actual-expected)<.01)
       check(key+'_target_damage',q['damage'][q['target']]>0)
       check(key+'_remote_runtime',len(q['client_nodes'])>0)
       check(key+'_visible_damage_text',len(q['numbers'])>0)
       if name in ['EmberBrand','StormConvergence']:check(key+'_replicated_layers',q['max_layers']>=2)
       if name in ['GravityWell','BrambleRepulse']:
        loc=v.location if q['target']=='mass' else enemy.get_actor_location();start=q['mass_start'] if q['target']=='mass' else q['actor_start']
        dist=((loc.x-start[0])**2+(loc.y-start[1])**2)**.5;q['move_distance']=dist;check(key+'_displaced',dist>10)
       check(key+'_mass_health_replicated',abs(cv.health-v.health)<.01)
       cea=ce.get_component_by_class(u.MyAbilitySystemComponent);check(key+'_actor_health_replicated',abs(attr(cea,'health')-attr(ea,'health'))<.01)
       q['samples'].append({k:q[k] for k in ['name','target','actual_cost','damage','server_nodes','client_nodes','numbers','max_layers']})
       q['index']+=1
       if q['index']==len(cases):phase('cleanup')
       else:phase('prepare')
       return
      if q['phase']=='cleanup':
       if age<4:return
       check('runtimes_clean_server',len(nodes(sw))==0);check('runtimes_clean_client',len(nodes(cw))==0)
       check('only_fixture_enemy_actor',len(u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter))==1)
       finish()
     except Exception as e:finish(repr(e));u.log_error('BATCH5_PIE '+repr(e))
    handle=u.register_slate_post_tick_callback(tick);write()
    

_batch5_start()

