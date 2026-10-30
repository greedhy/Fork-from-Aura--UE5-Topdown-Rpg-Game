"""Hold the two runtime montage contact poses for visual review in the probe."""
import unreal as u
world=u.EditorLevelLibrary.get_game_world()
assert world and '/Temp/' in world.get_path_name()
R='/Game/BluePrints/Characters/StoneGolem/Animations/'
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
    if not actor.actor_has_tag('SGAnimationProbe'):
        continue
    kind='Slam' if actor.actor_has_tag('Slam') else 'ShieldBash'
    mesh=actor.get_component_by_class(u.SkeletalMeshComponent)
    instance=mesh.get_anim_instance()
    montage=u.load_asset(R+'AM_SG_'+kind)
    instance.montage_stop(0.)
    instance.montage_play(montage,.000001)
    instance.montage_set_position(montage,.7 if kind=='Slam' else 25/30)
