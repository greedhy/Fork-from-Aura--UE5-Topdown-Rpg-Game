"""Exercise actual montage cancellation and lethal-GE interruption for Demon."""
from pathlib import Path
import unreal as u
root=Path(u.Paths.project_dir())
s=(root/'Scripts/GA/StoneGolem/run_runtime_regression.py').read_text()
s=s.replace('Saved/GAAuthoring/StoneGolemBuild/combat-probe.json','Saved/GAAuthoring/MonsterWave1/demon-combat-probe.json')
s=s.replace('Saved/GAAuthoring/StoneGolemBuild/runtime-regression.json','Saved/GAAuthoring/MonsterWave1/demon-interrupt-probe.json')
s=s.replace("fx_modes=[(i,'normal') for i in range(3)]+[(i,'interrupt') for i in range(3)]+[(0,'death')]","fx_modes=[(0,'normal'),(1,'normal'),(0,'interrupt'),(1,'interrupt'),(0,'death')]")
s=s.replace('{0:.4,1:.9,2:.3}','{0:.4,1:.6,2:.3}')
s=s.replace("exec((root/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text().split('sg_path=')[0])", "exec((root/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text().split('sg_path=')[0].replace('sg_source:u.Vector(0,0,89)','sg_source:u.Vector(0,0,50)').replace('sg_target:u.Vector(100,0,89)','sg_target:u.Vector(85,0,89)'))")
s=s.replace('u.Vector(100,0,89)','u.Vector(85,0,89)')
s=s.replace("'/StoneGolem/NS_SG_'", "'/Assets/Effects/Combat/NS_CombatImpact'")
s=s.replace("                fx_case['cooldown_rejected']=not sg_source.try_attack_index(i)", "                # Cooldown retry tested immediately after activation below.")
s=s.replace("assert sg_source.try_attack_index(i),'Activation refused '+str((i,mode))", "assert sg_source.try_attack_index(i),'Activation refused '+str((i,mode))\n            fx_case['cooldown_rejected']=not sg_source.try_attack_index(i)")
s=s.replace('set_global_time_dilation(world,.5)','set_global_time_dilation(world,1.)')
exec(compile(s,'demon_interrupt_probe','exec'),globals())
