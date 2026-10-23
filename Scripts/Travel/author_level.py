def main():
    """Run via MCP in Dungeon, Dungeon2 or L_DungeonLabyrinth; no global asset edits."""
    import json
    from pathlib import Path
    import unreal

    sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    name=w.get_name()
    assert name in ['Dungeon','Dungeon2','L_DungeonLabyrinth']
    group={'Dungeon':'Dungeon1PlayerStart1','Dungeon2':'Dungeon2PlayerStart1','L_DungeonLabyrinth':'LabyrinthEntry'}[name]
    all_actors=sub.get_all_level_actors()
    by_label={a.get_actor_label():a for a in all_actors}
    legacy_tag='PlayerStart' if name=='L_DungeonLabyrinth' else group
    primary=next(a for a in all_actors if isinstance(a,unreal.PlayerStart) and not isinstance(a,unreal.CheckPoint) and str(a.get_editor_property('player_start_tag')) in [legacy_tag,group])
    anchor=primary.get_actor_location()
    primary.set_editor_property('player_start_tag',unreal.Name(group))
    positions=[(anchor.x+180,anchor.y,anchor.z),(anchor.x,anchor.y+180,anchor.z),(anchor.x+180,anchor.y+180,anchor.z)]
    if name=='Dungeon2':
        positions=[(2000,700,110),(350,1100,110),(2050,1550,110)]

    def floor_z(x,y):
        hit=unreal.SystemLibrary.line_trace_single(w,unreal.Vector(x,y,1500),unreal.Vector(x,y,-1000),
            unreal.TraceTypeQuery.ECC_VISIBILITY,False,[],unreal.DrawDebugTrace.NONE)
        assert hit, 'No floor at '+str((x,y))
        data=hit.to_tuple()
        assert data[0] and data[7].z>.7, 'Invalid floor at '+str((x,y))
        return data[4].z

    for slot,location in enumerate(positions,1):
        label='TravelStart_'+group+'_P'+str(slot)
        a=by_label.get(label)
        if not a:
            x,y,_=location
            a=sub.spawn_actor_from_class(unreal.TravelPlayerStart,unreal.Vector(x,y,floor_z(x,y)+110),primary.get_actor_rotation())
            a.set_actor_label(label)
        assert isinstance(a,unreal.TravelPlayerStart)
        a.set_editor_property('player_start_tag',unreal.Name(group))
        a.set_editor_property('player_slot',slot)
        a.set_editor_property('default_entry_group',True)
        a.tags=[unreal.Name('PortalSetup')]
        a.set_folder_path('Travel/Arrival/'+group)

    portal=None
    if name=='Dungeon':
        portal=next(a for a in all_actors if isinstance(a,unreal.MapEntrance))
    elif name in ['Dungeon2','L_DungeonLabyrinth']:
        label='Portal_To_Labyrinth' if name=='Dungeon2' else 'Portal_Return_Dungeon'
        portal=by_label.get(label)
        if not portal:
            location=unreal.Vector(1820,260,92) if name=='Dungeon2' else unreal.Vector(-460,4350,292)
            rotation=unreal.Rotator(pitch=0,yaw=0 if name=='Dungeon2' else 90,roll=0)
            portal=sub.spawn_actor_from_class(unreal.load_class(None,'/Game/BluePrints/CheckPoint/BP_MapEntrance.BP_MapEntrance_C'),location,rotation)
            # APlayerStart's editor factory raises the capsule; place the staircase
            # root explicitly so its bottom rests on the intended floor.
            portal.set_actor_location(location,False,True)
            portal.set_actor_label(label)
        target='L_DungeonLabyrinth' if name=='Dungeon2' else 'Dungeon'
        tag='LabyrinthEntry' if name=='Dungeon2' else 'Dungeon1PlayerStart1'
        portal.set_editor_property('destination_map',unreal.load_asset('/Game/levels/'+target))
        portal.set_editor_property('destination_player_start_tag',unreal.Name(tag))
        portal.tags=[unreal.Name('PortalSetup')]
        portal.set_folder_path('Travel/Portals')

    portal.set_editor_property('required_stay_seconds',3.0)
    portal.set_replicates(True)
    portal.set_actor_tick_enabled(True)
    portal.get_component_by_class(unreal.SphereComponent).set_sphere_radius(260)
    sub.clear_actor_selection_set()
    out=Path(unreal.Paths.project_dir()).resolve()/'Saved/TravelValidation'
    result={'map':name,'group':group,'player_slots':4,'portal':portal.get_actor_label(),'stay_seconds':3,
        'placement':'separate locations' if name=='Dungeon2' else 'nearby individual slots'}
    (out/(name+'-authored.json')).write_text(json.dumps(result,indent=2),encoding='utf8')
    unreal.log('TRAVEL_AUTHORED '+json.dumps(result))

main()
