import unreal

for path, parent in [
    ('/Game/BluePrints/AbilitySystem/Player/Ability/Arcane/ArcaneNova/GA_ArcaneNova', '/Script/test_25d.MyArcaneNova'),
    ('/Game/BluePrints/AbilitySystem/GameplayCueNotify/GC_ArcaneNova', '/Script/test_25d.MyArcaneNovaCue'),
]:
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        continue
    factory = unreal.BlueprintFactory()
    factory.set_editor_property('parent_class', unreal.load_class(None, parent))
    folder, name = path.rsplit('/', 1)
    blueprint = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, folder, unreal.Blueprint, factory)
    assert blueprint, path
    unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
    assert unreal.EditorAssetLibrary.save_loaded_asset(blueprint, False), path
print('ARCANE_NOVA_BLUEPRINTS_CREATED')
