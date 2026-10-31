"""Real cast/burst effects and cancellation, including summon before its spawn window."""
from pathlib import Path
import unreal as u
root=Path(u.Paths.project_dir())
s=(root/'Scripts/GA/StoneGolem/run_runtime_regression.py').read_text()
s=s.replace('Saved/GAAuthoring/StoneGolemBuild/combat-probe.json','Saved/GAAuthoring/MonsterWave1/shaman-damage-runtime.json').replace('Saved/GAAuthoring/StoneGolemBuild/runtime-regression.json','Saved/GAAuthoring/MonsterWave1/shaman-interrupt-runtime.json')
s=s.replace("fx_modes=[(i,'normal') for i in range(3)]+[(i,'interrupt') for i in range(3)]+[(0,'death')]","fx_modes=[(0,'normal'),(1,'normal'),(0,'interrupt'),(1,'interrupt'),(2,'interrupt'),(0,'death')]")
s=s.replace('{0:.4,1:.9,2:.3}','{0:.4,1:.65,2:.65}')
s=s.replace("exec((root/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text().split('sg_path=')[0])", "exec((root/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text().split('sg_path=')[0].replace('sg_source:u.Vector(0,0,89)','sg_source:u.Vector(0,0,sg_source.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height())').replace('sg_target:u.Vector(100,0,89)','sg_target:u.Vector(350,0,89)'))")
s=s.replace('u.Vector(100,0,89)','u.Vector(350,0,89)')
s=s.replace("'/StoneGolem/NS_SG_' in a.get_path_name()", "any(x in a.get_path_name() for x in ['/Assets/Effects/Combat/NS_CombatImpact','/ShamanExpansion/Effects/','/Free_Spells/VFX_Niagara/NS_Free_Spells_Explosion','/Assets/Effects/Combat/NS_GroundSummon'])")
s=s.replace("                fx_case['cooldown_rejected']=not sg_source.try_attack_index(i)", "                # Retry recorded immediately after activation.")
s=s.replace("assert sg_source.try_attack_index(i),'Activation refused '+str((i,mode))", "assert sg_source.try_attack_index(i),'Activation refused '+str((i,mode))\n            fx_case['cooldown_rejected']=not sg_source.try_attack_index(i)")
s=s.replace("else:fx_case['passed']=sample['health']==fx_case['before'] and not spawns and cleaned","else:fx_case['passed']=sample['health']==fx_case['before'] and not spawns and cleaned and sg_source.get_owned_minion_count()==0")
s=s.replace('set_global_time_dilation(world,.5)','set_global_time_dilation(world,1.)')
exec(compile(s,'shaman_interrupt_probe','exec'),globals())
