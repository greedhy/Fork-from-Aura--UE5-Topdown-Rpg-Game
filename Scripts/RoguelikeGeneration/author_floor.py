"""Author the isolated full-floor template library after a native editor rebuild.

The caller holds the MCP world:current exclusive lock. Complete existing output
is validated without modification; partial output is left for inspection. This
script never edits the assembly-probe source maps or shared meshes/Blueprints.
"""


def main():
    import json
    import math
    from pathlib import Path
    import unreal as u

    base = '/Game/RoguelikeGeneration'
    source_room = base + '/Rooms/L_ProbeCombat'
    source_host = base + '/Maps/L_DungeonGenerationProbe'
    host_path = base + '/Maps/L_RoguelikeFloor'
    profile_path = base + '/DA_RoguelikeFloor'
    mode_path = base + '/BP_DungeonGenerationGameMode'
    ids = ('CombatA', 'CombatB', 'CombatC', 'CombatD', 'CombatE',
           'Treasure', 'Elite', 'Merchant', 'Rest', 'Boss')
    rooms = {name: base + '/Rooms/L_Floor_' + name for name in ids}
    outputs = set(rooms.values()) | {host_path, profile_path}
    schema = 'full-floor-v2'
    settings_values = {'main_rooms_min': 10, 'main_rooms_max': 12,
                       'side_rooms_min': 4, 'side_rooms_max': 6,
                       'branches_min': 2, 'branches_max': 3, 'grid_radius': 12,
                       'max_placement_attempts': 8, 'max_search_steps_per_attempt': 2000,
                       'allow_fallback': True}
    directory = Path(u.Paths.project_dir()).resolve() / 'Saved/RoguelikeGeneration'
    directory.mkdir(parents=True, exist_ok=True)
    report = {'passed': False, 'phase': 'preflight', 'schema': schema, 'created': [],
              'host': host_path, 'profile': profile_path, 'templates': rooms,
              'cook_maps': [host_path, *rooms.values()], 'room_spacing_cm': 2400,
              'door_width_cm': 800, 'navigation_extent_cm': [31200, 31200, 800]}
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    assets = u.AssetToolsHelpers.get_asset_tools()
    mesh_cache = {}

    def role(name):
        return 'Combat' if name.startswith('Combat') else name

    def dirty():
        return list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + list(
            u.EditorLoadingAndSavingUtils.get_dirty_content_packages())

    def clean():
        packages = dirty()
        if packages:
            raise RuntimeError('UnsavedPackages: ' + ', '.join(p.get_name() for p in packages))

    def own_dirty_only():
        foreign = [p.get_name() for p in dirty() if p.get_name() not in outputs]
        if foreign:
            raise RuntimeError('ForeignPackagesBecameDirty: ' + ', '.join(foreign))

    def current_path():
        return editor.get_editor_world().get_path_name().split('.')[0]

    def stamp(asset, template_id=None):
        if asset.get_path_name().split('.')[0] not in outputs:
            raise RuntimeError('WriteOutsideFloorOutput: ' + asset.get_path_name())
        u.EditorAssetLibrary.set_metadata_tag(asset, 'RoguelikeGenerationSchema', schema)
        if template_id:
            u.EditorAssetLibrary.set_metadata_tag(asset, 'RoguelikeTemplateId', template_id)

    def save_world(path, template_id=None):
        own_dirty_only()
        if current_path() != path:
            raise RuntimeError('WrongWorldBeforeSave: ' + current_path())
        stamp(editor.get_editor_world(), template_id)
        if not levels.save_current_level():
            raise RuntimeError('MapSaveFailed: ' + path)
        report['created'].append(path)
        clean()

    def clone_map(destination, source):
        clean()
        if not levels.new_level_from_template(destination, source):
            raise RuntimeError('MapCloneFailed: ' + destination)
        if current_path() != destination:
            raise RuntimeError('MapCloneSelectedWrongWorld')

    def mesh(name):
        if name not in mesh_cache:
            mesh_cache[name] = u.load_asset('/Game/Assets/Dungeon/' + name)
            if not mesh_cache[name]:
                raise RuntimeError('SourceMeshMissing: ' + name)
        return mesh_cache[name]

    def register(actor, label, group='Details'):
        if not actor:
            raise RuntimeError('ActorCreationFailed: ' + label)
        actor.set_actor_label('RF_' + label)
        actor.set_folder_path('RoguelikeFloor/' + group)
        actor.tags = [u.Name('RG_Floor')]
        return actor

    def box(name, label, x, y, width, depth, height, yaw=0):
        # All detail bounds stay in the corners: the centre and four door lanes
        # remain clear, including the generation validator's +/-200 cm samples.
        asset = mesh(name)
        bounds = asset.get_bounding_box()
        size = bounds.max - bounds.min
        if min(size.x, size.y, size.z) <= .1:
            raise RuntimeError('InvalidMeshBounds: ' + name)
        scale = u.Vector(width / size.x, depth / size.y, height / size.z)
        mx = (bounds.min.x + bounds.max.x) * .5 * scale.x
        my = (bounds.min.y + bounds.max.y) * .5 * scale.y
        angle = math.radians(yaw)
        location = u.Vector(x - mx * math.cos(angle) + my * math.sin(angle),
                            y - mx * math.sin(angle) - my * math.cos(angle), -bounds.min.z * scale.z)
        actor = register(actors.spawn_actor_from_class(
            u.StaticMeshActor, location, u.Rotator(pitch=0, yaw=yaw, roll=0)), label)
        actor.static_mesh_component.set_static_mesh(asset)
        actor.set_actor_scale3d(scale)
        actor.set_actor_location(location, False, True)
        actor.static_mesh_component.set_mobility(u.ComponentMobility.STATIC)
        actor.static_mesh_component.set_collision_profile_name('BlockAll')
        return actor

    def decorate(template_id):
        # Five different obstacle arrangements, rather than only different IDs.
        geometry = {
            'CombatA': [(-800, -800, 160, 160, 330), (800, 800, 160, 160, 330)],
            'CombatB': [(-800, -800, 220, 220, 290), (-800, 800, 220, 220, 290), (800, 800, 220, 220, 290)],
            'CombatC': [(x, y, 140, 140, 400) for x in (-800, 800) for y in (-800, 800)],
            'CombatD': [(-800, -800, 450, 180, 180), (800, 800, 180, 450, 180)],
            'CombatE': [(-800, -900, 420, 140, 220), (-900, -700, 140, 260, 220),
                        (800, 900, 420, 140, 220), (900, 700, 140, 260, 220)],
            'Treasure': [(-800, 800, 320, 320, 120), (800, -800, 200, 200, 80)],
            'Elite': [(-800, -800, 220, 220, 430), (800, 800, 220, 220, 430), (800, -800, 320, 180, 160)],
            'Merchant': [(-800, 800, 430, 220, 120), (800, 800, 430, 220, 120)],
            'Rest': [(-800, -800, 420, 180, 90), (-800, 800, 420, 180, 90), (800, 800, 160, 160, 150)],
            'Boss': [(x, y, 200, 200, 450) for x in (-800, 800) for y in (-800, 800)],
        }
        colours = {'Combat': (1, .55, .3), 'Treasure': (1, .85, .2), 'Elite': (1, .2, .1),
                   'Merchant': (.2, .8, 1), 'Rest': (.3, 1, .5), 'Boss': (.6, .3, 1)}
        for index, dimensions in enumerate(geometry[template_id]):
            box('SM_Block_1x1x2', template_id + '_Detail_' + str(index), *dimensions)
        marker = register(actors.spawn_actor_from_class(u.TargetPoint, u.Vector(0, 0, 30)),
                          template_id + '_Centre', 'Markers')
        marker.tags = [u.Name('RG_Floor'), u.Name('RG_Role_' + role(template_id)), u.Name('RG_Template_' + template_id)]
        text = register(actors.spawn_actor_from_class(u.TextRenderActor, u.Vector(-330, -650, 3),
                        u.Rotator(pitch=90, yaw=0, roll=0)), template_id + '_Label', 'Markers')
        text_component = text.get_component_by_class(u.TextRenderComponent)
        text_component.set_text(template_id.upper())
        text_component.set_world_size(90)
        colour = colours[role(template_id)]
        text_component.set_text_render_color(u.Color(*(int(v * 255) for v in colour), 255))

    def collision_floor():
        # Visual tiles meet at exact triangle edges. A solid, 1 cm overlapping
        # underlay keeps rotated instances watertight without changing the grid.
        cube = u.load_asset('/Engine/BasicShapes/Cube.Cube')
        if not cube:
            raise RuntimeError('CollisionCubeMissing')
        actor = register(actors.spawn_actor_from_class(u.StaticMeshActor, u.Vector(0, 0, -10)),
                         'CollisionFloor', 'Geometry')
        component = actor.static_mesh_component
        component.set_static_mesh(cube)
        component.set_mobility(u.ComponentMobility.STATIC)
        component.set_collision_profile_name('BlockAll')
        component.set_editor_property('cast_shadow', False)
        actor.set_actor_scale3d(u.Vector(24.02, 24.02, .2))
        actor.set_actor_location(u.Vector(0, 0, -10), False, True)
        actor.set_actor_hidden_in_game(True)

    def create_room(template_id):
        path = rooms[template_id]
        clone_map(path, source_room)
        for actor in list(actors.get_all_level_actors()):
            label = actor.get_actor_label()
            if u.Name('RG_Probe') not in actor.tags:
                continue
            if any(token in label for token in ('_Pillar_', '_Label', '_Glow', '_Centre')):
                actors.destroy_actor(actor)
            else:
                actor.set_actor_label('RF_' + template_id + '_' + label.removeprefix('RG_Combat_'))
                actor.tags = [u.Name('RG_Floor')]
        actor = None
        decorate(template_id)
        collision_floor()
        editor.get_editor_world().get_world_settings().set_editor_property('default_game_mode', None)
        save_world(path, template_id)

    def template(template_id, role_name, level_path=None):
        value = u.DungeonRoomTemplate()
        value.set_editor_property('template_id', u.Name(template_id))
        value.set_editor_property('role', getattr(u.DungeonRoomRole, role_name.upper()))
        value.set_editor_property('door_mask', 15)
        value.set_editor_property('allowed_rotations', 15 if level_path else 1)
        if level_path:
            value.set_editor_property('level', u.load_asset(level_path))
        return value

    def validate_world(path, template_id=None):
        clean()
        if not levels.load_level(path):
            raise RuntimeError('SavedMapLoadFailed: ' + path)
        world = editor.get_editor_world()
        all_actors = list(actors.get_all_level_actors())
        starts = list(u.GameplayStatics.get_all_actors_of_class(world, u.PlayerStart))
        runtimes = list(u.GameplayStatics.get_all_actors_of_class(world, u.DungeonGenerationRuntime))
        bounds = list(u.GameplayStatics.get_all_actors_of_class(world, u.NavMeshBoundsVolume))
        if u.GameplayStatics.get_all_actors_of_class(world, u.PureMassSpawnRegion):
            raise RuntimeError('FloorMustNotAutoSpawnEnemies: ' + path)
        result = {'map': path, 'actor_count': len(all_actors)}
        support = [a for a in all_actors if a.get_actor_label() == 'RF_CollisionFloor']
        if len(support) != 1:
            raise RuntimeError('CollisionFloorMissing: ' + path)
        origin, extent = support[0].get_actor_bounds(False)
        if (max(abs(origin.x), abs(origin.y), abs(origin.z + 10),
                abs(extent.x - 1201), abs(extent.y - 1201), abs(extent.z - 10)) > .1
                or str(support[0].static_mesh_component.get_collision_profile_name()) != 'BlockAll'):
            raise RuntimeError('CollisionFloorMismatch: ' + path)
        result['solid_collision_floor'] = True
        if template_id:
            if starts or runtimes or bounds or world.get_world_settings().get_editor_property('default_game_mode'):
                raise RuntimeError('TemplateContainsHostState: ' + path)
            centres = [a for a in all_actors if u.Name('RG_Template_' + template_id) in a.tags]
            if len(centres) != 1 or u.Name('RG_Role_' + role(template_id)) not in centres[0].tags:
                raise RuntimeError('TemplateRoleMarkerMismatch: ' + template_id)
            foundation = [a for a in all_actors if a.get_actor_label() == 'RF_' + template_id + '_Foundation']
            if len(foundation) != 1:
                raise RuntimeError('FoundationMissing: ' + template_id)
            origin, extent = foundation[0].get_actor_bounds(False)
            if max(abs(origin.x), abs(origin.y), abs(extent.x - 1200), abs(extent.y - 1200)) > .1:
                raise RuntimeError('TemplateFootprintMismatch: ' + template_id)
            details = [a for a in all_actors if a.get_actor_label().startswith('RF_' + template_id + '_Detail_')]
            if len(details) < 2:
                raise RuntimeError('TemplateDetailsMissing: ' + template_id)
            for detail in details:
                origin, extent = detail.get_actor_bounds(False)
                if (min(abs(origin.x) - extent.x, abs(origin.y) - extent.y) < 400
                        or max(abs(origin.x) + extent.x, abs(origin.y) + extent.y) > 1100):
                    raise RuntimeError('DetailObstructsDoorLane: ' + detail.get_actor_label())
            result.update(template=template_id, role=role(template_id), detail_count=len(details))
            return result
        if len(starts) != 2 or len(runtimes) != 1 or len(bounds) != 1:
            raise RuntimeError('HostSetupIncomplete')
        if any(not isinstance(start, u.TravelPlayerStart) for start in starts):
            raise RuntimeError('HostRequiresTravelPlayerStarts')
        if sorted(start.get_editor_property('player_slot') for start in starts) != [0, 1]:
            raise RuntimeError('HostArrivalSlotsMismatch')
        for start in starts:
            point = start.get_actor_location()
            expected_x = -300 if start.get_editor_property('player_slot') == 0 else 300
            if (str(start.get_editor_property('player_start_tag')) != 'RG_Entrance'
                    or not start.get_editor_property('default_entry_group')
                    or max(abs(point.x - expected_x), abs(point.y + 300), abs(point.z - 110)) > .1):
                raise RuntimeError('HostArrivalContractMismatch')
        runtime = runtimes[0]
        if (runtime.get_editor_property('profile') != u.load_asset(profile_path)
                or runtime.get_editor_property('seed') != 42
                or runtime.get_editor_property('expected_players') != 1
                or runtime.get_actor_location().length() > .1):
            raise RuntimeError('HostRuntimeConfigurationMismatch')
        _, extent = bounds[0].get_actor_bounds(False)
        if min(extent.x, extent.y) < 31199 or extent.z < 799:
            raise RuntimeError('InsufficientNavigationBrushBounds')
        navs = list(u.GameplayStatics.get_all_actors_of_class(world, u.RecastNavMesh))
        if len(navs) != 1 or navs[0].get_editor_property('runtime_generation') != u.RuntimeGenerationType.DYNAMIC:
            raise RuntimeError('DynamicNavigationNotConfigured')
        mode = u.load_class(None, mode_path + '.' + mode_path.rsplit('/', 1)[-1] + '_C')
        if world.get_world_settings().get_editor_property('default_game_mode') != mode:
            raise RuntimeError('HostGameModeMismatch')
        gm = u.get_default_object(mode)
        pc = u.get_default_object(gm.get_editor_property('player_controller_class'))
        if not isinstance(pc, u.DungeonGenerationController) or str(gm.get_editor_property('default_player_start_tag')) != 'RG_Entrance':
            raise RuntimeError('HostControllerOrEntryGroupMismatch')
        result.update(player_slots=[0, 1], navigation_extent_cm=[extent.x, extent.y, extent.z],
                      navigation_mode='Dynamic', seed=42, expected_players=1)
        return result

    def validate_complete():
        for path in sorted(outputs):
            asset = u.load_asset(path)
            if not asset or u.EditorAssetLibrary.get_metadata_tag(asset, 'RoguelikeGenerationSchema') != schema:
                raise RuntimeError('OutputSchemaMismatch: ' + path)
        asset = None
        profile = u.load_asset(profile_path)
        if (not isinstance(profile, u.DungeonGenerationProfile)
                or not profile.get_editor_property('generate_full_floor')
                or abs(profile.get_editor_property('room_spacing') - 2400) > .1
                or abs(profile.get_editor_property('ready_timeout') - 30) > .1):
            raise RuntimeError('ProfileConfigurationMismatch')
        settings = profile.get_editor_property('floor_settings')
        if any(settings.get_editor_property(key) != value for key, value in settings_values.items()):
            raise RuntimeError('FloorSettingsMismatch')
        entrance = profile.get_editor_property('entrance')
        if (str(entrance.get_editor_property('template_id')) != 'Entrance'
                or entrance.get_editor_property('role') != u.DungeonRoomRole.ENTRANCE
                or entrance.get_editor_property('level') is not None
                or entrance.get_editor_property('door_mask') != 15
                or entrance.get_editor_property('allowed_rotations') != 1):
            raise RuntimeError('PersistentEntranceMismatch')
        templates = profile.get_editor_property('templates')
        if len(templates) != 10 or {str(t.get_editor_property('template_id')) for t in templates} != set(ids):
            raise RuntimeError('TemplateLibraryMismatch')
        for item in templates:
            name = str(item.get_editor_property('template_id'))
            level = item.get_editor_property('level')
            if (item.get_editor_property('role') != getattr(u.DungeonRoomRole, role(name).upper())
                    or item.get_editor_property('door_mask') != 15
                    or item.get_editor_property('allowed_rotations') != 15
                    or not level or level.get_path_name().split('.')[0] != rooms[name]
                    or u.EditorAssetLibrary.get_metadata_tag(level, 'RoguelikeTemplateId') != name):
                raise RuntimeError('TemplateContractMismatch: ' + name)
        # Do not retain Python world/actor references while switching editor maps.
        profile = settings = entrance = templates = item = level = None
        results = [validate_world(rooms[name], name) for name in ids]
        results.append(validate_world(host_path))
        clean()
        return results

    def create_host_and_profile():
        clone_map(host_path, source_host)
        collision_floor()
        world = editor.get_editor_world()
        runtime = u.GameplayStatics.get_all_actors_of_class(world, u.DungeonGenerationRuntime)
        bounds = u.GameplayStatics.get_all_actors_of_class(world, u.NavMeshBoundsVolume)
        navs = u.GameplayStatics.get_all_actors_of_class(world, u.RecastNavMesh)
        if len(runtime) != 1 or len(bounds) != 1 or len(navs) != 1:
            raise RuntimeError('SourceProbeHostContractChanged')
        _, extent = bounds[0].get_actor_bounds(False)
        previous_scale = bounds[0].get_actor_scale3d()
        if min(extent.x, extent.y, extent.z) <= 0:
            raise RuntimeError('NavigationBrushMissing')
        bounds[0].set_actor_scale3d(u.Vector(previous_scale.x * 31200 / extent.x,
            previous_scale.y * 31200 / extent.y, previous_scale.z * 800 / extent.z))
        navs[0].set_editor_property('runtime_generation', u.RuntimeGenerationType.DYNAMIC)
        factory = u.DataAssetFactory()
        factory.set_editor_property('data_asset_class', u.DungeonGenerationProfile)
        profile = assets.create_asset('DA_RoguelikeFloor', base, u.DungeonGenerationProfile, factory)
        if not profile:
            raise RuntimeError('ProfileCreationFailed')
        profile.set_editor_property('generate_full_floor', True)
        profile.set_editor_property('room_spacing', 2400.0)
        profile.set_editor_property('ready_timeout', 30.0)
        settings = u.DungeonFloorSettings()
        for key, value in settings_values.items():
            settings.set_editor_property(key, value)
        profile.set_editor_property('floor_settings', settings)
        profile.set_editor_property('entrance', template('Entrance', 'Entrance'))
        profile.set_editor_property('templates', [template(name, role(name), rooms[name]) for name in ids])
        own_dirty_only()
        stamp(profile)
        if not u.EditorAssetLibrary.save_loaded_asset(profile, False):
            raise RuntimeError('ProfileSaveFailed')
        report['created'].append(profile_path)
        runtime[0].set_editor_property('profile', profile)
        runtime[0].set_editor_property('seed', 42)
        runtime[0].set_editor_property('expected_players', 1)
        save_world(host_path)

    try:
        clean()
        if levels.is_in_play_in_editor() or current_path().startswith('/Temp/'):
            raise RuntimeError('StopPIEAndOpenSavedMapBeforeAuthoring')
        for name in ('DungeonFloorSettings', 'DungeonGenerationProfile', 'DungeonRoomTemplate',
                     'DungeonGenerationRuntime', 'DungeonGenerationController', 'TravelPlayerStart'):
            if not hasattr(u, name):
                raise RuntimeError('NativeClassMissingCompileAndRestart: ' + name)
        for source in (source_room, source_host, mode_path):
            if not u.EditorAssetLibrary.does_asset_exist(source):
                raise RuntimeError('SourceAssetMissing: ' + source)
        mesh('SM_Block_1x1x2')
        present = sorted(path for path in outputs if u.EditorAssetLibrary.does_asset_exist(path))
        if present:
            if len(present) != len(outputs):
                raise RuntimeError('PartialFloorOutputRequiresInspection: ' + ', '.join(present))
            report['phase'] = 'validate_existing'
            report['worlds'] = validate_complete()
            report.update(passed=True, reused_existing=True, phase='complete')
            return report
        report['phase'] = 'room_templates'
        for name in ids:
            create_room(name)
        report['phase'] = 'host_and_profile'
        create_host_and_profile()
        report['phase'] = 'validate_saved_output'
        report['worlds'] = validate_complete()
        report.update(passed=True, reused_existing=False, phase='complete')
        return report
    except Exception as exc:
        report['error'] = repr(exc)
        raise
    finally:
        report['dirty_packages'] = [p.get_name() for p in dirty()]
        (directory / 'authoring-floor.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        u.log('ROGUELIKE_FLOOR_AUTHORING ' + json.dumps(report, ensure_ascii=False))


main()
