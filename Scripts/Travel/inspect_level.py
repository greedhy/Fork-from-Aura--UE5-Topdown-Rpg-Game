def main():
    import json
    from pathlib import Path
    import unreal

    w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    def vec(v): return [v.x,v.y,v.z]
    result={'world':w.get_path_name(),'starts':[],'portals':[]}
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if isinstance(a,unreal.PlayerStart):
            result['starts'].append({'label':a.get_actor_label(),'class':a.get_class().get_path_name(),'pos':vec(a.get_actor_location()),'tag':str(a.get_editor_property('player_start_tag'))})
        if isinstance(a,unreal.MapEntrance):
            result['portals'].append({'label':a.get_actor_label(),'replicates':a.get_editor_property('replicates'),
                'tick':a.is_actor_tick_enabled(),
                'destination':str(a.get_editor_property('destination_map')),
                'destination_tag':str(a.get_editor_property('destination_player_start_tag')),
                'components':[{'name':p.get_name(),'relative':vec(p.get_editor_property('relative_location')),'world':vec(p.get_world_location()),
                    'scale':vec(p.get_editor_property('relative_scale3d')),
                    'mesh':p.static_mesh.get_path_name() if isinstance(p,unreal.StaticMeshComponent) and p.static_mesh else None,
                    'mesh_bounds':str(p.static_mesh.get_bounding_box()) if isinstance(p,unreal.StaticMeshComponent) and p.static_mesh else None}
                    for p in a.get_components_by_class(unreal.SceneComponent)]})
    out=Path(unreal.Paths.project_dir()).resolve()/'Saved/TravelValidation'
    out.mkdir(parents=True,exist_ok=True)
    (out/(w.get_name()+'-before.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
    unreal.log('TRAVEL_INSPECTION '+json.dumps(result))

main()
