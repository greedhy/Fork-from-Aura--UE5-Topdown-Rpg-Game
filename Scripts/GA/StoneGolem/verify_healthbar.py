"""Check real health-change delegates and rendered bar percent on new and existing enemies."""
import unreal as u,json,uuid
from pathlib import Path
world=u.EditorLevelLibrary.get_game_world();assert world and world.get_path_name().startswith('/Temp/')
actors=u.GameplayStatics.get_all_actors_of_class(world,u.EnemyCharacter)
source=next(a for a in actors if a.actor_has_tag('Target'))
targets=[a for a in actors if a.actor_has_tag('SGSource') or a.actor_has_tag('SGOldEnemy')]
report={'run_id':uuid.uuid4().hex,'status':'running','cases':[]};out=Path(u.Paths.project_dir())/'Saved/GAAuthoring/StoneGolemMovementFix/healthbar-runtime.json'
def read(a):
 asc=a.get_component_by_class(u.MyAbilitySystemComponent);attrs=asc.get_attribute_set(u.MyAttributeSet)
 bar=a.get_editor_property('health_bar');w=bar.get_user_widget_object();assert w
 pbs=[x for x in u.ObjectIterator(u.ProgressBar) if w.get_path_name()+'.' in x.get_path_name() or w.get_path_name()+':' in x.get_path_name()]
 return {'health':attrs.get_editor_property('health').get_editor_property('current_value'),'max_health':attrs.get_editor_property('max_health').get_editor_property('current_value'),'widget_health':w.get_editor_property('Health'),'widget_max':w.get_editor_property('MaxHealth'),'bound':w.get_editor_property('BoundEnemy')==a,'space':str(bar.get_editor_property('space')),'offset':str(bar.get_editor_property('relative_location')),'bars':{p.get_name():p.get_editor_property('percent') for p in pbs},'widget_visibility':str(w.get_visibility())}
for a in targets:
 before=read(a)
 tag=u.GameplayTag();tag.import_text('(TagName="Damage.Physics")');params=u.DamageEffectParams()
 for k,v in {'source_ability_system_component':source.get_component_by_class(u.MyAbilitySystemComponent),'target_ability_system_component':a.get_component_by_class(u.MyAbilitySystemComponent),'damage_gameplay_effect_class':u.load_class(None,'/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage.GE_Damage_C'),'damage_type':tag,'base_damage':before['max_health']*.2,'ability_level':1.,'debuff_chance':0.}.items():params.set_editor_property(k,v)
 u.MyAbilitySystemLibrary.apply_damage_effect(params)
 report['cases'].append({'actor':a.get_path_name(),'before':before})
started=u.GameplayStatics.get_time_seconds(world)
def health_tick(dt):
 try:
  if u.GameplayStatics.get_time_seconds(world)-started<1.5:return
  for a,c in zip(targets,report['cases']):
   after=read(a);c['after']=after;ratio=after['health']/after['max_health']
   c['passed']=after['bound'] and after['health']<c['before']['health'] and abs(after['health']-after['widget_health'])<.01 and abs(after['max_health']-after['widget_max'])<.01 and bool(after['bars']) and any(abs(v-ratio)<.01 for v in after['bars'].values())
  report['passed']=len(targets)==2 and all(c['passed'] for c in report['cases']);report['status']='complete';out.write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(health_handle)
 except Exception as e:
  report['status']='error';report['error']=str(e);out.write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(health_handle)
health_handle=u.register_slate_post_tick_callback(health_tick)
out.write_text(json.dumps(report,indent=2))

