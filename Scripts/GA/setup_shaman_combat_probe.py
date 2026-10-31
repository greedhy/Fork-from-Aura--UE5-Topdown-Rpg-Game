"""Reuse isolated fixture geometry, with the authored Shaman and ranged targets."""
import unreal as u
from pathlib import Path
s=(Path(u.Paths.project_dir())/'Scripts/GA/setup_demon_combat_probe.py').read_text()
s=s.replace('/Game/BluePrints/Characters/Demon/Expansion/BP_DemonWarrior','/Game/BluePrints/Characters/Goblin/ShamanExpansion/BP_ShamanExpanded')
exec(compile(s,'setup_shaman_combat','exec'),globals())
half=source.get_component_by_class(u.CapsuleComponent).get_scaled_capsule_half_height()
source.set_actor_location(u.Vector(0,0,half),False,True)
nav=ss.spawn_actor_from_class(u.NavMeshBoundsVolume,u.Vector(0,0,100))
nav.set_actor_location(u.Vector(0,0,100),False,True);nav.set_actor_scale3d(u.Vector(12,12,3))
nav.set_editor_property('tags',['DemonAnimationProbe'])
recast=ss.spawn_actor_from_class(u.RecastNavMesh,u.Vector())
recast.set_editor_property('runtime_generation',u.RuntimeGenerationType.DYNAMIC)
recast.set_editor_property('tags',['DemonAnimationProbe'])
