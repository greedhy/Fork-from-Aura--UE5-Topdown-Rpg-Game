"""Hold real Burst warning or impact (phase selected by local phase.json) for capture."""
import unreal as u,json
from pathlib import Path
root=Path(u.Paths.project_dir());w=u.EditorLevelLibrary.get_game_world()
assert w and w.get_path_name().startswith('/Temp/')
phase=json.loads((root/'Saved/GAAuthoring/MonsterWave1/shaman-preview-phase.json').read_text())['phase']
a=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.EnemyCharacter) if a.actor_has_tag('SGSource'))
target=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.EnemyCharacter) if a.actor_has_tag('Target'))
for p in u.GameplayStatics.get_all_actors_of_class(w,u.DefaultPawn):p.set_actor_enable_collision(False)
a.get_component_by_class(u.CharacterMovementComponent).disable_movement()
target.set_actor_location(u.Vector(350,0,89),False,True);target.get_component_by_class(u.CharacterMovementComponent).disable_movement()
a.set_editor_property('combat_target',target)
pc=u.GameplayStatics.get_player_controller(w,0);pawn=pc.get_controlled_pawn()
pawn.set_actor_location(u.Vector(-150,-550,500),False,True);pc.set_control_rotation(u.Rotator(pitch=-33,yaw=55,roll=0))
u.GameplayStatics.set_global_time_dilation(w,1.)
assert a.try_attack_index(1)
started=u.GameplayStatics.get_time_seconds(w)
def hold(dt):
 if u.GameplayStatics.get_time_seconds(w)-started<(.5 if phase=='warning' else 1.04):return
 u.GameplayStatics.set_global_time_dilation(w,.0001)
 u.unregister_slate_post_tick_callback(shaman_preview_handle)
 u.SystemLibrary.execute_console_command(w,'viewmode unlit',pc)
 u.SystemLibrary.execute_console_command(w,'HighResShot 1280x720',pc)
 (root/'Saved/GAAuthoring/MonsterWave1/shaman-visual-held.json').write_text(json.dumps({'phase':phase,'world':w.get_path_name()}))
shaman_preview_handle=u.register_slate_post_tick_callback(hold)
