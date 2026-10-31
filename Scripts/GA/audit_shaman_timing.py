import unreal as u,json
from pathlib import Path
rows=[]
for name in ['AM_Attack_Shaman','AM_Shaman_Summon']:
 a=u.load_asset('/Game/Assets/Enemies/Shaman/Animations/'+name)
 rows.append({'name':name,'events':[x.export_text() for x in u.AnimationLibrary.get_animation_notify_events(a)]})
(Path(u.Paths.project_dir())/'Saved/GAAuthoring/MonsterWave1/shaman-timing.json').write_text(json.dumps(rows,indent=2))
