"""Author independent terrain FX, configs and ready-to-place gameplay actors."""
def main():
    import unreal as u
    import json, hashlib
    from pathlib import Path
    root=Path(u.Paths.project_dir()).resolve()
    report=root/'Saved/TerrainSurfaces'
    art='/Game/Art/TerrainSurfaces/Effects'
    gameplay='/Game/BluePrints/Actor/Terrain'
    lib=u.MaterialEditingLibrary
    atl=u.AssetToolsHelpers.get_asset_tools()
    sources={'embers':'/Game/Assets/Effects/Soul/NS_Embers','stars':'/Game/Assets/Effects/Stun/NS_Stars','fire':'/Game/Assets/Effects/Fire/NS_Fire'}
    hashes={p:hashlib.sha256((root/'Content'/(p.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest() for p in sources.values()}
    def create(path,cls,factory):
        if u.EditorAssetLibrary.does_asset_exist(path):
            obj=u.load_asset(path)
            assert isinstance(obj,cls),path
            return obj
        folder,name=path.rsplit('/',1)
        obj=atl.create_asset(name,folder,cls,factory)
        assert obj,path
        return obj
    def duplicate(source,target):
        obj=u.load_asset(target) if u.EditorAssetLibrary.does_asset_exist(target) else u.EditorAssetLibrary.duplicate_asset(source,target)
        assert obj,target
        return obj
    def save(obj):
        assert u.EditorAssetLibrary.save_loaded_asset(obj,False),obj.get_path_name()

    material=create(art+'/M_TerrainParticle',u.Material,u.MaterialFactoryNew())
    material.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided',True)
    material.set_editor_property('used_with_niagara_sprites',True)
    lib.delete_all_material_expressions(material)
    def node(cls): return lib.create_material_expression(material,cls)
    def scalar(name,value):
        obj=node(u.MaterialExpressionScalarParameter)
        obj.set_editor_property('parameter_name',name); obj.set_editor_property('default_value',value)
        return obj
    uv=node(u.MaterialExpressionTextureCoordinate)
    time=node(u.MaterialExpressionTime)
    particle=node(u.MaterialExpressionParticleColor)
    tint=node(u.MaterialExpressionVectorParameter)
    tint.set_editor_property('parameter_name','Tint'); tint.set_editor_property('default_value',u.LinearColor(1,.2,.02,1))
    mask=node(u.MaterialExpressionCustom)
    mask.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    mask.set_editor_property('code','''float2 p=UV*2-1;
float r=length(p); float a=atan2(p.y,p.x); float m=0;
if(Style<0.5) {
    float sway=sin(UV.y*10-Time*4)*.17;
    float width=(1-UV.y)*.85+.08;
    m=saturate((width-abs(p.x+sway))*5)*saturate((1-UV.y)*4)*saturate(UV.y*8);
} else if(Style<1.5) {
    float arms=pow(saturate(cos(a*6)),16);
    m=saturate((1-r)*5)*max(arms*.9,saturate((.3-r)*4));
} else if(Style<2.5) {
    float ripple=sin(a*5+Time*2+r*9)*.08;
    m=pow(saturate(1-r+ripple),1.5)*.7+saturate(1-abs(r-.65)*18)*.25;
} else {
    float leaf=saturate((1-abs(p.x)-p.y*p.y)*6);
    float vein=1-saturate(abs(p.x+.06*sin(p.y*9))*18)*.45;
    m=leaf*vein*saturate((1-r)*8);
}
return saturate(m);''')
    pins=[]
    for name,obj in [('UV',uv),('Time',time),('Style',scalar('Style',0))]:
        pin=u.CustomInput(); pin.set_editor_property('input_name',name); pins.append(pin)
    mask.set_editor_property('inputs',pins)
    for name,obj in [('UV',uv),('Time',time)]: lib.connect_material_expressions(obj,'',mask,name)
    style=next(x for x in lib.get_material_expressions(material) if isinstance(x,u.MaterialExpressionScalarParameter) and str(x.get_editor_property('parameter_name'))=='Style')
    lib.connect_material_expressions(style,'',mask,'Style')
    opacity=node(u.MaterialExpressionMultiply)
    lib.connect_material_expressions(mask,'',opacity,'A'); lib.connect_material_expressions(particle,'A',opacity,'B')
    lib.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
    emission=node(u.MaterialExpressionMultiply)
    lib.connect_material_expressions(tint,'',emission,'A'); lib.connect_material_expressions(scalar('Glow',2),'',emission,'B')
    lib.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.layout_material_expressions(material)
    errors=list(lib.recompile_material(material)); assert not errors,errors
    save(material)
    variants=[('Lava',u.TerrainSurfaceType.LAVA,0,(1,.16,.012,1),8,2,'fire'),
              ('Frost',u.TerrainSurfaceType.FROST,1,(.18,.65,1,1),0,0,'stars'),
              ('Toxic',u.TerrainSurfaceType.TOXIC,2,(.25,1,.025,1),4,3,'fire'),
              ('Vines',u.TerrainSurfaceType.VINES,3,(.15,.8,.05,1),0,0,'stars')]
    emitters={'embers':['Fountain'],'stars':['Fountain'],'fire':['Flame1_0','Flame1001_2','Flame1002_4','Sparks_5','HeatWave_8']}
    records=[]
    for name,kind,style,color,damage,linger,template in variants:
        systems={}
        for role,source_key in [('Surface','embers'),('Status',template)]:
            mi=create(f'{art}/MI_{name}_{role}',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
            lib.set_material_instance_parent(mi,material)
            lib.set_material_instance_scalar_parameter_value(mi,'Style',style)
            glow={'Lava':2.5,'Frost':3.,'Toxic':1.4,'Vines':2.2}[name]
            lib.set_material_instance_scalar_parameter_value(mi,'Glow',glow)
            lib.set_material_instance_vector_parameter_value(mi,'Tint',u.LinearColor(*color))
            lib.update_material_instance(mi); save(mi)
            path=f'{art}/NS_{name}_{role}'
            system=duplicate(sources[source_key],path)
            renderer_paths=[]
            for emitter in emitters[source_key]:
                renderer_path=f'{system.get_path_name()}:{emitter}.NiagaraSpriteRendererProperties_0'
                renderer=u.load_object(None,renderer_path)
                # Disabled distortion/spark emitters can have a different renderer.
                if not renderer:
                    assert emitter in ['Sparks_5','HeatWave_8'],renderer_path
                    continue
                assert isinstance(renderer,u.NiagaraSpriteRendererProperties),renderer_path
                renderer.set_editor_property('material',mi)
                renderer_paths.append(renderer_path)
            save(system)
            systems[role]={'asset':path,'emitters':emitters[source_key],'renderers':renderer_paths}
        factory=u.DataAssetFactory(); factory.set_editor_property('data_asset_class',u.TerrainSurfaceConfig)
        config=create(f'{gameplay}/Data/DA_Terrain_{name}',u.TerrainSurfaceConfig,factory)
        for key,value in {'surface_type':kind,'damage_per_second':damage,'exit_duration':linger,'movement_multiplier':.6,
                          'entangle_duration':2.,'entangle_recovery':3.,
                          'ground_mesh':u.load_asset(f'/Game/Art/TerrainSurfaces/{name}/SM_Ground_{name}_4x4'),
                          'surface_vfx':u.load_asset(systems['Surface']['asset']),'status_vfx':u.load_asset(systems['Status']['asset'])}.items():
            config.set_editor_property(key,value)
        save(config)
        bp_path=f'{gameplay}/BP_Terrain_{name}'
        factory=u.BlueprintFactory(); factory.set_editor_property('parent_class',u.TerrainSurface)
        bp=create(bp_path,u.Blueprint,factory)
        cls=u.EditorAssetLibrary.load_blueprint_class(bp_path)
        cdo=u.get_default_object(cls)
        cdo.set_editor_property('config',config)
        u.BlueprintEditorLibrary.compile_blueprint(bp); save(bp)
        records.append({'name':name,'blueprint':bp_path,'config':config.get_path_name(),'systems':systems,'damage':damage,'linger':linger})
    for path,sha in hashes.items():
        assert hashlib.sha256((root/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()==sha
    result={'variants':records,'source_hashes':hashes,'material_errors':errors,'source_assets_unchanged':True}
    (report/'effect_assets.json').write_text(json.dumps(result,indent=2))
    u.log('TERRAIN_EFFECT_ASSETS_CREATED '+str(len(records)))
main()
