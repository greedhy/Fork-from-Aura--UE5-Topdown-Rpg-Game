"""Finish the existing preview and make it safe to open in ordinary PIE."""
def main():
    import unreal as u
    sub=u.get_editor_subsystem(u.EditorActorSubsystem)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert world.get_name()=='L_TerrainSurfacePreview'
    actors={a.get_actor_label():a for a in sub.get_all_level_actors()}
    for i,name in enumerate(['Original','Lava','Mud','Toxic','Frost','Vines']):
        x=(i%3)*1200
        y=(i//3)*1200
        tile=actors['TS_'+name]
        tile.set_actor_location(u.Vector(x-400,y-400,2),False,True)
        actors['TS_'+name+'_Label'].set_actor_location(u.Vector(x,y-460,50),False,True)
        plinth=next(a for label,a in actors.items() if label==f'TS_Plinth_{(i%3)*1100}_{(i//3)*1100}' or label==f'TS_Plinth_{x}_{y}')
        bounds=plinth.static_mesh_component.static_mesh.get_bounding_box()
        center=(bounds.min+bounds.max)*.5
        s=plinth.get_actor_scale3d()
        plinth.set_actor_location(u.Vector(x-center.x*s.x,y-center.y*s.y,-40-center.z*s.z),False,True)
    material=u.load_asset('/Game/Art/TerrainSurfaces/M_TerrainSurface')
    for expr in u.MaterialEditingLibrary.get_material_expressions(material):
        if isinstance(expr,u.MaterialExpressionCustom):
            code=expr.get_editor_property('code')
            if 'Texture2DSampleLevel' in code:
                expr.set_editor_property('code',code.replace('Texture2DSampleLevel','Texture2DSample').replace(',0).rgb',').rgb'))
    errors=u.MaterialEditingLibrary.recompile_material(material)
    assert not errors,str(errors)
    u.EditorAssetLibrary.save_loaded_asset(material)
    world.get_world_settings().set_editor_property('default_game_mode',u.load_class(None,'/Script/Engine.GameModeBase'))
    start=actors.get('TS_PreviewCameraStart')
    if not start:
        start=sub.spawn_actor_from_class(u.PlayerStart,u.Vector(1200,-1800,2500),u.Rotator(pitch=-55,yaw=90,roll=0))
        start.set_actor_label('TS_PreviewCameraStart')
        start.set_folder_path('TerrainSurfacesPreview')
    volume=actors.get('TS_PreviewExposure')
    if not volume:
        volume=sub.spawn_actor_from_class(u.PostProcessVolume,u.Vector(0,0,-200))
        volume.set_actor_label('TS_PreviewExposure')
        volume.set_folder_path('TerrainSurfacesPreview')
    volume.set_editor_property('unbound',True)
    settings=volume.get_editor_property('settings')
    for key in ['auto_exposure_min_brightness','auto_exposure_max_brightness']:
        settings.set_editor_property('override_'+key,True)
        settings.set_editor_property(key,1.0)
    settings.set_editor_property('override_motion_blur_amount',True)
    settings.set_editor_property('motion_blur_amount',0.0)
    volume.set_editor_property('settings',settings)
    sub.clear_actor_selection_set()
    u.log('SURFACE_PREVIEW_FINALIZED')
main()
