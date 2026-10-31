import unreal as u,json
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world();assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
root=Path(u.Paths.project_dir());ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);loc,rot=u.EditorLevelLibrary.get_level_viewport_camera_info()
(root/'Saved/GAAuthoring/ShroomDesign/restore.json').write_text(json.dumps({'map':ed.get_editor_world().get_path_name().split('.')[0],'location':[loc.x,loc.y,loc.z],'rotation':[rot.pitch,rot.yaw,rot.roll]}))
u.EditorLoadingAndSavingUtils.new_blank_map(False)
ed.get_editor_world().get_world_settings().set_editor_property('default_game_mode',u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/StoneGolem/BP_SG_TestGameMode'))
ss=u.get_editor_subsystem(u.EditorActorSubsystem)
floor=ss.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-5));floor.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'));floor.set_actor_scale3d(u.Vector(25,25,.1));floor.set_actor_location(u.Vector(0,0,-5),False,True)
for i,name in enumerate(['Slam','Spore']):
 a=ss.spawn_actor_from_class(u.Character,u.Vector(0,i*400,55));a.set_actor_location(u.Vector(0,i*400,55),False,True);a.set_editor_property('tags',['ShroomAnimationProbe',name]);a.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
 a.get_component_by_class(u.CapsuleComponent).set_capsule_size(45,55)
 m=a.get_component_by_class(u.SkeletalMeshComponent);m.set_skeletal_mesh_asset(u.load_asset('/Game/Assets/Enemies/Shroom/Mesh/SKM_Shroom'))
 m.set_relative_location(u.Vector(0,0,-55),False,True);m.set_relative_rotation(u.Rotator(yaw=-90),False,True)
 m.set_anim_instance_class(u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/Shroom/Expansion/Animations/ABP_Shroom_Enemy'))
 m.set_editor_property('visibility_based_anim_tick_option',u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
exec((root/'Saved/GAAuthoring/MonsterWave1/unthrottle_probe.py').read_text());ss.clear_actor_selection_set()
