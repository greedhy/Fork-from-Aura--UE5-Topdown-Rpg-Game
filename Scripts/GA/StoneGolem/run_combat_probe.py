"""Run each real GA against fixed GAS targets; record warning, timing and damage."""
import unreal as u,json,time,uuid
from pathlib import Path
world=u.EditorLevelLibrary.get_game_world()
assert world and world.get_path_name().startswith('/Temp/')
assert not (globals().get('sg_probe_handle') and globals().get('sg_probe',{}).get('status')=='running')
sg_probe_handle=None
actors=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.EnemyCharacter) if a.actor_has_tag('SGCombatProbe')]
sg_source=next(a for a in actors if a.actor_has_tag('SGSource'))
sg_target=next(a for a in actors if a.actor_has_tag('Target'))
sg_friend=next(a for a in actors if a.actor_has_tag('Friend'))
sg_outside=next(a for a in actors if a.actor_has_tag('Outside'))
def attributes(a):return a.get_component_by_class(u.MyAbilitySystemComponent).get_attribute_set(u.MyAttributeSet)
def value(a,name):return attributes(a).get_editor_property(name).get_editor_property('current_value')
def assign(a,name,v):
    attrs=attributes(a);field=attrs.get_editor_property(name)
    field.import_text('(BaseValue='+str(v)+',CurrentValue='+str(v)+')');attrs.set_editor_property(name,field)
for a in actors:
    movement=a.get_component_by_class(u.CharacterMovementComponent)
    movement.stop_movement_immediately();movement.set_movement_mode(u.MovementMode.MOVE_NONE)
    movement.set_editor_property('gravity_scale',0.)
    pos={sg_source:u.Vector(0,0,89),sg_target:u.Vector(100,0,89),sg_friend:u.Vector(100,100,89),sg_outside:u.Vector(700,0,89)}[a]
    a.set_actor_location(pos,False,True)
    for name,v in [('max_health',10000.),('health',10000.),('armor',0.),('block_chance',0.),('critical_hit_chance',0.)]:assign(a,name,v)
sg_source.set_editor_property('combat_target',sg_target)
sg_path=Path(u.Paths.project_dir())/'Saved/GAAuthoring/StoneGolemBuild/combat-probe.json'
sg_probe={'run_id':uuid.uuid4().hex,'status':'running','passed':False,'cases':[]}
sg_path.write_text(json.dumps(sg_probe))
sg_original_dilation=u.GameplayStatics.get_global_time_dilation(world)
sg_case=None;sg_index=0;sg_wall=time.monotonic();sg_next=0.
def sg_healths():return [value(a,'health') for a in [sg_target,sg_friend,sg_outside]]
def sg_record(delta):
    global sg_case,sg_index,sg_next
    try:
        now=u.GameplayStatics.get_time_seconds(world)
        if sg_case is None and now>=sg_next and sg_index<3:
            before=sg_healths();accepted=sg_source.try_attack_index(sg_index)
            sg_case={'index':sg_index,'accepted':accepted,'started':now,'before':before,'samples':[],
                     'repeat_rejected':not sg_source.try_attack_index(sg_index)}
            assert accepted, 'GA activation rejected: '+str(sg_index)
        if sg_case is not None:
            elapsed=now-sg_case['started'];hp=sg_healths()
            components=sg_source.get_components_by_class(u.ProceduralMeshComponent)
            section_count=components[0].get_num_sections() if components else 0
            text=sg_source.get_component_by_class(u.TextRenderComponent)
            sg_case['samples'].append({'time':elapsed,'health':hp,'warning_sections':section_count,'exclamation':text.is_visible()})
            if elapsed>=3:
                sg_case['after']=hp
                changes=[s for s in sg_case['samples'] if s['health'][0]<sg_case['before'][0]-.01]
                sg_case['first_damage_time']=changes[0]['time'] if changes else None
                sg_case['distinct_health_values']=len(set(round(s['health'][0],3) for s in sg_case['samples']))
                sg_case['passed']=bool(changes) and hp[1:]==sg_case['before'][1:] and sg_case['distinct_health_values']==2 and sg_case['repeat_rejected'] and section_count==0 and not text.is_visible()
                sg_probe['cases'].append(sg_case);sg_case=None;sg_index+=1;sg_next=now+.3
        if sg_index==3 or time.monotonic()-sg_wall>180:
            sg_probe['status']='complete';sg_probe['passed']=len(sg_probe['cases'])==3 and all(c['passed'] for c in sg_probe['cases'])
            sg_path.write_text(json.dumps(sg_probe,indent=2));u.GameplayStatics.set_global_time_dilation(world,sg_original_dilation);u.unregister_slate_post_tick_callback(sg_probe_handle)
    except Exception as error:
        sg_probe['status']='error';sg_probe['error']=str(error)
        sg_path.write_text(json.dumps(sg_probe,indent=2));u.GameplayStatics.set_global_time_dilation(world,sg_original_dilation);u.unregister_slate_post_tick_callback(sg_probe_handle)
sg_probe_handle=u.register_slate_post_tick_callback(sg_record)
u.GameplayStatics.set_global_time_dilation(world,.25)
