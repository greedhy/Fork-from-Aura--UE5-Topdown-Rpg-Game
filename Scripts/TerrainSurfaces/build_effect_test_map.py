"""Create a separate walkable test map; never replace production-level floors."""
def main():
    import unreal as u
    from pathlib import Path
    import json
    root=Path(u.Paths.project_dir()).resolve()
    sub=u.get_editor_subsystem(u.EditorActorSubsystem)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert world.get_name()=='L_TerrainEffectsTest'
    assert not any(a.get_actor_label().startswith('TerrainDemo_') for a in sub.get_all_level_actors()),'Already populated'
    def named(actor,name):
        actor.set_actor_label('TerrainDemo_'+name); actor.set_folder_path('TerrainEffectsDemo'); return actor
    mesh=u.load_asset('/Game/Assets/Dungeon/SM_Block4x4x1')
    bounds=mesh.get_bounding_box(); center=(bounds.min+bounds.max)*.5; size=bounds.max-bounds.min
    scale=u.Vector(2800/size.x,2000/size.y,100/size.z)
    floor=named(sub.spawn_actor_from_class(u.StaticMeshActor,u.Vector(-center.x*scale.x,-center.y*scale.y,-50-center.z*scale.z)),'Floor')
    floor.static_mesh_component.set_static_mesh(mesh); floor.set_actor_scale3d(scale)
    floor.static_mesh_component.set_collision_profile_name('BlockAll')
    placements={'Lava':(-650,-250),'Frost':(650,-250),'Toxic':(-650,450),'Vines':(650,450)}
    for name,(x,y) in placements.items():
        cls=u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Actor/Terrain/BP_Terrain_'+name)
        terrain=named(sub.spawn_actor_from_class(cls,u.Vector(x,y,6)),name)
        terrain.set_editor_property('surface_size',u.Vector2D(600,500))
        # Editor property edit reruns construction through the native actor.
        label=named(sub.spawn_actor_from_class(u.TextRenderActor,u.Vector(x,y-280,20),u.Rotator(pitch=90,yaw=-90,roll=0)),name+'_Label')
        text=label.get_component_by_class(u.TextRenderComponent)
        text.set_text({'Lava':'LAVA / BURN','Frost':'FROST / SLOW','Toxic':'TOXIC / POISON','Vines':'VINES / ROOT'}[name])
        text.set_world_size(45); text.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
    for slot,x in enumerate([-100,100]):
        start=named(sub.spawn_actor_from_class(u.TravelPlayerStart,u.Vector(x,-750,110)),'Start_'+str(slot))
        start.set_editor_property('player_start_tag',u.Name('TerrainEntry'))
        start.set_editor_property('player_slot',slot)
        start.set_editor_property('default_entry_group',True)
    world.get_world_settings().set_editor_property('default_game_mode',u.EditorAssetLibrary.load_blueprint_class('/Game/BluePrints/Game/BP_MyGameMode'))
    light=named(sub.spawn_actor_from_class(u.DirectionalLight,u.Vector(0,0,1600),u.Rotator(pitch=-55,yaw=-35,roll=0)),'Light')
    light.light_component.set_mobility(u.ComponentMobility.MOVABLE); light.light_component.set_intensity(6)
    sky=named(sub.spawn_actor_from_class(u.SkyLight,u.Vector(0,0,1200)),'Sky')
    sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    sky.light_component.set_intensity(1.5)
    sky.light_component.set_editor_property('source_type',u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sky.light_component.set_editor_property('cubemap',u.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
    sky.light_component.set_editor_property('lower_hemisphere_is_black',False); sky.light_component.recapture_sky()
    volume=named(sub.spawn_actor_from_class(u.PostProcessVolume,u.Vector(0,0,-200)),'Exposure')
    volume.set_editor_property('unbound',True)
    settings=volume.get_editor_property('settings')
    for key in ['auto_exposure_min_brightness','auto_exposure_max_brightness']:
        settings.set_editor_property('override_'+key,True); settings.set_editor_property(key,1.)
    volume.set_editor_property('settings',settings)
    sub.clear_actor_selection_set()
    assert u.EditorLoadingAndSavingUtils.save_map(world,'/Game/levels/L_TerrainEffectsTest')
    (root/'Saved/TerrainSurfaces/effect_test_map.json').write_text(json.dumps({'map':world.get_path_name(),'placements':placements,'player_starts':2},indent=2))
    u.log('TERRAIN_EFFECT_TEST_MAP_SAVED')
main()
