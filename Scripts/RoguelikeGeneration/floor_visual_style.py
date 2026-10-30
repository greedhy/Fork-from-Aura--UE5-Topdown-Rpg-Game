"""Shared floor and lighting contract for generated maps; never edits shared source assets."""
import unreal as u

REFERENCE = '/Game/levels/Dungeon'
FLOOR_MESH = '/Game/Assets/Dungeon/SM_Tile_6x6'
FLOOR_MATERIAL = '/Game/Assets/Dungeon/Materials/Tileset1/M_Tileset1.M_Tileset1'
ENVIRONMENT = {
    'DirectionalLight': ('DirectionalLightComponent', (
        'intensity', 'light_color', 'use_temperature', 'temperature', 'cast_shadows',
        'indirect_lighting_intensity', 'volumetric_scattering_intensity',
        'light_source_angle', 'light_source_soft_angle', 'atmosphere_sun_light', 'forward_shading_priority')),
    'SkyLight': ('SkyLightComponent', (
        'intensity', 'light_color', 'indirect_lighting_intensity', 'volumetric_scattering_intensity',
        'lower_hemisphere_is_black', 'lower_hemisphere_color', 'real_time_capture',
        'source_type', 'cubemap', 'source_cubemap_angle', 'sky_distance_threshold', 'cast_shadows')),
    'SkyAtmosphere': ('SkyAtmosphereComponent', (
        'bottom_radius', 'atmosphere_height', 'ground_albedo', 'rayleigh_scattering_scale',
        'rayleigh_scattering', 'rayleigh_exponential_distribution', 'mie_scattering_scale',
        'mie_scattering', 'mie_absorption_scale', 'mie_absorption', 'mie_anisotropy',
        'mie_exponential_distribution', 'other_absorption_scale')),
    'ExponentialHeightFog': ('ExponentialHeightFogComponent', (
        'fog_density', 'fog_height_falloff', 'fog_inscattering_luminance',
        'directional_inscattering_exponent', 'directional_inscattering_start_distance',
        'directional_inscattering_luminance', 'fog_max_opacity', 'start_distance',
        'fog_cutoff_distance', 'enable_volumetric_fog', 'volumetric_fog_scattering_distribution',
        'volumetric_fog_albedo', 'volumetric_fog_emissive', 'volumetric_fog_extinction_scale')),
    'VolumetricCloud': ('VolumetricCloudComponent', (
        'layer_bottom_altitude', 'layer_height', 'tracing_start_max_distance',
        'tracing_start_distance_from_camera', 'tracing_max_distance', 'material')),
    'PostProcessVolume': (None, ('settings', 'priority', 'blend_radius', 'blend_weight', 'enabled')),
}

def dirty_packages():
    return [p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())
            + list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())]

def frozen(value):
    if value is None or isinstance(value, (str, int, float, bool)): return value
    if hasattr(value, 'export_text'): return value.export_text()
    if hasattr(value, 'get_path_name'): return value.get_path_name()
    return str(value)

def detached(value):
    if hasattr(value, 'export_text'):
        result = type(value)()
        assert result.import_text(value.export_text())
        return result
    return value

def capture_reference():
    """Capture values, not world/actor references, then restore the caller's map."""
    assert not dirty_packages(), 'UnsavedPackages: '+str(dirty_packages())
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    previous = editor.get_editor_world().get_path_name().split('.')[0]
    def read():
        world = u.EditorLoadingAndSavingUtils.load_map(REFERENCE)
        result = {}
        for name, (component, properties) in ENVIRONMENT.items():
            actors = u.GameplayStatics.get_all_actors_of_class(world, getattr(u, name))
            assert len(actors) == 1, 'ExpectedOneReferenceEnvironmentActor: '+name
            actor = actors[0]
            target = actor.get_component_by_class(getattr(u, component)) if component else actor
            result[name] = {'transform': detached(actor.get_actor_transform()),
                            'values': {key: detached(target.get_editor_property(key)) for key in properties}}
        return result
    try:
        return read()
    finally:
        assert not dirty_packages(), 'ReferenceLoadDirtiedPackages'
        u.EditorLoadingAndSavingUtils.load_map(previous)

def apply_environment(world, reference):
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    # Only our generated light actors may be replaced. Preserve unknown authored lights.
    for actor in list(u.GameplayStatics.get_all_actors_of_class(world, u.Actor)):
        label = actor.get_actor_label()
        if label.startswith(('RG_', 'RF_')) and (
            actor.get_components_by_class(u.LightComponentBase) or label.startswith('RF_Environment_')):
            assert actors.destroy_actor(actor)
    for name, (component, _) in ENVIRONMENT.items():
        row = reference[name]
        transform = row['transform']
        actor = actors.spawn_actor_from_class(getattr(u, name), transform.translation)
        assert actor
        actor.set_actor_transform(transform, False, True)
        actor.set_actor_label('RF_Environment_'+name)
        actor.set_folder_path('RoguelikeFloor/Lighting')
        actor.tags = [u.Name('RG_Floor')]
        target = actor.get_component_by_class(getattr(u, component)) if component else actor
        if component: target.set_mobility(u.ComponentMobility.MOVABLE)
        for key, value in row['values'].items(): target.set_editor_property(key, value)
        if name == 'PostProcessVolume': actor.set_editor_property('unbound', True)

