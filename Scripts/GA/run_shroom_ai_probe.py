from pathlib import Path
import unreal as u
s=(Path(u.Paths.project_dir())/'Scripts/GA/run_wave1_ai_probe.py').read_text()
s=s.replace("paths=['/Game/BluePrints/Characters/Demon/Expansion/BP_DemonWarrior','/Game/BluePrints/Characters/Goblin/ShamanExpansion/BP_ShamanExpanded']","paths=['/Game/BluePrints/Characters/Shroom/Expansion/BP_Shroom']")
s=s.replace('MonsterWave1/wave1-ai-runtime.json','ShroomDesign/ai-runtime.json').replace("['foot','ankle']","['pelvis','head']")
exec(compile(s,'shroom_ai_probe','exec'),globals())
