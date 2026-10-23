"""Create a neutral six-panel comparison using the project's floor/block assets."""
def main():
    import unreal as u
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert world.get_name()=='L_TerrainSurfacePreview','Open the dedicated preview map first'
    sub=u.get_editor_subsystem(u.EditorActorSubsystem)
    assert not any(a.get_actor_label().startswith('TS_') for a in sub.get_all_level_actors()),'Preview already populated'
    folder='/Game/Art/TerrainSurfaces'
    block=u.load_asset('/Game/Assets/Dungeon/SM_Block4x4x1')
    def tag(a,label):
        a.set_actor_label('TS_'+label)
        a.set_folder_path('TerrainSurfacesPreview')
        a.tags=[u.Name('TerrainSurfacesPreview')]
        return a
    def platform(x,y):
        bounds=block.get_bounding_box()
        size=bounds.max-bounds.min
        scale=u.Vector(840/size.x,840/size.y,80/size.z)
        center=(bounds.min+bounds.max)*.5
        a=tag(sub.spawn_actor_from_class(u.StaticMeshActor,u.Vector(x-center.x*scale.x,y-center.y*scale.y,-40-center.z*scale.z)),f'Plinth_{x}_{y}')
        a.static_mesh_component.set_static_mesh(block)
        a.set_actor_scale3d(scale)
    names=['Original','Lava','Mud','Toxic','Frost','Vines']
    for i,name in enumerate(names):
        x=(i%3)*1200
        y=(i//3)*1200
        platform(x,y)
        path='/Game/Assets/Dungeon/SM_Tile_4x4' if name=='Original' else f'{folder}/{name}/SM_Ground_{name}_4x4'
        mesh=u.load_asset(path)
        a=tag(sub.spawn_actor_from_class(u.StaticMeshActor,u.Vector(x-400,y-400,2)),name)
        a.static_mesh_component.set_static_mesh(mesh)
        a.static_mesh_component.set_mobility(u.ComponentMobility.STATIC)
        a.static_mesh_component.set_collision_profile_name('BlockAll')
        label=tag(sub.spawn_actor_from_class(u.TextRenderActor,u.Vector(x,y-455,40),u.Rotator(pitch=90,yaw=-90,roll=0)),name+'_Label')
        text=label.get_component_by_class(u.TextRenderComponent)
        text.set_text(name.upper())
        text.set_world_size(65)
        text.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
        text.set_text_render_color(u.Color(220,233,245,255))
    light=tag(sub.spawn_actor_from_class(u.DirectionalLight,u.Vector(0,0,1600),u.Rotator(pitch=-55,yaw=-35,roll=0)),'KeyLight')
    light.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    light.light_component.set_intensity(6.0)
    sky=tag(sub.spawn_actor_from_class(u.SkyLight,u.Vector(0,0,1200)),'SkyFill')
    sky.light_component.set_mobility(u.ComponentMobility.MOVABLE)
    sky.light_component.set_intensity(1.5)
    sky.light_component.set_editor_property('lower_hemisphere_is_black',False)
    sky.light_component.set_editor_property('source_type',u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    sky.light_component.set_editor_property('cubemap',u.load_asset('/Engine/MapTemplates/Sky/DaylightAmbientCubemap'))
    sky.light_component.recapture_sky()
    sub.clear_actor_selection_set()
    u.log('SURFACE_PREVIEW_COMPLETE six comparison panels')
main()
