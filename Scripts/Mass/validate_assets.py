"""Read back saved assets after restarting the editor. Run outside PIE."""
def main():
    import unreal as u, json
    from pathlib import Path
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert world.get_name() == 'L_MassDungeonTest'
    cls = world.get_world_settings().get_editor_property('default_game_mode')
    cdo = u.get_default_object(cls)
    assert isinstance(cdo, u.MassDungeonGameMode)
    old = u.get_default_object(u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Game/BP_MyGameMode'))
    retained = ['character_class_info','ability_info','loot_tiers','load_screen_save_game_class','default_pawn_class',
        'player_controller_class','player_state_class','hud_class','game_state_class','default_map','default_map_name','default_player_start_tag']
    checks = {}
    for prop in retained:
        checks[prop] = cdo.get_editor_property(prop) == old.get_editor_property(prop)
        assert checks[prop], prop
    config = cdo.get_editor_property('monster_management_config')
    assert isinstance(config, u.MonsterManagementConfig)
    checks['config_saved'] = config.get_path_name().startswith('/Game/BluePrints/Mass/DA_MonsterManagement.')
    checks['cell_size'] = config.get_editor_property('cell_size') == 1000
    checks['distances'] = config.get_editor_property('wake_radius') == 2500 and config.get_editor_property('sleep_radius') == 3500
    checks['room_ids'] = all(str(a.get_editor_property('monster_room_id')) == 'TestRoom' for a in
        u.GameplayStatics.get_all_actors_of_class(world,u.EnemyCharacter)+u.GameplayStatics.get_all_actors_of_class(world,u.MyEnemySpawnPoint))
    assert all(checks.values()), checks
    (Path(u.Paths.project_dir())/'Saved/MassMonsters/asset-validation.json').write_text(json.dumps({'passed':True,'checks':checks},indent=2))
    u.log('MASS_ASSETS_VALIDATED')
main()
