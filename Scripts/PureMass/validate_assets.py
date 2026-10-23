def main():
    import unreal as u,json
    from pathlib import Path
    checks={}
    def check(name,ok):checks[name]=bool(ok);assert ok,name
    folder='/Game/PureMass'
    def cdo(path):return u.get_default_object(u.load_class(None,path+'.'+path.rsplit('/',1)[-1]+'_C'))
    mode=cdo(folder+'/BP_PureMassGameMode')
    check('native_mode',isinstance(mode,u.PureMassGameMode))
    check('isolated_pawn',isinstance(u.get_default_object(mode.get_editor_property('default_pawn_class')),u.PureMassPlayerCharacter))
    check('isolated_input',isinstance(u.get_default_object(mode.get_editor_property('player_controller_class')),u.PureMassPlayerController))
    catalog=mode.get_editor_property('ability_info');rows=catalog.get_editor_property('ability_information')
    check('catalog_26',len(rows)==26)
    for row in rows:
        default=u.get_default_object(row.get_editor_property('ability'))
        check(default.get_name(),isinstance(default,u.PureMassAbility) and default.get_editor_property('prototype').is_valid_configuration())
    hud=u.get_default_object(mode.get_editor_property('hud_class'))
    for key in ['overlay_widget_controller_class','spell_menu_widget_controller_class','attribute_menu_widget_controller_class']:
        wc=u.get_default_object(hud.get_editor_property(key));check(key,wc.get_editor_property('ability_info')==catalog)
    monster=u.load_asset(folder+'/DA_MassGoblin');mesh=monster.get_editor_property('mesh')
    check('cloned_mesh',mesh.get_path_name().startswith(folder+'/'))
    check('cloned_materials',all(s.get_editor_property('material_interface').get_path_name().startswith(folder+'/') for s in mesh.get_editor_property('materials')))
    check('cloned_provider',monster.get_editor_property('animation_provider').get_path_name().startswith(folder+'/'))
    editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    check('optimized_for_instancing',all(editor.get_lod_build_settings(mesh,i).get_editor_property('optimize_for_instancing') for i in range(editor.get_lod_count(mesh))))
    orbit=cdo(folder+'/Abilities/GA_Prototype_Orbit').get_editor_property('prototype')
    check('orbit_visual',bool(orbit.get_editor_property('loop_vfx')) and orbit.get_path_name().startswith(folder+'/'))
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    check('copied_map_loaded','/Game/PureMass/Maps/L_PureMassDungeon.' in world.get_path_name())
    check('map_no_enemy_actors',not u.GameplayStatics.get_all_actors_of_class(world,u.EnemyCharacter))
    check('map_no_old_spawn_points',not u.GameplayStatics.get_all_actors_of_class(world,u.MyEnemySpawnPoint))
    check('map_new_spawn_regions',len(u.GameplayStatics.get_all_actors_of_class(world,u.PureMassSpawnRegion))==2)
    check('map_opted_into_new_mode',world.get_world_settings().get_editor_property('default_game_mode')==mode.get_class())
    Path(u.Paths.project_dir(),'Saved/PureMass/asset-validation.json').write_text(json.dumps({'passed':True,'checks':checks},indent=2),encoding='utf8')
main()
