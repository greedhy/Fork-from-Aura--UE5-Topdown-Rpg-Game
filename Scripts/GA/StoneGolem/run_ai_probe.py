import unreal as u,json,time
from pathlib import Path
root=Path(u.Paths.project_dir())
exec((root/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text().split('sg_path=')[0])
ai_result={'status':'running','samples':[]};ai_start=u.GameplayStatics.get_time_seconds(world)
m=sg_source.get_component_by_class(u.CharacterMovementComponent)
m.set_movement_mode(u.MovementMode.MOVE_FLYING);m.set_editor_property('braking_deceleration_flying',0.);m.set_editor_property('velocity',u.Vector(150,0,0))
anim=sg_source.get_component_by_class(u.SkeletalMeshComponent).get_anim_instance()
ai_phase=0
sg_source.set_actor_location(u.Vector(0,-400,89),False,True)

def ai_tick(dt):
 global ai_phase
 try:
  t=u.GameplayStatics.get_time_seconds(world)-ai_start
  if ai_phase==0:
   ai_result['samples'].append({'speed':sg_source.get_velocity().length(),'should_move':anim.get_editor_property('ShouldMove'),'ground_speed':anim.get_editor_property('GroundSpeed')})
   if t>1:
    ai_result['movement_passed']=any(s['speed']>20 and s['should_move'] for s in ai_result['samples'])
    m.stop_movement_immediately();m.set_movement_mode(u.MovementMode.MOVE_NONE);sg_source.set_actor_location(u.Vector(0,0,89),False,True)
    sg_target.set_actor_location(u.Vector(100,0,89),False,True)
    sg_source.set_editor_property('combat_target',sg_target)
    ai_result['positions']=[str(sg_source.get_actor_location()),str(sg_target.get_actor_location())]
    task=u.get_default_object(u.load_class(None,'/Game/BluePrints/AI/Task/BTT_Attack.BTT_Attack_C'))
    tag=task.get_editor_property('AttackTag');ai_result['attack_tag']=tag.export_text()
    tags=u.GameplayTagContainer();tags.import_text('(GameplayTags=('+tag.export_text()+'))')
    ai_result['selector_accepted']=sg_source.get_component_by_class(u.MyAbilitySystemComponent).try_activate_abilities_by_tag(tags,False)
    ai_result['warning_after_selector']=sg_source.get_component_by_class(u.ProceduralMeshComponent).get_num_sections()
    ai_phase=1
  elif t>4:
   ai_result['damage']=10000-value(sg_target,'health');ai_result['passed']=ai_result['movement_passed'] and ai_result['selector_accepted'] and ai_result['damage']>0
   ai_result['status']='complete';u.unregister_slate_post_tick_callback(ai_handle)
  (root/'Saved/GAAuthoring/StoneGolemBuild/ai-runtime.json').write_text(json.dumps(ai_result,indent=2))
 except Exception as e:
  ai_result['status']='error';ai_result['error']=str(e);(root/'Saved/GAAuthoring/StoneGolemBuild/ai-runtime.json').write_text(json.dumps(ai_result));u.unregister_slate_post_tick_callback(ai_handle)
ai_handle=u.register_slate_post_tick_callback(ai_tick)
