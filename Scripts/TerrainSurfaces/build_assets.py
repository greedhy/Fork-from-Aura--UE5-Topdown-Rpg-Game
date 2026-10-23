"""Duplicate project textures/material/mesh, import edited albedos, build surface variants.

Run in Unreal through MCP. All UObject references are function-local, so changing
editor maps afterwards is safe. Only /Game/Art/TerrainSurfaces is written.
"""
def main():
    import json
    import hashlib
    from pathlib import Path
    import unreal as u
    root=Path(u.Paths.project_dir()).resolve()
    folder='/Game/Art/TerrainSurfaces'
    src='/Game/Assets/Dungeon/Materials/Tileset1x1/Tileset1x1_1/'
    stem='Tileset1x1_low_DefaultMaterial_'
    sources={'BC':src+stem+'BaseColor','N':src+stem+'Normal','ORM':src+stem+'OcclusionRoughnessMetallic',
             'Material':src+'M_Tileset1x1_1','Mesh':'/Game/Assets/Dungeon/SM_Tile_4x4',
             'Noise':'/Game/Assets/Effects/Projectiles/FireBolt/Materials/Textures/Noise_blur_1'}
    def hash_source(path):
        file=root/'Content'/(path.removeprefix('/Game/')+'.uasset')
        return hashlib.sha256(file.read_bytes()).hexdigest()
    before={k:hash_source(v) for k,v in sources.items()}
    lib=u.MaterialEditingLibrary
    atl=u.AssetToolsHelpers.get_asset_tools()
    report=root/'Saved/TerrainSurfaces'
    report.mkdir(parents=True,exist_ok=True)
    def dup(source,dest):
        assert dest.startswith(folder+'/')
        obj=u.EditorAssetLibrary.load_asset(dest) if u.EditorAssetLibrary.does_asset_exist(dest) else u.EditorAssetLibrary.duplicate_asset(source,dest)
        assert obj,dest
        u.EditorAssetLibrary.set_metadata_tag(obj,'TerrainSurfaceAuthoring','2026-10-22')
        return obj
    def tex_settings(t,role):
        t.set_editor_property('srgb',role=='BC')
        t.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if role=='N' else
            u.TextureCompressionSettings.TC_MASKS if role in ['ORM','Noise'] else u.TextureCompressionSettings.TC_DEFAULT)
        t.set_editor_property('power_of_two_mode',u.TexturePowerOfTwoSetting.RESIZE_TO_SPECIFIC_RESOLUTION)
        size=256 if role=='Noise' else 1024
        t.set_editor_property('resize_during_build_x',size)
        t.set_editor_property('resize_during_build_y',size)
        t.set_editor_property('max_texture_size',size)
        t.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
        t.set_editor_property('never_stream',False)
        t.set_editor_property('address_x',u.TextureAddress.TA_WRAP)
        t.set_editor_property('address_y',u.TextureAddress.TA_WRAP)
        u.EditorAssetLibrary.save_loaded_asset(t)
    names=['Lava','Mud','Toxic','Frost','Vines']
    textures={}
    for name in names:
        textures[name]={}
        for role in ['BC','N','ORM']:
            path=f'{folder}/{name}/T_Ground_{name}_{role}'
            texture=dup(sources[role],path)
            expected_source=str(root/'SourceArt/TerrainSurfaces/BaseColor'/f'T_Ground_{name}_BC.png')
            import_data=texture.get_editor_property('asset_import_data')
            already_imported=import_data and any(Path(p).resolve()==Path(expected_source).resolve() for p in import_data.extract_filenames())
            if role=='BC' and not already_imported:
                task=u.AssetImportTask()
                task.filename=expected_source
                task.destination_path=f'{folder}/{name}'
                task.destination_name=f'T_Ground_{name}_BC'
                task.automated=True
                task.replace_existing=True
                task.replace_existing_settings=False
                task.save=False
                atl.import_asset_tasks([task])
                texture=u.load_asset(path)
                assert texture and task.imported_object_paths, 'Albedo import failed: '+path
            tex_settings(texture,role)
            textures[name][role]=texture
    noise=dup(sources['Noise'],folder+'/Shared/T_Ground_FlowNoise')
    tex_settings(noise,'Noise')
    material=dup(sources['Material'],folder+'/M_TerrainSurface')
    lib.delete_all_material_expressions(material)
    material.set_editor_property('two_sided',False)
    material.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    material.set_editor_property('use_material_attributes',False)
    node_index=0
    def node(cls):
        nonlocal node_index
        node_index+=1
        return lib.create_material_expression(material,cls,-1800+(node_index%7)*260,(node_index//7)*230)
    def link(a,b,pin,out=''):
        assert lib.connect_material_expressions(a,out,b,pin),(a.get_name(),b.get_name(),pin,out)
    def scalar(name,value,group='Surface'):
        n=node(u.MaterialExpressionScalarParameter)
        n.set_editor_property('parameter_name',name)
        n.set_editor_property('default_value',value)
        n.set_editor_property('group',group)
        return n
    def vector(name,value,group='Surface'):
        n=node(u.MaterialExpressionVectorParameter)
        n.set_editor_property('parameter_name',name)
        n.set_editor_property('default_value',u.LinearColor(*value))
        n.set_editor_property('group',group)
        return n
    def custom(code,inputs,kind):
        n=node(u.MaterialExpressionCustom)
        n.set_editor_property('code',code)
        n.set_editor_property('output_type',kind)
        pins=[]
        for k in inputs:
            pin=u.CustomInput()
            pin.set_editor_property('input_name',k)
            pins.append(pin)
        n.set_editor_property('inputs',pins)
        for k,v in inputs.items(): link(v,n,k)
        return n
    world=node(u.MaterialExpressionWorldPosition)
    mesh_uv=node(u.MaterialExpressionTextureCoordinate)
    uv=custom('return lerp(MeshUV*Tiling, World.xy/max(TileSize,1.0), saturate(UseWorld));',
        {'World':world,'MeshUV':mesh_uv,'Tiling':scalar('UVTiling',1,'Mapping'),
         'TileSize':scalar('WorldTileSize',400,'Mapping'),'UseWorld':scalar('UseWorldUV',1,'Mapping')},u.CustomMaterialOutputType.CMOT_FLOAT2)
    def sample(name,texture,sampler,coords=uv):
        n=node(u.MaterialExpressionTextureSampleParameter2D)
        n.set_editor_property('parameter_name',name)
        n.set_editor_property('group','Textures')
        n.set_editor_property('texture',texture)
        n.set_editor_property('sampler_type',sampler)
        link(coords,n,'UVs')
        return n
    bc=sample('GroundBaseColor',textures['Lava']['BC'],u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    norm=sample('GroundNormal',textures['Lava']['N'],u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    orm=sample('GroundORM',textures['Lava']['ORM'],u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    surface_type=scalar('SurfaceType',0)
    mask=custom('''float m;
float lum=dot(C,float3(0.2126,0.7152,0.0722));
if(Type<0.5) m=saturate((C.r-max(C.g,C.b)*1.5-0.025)*5.0);
else if(Type<1.5) m=saturate((C.g/(C.r+0.002)-0.37)*6)*saturate((0.23-lum)*7);
else if(Type<2.5) m=saturate((C.g-max(C.b,C.r*0.65)-0.02)*7);
else if(Type<3.5) m=saturate((lum-0.12)*3.2);
else m=saturate((C.g-C.b-0.015)*8);
return saturate((m+Bias)*Contrast);''',{'C':bc,'Type':surface_type,'Bias':scalar('MaskBias',0),
        'Contrast':scalar('MaskContrast',1)},u.CustomMaterialOutputType.CMOT_FLOAT1)
    color=custom('return C*Tint*Brightness;',{'C':bc,'Tint':vector('ColorTint',(1,1,1,1)),
        'Brightness':scalar('Brightness',1)},u.CustomMaterialOutputType.CMOT_FLOAT3)
    lib.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    rough=custom('return clamp(lerp(Dry,Wet,Mask)*(0.85+0.15*ORM.g),0.04,1.0);',
        {'Dry':scalar('DryRoughness',.82),'Wet':scalar('DetailRoughness',.26),'Mask':mask,'ORM':orm},u.CustomMaterialOutputType.CMOT_FLOAT1)
    lib.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    ao=custom('return lerp(1,ORM.r,Amount);',{'ORM':orm,'Amount':scalar('OcclusionStrength',.35)},u.CustomMaterialOutputType.CMOT_FLOAT1)
    lib.connect_material_property(ao,'',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    metal=scalar('Metallic',0)
    lib.connect_material_property(metal,'',u.MaterialProperty.MP_METALLIC)
    # Shallow detail relief inferred from the edited albedo, plus the copied
    # original slab normal. This is surface shading, not mesh displacement.
    height_tex=node(u.MaterialExpressionTextureObjectParameter)
    height_tex.set_editor_property('parameter_name','GroundBaseColor')
    height_tex.set_editor_property('texture',textures['Lava']['BC'])
    detail=custom('''float2 d=float2(1.0/1024.0,0);
float3 w=float3(0.2126,0.7152,0.0722);
float l=dot(Texture2DSample(Tex,TexSampler,UV-d.xy).rgb,w);
float r=dot(Texture2DSample(Tex,TexSampler,UV+d.xy).rgb,w);
float b=dot(Texture2DSample(Tex,TexSampler,UV-d.yx).rgb,w);
float t=dot(Texture2DSample(Tex,TexSampler,UV+d.yx).rgb,w);
return normalize(float3(N.xy*NormalStrength+float2(l-r,b-t)*DetailStrength,max(N.z,0.15)));''',
        {'Tex':height_tex,'UV':uv,'N':norm,'NormalStrength':scalar('NormalStrength',.65),
         'DetailStrength':scalar('DetailNormalStrength',1.2)},u.CustomMaterialOutputType.CMOT_FLOAT3)
    lib.connect_material_property(detail,'',u.MaterialProperty.MP_NORMAL)
    time=node(u.MaterialExpressionTime)
    flow_uv=custom('return UV*2.0+float2(Time*Speed,Time*Speed*0.63);',
        {'UV':uv,'Time':time,'Speed':scalar('FlowSpeed',.025,'Animation')},u.CustomMaterialOutputType.CMOT_FLOAT2)
    noise_node=sample('FlowNoise',noise,u.MaterialSamplerType.SAMPLERTYPE_MASKS,flow_uv)
    emissive=custom('return C*Mask*Strength*(1.0+sin(Time*Speed)*Pulse)*(0.85+Noise.r*0.3);',
        {'C':bc,'Mask':mask,'Strength':scalar('EmissiveStrength',3.5,'Emission'),'Time':time,
         'Speed':scalar('PulseSpeed',1.4,'Animation'),'Pulse':scalar('PulseAmount',.12,'Animation'),
         'Noise':noise_node},u.CustomMaterialOutputType.CMOT_FLOAT3)
    lib.connect_material_property(emissive,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.layout_material_expressions(material)
    errors=lib.recompile_material(material)
    assert not errors,'Material compile errors: '+str(errors)
    u.EditorAssetLibrary.save_loaded_asset(material)
    presets={
      'Lava':dict(SurfaceType=0,DryRoughness=.87,DetailRoughness=.30,EmissiveStrength=3.5,DetailNormalStrength=1.6),
      'Mud':dict(SurfaceType=1,DryRoughness=.65,DetailRoughness=.12,EmissiveStrength=0,DetailNormalStrength=1.4),
      'Toxic':dict(SurfaceType=2,DryRoughness=.80,DetailRoughness=.14,EmissiveStrength=1.8,DetailNormalStrength=1.1),
      'Frost':dict(SurfaceType=3,DryRoughness=.18,DetailRoughness=.75,EmissiveStrength=0,DetailNormalStrength=.7),
      'Vines':dict(SurfaceType=4,DryRoughness=.88,DetailRoughness=.58,EmissiveStrength=0,DetailNormalStrength=1.8)}
    variants=[]
    for name in names:
        path=f'{folder}/{name}/MI_Ground_{name}'
        inst=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else atl.create_asset('MI_Ground_'+name,folder+'/'+name,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
        lib.set_material_instance_parent(inst,material)
        for role,param in [('BC','GroundBaseColor'),('N','GroundNormal'),('ORM','GroundORM')]:
            # UE 5.8's setters return false even after writing; verify readback.
            lib.set_material_instance_texture_parameter_value(inst,param,textures[name][role])
            assert lib.get_material_instance_texture_parameter_value(inst,param)==textures[name][role]
        for k,v in presets[name].items():
            lib.set_material_instance_scalar_parameter_value(inst,k,v)
            assert abs(lib.get_material_instance_scalar_parameter_value(inst,k)-v)<1e-5
        lib.update_material_instance(inst)
        u.EditorAssetLibrary.save_loaded_asset(inst)
        mesh=dup(sources['Mesh'],f'{folder}/{name}/SM_Ground_{name}_4x4')
        for i in range(len(mesh.static_materials)): mesh.set_material(i,inst)
        u.EditorAssetLibrary.save_loaded_asset(mesh)
        variants.append({'name':name,'material':path,'mesh':mesh.get_path_name(),
            'textures':{k:v.get_path_name() for k,v in textures[name].items()},'parameters':presets[name]})
    after={k:hash_source(v) for k,v in sources.items()}
    assert before==after,'Source assets were unexpectedly modified'
    result={'folder':folder,'variants':variants,'source_assets':sources,'source_hashes':after,
        'source_assets_unchanged':True,'material_compile_errors':list(errors),'runtime_texture_size':1024,
        'source_albedo_size':1254,'note':'Original stone normal and ORM are copied. Edited albedo supplies additional shallow shader relief.'}
    (report/'assets.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    unreal_log='SURFACE_ASSETS_COMPLETE '+json.dumps({'variants':len(variants),'textures':16,'compile_errors':list(errors),'sources_unchanged':before==after})
    u.log(unreal_log)
main()
