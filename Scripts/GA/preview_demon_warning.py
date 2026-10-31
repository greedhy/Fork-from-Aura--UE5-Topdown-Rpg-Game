"""Freeze the real warning phase in the isolated PIE fixture for visual inspection."""
import unreal as u,json
from pathlib import Path
w=u.EditorLevelLibrary.get_game_world();assert w and w.get_path_name().startswith('/Temp/')
a=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.EnemyCharacter) if a.actor_has_tag('SGSource'))
target=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.EnemyCharacter) if a.actor_has_tag('Target'))
a.set_editor_property('combat_target',target);a.set_actor_location(u.Vector(0,0,50),False,True)
a.get_component_by_class(u.CharacterMovementComponent).disable_movement()
assert a.try_attack_index(1)
started=u.GameplayStatics.get_time_seconds(w)
def hold(dt):
 if u.GameplayStatics.get_time_seconds(w)-started<.22:return
 u.GameplayStatics.set_global_time_dilation(w,.0001)
 u.unregister_slate_post_tick_callback(handle)
 (Path(u.Paths.project_dir())/'Saved/GAAuthoring/MonsterWave1/demon-visual-held.json').write_text(json.dumps({'phase':'warning','world':w.get_path_name()}))
handle=u.register_slate_post_tick_callback(hold)
