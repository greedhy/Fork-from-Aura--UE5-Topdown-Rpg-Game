"""Unsaved, isolated animation probe; run only when PIE is stopped."""
import json
from pathlib import Path
import unreal as u

assert not u.EditorLevelLibrary.get_game_world(), 'Stop PIE before creating the probe'
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
retry=ed.get_editor_world().get_path_name().startswith('/Temp/') and any(a.actor_has_tag('SGAnimationProbe') for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors())
assert retry or not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'Existing map has unsaved changes'
location,rotation=u.EditorLevelLibrary.get_level_viewport_camera_info()
state={'map':ed.get_editor_world().get_path_name().split('.')[0],
       'location':[location.x,location.y,location.z],
       'rotation':[rotation.pitch,rotation.yaw,rotation.roll]}
if not retry:
    (Path(u.Paths.project_dir())/'Saved/GAAuthoring/StoneGolemBuild/probe-restore.json').write_text(json.dumps(state))
u.EditorLoadingAndSavingUtils.new_blank_map(False)
world=ed.get_editor_world()
world.get_world_settings().set_editor_property('default_game_mode',u.GameModeBase.static_class())
ss=u.get_editor_subsystem(u.EditorActorSubsystem)
R='/Game/BluePrints/Characters/StoneGolem/Animations/'
for index,kind in enumerate(['Slam','ShieldBash']):
    actor=ss.spawn_actor_from_class(u.Character,u.Vector(0,index*350,89))
    actor.set_actor_label('SG_AnimationProbe_'+kind)
    actor.set_editor_property('tags',['SGAnimationProbe',kind])
    actor.get_component_by_class(u.CapsuleComponent).set_capsule_half_height(89)
    actor.get_component_by_class(u.CharacterMovementComponent).set_movement_mode(u.MovementMode.MOVE_NONE)
    mesh=actor.get_component_by_class(u.SkeletalMeshComponent)
    mesh.set_skinned_asset_and_update(u.load_asset('/Game/StoneGolem/Mesh/SKM_StoneGolem'))
    mesh.set_relative_location(u.Vector(0,0,-89),False,False)
    mesh.set_relative_rotation(u.Rotator(pitch=0,yaw=-90,roll=0),False,False)
    mesh.set_anim_instance_class(u.EditorAssetLibrary.load_blueprint_class(R+'ABP_SG_Elite'))
    mesh.set_editor_property('visibility_based_anim_tick_option',u.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
    for part,socket in [('Hammer','weapon_rSocket'),('Shield','weapon_lSocket')]:
        prop=ss.spawn_actor_from_class(u.StaticMeshActor,u.Vector())
        prop.static_mesh_component.set_static_mesh(u.load_asset('/Game/StoneGolem/Mesh/SM_StoneGolem_'+part))
        prop.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
        prop.static_mesh_component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        prop.attach_to_component(mesh,socket,u.AttachmentRule.SNAP_TO_TARGET,u.AttachmentRule.SNAP_TO_TARGET,u.AttachmentRule.SNAP_TO_TARGET,False)
ss.clear_actor_selection_set()
