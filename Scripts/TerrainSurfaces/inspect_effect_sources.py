def main():
    import unreal as u
    import json
    from pathlib import Path
    result={}
    for path in ['/Game/Assets/Effects/Soul/NS_Embers','/Game/Assets/Effects/Stun/NS_Halo','/Game/Assets/Effects/Fire/NS_Fire']:
        obj=u.load_asset(path)
        result[path]={'api':[x for x in dir(obj) if any(k in x for k in ['emitter','compil','parameter'])]}
    result['unreal_api']=[x for x in dir(u) if any(k in x.lower() for k in ['niagaraeditor','get_objects','object_iterator','systemlibrary'])]
    result['dirty']=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]+[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    out=Path(u.Paths.project_dir())/'Saved/TerrainSurfaces/effect_sources.json'
    out.write_text(json.dumps(result,indent=2))
    u.log('TERRAIN_EFFECT_SOURCES '+str(out))
main()
