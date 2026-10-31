import unreal as u,json
from pathlib import Path
root=Path(u.Paths.project_dir());req=json.loads((root/'Saved/GAAuthoring/LegacyMonsterDesign/preview-request.json').read_text(encoding='utf-8-sig'))
w=u.EditorLevelLibrary.get_game_world();assert w and w.get_path_name().startswith('/Temp/')
actors=[a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Character) if a.actor_has_tag('LegacyAnimationProbe')];a=next(a for a in actors if a.actor_has_tag(req['clip']))
for other in actors:other.set_actor_hidden_in_game(other!=a)
pc=u.GameplayStatics.get_player_controller(w,0);pawn=pc.get_controlled_pawn();pawn.set_actor_enable_collision(False)
pawn.set_actor_location(a.get_actor_location()+u.Vector(210,-250,140),False,True);pc.set_control_rotation(u.Rotator(pitch=-20,yaw=126,roll=0))
anim=a.get_component_by_class(u.SkeletalMeshComponent).get_anim_instance();montage=u.load_asset('/Game/BluePrints/Characters/LegacyExpansion/Animations/AM_Legacy_'+req['clip'])
anim.montage_play(montage,1.);anim.montage_set_position(montage,req['position']);anim.montage_set_play_rate(montage,0.)
ticks=0
def tick(dt):
 global ticks
 ticks+=1
 if ticks<20:return
 u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.execute_console_command(w,'viewmode unlit',pc);u.SystemLibrary.execute_console_command(w,'HighResShot 1280x720',pc)
handle=u.register_slate_post_tick_callback(tick)
