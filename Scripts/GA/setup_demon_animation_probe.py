"""Create an isolated unsaved world to verify actual Demon AnimBP slot playback."""
import unreal as u,json
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
loc,rot=u.EditorLevelLibrary.get_level_viewport_camera_info()
out=Path(u.Paths.project_dir())/'Saved/GAAuthoring/MonsterWave1'
(out/'demon-probe-restore.json').write_text(json.dumps({'map':ed.get_editor_world().get_path_name().split('.')[0],'location':[loc.x,loc.y,loc.z],'rotation':[rot.pitch,rot.yaw,rot.roll]}))
u.EditorLoadingAndSavingUtils.new_blank_map(False)
ed.get_editor_world().get_world_settings().set_editor_property('default_game_mode',u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/StoneGolem/BP_SG_TestGameMode'))
ss=u.get_editor_subsystem(u.EditorActorSubsystem)
floor=ss.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-5))
floor.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
floor.set_actor_scale3d(u.Vector(30,30,.1));floor.set_editor_property('tags',['DemonAnimationProbe'])
floor.set_actor_location(u.Vector(0,0,-5),False,True)
for i,clip in enumerate(['ClawL','ClawR','Tailspin']):
 a=ss.spawn_actor_from_class(u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/Demon/BP_Demon_Warrior'),u.Vector(0,i*350,100))
 a.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
 a.set_actor_location(u.Vector(0,i*350,100),False,True)
 a.set_editor_property('tags',['Enemy','DemonAnimationProbe',clip])
 a.set_actor_label('DemonProbe_'+clip)
 a.get_component_by_class(u.SkeletalMeshComponent).set_editor_property('visibility_based_anim_tick_option',u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
ss.clear_actor_selection_set()
