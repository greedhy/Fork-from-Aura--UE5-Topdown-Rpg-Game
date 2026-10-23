"""Run once in the editor: add the lobby map/UI asset, bind the existing load HUD."""
def main():
    import unreal as u
    import json,uuid
    from pathlib import Path
    root=Path(u.Paths.project_dir()).resolve()
    tools=u.AssetToolsHelpers.get_asset_tools()
    path='/Game/BluePrints/UI/Rooms/WBP_ModeAndRoom'
    widget=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else None
    if not widget:
        factory=u.WidgetBlueprintFactory(); factory.set_editor_property('parent_class',u.RoomMenuWidget)
        widget=tools.create_asset('WBP_ModeAndRoom','/Game/BluePrints/UI/Rooms',u.WidgetBlueprint,factory)
    assert widget
    u.BlueprintEditorLibrary.compile_blueprint(widget)
    cls=u.EditorAssetLibrary.load_blueprint_class(path)
    assert cls and isinstance(u.get_default_object(cls),u.RoomMenuWidget)
    u.get_default_object(cls).set_editor_property('is_focusable',True)
    assert u.EditorAssetLibrary.save_loaded_asset(widget,False)
    hud_path='/Game/BluePrints/UI/HUD/BP_LoadScreenHud'
    hud=u.load_asset(hud_path); cdo=u.get_default_object(u.EditorAssetLibrary.load_blueprint_class(hud_path))
    cdo.set_editor_property('room_menu_widget_class',cls)
    u.BlueprintEditorLibrary.compile_blueprint(hud); assert u.EditorAssetLibrary.save_loaded_asset(hud,False)
    map_path='/Game/levels/RoomLobby'
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    assert not dirty,[p.get_name() for p in dirty]
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if u.EditorAssetLibrary.does_asset_exist(map_path): assert levels.load_level(map_path)
    else: assert levels.new_level(map_path)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode',u.RoomLobbyGameMode)
    assert levels.save_current_level()
    gi_path='/Game/BluePrints/Game/BP_MyGameInstance'
    gi=u.load_asset(gi_path); gi_cdo=u.get_default_object(u.EditorAssetLibrary.load_blueprint_class(gi_path))
    gi_cdo.set_editor_property('room_lobby_map',world)
    u.BlueprintEditorLibrary.compile_blueprint(gi); assert u.EditorAssetLibrary.save_loaded_asset(gi,False)
    report={'run_id':uuid.uuid4().hex,'assets':[path,hud_path,map_path,gi_path],'passed':True}
    (root/'Saved/Rooms/asset_authoring.json').write_text(json.dumps(report,indent=2))
    u.log('ROOM_ASSETS_AUTHORED '+json.dumps(report))
main()
