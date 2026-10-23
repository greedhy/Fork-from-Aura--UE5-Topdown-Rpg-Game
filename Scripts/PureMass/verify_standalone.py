import unreal as u,json,time
from pathlib import Path
_st={'started':time.monotonic(),'checks':{}}
def _st_tick(dt):
    try:
        worlds=[m for m in u.ObjectIterator(u.PureMassSubsystem) if m.get_world() and 'UEDPIE_' in m.get_world().get_path_name()]
        if time.monotonic()-_st['started']>20:raise AssertionError('Standalone startup timeout')
        if len(worlds)!=1:return
        sim=worlds[0];world=sim.get_world();views=list(sim.get_snapshots())
        crowds=u.GameplayStatics.get_all_actors_of_class(world,u.PureMassCrowd)
        if len(crowds)!=1 or len(views)!=8 or crowds[0].get_rendered_instance_count()!=8:return
        _st['checks']={
            'single_pie_world':True,
            'eight_mass_entities':len(views)==8,
            'zero_enemy_actors':not u.GameplayStatics.get_all_actors_of_class(world,u.EnemyCharacter),
            'one_shared_renderer':len(crowds)==1,
            'eight_skinned_instances':crowds[0].get_rendered_instance_count()==8,
            'one_component_for_type':crowds[0].get_render_component_count()==1,
            'pure_mass_pawn':len(u.GameplayStatics.get_all_actors_of_class(world,u.PureMassPlayerCharacter))==1,
            'processor_running':any(v.state in [1,2] for v in views)}
        if not _st['checks']['processor_running']:return
        _st['passed']=all(_st['checks'].values())
    except Exception as exc:_st.update(passed=False,error=repr(exc))
    u.unregister_slate_post_tick_callback(_st_handle)
    Path(u.Paths.project_dir(),'Saved/PureMass/standalone.json').write_text(json.dumps(_st,indent=2),encoding='utf8')
_st_handle=u.register_slate_post_tick_callback(_st_tick)
