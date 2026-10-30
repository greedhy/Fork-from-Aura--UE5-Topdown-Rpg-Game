"""Create only the isolated three-room assembly assets through Unreal Editor Python.

Run after compiling/restarting the editor with the Roguelike classes. The caller
must hold the editor's world:current exclusive MCP lock. Existing complete output
is inspected, never rewritten. Partial output is reported for explicit repair.
"""


def main():
    import json
    import math
    import sys
    from pathlib import Path
    import unreal as u
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import floor_visual_style as visual_style

    base = '/Game/RoguelikeGeneration'
    paths = {
        'combat': base + '/Rooms/L_ProbeCombat',
        'boss': base + '/Rooms/L_ProbeBoss',
        'profile': base + '/DA_DungeonAssemblyProbe',
        'controller': base + '/BP_DungeonGenerationController',
        'mode': base + '/BP_DungeonGenerationGameMode',
        'host': base + '/Maps/L_DungeonGenerationProbe',
    }
    schema = 'assembly-probe-v1'
    entry_group = 'RG_Entrance'
    report_dir = Path(u.Paths.project_dir()).resolve() / 'Saved/RoguelikeGeneration'
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'phase': 'preflight', 'assets': paths,
              'created': [], 'schema': schema, 'room_spacing_cm': 2400,
              'door_width_cm': 800, 'cook_maps': [paths[k] for k in ('host', 'combat', 'boss')]}
    tools = u.AssetToolsHelpers.get_asset_tools()
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    mesh_cache = {}

    def dirty_packages():
        return list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + list(
            u.EditorLoadingAndSavingUtils.get_dirty_content_packages())

    def require_clean():
        dirty = dirty_packages()
        if dirty:
            raise RuntimeError('UnsavedPackages: ' + ', '.join(p.get_name() for p in dirty))

    def require_own_dirty():
        foreign = [p.get_name() for p in dirty_packages()
                   if not p.get_name().startswith(base + '/')]
        if foreign:
            raise RuntimeError('ForeignPackagesBecameDirty: ' + ', '.join(foreign))

    def current_world_path():
        return editor.get_editor_world().get_path_name().split('.')[0]

    def tag_asset(asset):
        if not asset.get_path_name().startswith(base + '/'):
            raise RuntimeError('RefusingToWriteOutsideProbe: ' + asset.get_path_name())
        u.EditorAssetLibrary.set_metadata_tag(asset, 'RoguelikeGenerationSchema', schema)

    def save_asset(asset):
        require_own_dirty()
        tag_asset(asset)
        if not u.EditorAssetLibrary.save_loaded_asset(asset, False):
            raise RuntimeError('AssetSaveFailed: ' + asset.get_path_name())
        report['created'].append(asset.get_path_name())

    def save_world(path):
        require_own_dirty()
        if current_world_path() != path:
            raise RuntimeError('WrongWorldBeforeSave: ' + current_world_path())
        tag_asset(editor.get_editor_world())
        if not levels.save_current_level():
            raise RuntimeError('MapSaveFailed: ' + path)
        report['created'].append(path)
        require_clean()

    def generated_class(blueprint):
        result = u.load_class(None, blueprint.get_path_name() + '_C')
        if not result:
            raise RuntimeError('BlueprintHasNoGeneratedClass: ' + blueprint.get_path_name())
        return result

    def duplicate_blueprint(source_path, destination, parent=None):
        source = u.load_asset(source_path)
        name = destination.rsplit('/', 1)[-1]
        asset = tools.duplicate_asset(name, destination.rsplit('/', 1)[0], source)
        if not asset:
            raise RuntimeError('DuplicateFailed: ' + destination)
        if parent is not None:
            u.BlueprintEditorLibrary.reparent_blueprint(asset, parent)
        u.BlueprintEditorLibrary.compile_blueprint(asset)
        return asset, u.get_default_object(generated_class(asset))

    def register(actor, label, group):
        if not actor:
            raise RuntimeError('ActorCreationFailed: ' + label)
        actor.set_actor_label('RG_' + label)
        actor.set_folder_path('RoguelikeGeneration/' + group)
        actor.tags = [u.Name('RG_Probe')]
        return actor

    def mesh(name):
        if name not in mesh_cache:
            mesh_cache[name] = u.load_asset('/Game/Assets/Dungeon/' + name)
            if not mesh_cache[name]:
                raise RuntimeError('SourceMeshMissing: ' + name)
        return mesh_cache[name]

    def box(name, label, x, y, bottom, width, depth, height,
            group, yaw=0, hidden=False):
        asset = mesh(name)
        bounds = asset.get_bounding_box()
        size = bounds.max - bounds.min
        if min(size.x, size.y) <= 0:
            raise RuntimeError('InvalidSourceMeshBounds: ' + name)
        scale = u.Vector(width / size.x, depth / size.y,
                         height / size.z if size.z > .1 else 1)
        mx = (bounds.min.x + bounds.max.x) * .5 * scale.x
        my = (bounds.min.y + bounds.max.y) * .5 * scale.y
        angle = math.radians(yaw)
        location = u.Vector(x - mx * math.cos(angle) + my * math.sin(angle),
                            y - mx * math.sin(angle) - my * math.cos(angle),
                            bottom - bounds.min.z * scale.z)
        actor = register(actors.spawn_actor_from_class(
            u.StaticMeshActor, location, u.Rotator(pitch=0, yaw=yaw, roll=0)), label, group)
        component = actor.static_mesh_component
        component.set_static_mesh(asset)
        actor.set_actor_scale3d(scale)
        component.set_mobility(u.ComponentMobility.STATIC)
        component.set_collision_profile_name('BlockAll')
        if hidden:
            component.set_visibility(False)
            component.set_editor_property('cast_shadow', False)
            actor.set_actor_hidden_in_game(True)
        return actor

    def room_geometry(role):
        # Footprint is exactly [-1200, 1200] in XY. Door openings are [-400, 400].
        box('SM_Block4x4x1', role + '_Foundation', 0, 0, -200,
            2400, 2400, 200, 'Foundation')
        for ix, x in enumerate((-600, 600)):
            for iy, y in enumerate((-600, 600)):
                box('SM_Tile_6x6', '%s_Floor_%d_%d' % (role, ix, iy),
                    x, y, 1, 1200, 1200, 1, 'Floor')
        for side in (-1, 1):
            for segment in (-800, 800):
                for axis in ('X', 'Y'):
                    x, y, yaw = ((side * 1150, segment, 90) if axis == 'X'
                                 else (segment, side * 1150, 0))
                    label = '%s_%s_%d_%d' % (role, axis, side, segment)
                    box('SM_Wall_4x2', label + '_Wall', x, y, 0,
                        800, 100, 280, 'Walls', yaw)
                    # This kit's visible walls do not consistently provide simple collision.
                    box('SM_Block4x4x1', label + '_Collision', x, y, 0,
                        800, 100, 280, 'Collision', yaw, True)
        # Corner furniture leaves every door-to-centre lane and the centre itself clear.
        offsets = ((-800, -800), (800, 800)) if role == 'Combat' else (
            (-800, -800), (-800, 800), (800, -800), (800, 800))
        for index, (x, y) in enumerate(offsets):
            box('SM_Block_1x1x2', role + '_Pillar_%d' % index,
                x, y, 0, 160, 160, 330, 'Details')
        marker = register(actors.spawn_actor_from_class(u.TargetPoint, u.Vector(0, 0, 30)),
                          role + '_Centre', 'Markers')
        marker.tags = [u.Name('RG_Probe'), u.Name('RG_Room_' + role)]
        text = register(actors.spawn_actor_from_class(
            u.TextRenderActor, u.Vector(-330, -750, 3),
            u.Rotator(pitch=90, yaw=0, roll=0)), role + '_Label', 'Markers')
        text_component = text.get_component_by_class(u.TextRenderComponent)
        text_component.set_text(role.upper())
        text_component.set_world_size(95)

    def new_room_map(path, role):
        require_clean()
        if not levels.new_level(path, False):
            raise RuntimeError('MapCreationFailed: ' + path)
        room_geometry(role)
        # Streamed templates contain no gameplay actors, PlayerStarts, or navigation volumes.
        editor.get_editor_world().get_world_settings().set_editor_property('default_game_mode', None)
        save_world(path)

    def make_template(template_id, role, path=None, rotations=15):
        value = u.DungeonRoomTemplate()
        value.set_editor_property('template_id', u.Name(template_id))
        value.set_editor_property('role', role)
        value.set_editor_property('door_mask', 15)
        value.set_editor_property('allowed_rotations', rotations)
        if path:
            # The native property stores a soft reference, so no world is held by the profile.
            value.set_editor_property('level', u.load_asset(path))
        return value

    def validate_world(path, host):
        require_clean()
        if not levels.load_level(path):
            raise RuntimeError('SavedMapCouldNotBeOpened: ' + path)
        world = editor.get_editor_world()
        owned = [a for a in actors.get_all_level_actors() if u.Name('RG_Probe') in a.tags]
        if not owned:
            raise RuntimeError('ProbeGeometryMissing: ' + path)
        assert not visual_style.floor_errors(world), 'FloorVisualContractMismatch: '+path
        result = {'map': path, 'owned_actor_count': len(owned)}
        starts = u.GameplayStatics.get_all_actors_of_class(world, u.PlayerStart)
        runtimes = u.GameplayStatics.get_all_actors_of_class(world, u.DungeonGenerationRuntime)
        bounds = u.GameplayStatics.get_all_actors_of_class(world, u.NavMeshBoundsVolume)
        if host:
            if len(starts) != 2 or len(runtimes) != 1 or len(bounds) != 1:
                raise RuntimeError('HostSetupIncomplete: ' + path)
            if any(not isinstance(start, u.TravelPlayerStart) for start in starts):
                raise RuntimeError('HostRequiresTravelPlayerStarts')
            if any(str(start.get_editor_property('player_start_tag')) != entry_group
                   or not start.get_editor_property('default_entry_group') for start in starts):
                raise RuntimeError('HostArrivalGroupMismatch')
            slots = sorted(start.get_editor_property('player_slot') for start in starts)
            if slots != [0, 1]:
                raise RuntimeError('HostArrivalSlotsMismatch: ' + str(slots))
            for start in starts:
                location = start.get_actor_location()
                expected_x = -300 if start.get_editor_property('player_slot') == 0 else 300
                if max(abs(location.x - expected_x), abs(location.y + 300), abs(location.z - 110)) > .1:
                    raise RuntimeError('HostArrivalLocationMismatch: ' + start.get_actor_label())
            if runtimes[0].get_editor_property('profile') != u.load_asset(paths['profile']):
                raise RuntimeError('HostProfileMismatch')
            _, extent = bounds[0].get_actor_bounds(False)
            if extent.x < 7199 or extent.y < 7199 or extent.z < 799:
                raise RuntimeError('InvalidNavigationBrushBounds: ' + str(extent))
            navs = u.GameplayStatics.get_all_actors_of_class(world, u.RecastNavMesh)
            if len(navs) != 1 or navs[0].get_editor_property('runtime_generation') != u.RuntimeGenerationType.DYNAMIC:
                raise RuntimeError('DynamicNavigationNotConfigured')
            mode = u.load_class(None, paths['mode'] + '.' + paths['mode'].rsplit('/', 1)[-1] + '_C')
            if world.get_world_settings().get_editor_property('default_game_mode') != mode:
                raise RuntimeError('HostGameModeMismatch')
            if str(u.get_default_object(mode).get_editor_property('default_player_start_tag')) != entry_group:
                raise RuntimeError('HostGameModeArrivalGroupMismatch')
            result.update(player_starts=len(starts), navigation_extent_cm=[extent.x, extent.y, extent.z],
                          navigation_mode='Dynamic', expected_players=runtimes[0].get_editor_property('expected_players'),
                          arrival_group=entry_group, player_slots=slots, player_start_type='TravelPlayerStart')
        elif starts or runtimes or bounds:
            raise RuntimeError('StreamedTemplateContainsHostActors: ' + path)
        elif world.get_world_settings().get_editor_property('default_game_mode') is not None:
            raise RuntimeError('StreamedTemplateOverridesGameMode: ' + path)
        if u.GameplayStatics.get_all_actors_of_class(world, u.PureMassSpawnRegion):
            raise RuntimeError('ProbeMustNotAutoSpawnEnemies: ' + path)
        return result

    def validate_complete():
        for path in paths.values():
            asset = u.load_asset(path)
            if not asset or u.EditorAssetLibrary.get_metadata_tag(asset, 'RoguelikeGenerationSchema') != schema:
                raise RuntimeError('OutputSchemaMismatch: ' + path)
        asset = None
        profile = u.load_asset(paths['profile'])
        if not isinstance(profile, u.DungeonGenerationProfile):
            raise RuntimeError('ProfileClassMismatch')
        if abs(profile.get_editor_property('room_spacing') - 2400) > .1:
            raise RuntimeError('ProfileFootprintMismatch')
        if abs(profile.get_editor_property('ready_timeout') - 30) > .1:
            raise RuntimeError('ProfileReadyTimeoutMismatch')
        entrance = profile.get_editor_property('entrance')
        if (str(entrance.get_editor_property('template_id')) != 'Entrance'
                or entrance.get_editor_property('role') != u.DungeonRoomRole.ENTRANCE
                or entrance.get_editor_property('level') is not None
                or entrance.get_editor_property('door_mask') != 15
                or entrance.get_editor_property('allowed_rotations') != 1):
            raise RuntimeError('ProfileEntranceMismatch')
        templates = profile.get_editor_property('templates')
        if (len(templates) != 2
                or {str(t.get_editor_property('template_id')) for t in templates} != {'Combat', 'Boss'}):
            raise RuntimeError('ProfileTemplateSetMismatch')
        for template in templates:
            name = str(template.get_editor_property('template_id'))
            template_level = template.get_editor_property('level')
            if (template.get_editor_property('role') != getattr(u.DungeonRoomRole, name.upper())
                    or template.get_editor_property('door_mask') != 15
                    or template.get_editor_property('allowed_rotations') != 15
                    or not template_level
                    or template_level.get_path_name().split('.')[0] != paths[name.lower()]):
                raise RuntimeError('ProfileTemplateMismatch: ' + name)
        template = template_level = None
        pc = u.load_asset(paths['controller'])
        pc_default = u.get_default_object(generated_class(pc))
        if not isinstance(pc_default, u.DungeonGenerationController):
            raise RuntimeError('ControllerParentMismatch')
        gm = u.get_default_object(generated_class(u.load_asset(paths['mode'])))
        if gm.get_editor_property('player_controller_class') != generated_class(pc):
            raise RuntimeError('GameModeControllerMismatch')
        if str(gm.get_editor_property('default_player_start_tag')) != entry_group:
            raise RuntimeError('GameModeArrivalGroupMismatch')
        source_gm = u.get_default_object(generated_class(u.load_asset('/Game/PureMass/BP_PureMassGameMode')))
        for key in ('default_pawn_class', 'hud_class', 'ability_info'):
            if gm.get_editor_property(key) != source_gm.get_editor_property(key):
                raise RuntimeError('GameModeConfigurationChanged: ' + key)
        # Release Python world references before changing the current editor world.
        profile = entrance = templates = pc = pc_default = gm = source_gm = None
        worlds = [validate_world(paths['combat'], False), validate_world(paths['boss'], False),
                  validate_world(paths['host'], True)]
        require_clean()
        return worlds

    try:
        require_clean()
        if levels.is_in_play_in_editor():
            raise RuntimeError('StopPIEBeforeAuthoring')
        if current_world_path().startswith('/Temp/'):
            raise RuntimeError('OpenASavedMapBeforeAuthoring')
        for name in ('DungeonRoomTemplate', 'DungeonRoomRole', 'DungeonGenerationProfile',
                     'DungeonGenerationRuntime', 'DungeonGenerationController', 'TravelPlayerStart'):
            if not hasattr(u, name):
                raise RuntimeError('NativeClassMissingCompileAndRestart: ' + name)
        for source in ('/Game/PureMass/BP_MassPlayerController', '/Game/PureMass/BP_PureMassGameMode'):
            if not u.EditorAssetLibrary.does_asset_exist(source):
                raise RuntimeError('SourceAssetMissing: ' + source)
        for name in ('SM_Block4x4x1', 'SM_Tile_6x6', 'SM_Wall_4x2', 'SM_Block_1x1x2'):
            mesh(name)
        present = [path for path in paths.values() if u.EditorAssetLibrary.does_asset_exist(path)]
        if present:
            if len(present) != len(paths):
                raise RuntimeError('PartialProbeOutputRequiresInspection: ' + ', '.join(present))
            report['phase'] = 'validate_existing'
            report['worlds'] = validate_complete()
            report.update(passed=True, reused_existing=True, phase='complete')
            return report

        reference_lighting = visual_style.capture_reference()
        report['phase'] = 'controller_and_mode'
        pc, pc_default = duplicate_blueprint('/Game/PureMass/BP_MassPlayerController',
                                             paths['controller'], u.DungeonGenerationController)
        save_asset(pc)
        mode, mode_default = duplicate_blueprint('/Game/PureMass/BP_PureMassGameMode', paths['mode'])
        mode_default.set_editor_property('player_controller_class', generated_class(pc))
        mode_default.set_editor_property('default_player_start_tag', u.Name(entry_group))
        u.BlueprintEditorLibrary.compile_blueprint(mode)
        save_asset(mode)
        pc = pc_default = mode = mode_default = None
        require_clean()

        report['phase'] = 'room_templates'
        new_room_map(paths['combat'], 'Combat')
        new_room_map(paths['boss'], 'Boss')

        report['phase'] = 'host_and_profile'
        require_clean()
        if not levels.new_level(paths['host'], False):
            raise RuntimeError('HostMapCreationFailed')
        room_geometry('Entrance')
        for index, x in enumerate((-300, 300)):
            start = register(actors.spawn_actor_from_class(u.TravelPlayerStart, u.Vector(x, -300, 110)),
                             'PlayerStart_%d' % index, 'Gameplay')
            # The editor's PlayerStart factory may lift the actor; fix its authored capsule origin.
            start.set_actor_location(u.Vector(x, -300, 110), False, True)
            start.set_editor_property('player_start_tag', u.Name(entry_group))
            start.set_editor_property('player_slot', index)
            start.set_editor_property('default_entry_group', True)
        visual_style.apply_environment(editor.get_editor_world(), reference_lighting)
        nav = register(actors.spawn_actor_from_class(u.NavMeshBoundsVolume, u.Vector(0, 0, 400)),
                       'NavigationBounds', 'Navigation')
        _, extent = nav.get_actor_bounds(False)
        if min(extent.x, extent.y, extent.z) <= 0:
            raise RuntimeError('NavigationVolumeFactoryDidNotCreateBrush')
        nav.set_actor_scale3d(u.Vector(7200 / extent.x, 7200 / extent.y, 800 / extent.z))
        world = editor.get_editor_world()
        navs = list(u.GameplayStatics.get_all_actors_of_class(world, u.RecastNavMesh))
        if not navs:
            navs = [register(actors.spawn_actor_from_class(u.RecastNavMesh, u.Vector(0, 0, 0)),
                             'RecastNavMesh', 'Navigation')]
        if len(navs) != 1:
            raise RuntimeError('MultipleNavigationDataActors')
        navs[0].set_editor_property('runtime_generation', u.RuntimeGenerationType.DYNAMIC)
        factory = u.DataAssetFactory()
        factory.set_editor_property('data_asset_class', u.DungeonGenerationProfile)
        profile = tools.create_asset(paths['profile'].rsplit('/', 1)[-1], base,
                                     u.DungeonGenerationProfile, factory)
        if not profile:
            raise RuntimeError('ProfileCreationFailed')
        profile.set_editor_property('room_spacing', 2400.0)
        profile.set_editor_property('ready_timeout', 30.0)
        profile.set_editor_property('entrance', make_template('Entrance', u.DungeonRoomRole.ENTRANCE, rotations=1))
        profile.set_editor_property('templates', [
            make_template('Combat', u.DungeonRoomRole.COMBAT, paths['combat']),
            make_template('Boss', u.DungeonRoomRole.BOSS, paths['boss'])])
        save_asset(profile)
        runtime = register(actors.spawn_actor_from_class(u.DungeonGenerationRuntime, u.Vector(0, 0, 0)),
                           'GenerationRuntime', 'Gameplay')
        runtime.set_editor_property('profile', profile)
        runtime.set_editor_property('seed', 42)
        runtime.set_editor_property('expected_players', 1)
        world.get_world_settings().set_editor_property('default_game_mode', u.load_class(
            None, paths['mode'] + '.' + paths['mode'].rsplit('/', 1)[-1] + '_C'))
        world.get_world_settings().set_editor_property('kill_z', -3000.0)
        save_world(paths['host'])
        # Locals holding actors/worlds must be released before validate_complete changes maps.
        world = nav = navs = start = actor = light = runtime = profile = factory = None
        report['phase'] = 'validate_saved_output'
        report['worlds'] = validate_complete()
        report.update(passed=True, reused_existing=False, phase='complete')
        return report
    except Exception as exc:
        report['error'] = repr(exc)
        raise
    finally:
        report['dirty_packages'] = [p.get_name() for p in dirty_packages()]
        (report_dir / 'authoring.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        u.log('ROGUELIKE_PROBE_AUTHORING ' + json.dumps(report, ensure_ascii=False))


main()
