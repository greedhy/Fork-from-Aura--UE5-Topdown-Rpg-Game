"""PIE regression: actual Niagara spawn/cleanup, montage interruption and lethal GE."""
import unreal as u,json,time,uuid
from pathlib import Path
root=Path(u.Paths.project_dir())
prior=json.loads((root/'Saved/GAAuthoring/StoneGolemBuild/combat-probe.json').read_text())
assert prior['status']=='complete' and prior['passed']
exec((root/'Scripts/GA/StoneGolem/run_combat_probe.py').read_text().split('sg_path=')[0])
world=u.EditorLevelLibrary.get_game_world()
fx_report={'run_id':uuid.uuid4().hex,'status':'running','passed':False,'cases':[]}
fx_path=root/'Saved/GAAuthoring/StoneGolemBuild/runtime-regression.json'
fx_path.write_text(json.dumps(fx_report))
fx_modes=[(i,'normal') for i in range(3)]+[(i,'interrupt') for i in range(3)]+[(0,'death')]
fx_index=0;fx_case=None;fx_next=u.GameplayStatics.get_time_seconds(world)+10;fx_wall=time.monotonic()
fx_original=u.GameplayStatics.get_global_time_dilation(world)

def fx_components():
    out=[]
    for c in u.ObjectIterator(u.NiagaraComponent):
        try:
            a=c.get_asset()
            if a and '/StoneGolem/NS_SG_' in a.get_path_name() and c.get_world()==world and c.is_active():out.append(c)
        except Exception:pass
    return out

def fx_tick(delta):
    global fx_case,fx_index,fx_next
    try:
        now=u.GameplayStatics.get_time_seconds(world)
        if fx_case is None and now>=fx_next:
            i,mode=fx_modes[fx_index]
            sg_target.set_actor_location(u.Vector(100,0,89),False,True)
            sg_target.get_component_by_class(u.CharacterMovementComponent).stop_movement_immediately()
            fx_case={'index':i,'mode':mode,'start':now,'before':value(sg_target,'health'),'samples':[],'acted':False}
            assert sg_source.try_attack_index(i),'Activation refused '+str((i,mode))
        if fx_case:
            elapsed=now-fx_case['start'];i=fx_case['index'];mode=fx_case['mode']
            if mode!='normal' and not fx_case['acted'] and elapsed>({0:.4,1:.9,2:.3}[i]):
                fx_case['acted']=True
                if mode=='interrupt':sg_source.get_component_by_class(u.SkeletalMeshComponent).get_anim_instance().montage_stop(0.)
                else:
                    params=u.DamageEffectParams();tag=u.GameplayTag();tag.import_text('(TagName="Damage.Physics")')
                    for k,v in {'source_ability_system_component':sg_target.get_component_by_class(u.MyAbilitySystemComponent),'target_ability_system_component':sg_source.get_component_by_class(u.MyAbilitySystemComponent),'damage_gameplay_effect_class':u.load_class(None,'/Game/BluePrints/AbilitySystem/Player/Effect/GE_Damage.GE_Damage_C'),'damage_type':tag,'base_damage':1000000.,'ability_level':1.,'debuff_chance':0.}.items():params.set_editor_property(k,v)
                    assert params.get_editor_property('damage_gameplay_effect_class'), 'Missing death damage GE'
                    u.MyAbilitySystemLibrary.apply_damage_effect(params)
                    fx_case['source_health_after_lethal']=value(sg_source,'health')
                    assert fx_case['source_health_after_lethal']<=0, 'Lethal fixture did not kill source'
            comps=fx_components();foot=sg_source.get_component_by_class(u.ProceduralMeshComponent)
            sample={'t':elapsed,'health':value(sg_target,'health'),'fx':len(comps),'warning':foot.get_num_sections(),'text':sg_source.get_component_by_class(u.TextRenderComponent).is_visible()}
            if comps:
                p=comps[0].get_world_location();sample['fx_location']=[p.x,p.y,p.z];sample['asset']=comps[0].get_asset().get_path_name()
            fx_case['samples'].append(sample)
            if elapsed>=3:
                samples=fx_case['samples'];spawns=[s for s in samples if s['fx']]
                fx_case['cooldown_rejected']=not sg_source.try_attack_index(i)
                cleaned=not sample['fx'] and not sample['warning'] and not sample['text']
                if mode=='normal':
                    fx_case['passed']=bool(spawns) and sample['health']<fx_case['before'] and cleaned and fx_case['cooldown_rejected']
                    fx_case['first_fx']=spawns[0] if spawns else None
                else:fx_case['passed']=sample['health']==fx_case['before'] and not spawns and cleaned
                fx_report['cases'].append(fx_case);fx_index+=1;fx_case=None;fx_next=now+7
                fx_path.write_text(json.dumps(fx_report,indent=2))
        if fx_index==len(fx_modes) or time.monotonic()-fx_wall>400:
            fx_report['status']='complete';fx_report['passed']=fx_index==len(fx_modes) and all(c['passed'] for c in fx_report['cases'])
            fx_path.write_text(json.dumps(fx_report,indent=2));u.GameplayStatics.set_global_time_dilation(world,fx_original);u.unregister_slate_post_tick_callback(fx_handle)
    except Exception as e:
        fx_report['status']='error';fx_report['error']=str(e);fx_path.write_text(json.dumps(fx_report,indent=2));u.GameplayStatics.set_global_time_dilation(world,fx_original);u.unregister_slate_post_tick_callback(fx_handle)
fx_handle=u.register_slate_post_tick_callback(fx_tick)
u.GameplayStatics.set_global_time_dilation(world,.5)
