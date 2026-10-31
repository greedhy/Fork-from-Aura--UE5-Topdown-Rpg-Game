"""Own animation clips and default-slot montages for measured Grux attacks."""
from pathlib import Path
import unreal as u
root=Path(u.Paths.project_dir())
s=(root/'Scripts/GA/author_demon_animations.py').read_text()
s=s.replace("'Saved/GAAuthoring/MonsterWave1'","'Saved/GAAuthoring/GruxDesign'")
s=s.replace('/Game/BluePrints/Characters/Demon/Expansion/Animations','/Game/BluePrints/Characters/Grux/Expansion/Animations').replace('DemonExpansionAnimationsV1','GruxExpansionAnimationsV1')
s=s.replace("[('ClawL','Demon_Attack_L'),('ClawR','Demon_Attack_R'),('Tailspin','Demon_Red_Tailspin')]","[('Left','PrimaryAttack_LA'),('Right','PrimaryAttack_RA'),('Charge','Stampede'),('Uppercut','Stampede_Knockup'),('Roar','Ultimate_Roar')]")
s=s.replace('/Game/Assets/Enemies/Demon/Animations/','/Game/ParagonGrux/Characters/Heroes/Grux/Animations/').replace('Content/Assets/Enemies/Demon/Animations','Content/ParagonGrux/Characters/Heroes/Grux/Animations')
s=s.replace('AS_Demon_','AS_Grux_').replace('AM_Demon_','AM_Grux_').replace('demon-animation-assets.json','grux-animation-assets.json')
exec(compile(s,'grux_owned_animations','exec'),globals())
