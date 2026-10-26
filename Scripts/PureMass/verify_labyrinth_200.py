"""PIE-only smoke/load sample. Never saves runtime actors or player attribute changes."""
import unreal as u, json, time, statistics, math
from pathlib import Path

_lab = {'started':time.monotonic(), 'phase':'startup', 'checks':{}, 'frames_ms':[], 'samples':[]}
_lab_out = Path(u.Paths.project_dir(), 'Saved/PureMass/Labyrinth200')
_lab_perf = u.get_default_object(u.load_class(None, '/Script/UnrealEd.EditorPerformanceSettings'))
_lab_throttle = _lab_perf.get_editor_property('bThrottleCPUWhenNotForeground')
_lab_perf.set_editor_property('bThrottleCPUWhenNotForeground', False)

def _lab_check(name, condition):
    _lab['checks'][name] = bool(condition)
    assert condition, name

def _lab_finish(error=None):
    u.unregister_slate_post_tick_callback(_lab_handle)
    _lab_perf.set_editor_property('bThrottleCPUWhenNotForeground', _lab_throttle)
    _lab['passed'] = error is None and all(_lab['checks'].values())
    _lab['error'] = error
    frames = sorted(_lab.pop('frames_ms'))
    if frames:
        _lab['editor_frame_sample'] = {'frames':len(frames),'mean_ms':statistics.mean(frames),
            'median_ms':statistics.median(frames),'p95_ms':frames[min(len(frames)-1,math.ceil(len(frames)*.95)-1)],
            'mean_fps':1000/statistics.mean(frames),
            'note':'Slate callback wall intervals, PIE editor with background throttling temporarily disabled; not GPU or Mass processor timings.'}
    _lab['elapsed_seconds'] = time.monotonic()-_lab['started']
    (_lab_out/('pie-'+str(_lab.get('world_count',0))+'.json')).write_text(json.dumps(_lab,indent=2),encoding='utf8')
    u.log('LABYRINTH_200_RESULT '+str(_lab['passed'])+' '+str(error))

def _lab_tick(dt):
    try:
        now = time.monotonic()
        if now-_lab['started']>75: raise AssertionError('Timeout '+_lab['phase'])
        sims = [s for s in u.ObjectIterator(u.PureMassSubsystem) if s.get_world() and 'UEDPIE_' in s.get_world().get_path_name()]
        if not sims:return
        authority = next((s for s in sims if u.GameplayStatics.get_game_mode(s.get_world())),None)
        if not authority:return
        crowds = [u.GameplayStatics.get_all_actors_of_class(s.get_world(),u.PureMassCrowd) for s in sims]
        if not all(len(c)==1 for c in crowds):return
        if _lab['phase']=='startup':
            if not all(len(s.get_snapshots())==200 and c[0].get_rendered_instance_count()==200 for s,c in zip(sims,crowds)):return
            _lab['world_count']=len(sims)
            _lab_check('200_entities_each_world',all(len(s.get_snapshots())==200 for s in sims))
            _lab_check('zero_enemy_actors',all(not u.GameplayStatics.get_all_actors_of_class(s.get_world(),u.EnemyCharacter) for s in sims))
            _lab_check('one_shared_crowd_each_world',all(len(c)==1 for c in crowds))
            _lab_check('200_animation_tracks_each_world',all(c[0].get_animation_track_count()==200 for c in crowds))
            _lab_check('one_render_component_each_world',all(c[0].get_render_component_count()==1 for c in crowds))
            _lab['initial']={str(v.id):[v.location.x,v.location.y,v.location.z] for v in authority.get_snapshots()}
            for pc in u.GameplayStatics.get_all_actors_of_class(authority.get_world(),u.PureMassPlayerController):
                asc=pc.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent)
                attrs=asc.get_attribute_set(u.MyAttributeSet)
                for key in ['max_health','health']:
                    field=attrs.get_editor_property(key);field.import_text('(BaseValue=1000000,CurrentValue=1000000)');attrs.set_editor_property(key,field)
                pawn=pc.get_controlled_pawn()
                pawn.set_actor_location(u.Vector(0,-2800,100),False,True)
            _lab.update(phase='warmup',at=now,last=now,next_sample=now)
            return
        age=now-_lab['at']
        if _lab['phase']=='warmup':
            if age<3:return
            _lab.update(phase='sample',at=now,last=now,next_sample=now)
            return
        if _lab['phase']=='sample':
            _lab['frames_ms'].append((now-_lab['last'])*1000);_lab['last']=now
            if now>=_lab['next_sample']:
                views=list(authority.get_snapshots())
                _lab['samples'].append({'seconds':age,'entities':len(views),'instances':[c[0].get_rendered_instance_count() for c in crowds],
                    'moving':sum(v.velocity.length()>1 for v in views),'attacking':sum(v.state==2 for v in views),
                    'min_z':min(v.location.z for v in views)})
                _lab['next_sample']=now+.5
            if age<12:return
            views=list(authority.get_snapshots())
            moved=sum((v.location-u.Vector(*_lab['initial'][str(v.id)])).length()>30 for v in views)
            _lab['moved_entities']=moved
            _lab_check('entities_move_on_navigation',moved>0)
            _lab_check('200_survive_entire_sample',all(s['entities']==200 and all(n==200 for n in s['instances']) for s in _lab['samples']))
            _lab_check('no_entities_fall_below_floor',all(s['min_z']>0 for s in _lab['samples']))
            victim=views[0];_lab['victim']=victim.id
            damage=u.PureMassDamage();damage.set_editor_property('amount',1000000)
            _lab_check('entity_damage_applied',authority.apply_damage(victim.id,damage)>0)
            _lab.update(phase='death',at=now)
            return
        if _lab['phase']=='death':
            if age<2:return
            _lab_check('death_removes_entity_each_world',all(len(s.get_snapshots())==199 and all(v.id!=_lab['victim'] for v in s.get_snapshots()) for s in sims))
            _lab_check('death_removes_render_track_each_world',all(c[0].get_rendered_instance_count()==199 and c[0].get_animation_track_count()==199 for c in crowds))
            _lab_finish()
    except Exception as exc:
        _lab_finish(repr(exc))

_lab_handle=u.register_slate_post_tick_callback(_lab_tick)

