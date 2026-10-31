"""Isolated source model preview; no source assets or gameplay roster edits."""
import unreal as u,json
from pathlib import Path
assert not u.EditorLevelLibrary.get_game_world()
assert not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
root=Path(u.Paths.project_dir());dest=root/'Saved/GAAuthoring/LegacyMonsterDesign';dest.mkdir(parents=True,exist_ok=True)
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem);loc,rot=u.EditorLevelLibrary.get_level_viewport_camera_info()
(dest/'restore.json').write_text(json.dumps({'map':ed.get_editor_world().get_path_name().split('.')[0],'location':[loc.x,loc.y,loc.z],'rotation':[rot.pitch,rot.yaw,rot.roll]}))

u.EditorLoadingAndSavingUtils.new_blank_map(False)
ed.get_editor_world().get_world_settings().set_editor_property('default_game_mode',u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/StoneGolem/BP_SG_TestGameMode'))
ss=u.get_editor_subsystem(u.EditorActorSubsystem)
floor=ss.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-5));floor.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'));floor.set_actor_scale3d(u.Vector(40,40,.1));floor.set_actor_location(u.Vector(0,0,-5),False,True)
for i,(name,path,abp) in enumerate([('Spear','Goblin/BP_GoblinSpear','Spear'),('Sling','Goblin/BP_Goblin_Slinshot','Sling'),('GhoulL','Ghoul/BP_Ghoul','Ghoul'),('GhoulR','Ghoul/BP_Ghoul','Ghoul')]):
 cls=u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/'+path);a=ss.spawn_actor_from_class(cls,u.Vector(0,i*350,100))
 a.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED);a.set_editor_property('tags',['LegacyAnimationProbe',name])
 h=a.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height();a.set_actor_location(u.Vector(0,i*350,h+2),False,True)
 m=a.get_component_by_class(u.SkeletalMeshComponent);m.set_anim_instance_class(u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Characters/LegacyExpansion/Animations/ABP_Legacy_'+abp))
 m.set_editor_property('visibility_based_anim_tick_option',u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
ss.clear_actor_selection_set()
exec((root/'Saved/GAAuthoring/MonsterWave1/unthrottle_probe.py').read_text())
