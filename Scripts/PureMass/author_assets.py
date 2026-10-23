"""Author ONLY /Game/PureMass packages. Run after the native editor build/restart."""
def main():
    import unreal as u, json
    from pathlib import Path
    root = Path(u.Paths.project_dir()).resolve()
    tools = u.AssetToolsHelpers.get_asset_tools()
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    folder = '/Game/PureMass'
    created = []
    dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    assert all(p.get_name().startswith(folder+'/') for p in dirty), [p.get_name() for p in dirty]
    original = editor.get_editor_world().get_path_name().split('.')[0]

    def save(asset):
        assert asset.get_path_name().startswith(folder+'/'), asset.get_path_name()
        assert u.EditorAssetLibrary.save_loaded_asset(asset, False)
        created.append(asset.get_path_name())
        return asset
    def duplicate(source, name, sub=''):
        dest = folder + ('/'+sub if sub else '')
        existing = u.load_asset(dest+'/'+name) if u.EditorAssetLibrary.does_asset_exist(dest+'/'+name) else None
        return existing or tools.duplicate_asset(name,dest,u.load_asset(source))
    def cls(asset):
        return u.load_class(None,asset.get_path_name()+'_C')
    def copy_bp(source,name,parent=None,sub=''):
        bp = duplicate(source,name,sub)
        assert bp, source
        if parent: u.BlueprintEditorLibrary.reparent_blueprint(bp,parent)
        u.BlueprintEditorLibrary.compile_blueprint(bp)
        return bp,u.get_default_object(cls(bp))
    def data(name,kind):
        path=folder+'/'+name
        if u.EditorAssetLibrary.does_asset_exist(path): return u.load_asset(path)
        factory=u.DataAssetFactory(); factory.set_editor_property('data_asset_class',kind)
        return tools.create_asset(name,folder,kind,factory)

    # Clone material before any instanced renderer sees it; automatic usage flags cannot dirty the original.
    material=duplicate('/Game/Assets/Enemies/Goblin/Materials/M_Goblin','M_MassGoblin','Rendering')
    u.MaterialEditingLibrary.set_material_usage(material,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    u.MaterialEditingLibrary.set_material_usage(material,u.MaterialUsage.MATUSAGE_INSTANCED_SKINNED_MESH)
    u.MaterialEditingLibrary.recompile_material(material); save(material)
    mesh=duplicate('/Game/Assets/Enemies/Goblin/SKM_Goblin','SKM_MassGoblin','Rendering')
    slots=list(mesh.get_editor_property('materials'))
    assert len(slots)==1, 'Inspect additional materials before assigning'
    slots[0].set_editor_property('material_interface',material)
    mesh.set_editor_property('materials',slots)
    mesh_editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    for lod in range(mesh_editor.get_lod_count(mesh)):
        settings=mesh_editor.get_lod_build_settings(mesh,lod)
        settings.set_editor_property('optimize_for_instancing',True)
        mesh_editor.set_lod_build_settings(mesh,lod,settings)
    save(mesh)
    bank_path=folder+'/Rendering/AB_MassGoblin'
    if u.EditorAssetLibrary.does_asset_exist(bank_path): bank=u.load_asset(bank_path)
    else:
        factory=u.AnimBankFactory()
        factory.set_editor_property('target_skeleton',mesh.get_editor_property('skeleton'))
        factory.set_editor_property('preview_skeletal_mesh',mesh)
        bank=tools.create_asset('AB_MassGoblin',folder+'/Rendering',u.AnimBank,factory)
    bank.set_editor_property('asset',mesh)
    seq=[]
    for name in ['Idle_Spear2','Run_Spear_fix','Attack_Spear']:
        item=u.AnimBankSequence()
        item.set_editor_property('sequence',u.load_asset('/Game/Assets/Enemies/Goblin/Animations/Spear/'+name))
        item.set_editor_property('looping',name!='Attack_Spear')
        seq.append(item)
    bank.set_editor_property('sequences',seq); save(bank)
    provider_path=bank_path+'_ASTP'
    provider=u.load_asset(provider_path) if u.EditorAssetLibrary.does_asset_exist(provider_path) else u.PureMassCrowd.create_animation_provider(bank)
    assert provider; save(provider)
    monster=data('DA_MassGoblin',u.PureMassMonsterType)
    monster.set_editor_property('mesh',mesh)
    monster.set_editor_property('animation_provider',provider)
    monster.set_editor_property('mesh_offset',u.Transform(location=u.Vector(0,0,-60),rotation=u.Rotator(pitch=0,yaw=-90,roll=0)))
    monster.set_editor_property('health',150.0)
    monster.set_editor_property('speed',200.0)
    monster.set_editor_property('attack_damage',5.0)
    save(monster)
    qa=duplicate(monster.get_path_name(),'DA_MassQAGoblin')
    qa.set_editor_property('mesh_offset',monster.get_editor_property('mesh_offset'))
    qa.set_editor_property('health',100000.0)
    qa.set_editor_property('speed',0.0)
    qa.set_editor_property('attack_damage',0.0)
    save(qa)

    # Copy every prototype/combination GA. Original config graphs remain immutable shared data.
    mapping={}
    for subtree in ['Prototypes','Compositions']:
        src='/Game/BluePrints/AbilitySystem/Player/Ability/'+subtree
        for asset_path in u.EditorAssetLibrary.list_assets(src,recursive=False):
            if not asset_path.rsplit('/',1)[-1].startswith('GA_'): continue
            old=u.load_asset(asset_path)
            old_class=u.load_class(None,asset_path+'_C')
            if not old_class or not isinstance(u.get_default_object(old_class),u.PrototypeAbility): continue
            bp,cdo=copy_bp(asset_path,old.get_name(),u.PureMassAbility,'Abilities')
            if old.get_name()=='GA_Prototype_Orbit':
                orbit=duplicate(cdo.get_editor_property('prototype').get_path_name(),'DA_MassOrbit','Abilities')
                shot=u.load_asset('/Game/BluePrints/AbilitySystem/Player/Ability/Prototypes/DA_Prototype_Projectile')
                visual=shot.get_editor_property('loop_vfx')
                assert visual, 'Orbit needs a firebolt Niagara system'
                orbit.set_editor_property('loop_vfx',visual);save(orbit)
                cdo.set_editor_property('prototype',orbit)
                u.BlueprintEditorLibrary.compile_blueprint(bp)
            save(bp)
            mapping[old_class.get_path_name()]=cls(bp)
    assert len(mapping)==26, len(mapping)
    catalog=duplicate('/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo','DA_MassAbilityInfo')
    rows=[]
    source_catalog=u.load_asset('/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo')
    for source_row in source_catalog.get_editor_property('ability_information'):
        row=u.MyAbilityInfo();row.import_text(source_row.export_text())
        ability=row.get_editor_property('ability')
        if ability and ability.get_path_name() in mapping:
            row.import_text(row.export_text().replace(ability.get_path_name(),mapping[ability.get_path_name()].get_path_name())); rows.append(row)
    assert len(rows)==26, len(rows)
    catalog.set_editor_property('ability_information',rows); save(catalog)

    pc,pc_cdo=copy_bp('/Game/BluePrints/Player/BP_PlayerController','BP_MassPlayerController',u.PureMassPlayerController)
    for key in ['input_config','move_action','shift_action']:
        pc_cdo.set_editor_property('mass_'+key,pc_cdo.get_editor_property(key))
    u.BlueprintEditorLibrary.compile_blueprint(pc); save(pc)
    pawn,pawn_cdo=copy_bp('/Game/BluePrints/Characters/Player/BP_Player','BP_MassPlayer',u.PureMassPlayerCharacter)
    loadout=[]
    for kind,key in [('Projectile','LMB'),('Burst','1'),('Homing','2'),('Chain','3'),('Orbit','4'),('Beam','RMB')]:
        bp=u.load_asset(folder+'/Abilities/GA_Prototype_'+kind)
        cdo=u.get_default_object(cls(bp)); tag=u.GameplayTag(); tag.import_text('(TagName="InputTag.'+key+'")')
        cdo.set_editor_property('startup_input_tag',tag)
        u.BlueprintEditorLibrary.compile_blueprint(bp); save(bp); loadout.append(cls(bp))
    pawn_cdo.set_editor_property('startup_ability',loadout)
    u.BlueprintEditorLibrary.compile_blueprint(pawn); save(pawn)
    mode,mode_cdo=copy_bp('/Game/BluePrints/Game/BP_MyGameMode','BP_PureMassGameMode',u.PureMassGameMode)
    # HUD controller copies need the same isolated skill catalogue on clients (GameMode is server-only).
    old_hud=mode_cdo.get_editor_property('hud_class')
    hud,hud_cdo=copy_bp(old_hud.get_path_name().removesuffix('_C'),'BP_MassHUD')
    original_mode=u.get_default_object(u.load_class(None,'/Game/BluePrints/Game/BP_MyGameMode.BP_MyGameMode_C'))
    original_hud=u.get_default_object(original_mode.get_editor_property('hud_class'))
    for key in ['overlay_widget_controller_class','spell_menu_widget_controller_class','attribute_menu_widget_controller_class']:
        old=original_hud.get_editor_property(key)
        # Existing widgets cast to these Blueprint classes; a child preserves those casts.
        name='BP_MassChild_'+key
        if u.EditorAssetLibrary.does_asset_exist(folder+'/'+name):bp=u.load_asset(folder+'/'+name)
        else:
            factory=u.BlueprintFactory();factory.set_editor_property('parent_class',old)
            bp=tools.create_asset(name,folder,u.Blueprint,factory)
        u.BlueprintEditorLibrary.compile_blueprint(bp)
        default=u.get_default_object(cls(bp))
        default.set_editor_property('ability_info',catalog)
        u.BlueprintEditorLibrary.compile_blueprint(bp); save(bp)
        hud_cdo.set_editor_property(key,cls(bp))
    u.BlueprintEditorLibrary.compile_blueprint(hud); save(hud)
    for key,value in [('ability_info',catalog),('default_pawn_class',cls(pawn)),('player_controller_class',cls(pc)),('hud_class',cls(hud))]:
        mode_cdo.set_editor_property(key,value)
    u.BlueprintEditorLibrary.compile_blueprint(mode); save(mode)

    map_path=folder+'/Maps/L_PureMassDungeon'
    if not u.EditorAssetLibrary.does_asset_exist(map_path):
        assert levels.new_level_from_template(map_path,'/Game/levels/Dungeon')
    else: assert levels.load_level(map_path)
    world=editor.get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode',cls(mode))
    old_enemies=list(u.GameplayStatics.get_all_actors_of_class(world,u.EnemyCharacter))
    positions=[a.get_actor_location() for a in old_enemies]
    old_spawns=list(u.GameplayStatics.get_all_actors_of_class(world,u.MyEnemySpawnPoint))
    for actor in old_enemies+old_spawns: assert actors.destroy_actor(actor)
    # Keep portals out of this isolated test map so they cannot travel into an Actor gameplay mode.
    for actor in list(u.GameplayStatics.get_all_actors_of_class(world,u.MapEntrance)): assert actors.destroy_actor(actor)
    existing=list(u.GameplayStatics.get_all_actors_of_class(world,u.PureMassSpawnRegion))
    if not existing:
        assert positions
        for index,pos in enumerate(positions):
            region=actors.spawn_actor_from_class(u.PureMassSpawnRegion,pos)
            region.set_editor_property('monster_type',monster)
            region.set_editor_property('count',4)
            region.set_editor_property('spacing',125.0)
            region.set_editor_property('room_id','PureMassRoom'+str(index))
            region.set_actor_label('Mass group '+str(index))
    assert levels.save_current_level()
    # Drop references before switching worlds; UObject Python references can prevent map unloading.
    old_enemies.clear();old_spawns.clear();existing.clear()
    actor=None;region=None;world=None
    assert levels.load_level(original)
    report={'passed':True,'assets':created,'ability_count':len(mapping),'map':map_path,'source_assets_modified':False}
    (root/'Saved/PureMass/assets.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    u.log('PURE_MASS_ASSETS_CREATED')
main()
