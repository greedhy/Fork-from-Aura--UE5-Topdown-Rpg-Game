from pathlib import Path
import unreal
source=(Path(unreal.Paths.project_dir())/'Scripts/GA/Batch5/verify_menu.py').read_text(encoding='utf-8-sig')
exec(source.rsplit('_batch5_menu()',1)[0]+"_batch5_menu(True)")
