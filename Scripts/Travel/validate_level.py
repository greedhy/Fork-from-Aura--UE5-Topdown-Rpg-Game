"""Validate the currently open authored map; keep all UObject refs local."""
def main():
    import json
    from pathlib import Path
    import unreal

    world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    name=world.get_name()
    groups={'Dungeon':'Dungeon1PlayerStart1','Dungeon2':'Dungeon2PlayerStart1','L_DungeonLabyrinth':'LabyrinthEntry'}
    assert name in groups
    group=groups[name]
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    starts=[a for a in actors if isinstance(a,unreal.PlayerStart) and not isinstance(a,unreal.MapEntrance)
        and str(a.get_editor_property('player_start_tag'))==group]
    def slot(a): return a.get_editor_property('player_slot') if isinstance(a,unreal.TravelPlayerStart) else 0
    assert sorted(slot(a) for a in starts)==[0,1,2,3], 'Arrival slots missing/duplicated'
    defaults={str(a.get_editor_property('player_start_tag')) for a in actors if isinstance(a,unreal.TravelPlayerStart) and a.get_editor_property('default_entry_group')}
    assert defaults=={group},'Map default group mismatch'
    portals=[a for a in actors if isinstance(a,unreal.MapEntrance)]
    assert len(portals)==1
    p=portals[0]
    assert p.get_editor_property('replicates') and p.is_actor_tick_enabled()
    assert p.get_editor_property('required_stay_seconds')==3
    sphere=p.get_component_by_class(unreal.SphereComponent)
    center=sphere.get_world_location()
    assert all((a.get_actor_location()-center).length()>sphere.get_scaled_sphere_radius()+100 for a in starts),'Arrival causes immediate portal re-entry'
    target=p.get_editor_property('destination_map')
    tag=str(p.get_editor_property('destination_player_start_tag'))
    assert target and target.get_name() in groups and tag==groups[target.get_name()]
    # Ground beneath the upper staircase must intersect the gathering sphere
    # when an ordinary walking capsule stands on it (no flying fixture).
    stair=unreal.SystemLibrary.line_trace_single(world,center+unreal.Vector(0,0,800),center-unreal.Vector(0,0,1000),
        unreal.TraceTypeQuery.ECC_VISIBILITY,False,[],unreal.DrawDebugTrace.NONE).to_tuple()
    assert stair[0] and stair[7].z>.7,'Portal gathering surface is not walkable'
    assert abs(stair[4].z+90-center.z)<sphere.get_scaled_sphere_radius(),'Walking capsule cannot reach gathering region'
    primary=next(a for a in starts if slot(a)==0)
    route=unreal.NavigationSystemV1.find_path_to_location_synchronously(world,primary.get_actor_location(),
        unreal.Vector(center.x,center.y,stair[4].z+30))
    assert route and route.is_valid() and not route.is_partial(),'No complete navigation path from arrival to portal'
    def vec(v): return [v.x,v.y,v.z]
    result={'map':name,'passed':True,'group':group,
        'starts':[{'label':a.get_actor_label(),'slot':slot(a),'position':vec(a.get_actor_location())} for a in sorted(starts,key=slot)],
        'portal':p.get_actor_label(),'portal_root':vec(p.get_actor_location()),'destination':target.get_name(),
        'destination_group':tag,'sphere_center':vec(center),'sphere_radius':sphere.get_scaled_sphere_radius(),
        'standing_center_z':stair[4].z+90,'surface_normal_z':stair[7].z,'complete_navigation_path':True,
        'navigation_points':len(route.path_points)}
    out=Path(unreal.Paths.project_dir()).resolve()/'Saved/TravelValidation'
    (out/(name+'-validated.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
    unreal.log('TRAVEL_ASSETS_VALIDATED '+json.dumps(result))

main()
