def main():
    import unreal as u
    import json,uuid
    from pathlib import Path
    root=Path(u.Paths.project_dir()).resolve()/'Saved/Rooms'
    root.mkdir(parents=True,exist_ok=True)
    classes=['RoomSubsystem','RoomLobbyGameMode','RoomLobbyGameState','RoomLobbyController','RoomMenuWidget']
    checks={name:u.load_class(None,'/Script/test_25d.'+name) is not None for name in classes}
    report={'run_id':uuid.uuid4().hex,'checks':checks,'passed':all(checks.values())}
    (root/'runtime_classes.json').write_text(json.dumps(report,indent=2))
    assert report['passed'],report
    u.log('ROOM_RUNTIME_CLASSES_READY')
main()
