import unreal as u,json
from pathlib import Path
def main():
    pc=next(p for p in u.ObjectIterator(u.MyPlayerController) if 'UEDPIE_' in p.get_path_name() and p.is_local_controller() and p.get_local_role()==u.NetRole.ROLE_AUTONOMOUS_PROXY)
    report={'channels':[n for n in dir(u.CollisionChannel) if not n.startswith('_')]}
    try:
        hit=pc.call_method('GetHitResultUnderCursor',(u.CollisionChannel.ECC_TARGET,False))
        report['hit']=hit.export_text() if hit else None
    except Exception as e:report['error']=repr(e)
    (Path(u.Paths.project_dir())/'Saved/GAAuthoring/Batch4/aim-inspection.json').write_text(json.dumps(report,indent=2))
main()

