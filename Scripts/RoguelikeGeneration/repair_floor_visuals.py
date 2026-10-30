"""Apply/verify the approved visual repair on generated maps only; never save Dungeon."""
def main():
    import json, sys, shutil, hashlib, importlib
    from pathlib import Path
    from datetime import datetime
    import unreal as u
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import floor_visual_style as style
    importlib.reload(style)
    root=Path(u.Paths.project_dir()).resolve(); directory=root/'Saved/RoguelikeGeneration'
    request=json.loads((directory/'floor-style-request.json').read_text(encoding='utf-8'))
    apply=request.get('apply',False)
    label=request['label']; assert label.replace('-','').isalnum()
    base='/Game/RoguelikeGeneration/'
    hosts=[base+'Maps/'+n for n in ('L_DungeonGenerationProbe','L_RoguelikeFloor','L_RoguelikeRun')]
    maps=hosts+[base+'Rooms/'+n for n in ('L_ProbeCombat','L_ProbeBoss')]+[
        base+'Rooms/L_Floor_'+n for n in ('CombatA','CombatB','CombatC','CombatD','CombatE','Treasure','Elite','Merchant','Rest','Boss')]
    report={'passed':False,'apply':apply,'maps':[],'reference':style.REFERENCE}
    levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    assert not levels.is_in_play_in_editor(), 'PIEActive'
    assert not style.dirty_packages(), 'UnsavedPackages'
    previous=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world().get_path_name().split('.')[0]
    def disk(path): return root/'Content'/(path.removeprefix('/Game/')+'.umap')
    source_hash=hashlib.sha256(disk(style.REFERENCE).read_bytes()).hexdigest()
    reference=style.capture_reference()
    report['reference_values']={n:{k:style.frozen(v) for k,v in row['values'].items()} for n,row in reference.items()}
    if apply:
        backup=directory/'VisualBackups'/datetime.now().strftime('%Y%m%d-%H%M%S')
        for path in maps:
            dest=backup/(path.removeprefix('/Game/')+'.umap'); dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(disk(path),dest)
        report['backup']=str(backup)
    def check(world,host): return style.floor_errors(world)+style.environment_errors(world,reference,host)
    def process(path):
        assert not style.dirty_packages(), 'DirtyBeforeMapSwitch'
        world=u.EditorLoadingAndSavingUtils.load_map(path); host=path in hosts
        before=check(world,host)
        if apply and before:
            style.replace_floor(world)
            if host: style.apply_environment(world,reference)
            else:
                for actor in list(u.GameplayStatics.get_all_actors_of_class(world,u.PointLight)):
                    assert actor.get_actor_label().startswith(('RG_','RF_')), 'ForeignRoomLight'
                    assert actors.destroy_actor(actor)
            after=check(world,host)
            assert not after, path+': '+str(after)
            assert set(style.dirty_packages())<={path}, 'ForeignDirtyPackages'
            assert levels.save_current_level(), 'SaveFailed'
        else: after=before
        return {'map':path,'before':before,'after':after}
    def reopen(path):
        world=u.EditorLoadingAndSavingUtils.load_map(path)
        return check(world,path in hosts)
    try:
        for path in maps:
            report['maps'].append(process(path))
        if apply:
            for row in report['maps']: row['reopened']=reopen(row['map'])
        report['source_unchanged']=source_hash==hashlib.sha256(disk(style.REFERENCE).read_bytes()).hexdigest()
        report['passed']=report['source_unchanged'] and all(not row['after'] and not row.get('reopened') for row in report['maps'])
    except Exception as error:
        report['error']=str(error)
        raise
    finally:
        (directory/(label+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if not style.dirty_packages(): u.EditorLoadingAndSavingUtils.load_map(previous)
if __name__=='__main__': main()
