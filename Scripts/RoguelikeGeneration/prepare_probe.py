"""Configure the isolated editor map for verify-request.json; never save test overrides.

Use {"restore": true} in the request to restore the original actor settings.
Failure injection uses a transient profile; shared source assets stay untouched.
"""
import builtins
import json
from pathlib import Path
import unreal as u


def main():
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert not levels.is_in_play_in_editor(), 'Stop PIE before configuring the probe'
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert world.get_path_name().split('.')[0] == '/Game/RoguelikeGeneration/Maps/L_DungeonGenerationProbe'
    runtimes = u.GameplayStatics.get_all_actors_of_class(world, u.DungeonGenerationRuntime)
    assert len(runtimes) == 1
    runtime = runtimes[0]
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    # Remove only unsaved QA actors created by this script on an earlier run.
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label() == 'RG_QADoorBlocker' and u.Name('RG_ProbeQA') in actor.tags:
            actors.destroy_actor(actor)
    request = json.loads((Path(u.Paths.project_dir()) / 'Saved/RoguelikeGeneration/verify-request.json').read_text(encoding='utf-8-sig'))
    original = getattr(builtins, '_roguelike_probe_original', None)
    if original is None:
        original = {key: runtime.get_editor_property(key) for key in ('seed', 'expected_players', 'profile')}
        builtins._roguelike_probe_original = original
    for key, value in original.items():
        runtime.set_editor_property(key, value)
    if request.get('restore'):
        builtins._roguelike_probe_original = None
        u.log('DUNGEON_PROBE_CONFIG_RESTORED')
        return
    runtime.set_editor_property('seed', int(request.get('seed', 42)))
    runtime.set_editor_property('expected_players', int(request.get('expected_players', 1)))
    if request.get('blocked_door'):
        # Seed 42's non-entrance seam joins (0,-2400) to (-2400,-2400).
        assert int(request.get('seed', 42)) == 42, 'The blocker fixture is authored for seed 42'
        actor = actors.spawn_actor_from_class(u.StaticMeshActor, u.Vector(-1200, -2400, 140))
        actor.set_actor_label('RG_QADoorBlocker')
        actor.tags = [u.Name('RG_ProbeQA')]
        component = actor.static_mesh_component
        component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
        actor.set_actor_scale3d(u.Vector(1, 8, 2.8))
        actor.set_actor_location(u.Vector(-1200, -2400, 140), False, True)
        component.set_collision_profile_name('InvisibleWall')
        component.set_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY, u.CollisionResponseType.ECR_IGNORE)
        component.set_editor_property('can_ever_affect_navigation', False)
    if request.get('missing_template'):
        source = original['profile']
        profile = u.new_object(u.DungeonGenerationProfile)
        for key in ('room_spacing', 'ready_timeout', 'entrance', 'templates'):
            profile.set_editor_property(key, source.get_editor_property(key))
        templates = list(profile.get_editor_property('templates'))
        template = u.DungeonRoomTemplate()
        template.import_text('(TemplateId="Combat",Role=Combat,Level="/Game/RoguelikeGeneration/Missing.Missing",DoorMask=15,AllowedRotations=15)')
        templates = [template if t.get_editor_property('role') == u.DungeonRoomRole.COMBAT else t for t in templates]
        profile.set_editor_property('templates', templates)
        runtime.set_editor_property('profile', profile)
    u.log('DUNGEON_PROBE_CONFIGURED ' + json.dumps(request))


main()
