def main():
    import unreal as u
    import json,hashlib,uuid
    from pathlib import Path
    root=Path(u.Paths.project_dir()).resolve()
    plan=json.loads((root/'Saved/TerrainSurfaces/effect_assets.json').read_text())
    result={'run_id':uuid.uuid4().hex,'variants':[]}
    for item in plan['variants']:
        cls=u.EditorAssetLibrary.load_blueprint_class(item['blueprint']); assert cls
        cdo=u.get_default_object(cls)
        config=cdo.get_editor_property('config'); assert config.get_path_name()==item['config']
        assert config.get_editor_property('damage_per_second')==item['damage']
        assert config.get_editor_property('exit_duration')==item['linger']
        assert config.get_editor_property('ground_mesh')
        for role,field in [('Surface','surface_vfx'),('Status','status_vfx')]:
            system=config.get_editor_property(field)
            assert system==u.load_asset(item['systems'][role]['asset'])
            for path in item['systems'][role]['renderers']:
                renderer=u.load_object(None,path)
                mat=renderer.get_editor_property('material')
                assert mat.get_name()==f"MI_{item['name']}_{role}"
        assert cdo.get_editor_property('replicates')
        result['variants'].append({'name':item['name'],'blueprint':item['blueprint'],'config':item['config'],'passed':True})
    for path,expected in plan['source_hashes'].items():
        assert hashlib.sha256((root/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()==expected
    errors=list(u.MaterialEditingLibrary.recompile_material(u.load_asset('/Game/Art/TerrainSurfaces/Effects/M_TerrainParticle')))
    assert not errors,errors
    for path in ['/Game/BluePrints/Characters/Player/BP_Player','/Game/BluePrints/Characters/Goblin/BP_Goblin']:
        # Character asset names include existing redirectors; load their generated class.
        cls=u.load_class(None,path+'.'+path.rsplit('/',1)[1]+'_C'); assert cls,path
        cdo=u.get_default_object(cls)
        assert cdo.get_component_by_class(u.TerrainStatusComponent),path
    result.update(passed=True,material_errors=errors,original_vfx_unchanged=True)
    (root/'Saved/TerrainSurfaces/effect_validation.json').write_text(json.dumps(result,indent=2))
    u.log('TERRAIN_EFFECT_ASSETS_VALIDATED '+json.dumps(result))
main()
