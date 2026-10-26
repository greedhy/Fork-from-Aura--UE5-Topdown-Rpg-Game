def _mass_points_qa():
    import unreal as u,json,time
    from pathlib import Path
    q={'phase':'start','started':time.monotonic(),'checks':{}}
    def finish(error=None):
        u.unregister_slate_post_tick_callback(handle);q.update(passed=error is None,error=error)
        (Path(u.Paths.project_dir())/'Saved/GAAuthoring/Batch5/existing-mass-points.json').write_text(json.dumps(q,indent=2),encoding='utf8')
    def tick(dt):
        try:
            if time.monotonic()-q['started']>25:raise AssertionError('Timeout')
            pcs=[p for p in u.ObjectIterator(u.MyPlayerController) if 'UEDPIE_' in p.get_path_name() and p.get_controlled_pawn() and p.get_local_role()!=u.NetRole.ROLE_NONE]
            if len(pcs)!=3:return
            if q['phase']=='start':
                assert all(p.get_world().get_name().endswith('L_DungeonLabyrinth') for p in pcs)
                for i,p in enumerate(pcs):
                    points=p.get_controlled_pawn().call_method('GetSpellPoints');assert points==999,(i,points)
                    q['checks'][str(i)+'_start_999']=True
                    if p.get_local_role()==u.NetRole.ROLE_AUTHORITY:p.get_controlled_pawn().call_method('AddToSpellPoints',(-7,))
                q.update(phase='spent',at=time.monotonic());return
            if time.monotonic()-q['at']<1:return
            for i,p in enumerate(pcs):
                points=p.get_controlled_pawn().call_method('GetSpellPoints');assert points==992,(i,points)
                q['checks'][str(i)+'_spent_992']=True
            finish()
        except Exception as e:finish(repr(e))
    handle=u.register_slate_post_tick_callback(tick)
_mass_points_qa()
