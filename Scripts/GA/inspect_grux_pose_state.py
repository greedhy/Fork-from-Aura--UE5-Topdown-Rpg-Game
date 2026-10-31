import unreal as u,json
from pathlib import Path
w=u.EditorLevelLibrary.get_game_world();a=next(a for a in u.GameplayStatics.get_all_actors_of_class(w,u.GruxEnemyCharacter) if a.actor_has_tag('SGSource'));m=a.get_component_by_class(u.SkeletalMeshComponent)
d={'actor':str(a.get_actor_transform()),'mesh_relative':str(m.get_relative_transform()),'simulates':m.is_simulating_physics(),'anim':str(m.get_anim_instance().get_class()),'mode':str(m.get_editor_property('animation_mode')),'cdo_rotation':str(u.get_default_object(a.get_class()).get_component_by_class(u.SkeletalMeshComponent).get_editor_property('relative_rotation'))}
for b in ['root','pelvis','head','foot_l','foot_r']:
 d[b]=str(a.get_actor_transform().inverse_transform_location(m.get_socket_location(b)))
(Path(u.Paths.project_dir())/'Saved/GAAuthoring/GruxDesign/pose-state.json').write_text(json.dumps(d,indent=2))
