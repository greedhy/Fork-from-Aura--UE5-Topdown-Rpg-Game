"""Real original BP_Player + original GA_FireBolt, remote activation in the Mass sandbox.
Runtime-only possession/loadout changes; never writes assets or saves.
"""
import unreal as u,json,time
from pathlib import Path
_fb={'phase':'setup','started':time.monotonic(),'started_wall':time.time(),'checks':{},'projectiles':{},'numbers':{}}
_fb_path=Path(u.Paths.project_dir()).resolve()/'Saved/PureMass/LegacyFireBolt/pie.json'
_fb_path.parent.mkdir(parents=True,exist_ok=True)
_fb_perf=u.get_default_object(u.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
_fb_throttle=_fb_perf.get_editor_property('bThrottleCPUWhenNotForeground')
_fb_perf.set_editor_property('bThrottleCPUWhenNotForeground',False)
_fb_ga='/Game/BluePrints/AbilitySystem/Player/Ability/Fire/FireBolt/GA_FireBolt.GA_FireBolt_C'
def _fb_write():_fb_path.write_text(json.dumps(_fb,indent=2),encoding='utf8')
def _fb_phase(name):_fb.update(phase=name,at=_fb['time']);_fb_write()
def _fb_check(name,ok):_fb['checks'][name]=bool(ok)
def _fb_finish(error=None):
 u.unregister_slate_post_tick_callback(_fb_handle)
 _fb_perf.set_editor_property('bThrottleCPUWhenNotForeground',_fb_throttle)
 _fb.update(passed=error is None and all(_fb['checks'].values()),error=error);_fb_write()
def _fb_tick(dt):
 try:
  if time.monotonic()-_fb['started']>90:raise AssertionError('Timeout '+_fb['phase'])
  pcs=[p for p in u.ObjectIterator(u.PureMassPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_controlled_pawn()]
  if len(pcs)!=3:return
  server=next(p for p in pcs if not p.is_local_controller())
  client=next(p for p in pcs if p.is_local_controller() and p.get_local_role()==u.NetRole.ROLE_AUTONOMOUS_PROXY)
  host=next(p for p in pcs if p.is_local_controller() and p.get_local_role()==u.NetRole.ROLE_AUTHORITY)
  sw=server.get_world();cw=client.get_world()
  sim=next(m for m in u.ObjectIterator(u.PureMassSubsystem) if m.get_world()==sw)
  asc=server.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent)
  _fb['time']=u.GameplayStatics.get_time_seconds(sw);age=_fb['time']-_fb.get('at',_fb['time']);phase=_fb['phase']
  if phase=='setup':
   for v in sim.get_snapshots():
    d=u.PureMassDamage();d.set_editor_property('amount',1000000);sim.apply_damage(v.id,d)
   for pc,pos in [(server,u.Vector(70,740,110)),(host,u.Vector(1500,-1500,110))]:
    pawn=pc.get_controlled_pawn();pawn.get_component_by_class(u.CharacterMovementComponent).set_movement_mode(u.MovementMode.MOVE_FLYING);pawn.set_actor_location(pos,False,True)
   # Clear the sandbox loadout, then let the original player's normal LoadProgress
   # grant its startup abilities. Never invoke a client GAS RPC from a Python Slate tick:
   # that runs outside PIE's scoped world and may execute the server thunk locally.
   asc.clear_all_abilities()
   old=server.get_controlled_pawn();old.set_actor_enable_collision(False)
   statics=u.get_default_object(u.GameplayStatics.static_class());tf=u.Transform(location=u.Vector(70,740,110))
   cls=u.load_class(None,'/Game/BluePrints/Characters/Player/BP_Player.BP_Player_C')
   pawn=statics.call_method('BeginDeferredActorSpawnFromClass',(sw,cls,tf,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
   statics.call_method('FinishSpawningActor',(pawn,tf,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
   server.possess(pawn);old.destroy_actor()
   pawn.get_component_by_class(u.CharacterMovementComponent).set_movement_mode(u.MovementMode.MOVE_FLYING)
   for key,value in [('max_mana',1000),('mana',1000),('mana_regeneration',0),('critical_hit_chance',0)]:
    attrs=asc.get_attribute_set(u.MyAttributeSet);field=attrs.get_editor_property(key)
    field.import_text('(BaseValue='+str(value)+',CurrentValue='+str(value)+')');attrs.set_editor_property(key,field)
   _fb['target']=sim.spawn_monster(u.load_asset('/Game/PureMass/DA_MassQAGoblin'),u.Vector(70,1150,60),'OriginalFireBoltQA')
   _fb_phase('settle');return
  v=next((v for v in sim.get_snapshots() if v.id==_fb['target']),None)
  for p in u.GameplayStatics.get_all_actors_of_class(sw,u.MyProjectile):
   s=p.get_editor_property('sphere');pos=p.get_actor_location()
   _fb['projectiles'][p.get_name()]={'class':p.get_class().get_path_name(),'collision':str(s.get_collision_enabled()),
    'pawn_response':str(s.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN)),
    'position':[pos.x,pos.y,pos.z]}
  for c in u.ObjectIterator(u.DamageTextComponent):
   if c.get_world()!=cw or not c.get_owner():continue
   if c.get_owner()!=client and not (c.get_owner().get_owner()==client and c.get_owner().get_class()==u.Actor.static_class()):continue
   widget=c.get_user_widget_object()
   if widget:
    _fb['numbers'][c.get_path_name()]={'text':str(widget.get_editor_property('Text_Damage').get_text()),'owner_hidden':bool(c.get_owner().get_editor_property('hidden'))}
    if phase=='wait':_fb.setdefault('first_number_at',_fb['time'])
    if phase=='wait' and _fb['time']-_fb['first_number_at']>.15 and not _fb.get('capture_requested'):
     u.SystemLibrary.execute_console_command(cw,'PureMass.QA.CaptureUI 1 original-firebolt-remote',client)
     _fb['capture_requested']=True
  if phase=='settle':
   if age<1.5:return
   _fb_check('original_player_on_client',client.get_controlled_pawn().get_class().get_path_name()=='/Game/BluePrints/Characters/Player/BP_Player.BP_Player_C')
   _fb['before']=v.health;_fb['before_location']=[v.location.x,v.location.y,v.location.z]
   u.get_default_object(u.load_class(None,'/Script/UMG.WidgetBlueprintLibrary')).call_method('SetInputMode_GameOnly',(client,False))
   _fb_phase('press');return
  if phase in ['press','wait','actor_press','actor_wait']:
   screen=client.project_world_location_to_screen(u.Vector(70,1150,10))
   client.set_mouse_location(int(screen.x),int(screen.y))
   if phase in ['press','actor_press']:
    lib=u.get_default_object(u.load_class(None,'/Script/Engine.SubsystemBlueprintLibrary'))
    inp=lib.call_method('GetLocalPlayerSubSystemFromPlayerController',(client,u.EnhancedInputLocalPlayerSubsystem.static_class()))
    inp.inject_input_vector_for_action(u.load_asset('/Game/BluePrints/Input/InputActions/IA_LMB'),u.Vector(1,0,0),[],[])
    if age>.1:_fb_phase('actor_wait' if phase=='actor_press' else 'wait')
    return
   if age<3:return
   if phase=='actor_wait':
    actor=next(a for a in u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter) if a.get_name()==_fb['actor'])
    ea=actor.get_component_by_class(u.MyAbilitySystemComponent)
    hp=ea.get_attribute_set(u.MyAttributeSet).get_editor_property('health').get_editor_property('current_value')
    _fb['actor_after']=hp
    _fb_check('actor_enemy_still_takes_gas_damage',hp<100000)
    _fb_check('mass_behind_actor_not_damaged',v.health==_fb['after'])
    _fb_check('actor_hit_consumes_firebolt',not u.GameplayStatics.get_all_actors_of_class(sw,u.MyProjectile))
    _fb_finish();return
   _fb['after']=v.health if v else 0;_fb['after_location']=[v.location.x,v.location.y,v.location.z] if v else None
   _fb_check('original_firebolt_spawned',bool(_fb['projectiles']))
   _fb_check('original_firebolt_damages_mass',_fb['after']<_fb['before'])
   _fb_check('remote_attacker_has_visible_number',bool(_fb['numbers']) and all(not n['owner_hidden'] for n in _fb['numbers'].values()))
   capture=_fb_path.parents[1]/'FeedbackUI/original-firebolt-remote.json'
   _fb_check('fresh_remote_ui_capture',capture.exists() and capture.stat().st_mtime>=_fb['started_wall'])
   if capture.exists():
    screen_report=json.loads(capture.read_text(encoding='utf8'))
    _fb_check('remote_firebolt_number_reached_screen_layer',any(n['added_to_screen'] and not n['owner_hidden'] and n.get('text') for n in screen_report['numbers']))
   _fb_check('projectile_consumed',not u.GameplayStatics.get_all_actors_of_class(sw,u.MyProjectile))
   _fb_check('no_monster_actor_proxy',not u.GameplayStatics.get_all_actors_of_class(sw,u.EnemyCharacter))
   _fb_check('firebolt_does_not_displace_mass',_fb['before_location']==_fb['after_location'])
   actor_class=u.load_class(None,'/Game/BluePrints/Characters/Goblin/BP_GoblinSpear.BP_GoblinSpear_C')
   tf=u.Transform(location=u.Vector(70,1030,60));statics=u.get_default_object(u.GameplayStatics.static_class())
   actor=statics.call_method('BeginDeferredActorSpawnFromClass',(sw,actor_class,tf,u.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,None,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
   actor.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
   statics.call_method('FinishSpawningActor',(actor,tf,u.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
   actor.get_component_by_class(u.CharacterMovementComponent).disable_movement()
   ea=actor.get_component_by_class(u.MyAbilitySystemComponent)
   for key,value in [('max_health',100000),('health',100000),('health_regeneration',0),('block_chance',0)]:
    attrs=ea.get_attribute_set(u.MyAttributeSet);field=attrs.get_editor_property(key)
    field.import_text('(BaseValue='+str(value)+',CurrentValue='+str(value)+')');attrs.set_editor_property(key,field)
   _fb['actor']=actor.get_name();_fb_phase('actor_settle');return
  if phase=='actor_settle' and age>1:_fb_phase('actor_press')
 except Exception as e:_fb_finish(repr(e));u.log_error('LEGACY_FIREBOLT_QA '+repr(e))
_fb_handle=u.register_slate_post_tick_callback(_fb_tick)
_fb_write()
