"""Configure only DA_DungeonGameplay; validate shared GAS BPs without editing them."""
def main():
    import json
    from pathlib import Path
    import unreal as u
    root=Path(u.Paths.project_dir()).resolve()
    report={'passed':False,'types':[]}
    output=root/'Saved/RoguelikeGeneration/author-enemy-roster.json'
    profile_path='/Game/RoguelikeGeneration/Gameplay/DA_DungeonGameplay'
    sources=(
        ('GoblinSpear','/Game/BluePrints/Characters/Goblin/BP_GoblinSpear'),
        ('GoblinSlinger','/Game/BluePrints/Characters/Goblin/BP_Goblin_Slinshot'),
        ('Ghoul','/Game/BluePrints/Characters/Ghoul/BP_Ghoul'))
    def dirty():
        return [p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+
                list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())]
    try:
        assert not u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(), 'PIEActive'
        assert not dirty(), 'UnsavedPackages: '+str(dirty())
        profile=u.load_asset(profile_path)
        assert isinstance(profile,u.DungeonRunProfile)
        report['before']=[v.export_text() for v in profile.get_editor_property('normal_roster')]
        entries=[]
        for identity,path in sources:
            bp=u.load_asset(path)
            cls=u.load_class(None,path+'.'+path.rsplit('/',1)[-1]+'_C')
            assert cls is not None, path
            cdo=u.get_default_object(cls)
            assert isinstance(cdo,u.EnemyCharacter), path
            mesh=cdo.get_editor_property('mesh')
            assert mesh.get_editor_property('skeletal_mesh_asset') is not None, path
            assert mesh.get_editor_property('anim_class') is not None, path
            assert cdo.get_editor_property('behavior_tree') is not None, path
            assert cdo.get_editor_property('ai_controller_class') is not None, path
            assert cdo.get_editor_property('auto_possess_ai') in (
                u.AutoPossessAI.SPAWNED,u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED), 'Runtime AI possession disabled: '+path
            assert len(cdo.get_editor_property('attack_montage'))>0, path
            entry=u.DungeonNormalEnemy()
            entry.set_editor_property('id',identity)
            entry.set_editor_property('enemy_class',cls)
            entry.set_editor_property('health',100.0)
            entry.set_editor_property('pool_eligible',True)
            entries.append(entry)
            report['types'].append({'id':identity,'class':cls.get_path_name(),
                'character_class':str(cdo.get_editor_property('character_class')),
                'behavior_tree':cdo.get_editor_property('behavior_tree').get_path_name(),
                'animation':mesh.get_editor_property('anim_class').get_path_name(),
                'startup_abilities':[a.get_path_name() for a in cdo.get_editor_property('startup_ability')],
                'status':str(bp.get_editor_property('status'))})
        assert not dirty(), 'DependencyLoadDirtiedPackages'
        profile.set_editor_property('normal_roster',entries)
        assert set(dirty())<= {profile_path}, 'ForeignDirtyPackages'
        assert u.EditorAssetLibrary.save_loaded_asset(profile,False), 'SaveFailed'
        actual=profile.get_editor_property('normal_roster')
        assert [str(v.get_editor_property('id')) for v in actual]==[s[0] for s in sources]
        report['after']=[v.export_text() for v in actual]
        report['dirty_after']=dirty()
        assert not report['dirty_after']
        report['passed']=True
    except Exception as error:
        report['error']=str(error)
        raise
    finally:
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
main()
