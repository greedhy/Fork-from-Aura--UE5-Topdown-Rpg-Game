"""Capture real warning/contact frame; request file controls skill and phase time."""
import unreal as u,json
from pathlib import Path
root=Path(u.Paths.project_dir());req=json.loads((root/'Saved/GAAuthoring/LegacyMonsterDesign/combat-preview-request.json').read_text(encoding='utf-8-sig'))
w=u.EditorLevelLibrary.get_game_world();assert w and w.get_path_name().startswith('/Temp/')
a=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.TelegraphedEnemyCharacter) if a.actor_has_tag(req['source']))
for other in u.GameplayStatics.get_all_actors_of_class(w,u.TelegraphedEnemyCharacter):
 if other!=a:other.set_actor_hidden_in_game(True);other.set_actor_enable_collision(False)
target=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.EnemyCharacter) if a.actor_has_tag('Target'))
a.enable_dungeon_pooling(0.);a.sleep_for_dungeon_pool(False);assert a.wake_from_dungeon_pool(u.Transform(location=u.Vector(0,0,a.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height()+2)),'LegacyPreview')
a.get_component_by_class(u.CharacterMovementComponent).disable_movement();a.set_editor_property('combat_target',target)
target.get_component_by_class(u.CharacterMovementComponent).disable_movement();target.set_actor_location(u.Vector(400 if req['source']=='GoblinSlinger' else 100,0,89),False,True)
pc=u.GameplayStatics.get_player_controller(w,0);pawn=pc.get_controlled_pawn();pawn.set_actor_enable_collision(False)
pawn.set_actor_location(u.Vector(220,-320,260),False,True);pc.set_control_rotation(u.Rotator(pitch=-25,yaw=120,roll=0))
u.SystemLibrary.execute_console_command(w,'viewmode unlit',pc)
assert a.try_attack_index(req['index'])
start=u.GameplayStatics.get_time_seconds(w);ticks=0;captured=False
u.GameplayStatics.set_global_time_dilation(w,.3)
def tick(dt):
 global ticks,captured
 if not captured and u.GameplayStatics.get_time_seconds(w)-start>=req['time']:
  captured=True;u.GameplayStatics.set_global_time_dilation(w,.001);u.SystemLibrary.execute_console_command(w,'HighResShot 1280x720',pc)
 if captured:
  ticks+=1
  if ticks>20:u.GameplayStatics.set_global_time_dilation(w,1.);u.unregister_slate_post_tick_callback(handle)
handle=u.register_slate_post_tick_callback(tick)
