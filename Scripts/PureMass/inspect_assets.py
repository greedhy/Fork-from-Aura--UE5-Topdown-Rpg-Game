def main():
    import unreal as u, json
    from pathlib import Path
    def obj(p): return u.load_asset(p)
    def cdo(p): return u.get_default_object(u.load_class(None, p + '.' + p.rsplit('/',1)[-1] + '_C'))
    result = {}
    goblin = cdo('/Game/BluePrints/Characters/Goblin/BP_Goblin')
    mesh = goblin.get_component_by_class(u.SkeletalMeshComponent)
    result['goblin'] = {'mesh':mesh.get_editor_property('skeletal_mesh_asset').get_path_name(),
                        'transform':str(mesh.get_relative_transform()),
                        'materials':[x.get_path_name() for x in mesh.get_materials()]}
    result['animations'] = u.EditorAssetLibrary.list_assets('/Game/Assets/Enemies/Goblin/Animations',recursive=True)
    result['prototype_gas'] = u.EditorAssetLibrary.list_assets('/Game/BluePrints/AbilitySystem/Player/Ability/Prototypes',recursive=True)
    result['compositions'] = u.EditorAssetLibrary.list_assets('/Game/BluePrints/AbilitySystem/Player/Ability/Compositions',recursive=True)
    result['controller'] = {}
    pc = cdo('/Game/BluePrints/Player/BP_PlayerController')
    for key in ['input_config','move_action','shift_action','player_context']:
        value = pc.get_editor_property(key)
        result['controller'][key] = value.get_path_name() if value else None
    player = cdo('/Game/BluePrints/Characters/Player/BP_Player')
    result['player_startup'] = [x.get_path_name() for x in player.get_editor_property('startup_ability')]
    result['player_passive'] = [x.get_path_name() for x in player.get_editor_property('startup_passive_ability')]
    Path(u.Paths.project_dir(),'Saved/PureMass/inspection.json').write_text(json.dumps(result,indent=2,default=list),encoding='utf8')
main()


