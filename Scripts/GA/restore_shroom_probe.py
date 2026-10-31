from pathlib import Path
import unreal as u
s=(Path(u.Paths.project_dir())/'Scripts/GA/restore_grux_probe.py').read_text().replace('GruxDesign/restore.json','ShroomDesign/restore.json')
exec(compile(s,'restore_shroom','exec'),globals())
