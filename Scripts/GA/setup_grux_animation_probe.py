"""Isolated source model preview; no source assets or gameplay roster edits."""
import unreal as u,json
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
root=Path(u.Paths.project_dir());dest=root/'Saved/GAAuthoring/GruxDesign';dest.mkdir(parents=True,exist_ok=True)
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);loc,rot=u.EditorLevelLibrary.get_level_viewport_camera_info()
(dest/'restore.json').write_text(json.dumps({'map':ed.get_editor_world().get_path_name().split('.')[0],'location':[loc.x,loc.y,loc.z],'rotation':[rot.pitch,rot.yaw,rot.roll]}))
base='/Game/ParagonGrux/Characters/Heroes/Grux'
mesh=u.load_asset(base+'/Meshes/Grux');anim=u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/Grux/Expansion/Animations/ABP_Grux_Enemy')
assert mesh and anim
u.EditorLoadingAndSavingUtils.new_blank_map(False)
ed.get_editor_world().get_world_settings().set_editor_property('default_game_mode',u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/StoneGolem/BP_SG_TestGameMode'))
ss=u.get_editor_subsystem(u.EditorActorSubsystem)
floor=ss.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-5));floor.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'));floor.set_actor_scale3d(u.Vector(40,40,.1));floor.set_actor_location(u.Vector(0,0,-5),False,True);floor.set_editor_property('tags',['GruxAnimationProbe'])
for i,name in enumerate(['PrimaryAttack_LA','PrimaryAttack_RA','Stampede_Knockup','Ultimate_Roar']):
 a=ss.spawn_actor_from_class(u.Character,u.Vector(0,i*400,130));a.set_actor_location(u.Vector(0,i*400,130),False,True)
 a.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED);a.set_editor_property('tags',['GruxAnimationProbe',name])
 a.get_component_by_class(u.CapsuleComponent).set_capsule_size(55,130)
 m=a.get_component_by_class(u.SkeletalMeshComponent);m.set_skeletal_mesh_asset(mesh);m.set_relative_location(u.Vector(0,0,-130),False,True);m.set_relative_rotation(u.Rotator(yaw=-90),False,True);m.set_anim_instance_class(anim)
 m.set_editor_property('visibility_based_anim_tick_option',u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
ss.clear_actor_selection_set()
