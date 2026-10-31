from pathlib import Path
import unreal as u
s=(Path(u.Paths.project_dir())/'Scripts/GA/run_wave1_ai_probe.py').read_text()
s=s.replace("paths=['/Game/BluePrints/Characters/Demon/Expansion/BP_DemonWarrior','/Game/BluePrints/Characters/Goblin/ShamanExpansion/BP_ShamanExpanded']","paths=['/Game/BluePrints/Characters/Grux/Expansion/BP_GruxBoss']")
s=s.replace('MonsterWave1/wave1-ai-runtime.json','GruxDesign/ai-runtime.json')
exec(compile(s,'grux_ai_probe','exec'),globals())
