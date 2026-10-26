def _inspect_actor_movement():
    import unreal as u,json
    from pathlib import Path
    rows=[]
    for e in u.ObjectIterator(u.EnemyCharacter):
        if 'UEDPIE_' not in e.get_path_name():continue
        m=e.get_component_by_class(u.CharacterMovementComponent)
        rows.append({'actor':e.get_path_name(),'role':str(e.get_local_role()),'mode':str(m.get_editor_property('movement_mode')),'active':m.is_active(),'tick':m.is_component_tick_enabled(),'no_controller_physics':m.get_editor_property('run_physics_with_no_controller'),'controller':str(e.get_controller()),'location':str(e.get_actor_location())})
    (Path(u.Paths.project_dir())/'Saved/GAAuthoring/Batch5/actor-movement.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
_inspect_actor_movement()

