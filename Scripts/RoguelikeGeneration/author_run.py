"""Author the isolated stage-3 playable host after a native Editor rebuild.

The caller holds the editor's world:current exclusive lock and stops PIE first.
Only the nine declared output packages may be changed or saved. Complete output
is read back without compiling, stamping, or saving it; partial/schema-conflicting
output is left intact for inspection. This does not prove runtime GA activation.
"""


def main():
    import json
    from datetime import datetime, timezone
    from pathlib import Path
    from uuid import uuid4
    import unreal as u

    base = '/Game/RoguelikeGeneration'
    gameplay = base + '/Gameplay'
    paths = {
        'controller': gameplay + '/BP_DungeonRunController',
        'player': gameplay + '/BP_DungeonPlayer',
        'animation': gameplay + '/ABP_DungeonPlayer',
        'mode': gameplay + '/BP_DungeonRunGameMode',
        'elite': gameplay + '/BP_DungeonElite',
        'boss': gameplay + '/BP_DungeonBoss',
        'monster': gameplay + '/DA_DungeonGoblin',
        'profile': gameplay + '/DA_DungeonGameplay',
        'host': base + '/Maps/L_RoguelikeRun',
    }
    sources = {
        'host': base + '/Maps/L_RoguelikeFloor',
        'floor_profile': base + '/DA_RoguelikeFloor',
        'controller': base + '/BP_DungeonGenerationController',
        'mode': base + '/BP_DungeonGenerationGameMode',
        'pure_mass_mode': '/Game/PureMass/BP_PureMassGameMode',
        'elite': '/Game/BluePrints/Characters/Goblin/BP_GoblinSpear',
        'boss': '/Game/BluePrints/Characters/Demon/BP_Demon_Warrior',
        'monster': '/Game/PureMass/DA_MassGoblin',
        'catalog': '/Game/BluePrints/DA/DA_BackpackItemDefinitions',
    }
    template_ids = ('CombatA', 'CombatB', 'CombatC', 'CombatD', 'CombatE',
                    'Treasure', 'Elite', 'Merchant', 'Rest', 'Boss')
    templates = [base + '/Rooms/L_Floor_' + name for name in template_ids]
    outputs = set(paths.values())
    schema = 'roguelike-run-v1'
    schema_key = 'RoguelikeGenerationSchema'
    profile_values = {
        'combat_coins': 15, 'elite_coins': 30, 'boss_coins': 50,
        'elite_health': 450.0, 'boss_health': 1500.0,
        'boss_pulse_damage': 20.0, 'boss_pulse_radius': 550.0,
        'revive_fraction': .3,
    }
    item_prices = (('HealthPotion', 30), ('ManaPotion', 45), ('QuestRelic', 60))
    controller_keys = ('player_context', 'input_config', 'move_action', 'shift_action',
                       'mass_input_config', 'mass_move_action', 'mass_shift_action',
                       'backpack_widget_class', 'mass_damage_text_component_class',
                       'damage_text_component_class', 'magic_circle_class')
    mode_keys = ('hud_class', 'player_state_class', 'game_state_class',
                 'character_class_info', 'ability_info', 'loot_tiers',
                 'load_screen_save_game_class', 'default_player_start_tag',
                 'default_map_name', 'default_map', 'maps')
    character_keys = ('startup_ability', 'startup_passive_ability', 'attack_montage',
                      'default_primary_attributes', 'default_secondary_attributes',
                      'default_vital_attributes', 'character_class', 'hit_react_montage')
    monster_keys = ('mesh', 'animation_provider', 'mesh_offset', 'idle_animation',
                    'run_animation', 'attack_animation', 'radius', 'half_height',
                    'attack_range', 'attack_period', 'armor', 'block_chance',
                    'critical_resistance', 'resistances', 'level', 'xp_reward')
    report_dir = Path(u.Paths.project_dir()).resolve() / 'Saved/RoguelikeGeneration'
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        'passed': False, 'phase': 'preflight', 'schema': schema,
        'run_id': str(uuid4()), 'started_utc': datetime.now(timezone.utc).isoformat(),
        'created': [], 'assets': paths, 'asset_list': sorted(outputs),
        'dependencies': {}, 'cook_maps': [paths['host'], *templates],
        'runtime_ability_activation_verified': False,
        'animation_retarget_required': True,
    }
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    asset_tools = u.AssetToolsHelpers.get_asset_tools()

    def fail(message):
        raise RuntimeError(message)

    def require(condition, message):
        if not condition:
            fail(message)

    def dirty():
        return list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + list(
            u.EditorLoadingAndSavingUtils.get_dirty_content_packages())

    def clean():
        packages = [package.get_name() for package in dirty()]
        require(not packages, 'UnsavedPackages: ' + ', '.join(packages))

    def own_dirty_only():
        foreign = [package.get_name() for package in dirty()
                   if package.get_name() not in outputs]
        require(not foreign, 'ForeignPackagesBecameDirty: ' + ', '.join(foreign))

    def object_path(value):
        return value.get_path_name() if value is not None else None

    def package_path(value):
        return value.get_path_name().split('.')[0]

    def load(path):
        value = u.load_asset(path)
        require(value is not None, 'AssetLoadFailed: ' + path)
        return value

    def generated_class(blueprint):
        value = u.load_class(None, blueprint.get_path_name() + '_C')
        require(value is not None, 'BlueprintGeneratedClassMissing: ' + blueprint.get_path_name())
        return value

    def default(path):
        return u.get_default_object(generated_class(load(path)))

    def frozen(value):
        # Return plain values only: no world/actor/CDO references survive a map switch.
        if value is None or isinstance(value, (str, bool, int, float)):
            return value
        if hasattr(value, 'get_path_name'):
            return value.get_path_name()
        if hasattr(value, 'export_text'):
            return value.export_text()
        if hasattr(value, 'items'):
            return sorted((str(key), frozen(item)) for key, item in value.items())
        if isinstance(value, (list, tuple, u.Array)):
            return [frozen(item) for item in value]
        return str(value)

    def properties(value, names):
        return {name: frozen(value.get_editor_property(name)) for name in names}

    def compile_status(blueprint):
        status = str(blueprint.get_editor_property('status'))
        normalized = status.upper().replace('_', '').replace(' ', '')
        require('UPTODATE' in normalized and 'ERROR' not in normalized,
                'BlueprintNotCompiled: ' + blueprint.get_path_name() + ': ' + status)
        return status

    def stamp(asset):
        require(package_path(asset) in outputs, 'WriteOutsideRunOutput: ' + asset.get_path_name())
        u.EditorAssetLibrary.set_metadata_tag(asset, schema_key, schema)

    def save_asset(asset):
        own_dirty_only()
        stamp(asset)
        require(u.EditorAssetLibrary.save_loaded_asset(asset, False),
                'AssetSaveFailed: ' + asset.get_path_name())
        report['created'].append(package_path(asset))
        clean()

    def duplicate(source, destination, parent=None):
        require(destination in outputs, 'DuplicateOutsideRunOutput: ' + destination)
        require(not u.EditorAssetLibrary.does_asset_exist(destination),
                'RefusingToOverwriteAsset: ' + destination)
        result = asset_tools.duplicate_asset(destination.rsplit('/', 1)[-1],
                                             destination.rsplit('/', 1)[0], load(source))
        require(result is not None, 'DuplicateFailed: ' + destination)
        if parent is not None:
            u.BlueprintEditorLibrary.reparent_blueprint(result, parent)
        return result

    def compile_and_save(blueprint):
        u.BlueprintEditorLibrary.compile_blueprint(blueprint)
        compile_status(blueprint)
        save_asset(blueprint)

    def mesh_contract(cdo):
        component = cdo.get_editor_property('mesh')
        require(component is not None, 'CharacterMeshComponentMissing: ' + cdo.get_path_name())
        mesh = component.get_editor_property('skeletal_mesh_asset')
        animation = component.get_editor_property('anim_class')
        require(mesh is not None and animation is not None,
                'CharacterMeshOrAnimationMissing: ' + cdo.get_path_name())
        return {'mesh': object_path(mesh), 'anim_class': object_path(animation),
                'animation_mode': frozen(component.get_editor_property('animation_mode')),
                'relative_transform': frozen(component.get_relative_transform()),
                'materials': [object_path(component.get_material(index))
                              for index in range(component.get_num_materials())]}

    def character_contract(cdo, enemy=False):
        require(isinstance(cdo, u.EnemyCharacter if enemy else u.PureMassPlayerCharacter),
                'CharacterNativeTypeMismatch: ' + cdo.get_path_name())
        result = {'defaults': properties(cdo, character_keys), 'presentation': mesh_contract(cdo)}
        abilities = cdo.get_editor_property('startup_ability')
        require(all(ability is not None for ability in abilities),
                'NullStartupAbility: ' + cdo.get_path_name())
        if enemy:
            tree = cdo.get_editor_property('behavior_tree')
            bar = cdo.get_editor_property('health_bar')
            require(tree is not None and bar is not None, 'EnemyTreeOrHealthBarMissing: ' + cdo.get_path_name())
            widget = bar.get_editor_property('widget_class')
            require(widget is not None, 'EnemyHealthBarWidgetMissing: ' + cdo.get_path_name())
            montages = cdo.get_editor_property('attack_montage')
            require(len(montages) > 0 and all(row.get_editor_property('montage') for row in montages),
                    'EnemyAttackMontagesMissing: ' + cdo.get_path_name())
            result.update(behavior_tree=object_path(tree), health_bar_widget=object_path(widget),
                          ai_controller_class=frozen(cdo.get_editor_property('ai_controller_class')))
            require(result['ai_controller_class'] is not None, 'EnemyAIControllerMissing')
        else:
            require(len(abilities) > 0, 'PlayerStartupAbilitiesMissing')
        return result

    def catalog_rows():
        catalog = load(sources['catalog'])
        require(isinstance(catalog, u.BackpackItemDefinitions), 'CatalogNativeTypeMismatch')
        selected = {}
        wanted = {name for name, _ in item_prices}
        for row in catalog.get_editor_property('items'):
            item_id = row.get_editor_property('item_definition_id')
            type_name = str(item_id.get_editor_property('primary_asset_type').get_editor_property('name'))
            name = str(item_id.get_editor_property('primary_asset_name'))
            if type_name != 'BackpackItem' or name not in wanted:
                continue
            require(name not in selected, 'DuplicateCatalogItem: BackpackItem:' + name)
            require(str(row.get_editor_property('display_name')).strip(), 'CatalogDisplayNameMissing: ' + name)
            require(row.get_editor_property('max_stack') >= 1, 'CatalogStackInvalid: ' + name)
            selected[name] = row
        require(set(selected) == wanted, 'RequiredCatalogItemsMissing: ' + ', '.join(sorted(wanted - set(selected))))
        relic = selected['QuestRelic']
        require(not relic.get_editor_property('usable') and relic.get_editor_property('use_effect') is None,
                'QuestRelicMustRemainAnExistingCollectible')
        return selected

    def source_contracts():
        mode = default(sources['mode'])
        pure_mode = default(sources['pure_mass_mode'])
        pawn_class = pure_mode.get_editor_property('default_pawn_class')
        require(pawn_class is not None, 'PureMassDefaultPawnMissing')
        require(pawn_class == mode.get_editor_property('default_pawn_class'),
                'GenerationAndPureMassDefaultPawnsDiffer')
        sources['player'] = pawn_class.get_path_name().removesuffix('_C').split('.')[0]
        require(isinstance(load(sources['player']), u.Blueprint), 'DefaultPawnMustBeBlueprint')
        pawn = u.get_default_object(pawn_class)
        animation = pawn.get_editor_property('mesh').get_editor_property('anim_class')
        require(animation is not None, 'SourcePlayerAnimationMissing')
        sources['animation'] = animation.get_path_name().removesuffix('_C').split('.')[0]
        require(isinstance(load(sources['animation']), u.AnimBlueprint), 'SourcePlayerAnimationMustBeAnimBlueprint')
        pc = default(sources['controller'])
        require(isinstance(pc, u.DungeonGenerationController), 'SourceControllerNativeTypeMismatch')
        require(mode.get_editor_property('player_controller_class') == generated_class(load(sources['controller'])),
                'SourceModeControllerMismatch')
        require(str(mode.get_editor_property('default_player_start_tag')) == 'RG_Entrance',
                'SourceModeArrivalGroupMismatch')
        require(isinstance(mode, u.PureMassGameMode), 'SourceModeNativeTypeMismatch')
        pc_values = properties(pc, controller_keys)
        require(all(pc_values[key] for key in ('player_context', 'mass_input_config', 'mass_move_action', 'mass_shift_action')),
                'SourceControllerInputMissing')
        gm_values = properties(mode, mode_keys)
        require(all(gm_values[key] for key in ('hud_class', 'player_state_class', 'character_class_info', 'ability_info')),
                'SourceModeCoreDependenciesMissing')
        monster = load(sources['monster'])
        require(isinstance(monster, u.PureMassMonsterType), 'SourceMonsterNativeTypeMismatch')
        require(monster.get_editor_property('mesh') and monster.get_editor_property('animation_provider'),
                'SourceMonsterRenderingMissing')
        rows = catalog_rows()
        return {
            'controller': pc_values, 'mode': gm_values,
            'player': character_contract(u.get_default_object(pawn_class)),
            'elite': character_contract(default(sources['elite']), True),
            'boss': character_contract(default(sources['boss']), True),
            'monster': properties(monster, monster_keys),
            'catalog': {name: frozen(row) for name, row in rows.items()},
        }

    def validate_floor_profile():
        profile = load(sources['floor_profile'])
        require(isinstance(profile, u.DungeonGenerationProfile), 'FloorProfileNativeTypeMismatch')
        require(u.EditorAssetLibrary.get_metadata_tag(profile, schema_key) == 'full-floor-v2',
                'FloorProfileSourceSchemaMismatch')
        require(profile.get_editor_property('generate_full_floor') and
                abs(profile.get_editor_property('room_spacing') - 2400) < .1,
                'FloorProfileConfigurationMismatch')
        actual = {}
        for row in profile.get_editor_property('templates'):
            name = str(row.get_editor_property('template_id'))
            require(name not in actual, 'DuplicateFloorTemplate: ' + name)
            level = row.get_editor_property('level')
            require(level is not None, 'FloorTemplateLevelMissing: ' + name)
            actual[name] = package_path(level)
        require(actual == dict(zip(template_ids, templates)), 'FloorTemplateLibraryMismatch')

    def xyz(vector):
        return [round(vector.x, 4), round(vector.y, 4), round(vector.z, 4)]

    def world_contract(path, run=False):
        clean()
        require(levels.load_level(path), 'MapLoadFailed: ' + path)
        world = editor.get_editor_world()
        require(package_path(world) == path, 'WrongWorldLoaded: ' + path)
        expected_schema = schema if run else 'full-floor-v2'
        require(u.EditorAssetLibrary.get_metadata_tag(world, schema_key) == expected_schema,
                'WorldSchemaMismatch: ' + path)
        all_actors = list(actors.get_all_level_actors())
        starts = list(u.GameplayStatics.get_all_actors_of_class(world, u.PlayerStart))
        runtimes = list(u.GameplayStatics.get_all_actors_of_class(world, u.DungeonGenerationRuntime))
        bounds = list(u.GameplayStatics.get_all_actors_of_class(world, u.NavMeshBoundsVolume))
        navs = list(u.GameplayStatics.get_all_actors_of_class(world, u.RecastNavMesh))
        directors = list(u.GameplayStatics.get_all_actors_of_class(world, u.DungeonRunDirector))
        require(len(starts) == 2 and len(runtimes) == 1 and len(bounds) == 1 and len(navs) == 1,
                'HostSourceActorContractMismatch: ' + path)
        require(not u.GameplayStatics.get_all_actors_of_class(world, u.PureMassSpawnRegion) and
                not u.GameplayStatics.get_all_actors_of_class(world, u.EnemyCharacter),
                'HostMustNotContainAutomaticEnemies: ' + path)
        require(all(isinstance(start, u.TravelPlayerStart) for start in starts), 'HostRequiresTravelPlayerStarts')
        require(sorted(start.get_editor_property('player_slot') for start in starts) == [0, 1],
                'HostArrivalSlotsMismatch')
        for start in starts:
            point = start.get_actor_location()
            x = -300 if start.get_editor_property('player_slot') == 0 else 300
            require(str(start.get_editor_property('player_start_tag')) == 'RG_Entrance' and
                    start.get_editor_property('default_entry_group') and
                    max(abs(point.x - x), abs(point.y + 300), abs(point.z - 110)) < .1,
                    'HostArrivalContractMismatch')
        runtime = runtimes[0]
        require(runtime.get_editor_property('profile') == load(sources['floor_profile']) and
                runtime.get_editor_property('seed') == 42 and
                runtime.get_editor_property('expected_players') == 1 and
                runtime.get_actor_location().length() < .1, 'HostRuntimeConfigurationMismatch')
        _, extent = bounds[0].get_actor_bounds(False)
        require(min(extent.x, extent.y) >= 31199 and extent.z >= 799, 'HostNavigationBoundsTooSmall')
        require(navs[0].get_editor_property('runtime_generation') == u.RuntimeGenerationType.DYNAMIC,
                'HostNavigationMustRemainDynamic')
        support = [actor for actor in all_actors if actor.get_actor_label() == 'RF_CollisionFloor']
        require(len(support) == 1, 'HostSolidUnderlayMissing')
        origin, support_extent = support[0].get_actor_bounds(False)
        require(max(abs(origin.x), abs(origin.y), abs(origin.z + 10),
                    abs(support_extent.x - 1201), abs(support_extent.y - 1201),
                    abs(support_extent.z - 10)) < .1 and
                str(support[0].static_mesh_component.get_collision_profile_name()) == 'BlockAll',
                'HostSolidUnderlayChanged')
        mode = paths['mode'] if run else sources['mode']
        settings = world.get_world_settings()
        require(settings.get_editor_property('default_game_mode') == generated_class(load(mode)),
                'HostGameModeMismatch')
        require(len(directors) == (1 if run else 0), 'HostRunDirectorCountMismatch')
        if run:
            director = directors[0]
            require(director.get_actor_label() == 'RG_RunDirector' and
                    director.get_actor_location().length() < .1 and
                    director.get_editor_property('profile') == load(paths['profile']),
                    'HostRunDirectorConfigurationMismatch')
        preserved = []
        for actor in all_actors:
            if isinstance(actor, u.DungeonRunDirector):
                continue
            record = {'label': actor.get_actor_label(), 'class': actor.get_class().get_path_name(),
                      'location': xyz(actor.get_actor_location()),
                      'rotation': frozen(actor.get_actor_rotation()), 'scale': xyz(actor.get_actor_scale3d()),
                      'tags': sorted(str(tag) for tag in actor.tags)}
            if isinstance(actor, u.StaticMeshActor):
                component = actor.static_mesh_component
                record.update(mesh=object_path(component.get_editor_property('static_mesh')),
                              collision=str(component.get_collision_profile_name()),
                              mobility=frozen(component.get_editor_property('mobility')),
                              materials=[object_path(component.get_material(index))
                                         for index in range(component.get_num_materials())])
            preserved.append(record)
        clean()
        return {'actors': sorted(preserved, key=lambda value: json.dumps(value, sort_keys=True)),
                'kill_z': settings.get_editor_property('kill_z'),
                'navigation_extent_cm': xyz(extent), 'player_slots': [0, 1],
                'seed': 42, 'expected_players': 1, 'solid_collision_floor': True}

    def create_content():
        # EventGraph casts/member types still name the source pawn. The root
        # workflow retargets only this isolated AnimBP and then stamps the flag.
        animation = duplicate(sources['animation'], paths['animation'])
        u.EditorAssetLibrary.set_metadata_tag(animation, 'DungeonPlayerReferencesRetargeted', 'false')
        compile_and_save(animation)
        for key, parent in (('controller', u.DungeonRunController), ('player', u.DungeonPlayerCharacter),
                            ('elite', None), ('boss', None)):
            blueprint = duplicate(sources[key], paths[key], parent)
            u.BlueprintEditorLibrary.compile_blueprint(blueprint)
            cdo = u.get_default_object(generated_class(blueprint))
            if key == 'player':
                cdo.get_editor_property('mesh').set_editor_property(
                    'anim_class', generated_class(load(paths['animation'])))
            if key in ('elite', 'boss'):
                # Level is exported by AEnemyCharacter; health/loot are Director-owned at spawn.
                cdo.set_editor_property('level', 2 if key == 'elite' else 3)
                cdo.set_editor_property('auto_possess_ai', u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
            compile_and_save(blueprint)
        blueprint = duplicate(sources['mode'], paths['mode'])
        u.BlueprintEditorLibrary.compile_blueprint(blueprint)
        cdo = u.get_default_object(generated_class(blueprint))
        cdo.set_editor_property('player_controller_class', generated_class(load(paths['controller'])))
        cdo.set_editor_property('default_pawn_class', generated_class(load(paths['player'])))
        compile_and_save(blueprint)
        monster = duplicate(sources['monster'], paths['monster'])
        for key, value in (('health', 100.0), ('speed', 180.0), ('attack_damage', 4.0)):
            monster.set_editor_property(key, value)
        save_asset(monster)
        factory = u.DataAssetFactory()
        factory.set_editor_property('data_asset_class', u.DungeonRunProfile)
        profile = asset_tools.create_asset('DA_DungeonGameplay', gameplay, u.DungeonRunProfile, factory)
        require(profile is not None, 'RunProfileCreationFailed')
        profile.set_editor_property('monster_type', monster)
        profile.set_editor_property('elite_class', generated_class(load(paths['elite'])))
        profile.set_editor_property('boss_class', generated_class(load(paths['boss'])))
        profile.set_editor_property('item_definitions', load(sources['catalog']))
        rows = catalog_rows()
        profile.set_editor_property('chest_items', [rows[name].get_editor_property('item_definition_id')
                                                   for name in ('HealthPotion', 'ManaPotion')])
        offers = []
        for name, price in item_prices:
            offer = u.DungeonShopOffer()
            offer.set_editor_property('item_id', rows[name].get_editor_property('item_definition_id'))
            offer.set_editor_property('name', rows[name].get_editor_property('display_name'))
            offer.set_editor_property('price', price)
            offers.append(offer)
        profile.set_editor_property('offers', offers)
        for key, value in profile_values.items():
            profile.set_editor_property(key, value)
        save_asset(profile)

    def create_host():
        clean()
        require(levels.new_level_from_template(paths['host'], sources['host']), 'RunHostCloneFailed')
        world = editor.get_editor_world()
        require(package_path(world) == paths['host'], 'WrongWorldAfterHostClone')
        require(not u.GameplayStatics.get_all_actors_of_class(world, u.DungeonRunDirector),
                'SourceHostAlreadyContainsRunDirector')
        director = actors.spawn_actor_from_class(u.DungeonRunDirector, u.Vector(0, 0, 0))
        require(director is not None, 'RunDirectorCreationFailed')
        director.set_actor_label('RG_RunDirector')
        director.set_folder_path('RoguelikeRun/Gameplay')
        director.tags = [u.Name('RG_Run')]
        director.set_actor_location(u.Vector(0, 0, 0), False, True)
        director.set_editor_property('profile', load(paths['profile']))
        world.get_world_settings().set_editor_property('default_game_mode', generated_class(load(paths['mode'])))
        own_dirty_only()
        stamp(world)
        require(levels.save_current_level(), 'RunHostSaveFailed')
        report['created'].append(paths['host'])
        clean()

    def validate_content(baseline):
        for path in sorted(outputs):
            asset = load(path)
            require(u.EditorAssetLibrary.get_metadata_tag(asset, schema_key) == schema,
                    'OutputSchemaMismatch: ' + path)
        # Do not keep the map asset local alive while the caller switches worlds.
        asset = None
        compiled = {}
        for key in ('controller', 'player', 'animation', 'mode', 'elite', 'boss'):
            compiled[key] = compile_status(load(paths[key]))
        controller = default(paths['controller'])
        player = default(paths['player'])
        mode = default(paths['mode'])
        require(isinstance(controller, u.DungeonRunController), 'RunControllerNativeTypeMismatch')
        require(isinstance(player, u.DungeonPlayerCharacter), 'RunPlayerNativeTypeMismatch')
        require(isinstance(mode, u.PureMassGameMode), 'RunModeNativeTypeMismatch')
        require(properties(controller, controller_keys) == baseline['controller'], 'CopiedControllerInputChanged')
        expected_player = json.loads(json.dumps(baseline['player']))
        expected_player['presentation']['anim_class'] = object_path(generated_class(load(paths['animation'])))
        require(character_contract(player) == expected_player, 'CopiedPlayerConfigurationChanged')
        animation = load(paths['animation'])
        require(isinstance(animation, u.AnimBlueprint) and
                isinstance(u.get_default_object(generated_class(animation)), u.AnimInstance),
                'RunPlayerAnimationNativeTypeMismatch')
        retargeted = u.EditorAssetLibrary.get_metadata_tag(animation, 'DungeonPlayerReferencesRetargeted')
        require(retargeted.lower() in ('true', 'false'), 'AnimationRetargetMetadataMissingOrInvalid')
        report['animation_retarget_required'] = retargeted.lower() != 'true'
        require(properties(mode, mode_keys) == baseline['mode'], 'CopiedGameModeConfigurationChanged')
        require(mode.get_editor_property('player_controller_class') == generated_class(load(paths['controller'])) and
                mode.get_editor_property('default_pawn_class') == generated_class(load(paths['player'])),
                'RunModeClassReferencesMismatch')
        for key, level in (('elite', 2), ('boss', 3)):
            cdo = default(paths[key])
            require(character_contract(cdo, True) == baseline[key], 'CopiedEnemyConfigurationChanged: ' + key)
            require(cdo.get_editor_property('level') == level, 'CopiedEnemyLevelMismatch: ' + key)
            require(cdo.get_editor_property('auto_possess_ai') == u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED,
                    'RuntimeEnemyAIRequiresSpawnPossession: ' + key)
        monster = load(paths['monster'])
        require(isinstance(monster, u.PureMassMonsterType), 'RunMonsterNativeTypeMismatch')
        require(properties(monster, monster_keys) == baseline['monster'], 'CopiedMonsterRenderingOrDefaultsChanged')
        for key, value in (('health', 100.0), ('speed', 180.0), ('attack_damage', 4.0)):
            require(abs(monster.get_editor_property(key) - value) < .001, 'RunMonsterValueMismatch: ' + key)
        profile = load(paths['profile'])
        require(isinstance(profile, u.DungeonRunProfile), 'RunProfileNativeTypeMismatch')
        for key, value in profile_values.items():
            require(abs(profile.get_editor_property(key) - value) < .001, 'RunProfileValueMismatch: ' + key)
        require(profile.get_editor_property('monster_type') == monster and
                profile.get_editor_property('item_definitions') == load(sources['catalog']) and
                profile.get_editor_property('elite_class') == generated_class(load(paths['elite'])) and
                profile.get_editor_property('boss_class') == generated_class(load(paths['boss'])),
                'RunProfileDependencyMismatch')
        rows = catalog_rows()
        expected_chest = [frozen(rows[name].get_editor_property('item_definition_id'))
                          for name in ('HealthPotion', 'ManaPotion')]
        require(frozen(profile.get_editor_property('chest_items')) == expected_chest, 'ChestItemIdsMismatch')
        offers = profile.get_editor_property('offers')
        require(len(offers) == 3, 'ShopMustHaveExactlyThreeOffers')
        offer_report = []
        for offer, (name, price) in zip(offers, item_prices):
            row = rows[name]
            require(frozen(offer.get_editor_property('item_id')) == frozen(row.get_editor_property('item_definition_id')) and
                    str(offer.get_editor_property('name')) == str(row.get_editor_property('display_name')) and
                    offer.get_editor_property('price') == price, 'ShopOfferMismatch: ' + name)
            offer_report.append({'item_id': 'BackpackItem:' + name,
                                 'name': str(row.get_editor_property('display_name')), 'price': price,
                                 'usable': row.get_editor_property('usable'),
                                 'use_effect': object_path(row.get_editor_property('use_effect'))})
        return {'blueprint_compile_status': compiled, 'offers': offer_report,
                'animation_retarget_required': report['animation_retarget_required'],
                'animation_asset': paths['animation'],
                'elite_level': 2, 'boss_level': 3, 'profile_values': profile_values,
                'monster_values': {'health': 100, 'speed': 180, 'attack_damage': 4}}

    try:
        clean()
        require(not levels.is_in_play_in_editor(), 'StopPIEBeforeAuthoring')
        world_path = package_path(editor.get_editor_world())
        require(world_path.startswith('/Game/') and u.EditorAssetLibrary.does_asset_exist(world_path),
                'OpenASavedGameMapBeforeAuthoring')
        for name in ('DungeonRunController', 'DungeonPlayerCharacter', 'DungeonRunDirector',
                     'DungeonRunProfile', 'DungeonShopOffer', 'DungeonGenerationController',
                     'DungeonGenerationRuntime', 'DungeonGenerationProfile', 'PureMassPlayerCharacter',
                     'PureMassMonsterType', 'PureMassGameMode', 'TravelPlayerStart', 'BackpackItemDefinitions'):
            require(hasattr(u, name), 'NativeClassMissingCompileAndRestart: ' + name)
        present = sorted(path for path in outputs if u.EditorAssetLibrary.does_asset_exist(path))
        require(not present or len(present) == len(outputs),
                'PartialRunOutputRequiresInspection: ' + ', '.join(present))
        if present:
            for path in present:
                require(u.EditorAssetLibrary.get_metadata_tag(load(path), schema_key) == schema,
                        'OutputSchemaMismatch: ' + path)
        for path in [*sources.values(), *templates]:
            require(u.EditorAssetLibrary.does_asset_exist(path), 'SourceAssetMissing: ' + path)
        baseline = source_contracts()
        report['dependencies'] = dict(sources)
        report['source_contracts'] = baseline
        validate_floor_profile()
        # The helpers return plain dictionaries, never retained world/actor wrappers.
        source_world = world_contract(sources['host'])
        report['source_host_contract'] = source_world
        clean()
        if present:
            report['phase'] = 'validate_existing'
        else:
            report['phase'] = 'create_gameplay_content'
            create_content()
            report['phase'] = 'clone_host'
            create_host()
            report['phase'] = 'validate_saved_output'
        report['content_validation'] = validate_content(baseline)
        require(source_contracts() == baseline, 'SharedSourceDefaultsChangedDuringAuthoring')
        host = world_contract(paths['host'], run=True)
        require(host == source_world, 'ClonedHostSourceContractChanged')
        report['host_validation'] = host
        clean()
        report.update(passed=True, phase='complete', reused_existing=bool(present))
        return report
    except Exception as exc:
        report['error'] = repr(exc)
        raise
    finally:
        report['dirty_packages'] = [package.get_name() for package in dirty()]
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (report_dir / 'authoring-run.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        u.log('ROGUELIKE_RUN_AUTHORING ' + json.dumps(report, ensure_ascii=False))


main()
