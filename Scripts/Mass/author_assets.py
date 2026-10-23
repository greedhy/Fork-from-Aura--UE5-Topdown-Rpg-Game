"""Create an isolated copy of Dungeon using the Mass game mode, through the editor bridge."""
def main():
    import unreal as u
    import json
    from pathlib import Path
    root = Path(u.Paths.project_dir()).resolve()
    report = root / 'Saved/MassMonsters/assets.json'
    tools = u.AssetToolsHelpers.get_asset_tools()
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    assert not list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    assert not list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    original = editor.get_editor_world().get_path_name().split('.')[0]
    folder = '/Game/BluePrints/Mass'
    config_path = folder + '/DA_MonsterManagement'
    config = u.load_asset(config_path) if u.EditorAssetLibrary.does_asset_exist(config_path) else None
    if not config:
        factory = u.DataAssetFactory(); factory.set_editor_property('data_asset_class', u.MonsterManagementConfig)
        config = tools.create_asset('DA_MonsterManagement', folder, u.MonsterManagementConfig, factory)
        config.set_editor_property('wake_radius', 2500.0)
        config.set_editor_property('sleep_radius', 3500.0)
    assert config
    assert u.EditorAssetLibrary.save_loaded_asset(config, False)
    mode_path = folder + '/BP_MassDungeonGameMode'
    if not u.EditorAssetLibrary.does_asset_exist(mode_path):
        # Duplicate to retain every gameplay default (GAS data, Pawn, HUD, save and travel classes).
        mode = tools.duplicate_asset('BP_MassDungeonGameMode', folder, u.load_asset('/Game/BluePrints/Game/BP_MyGameMode'))
        assert mode
        u.BlueprintEditorLibrary.reparent_blueprint(mode, u.MassDungeonGameMode)
    mode = u.load_asset(mode_path)
    u.BlueprintEditorLibrary.compile_blueprint(mode)
    mode_class = u.EditorAssetLibrary.load_blueprint_class(mode_path)
    cdo = u.get_default_object(mode_class)
    assert isinstance(cdo, u.MassDungeonGameMode)
    cdo.set_editor_property('monster_management_config', config)
    for key in ['character_class_info', 'ability_info', 'default_pawn_class', 'player_controller_class', 'player_state_class']:
        assert cdo.get_editor_property(key), key
    u.BlueprintEditorLibrary.compile_blueprint(mode)
    assert u.EditorAssetLibrary.save_loaded_asset(mode, False)
    map_path = '/Game/levels/L_MassDungeonTest'
    if not u.EditorAssetLibrary.does_asset_exist(map_path):
        assert levels.new_level_from_template(map_path, '/Game/levels/Dungeon')
    else:
        assert levels.load_level(map_path)
    world = editor.get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode', mode_class)
    actors = u.GameplayStatics.get_all_actors_of_class(world, u.EnemyCharacter)
    points = u.GameplayStatics.get_all_actors_of_class(world, u.MyEnemySpawnPoint)
    for actor in actors + points:
        if str(actor.get_editor_property('monster_room_id')) == 'None':
            actor.set_editor_property('monster_room_id', 'TestRoom')
    assert levels.save_current_level()
    counts = {'placed_enemies': len(actors), 'spawn_points': len(points)}
    actors.clear(); points.clear(); world = None; actor = None
    assert levels.load_level(original)
    report.write_text(json.dumps({'passed': True, 'config': config_path, 'mode': mode_path, 'map': map_path,
        **counts}, indent=2), encoding='utf8')
    u.log('MASS_ASSETS_CREATED')
main()