def replace_floor(world):
    actors = u.get_editor_subsystem(u.EditorActorSubsystem)
    old = [a for a in u.GameplayStatics.get_all_actors_of_class(world, u.StaticMeshActor)
           if a.get_actor_label().startswith(('RG_', 'RF_')) and '_Floor_' in a.get_actor_label()]
    assert len(old) in (4, 9), 'UnexpectedFloorTileCount: '+str(len(old))
    # Already migrated: leave actor identity and package dirtiness unchanged.
    if not floor_errors(world): return
    prefix = old[0].get_actor_label().split('_Floor_')[0]
    tags = list(old[0].tags)
    mesh = u.load_asset(FLOOR_MESH)
    assert mesh
    bounds = mesh.get_bounding_box()
    assert abs(bounds.max.x-bounds.min.x-1200)<.01 and abs(bounds.max.y-bounds.min.y-1200)<.01
    for actor in old: assert actors.destroy_actor(actor)
    for ix, x in enumerate((-600, 600)):
        for iy, y in enumerate((-600, 600)):
            actor = actors.spawn_actor_from_class(u.StaticMeshActor, u.Vector(0,0,0))
            actor.set_actor_label(prefix+'_Floor_'+str(ix)+'_'+str(iy))
            actor.set_folder_path('RoguelikeFloor/Floor'); actor.tags = tags
            component = actor.static_mesh_component
            component.set_static_mesh(mesh); component.set_mobility(u.ComponentMobility.STATIC)
            component.set_collision_profile_name('BlockAll')
            actor.set_actor_scale3d(u.Vector(1,1,1))
            actor.set_actor_location(u.Vector(x-(bounds.min.x+bounds.max.x)*.5,
                y-(bounds.min.y+bounds.max.y)*.5, 1-bounds.min.z), False, True)

def floor_errors(world):
    errors=[]
    all_actors=u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor)
    tiles=[a for a in all_actors if a.get_actor_label().startswith(('RG_','RF_')) and '_Floor_' in a.get_actor_label()]
    foundations=[a for a in all_actors if a.get_actor_label().startswith(('RG_','RF_')) and a.get_actor_label().endswith('_Foundation')]
    if len(tiles)!=4: errors.append('ExpectedFourTiles')
    if len(foundations)!=1: errors.append('ExpectedOneFoundation'); return errors
    base=foundations[0]; mesh=base.static_mesh_component.get_editor_property('static_mesh')
    top=base.get_actor_location().z+mesh.get_bounding_box().max.z*base.get_actor_scale3d().z
    centres=[]
    for a in tiles:
        c=a.static_mesh_component; m=c.get_editor_property('static_mesh')
        if m.get_path_name()!=FLOOR_MESH+'.SM_Tile_6x6': errors.append('WrongFloorMesh')
        if [frozen(c.get_material(i)) for i in range(c.get_num_materials())]!=[FLOOR_MATERIAL]: errors.append('WrongFloorMaterial')
        b=m.get_bounding_box(); p=a.get_actor_location(); scale=a.get_actor_scale3d()
        if max(abs(scale.x-1),abs(scale.y-1),abs(scale.z-1))>.0001: errors.append('FloorScaled')
        if p.z+b.min.z*scale.z-top<.99: errors.append('CoplanarFloorFoundation')
        centres.append((round(p.x+(b.min.x+b.max.x)*.5),round(p.y+(b.min.y+b.max.y)*.5)))
    if sorted(centres)!=[(-600,-600),(-600,600),(600,-600),(600,600)]: errors.append('FloorCoverageMismatch')
    return sorted(set(errors))

def environment_errors(world, reference, host):
    errors=[]
    for name,(component,_) in ENVIRONMENT.items():
        found=u.GameplayStatics.get_all_actors_of_class(world,getattr(u,name))
        if len(found)!=(1 if host else 0): errors.append('EnvironmentCount:'+name); continue
        if not host: continue
        a=found[0]; target=a.get_component_by_class(getattr(u,component)) if component else a
        for key,value in reference[name]['values'].items():
            if frozen(target.get_editor_property(key))!=frozen(value): errors.append('EnvironmentValue:'+name+'.'+key)
        if name=='PostProcessVolume' and not a.get_editor_property('unbound'): errors.append('BoundedPostProcess')
        if name=='DirectionalLight':
            actual=a.get_actor_rotation(); expected=reference[name]['transform'].rotation.rotator()
            if max(abs(actual.pitch-expected.pitch),abs(actual.yaw-expected.yaw),abs(actual.roll-expected.roll))>.01:
                errors.append('DirectionalLightRotation')
    if u.GameplayStatics.get_all_actors_of_class(world,u.PointLight): errors.append('UnexpectedRoomTintLights')
    return errors
