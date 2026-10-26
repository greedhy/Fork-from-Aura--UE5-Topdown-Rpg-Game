def _author_travel_map():
    import unreal as u
    base='/Game/PrototypeExtensions/Batch5/'
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not u.EditorAssetLibrary.does_asset_exist(base+'L_PrototypeTravel'):
        assert levels.new_level_from_template(base+'L_PrototypeTravel',base+'L_PrototypeLab')
        assert levels.save_current_level()
    assert levels.load_level(base+'L_PrototypeLab')
_author_travel_map()
