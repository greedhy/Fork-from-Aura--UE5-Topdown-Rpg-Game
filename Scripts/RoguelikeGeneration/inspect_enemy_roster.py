"""Read the saved roster and its effective class-based GAS grants. Never saves assets."""
def main():
    import json
    from pathlib import Path
    import unreal as u
    report={'passed':False,'types':[]}
    root=Path(u.Paths.project_dir()).resolve()
    try:
        profile=u.load_asset('/Game/RoguelikeGeneration/Gameplay/DA_DungeonGameplay')
        mode=u.get_default_object(u.load_class(None,
            '/Game/RoguelikeGeneration/Gameplay/BP_DungeonRunGameMode.BP_DungeonRunGameMode_C'))
        info=mode.get_editor_property('character_class_info')
        defaults=info.get_editor_property('character_class_information')
        common=list(info.get_editor_property('common_abilities'))
        roster=profile.get_editor_property('normal_roster')
        assert len(roster)==3
        for entry in roster:
            # A soft-class property may be returned as the resolved Class or a path wrapper.
            cls=entry.get_editor_property('enemy_class')
            if not isinstance(cls,u.Class):
                cls=u.load_class(None,str(cls))
            cdo=u.get_default_object(cls)
            kind=cdo.get_editor_property('character_class')
            grants=common+list(defaults[kind].get_editor_property('startup_abilities'))
            assert grants and all(g is not None for g in grants)
            report['types'].append({'id':str(entry.get_editor_property('id')),
                'class':cls.get_path_name(),'health':entry.get_editor_property('health'),
                'pool_eligible':entry.get_editor_property('pool_eligible'),
                'effective_abilities':[g.get_path_name() for g in grants]})
        assert {t['id'] for t in report['types']}=={'GoblinSpear','GoblinSlinger','Ghoul'}
        report['passed']=True
    except Exception as error:
        report['error']=str(error)
        raise
    finally:
        (root/'Saved/RoguelikeGeneration/inspect-enemy-roster.json').write_text(
            json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
main()
