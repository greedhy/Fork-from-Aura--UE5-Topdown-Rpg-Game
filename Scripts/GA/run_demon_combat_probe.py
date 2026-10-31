"""Reuse the fixed GAS target harness for the two authored Demon abilities."""
from pathlib import Path
import unreal as u
script=(Path(u.Paths.project_dir())/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text(encoding='utf8')
assert 'sg_index<3' in script and 'sg_index==3' in script
script=script.replace('sg_index<3','sg_index<2').replace('sg_index==3','sg_index==2').replace("len(sg_probe['cases'])==3","len(sg_probe['cases'])==2")
script=script.replace('Saved/GAAuthoring/StoneGolemBuild/combat-probe.json','Saved/GAAuthoring/MonsterWave1/demon-combat-probe.json')
script=script.replace('sg_source:u.Vector(0,0,89)','sg_source:u.Vector(0,0,50)').replace('sg_target:u.Vector(100,0,89)','sg_target:u.Vector(85,0,89)')
exec(compile(script,'demon_combat_probe','exec'),globals())
