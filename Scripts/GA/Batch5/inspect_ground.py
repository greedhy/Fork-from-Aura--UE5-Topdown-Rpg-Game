def _inspect_ground():
    import unreal as u,json
    from pathlib import Path
    pc=next(p for p in u.ObjectIterator(u.MyPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_local_role()==u.NetRole.ROLE_AUTHORITY)
    w=pc.get_world();ignore=list(u.GameplayStatics.get_all_actors_of_class(w,u.BaseCharacter));r={}
    for z in [1,2,10,30]:
        hit=u.SystemLibrary.line_trace_single(w,u.Vector(0,-4900,z),u.Vector(-100,-4800,71),u.TraceTypeQuery.ECC_VISIBILITY,False,ignore,u.DrawDebugTrace.NONE,True)
        if hit:
            r[str(z)]=hit.to_tuple() if hasattr(hit,'to_tuple') else str(hit)
    for z,hh in [(61,60),(71,70)]:
        hit=u.SystemLibrary.capsule_trace_single_for_objects(w,u.Vector(100,-4800,z),u.Vector(50,-4850,z),32,hh,[u.ObjectTypeQuery.ECC_WORLD_STATIC,u.ObjectTypeQuery.ECC_WORLD_DYNAMIC],False,ignore,u.DrawDebugTrace.NONE,True)
        r['capsule_'+str(z)]=hit.to_tuple() if hit else None
    (Path(u.Paths.project_dir())/'Saved/GAAuthoring/Batch5/ground.json').write_text(json.dumps(r,default=str,indent=2),encoding='utf8')
_inspect_ground()
