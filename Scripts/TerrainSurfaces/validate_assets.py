"""Check compiled materials, actual GPU texture sizes, references, and source hashes."""
def main():
    import hashlib
    import json
    from pathlib import Path
    import unreal as u
    root=Path(u.Paths.project_dir()).resolve()
    report=root/'Saved/TerrainSurfaces'
    plan=json.loads((report/'assets.json').read_text())
    lib=u.MaterialEditingLibrary
    checks=[]
    for variant in plan['variants']:
        name=variant['name']
        inst=u.load_asset(variant['material'])
        mesh=u.load_asset(variant['mesh'])
        assert inst and mesh
        assert all(item.material_interface==inst for item in mesh.static_materials),name+' mesh material assignment'
        textures=[]
        for role,param in [('BC','GroundBaseColor'),('N','GroundNormal'),('ORM','GroundORM')]:
            tex=u.load_asset(variant['textures'][role])
            assert lib.get_material_instance_texture_parameter_value(inst,param)==tex
            assert tex.blueprint_get_size_x()==1024 and tex.blueprint_get_size_y()==1024
            assert tex.get_editor_property('srgb')==(role=='BC')
            assert tex.get_editor_property('mip_gen_settings')==u.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP
            assert not tex.get_editor_property('never_stream')
            expected=u.TextureCompressionSettings.TC_NORMALMAP if role=='N' else u.TextureCompressionSettings.TC_MASKS if role=='ORM' else u.TextureCompressionSettings.TC_DEFAULT
            assert tex.get_editor_property('compression_settings')==expected
            textures.append({'role':role,'gpu_size':[1024,1024],'srgb':tex.get_editor_property('srgb'),'compression':str(expected)})
        for k,v in variant['parameters'].items():
            assert abs(lib.get_material_instance_scalar_parameter_value(inst,k)-v)<1e-5,(name,k)
        checks.append({'name':name,'passed':True,'textures':textures,'mesh_material_slots':len(mesh.static_materials)})
    material=u.load_asset(plan['folder']+'/M_TerrainSurface')
    errors=list(lib.recompile_material(material))
    assert not errors,errors
    for k,path in plan['source_assets'].items():
        file=root/'Content'/(path.removeprefix('/Game/')+'.uasset')
        assert hashlib.sha256(file.read_bytes()).hexdigest()==plan['source_hashes'][k],k+' source changed'
    result={'passed':True,'variants':checks,'shader_errors':errors,'source_assets_unchanged':True,
        'asset_count':len(u.EditorAssetLibrary.list_assets(plan['folder'],recursive=True,include_folder=False))}
    (report/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    u.log('SURFACE_VALIDATION '+json.dumps(result))
main()
