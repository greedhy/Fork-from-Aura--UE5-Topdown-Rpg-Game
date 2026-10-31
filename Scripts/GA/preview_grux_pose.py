"""Freeze requested authored montage position on actual mesh, capture real PIE viewport."""
import unreal as u,json
from pathlib import Path
root=Path(u.Paths.project_dir());request=json.loads((root/'Saved/GAAuthoring/GruxDesign/preview-request.json').read_text(encoding='utf-8-sig'))
w=u.EditorLevelLibrary.get_game_world();assert w and w.get_path_name().startswith('/Temp/')
actors=[a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Character) if a.actor_has_tag('GruxAnimationProbe')]
a=next(a for a in actors if a.actor_has_tag(request['source']))
for other in actors:other.set_actor_hidden_in_game(other!=a)
pc=u.GameplayStatics.get_player_controller(w,0);pawn=pc.get_controlled_pawn();pawn.set_actor_enable_collision(False)
p=a.get_actor_location();pawn.set_actor_location(p+u.Vector(340,-450,170),False,True);pc.set_control_rotation(u.Rotator(pitch=-15,yaw=128,roll=0))
m=a.get_component_by_class(u.SkeletalMeshComponent);anim=m.get_anim_instance();montage=u.load_asset('/Game/BluePrints/Characters/Grux/Expansion/Animations/AM_Grux_'+request['clip'])
anim.montage_play(montage,1.);anim.montage_set_position(montage,request['position']);anim.montage_set_play_rate(montage,0.)
ticks=0
def capture(dt):
 global ticks
 ticks+=1
 if ticks<20:return
 u.unregister_slate_post_tick_callback(grux_preview_handle)
 u.SystemLibrary.execute_console_command(w,'viewmode unlit',pc);u.SystemLibrary.execute_console_command(w,'HighResShot 1280x720',pc)
grux_preview_handle=u.register_slate_post_tick_callback(capture)
