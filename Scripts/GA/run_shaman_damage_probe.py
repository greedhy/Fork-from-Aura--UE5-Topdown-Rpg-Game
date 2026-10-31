import unreal as u
from pathlib import Path
s=(Path(u.Paths.project_dir())/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text()
s=s.replace('sg_index<3','sg_index<2').replace('sg_index==3','sg_index==2').replace("len(sg_probe['cases'])==3","len(sg_probe['cases'])==2")
s=s.replace('sg_source:u.Vector(0,0,89)','sg_source:u.Vector(0,0,sg_source.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height())')
s=s.replace('sg_target:u.Vector(100,0,89)','sg_target:u.Vector(350,0,89)').replace('sg_friend:u.Vector(100,100,89)','sg_friend:u.Vector(350,70,89)')
s=s.replace('Saved/GAAuthoring/StoneGolemBuild/combat-probe.json','Saved/GAAuthoring/MonsterWave1/shaman-damage-runtime.json')
s=s.replace('set_global_time_dilation(world,.25)','set_global_time_dilation(world,1.)')
exec(compile(s,'shaman_damage_probe','exec'),globals())
