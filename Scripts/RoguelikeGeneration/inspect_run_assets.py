"""Read saved run input, animation, enemy GAS and shared dependencies without edits."""
def main():
    import json
    import hashlib
    from pathlib import Path
    import unreal as u

    root = Path(u.Paths.project_dir()).resolve()
    directory = root / 'Saved/RoguelikeGeneration'
    author = json.loads((directory / 'authoring-run.json').read_text(encoding='utf-8-sig'))
    report = {'passed': False, 'errors': [], 'actors': {}, 'abilities': {}, 'inputs': []}
    assets = author['assets']

    def cdo(path):
        return u.get_default_object(u.load_class(None, path + '.' + path.rsplit('/', 1)[-1] + '_C'))

    def serial(value):
        if value is None:
            return None
        if hasattr(value, 'get_path_name'):
            return value.get_path_name()
        if hasattr(value, 'export_text'):
            return value.export_text()
        return str(value)

    try:
        assert not u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
        pc = cdo(assets['controller'])
        context = pc.get_editor_property('player_context')
        mappings = context.get_editor_property('default_key_mappings').get_editor_property('mappings')
        for mapping in mappings:
            report['inputs'].append({'key': serial(mapping.get_editor_property('key')),
                                     'action': serial(mapping.get_editor_property('action'))})
        report['input_context'] = context.get_path_name()
        report['f_conflicts'] = [r for r in report['inputs'] if r['key'] in ('F', '(KeyName="F")', '(KeyName=F)')]
        assert not report['f_conflicts'], 'ExistingFMappingConflictsWithRoomInteraction'
        mode = cdo(assets['mode'])
        info = mode.get_editor_property('character_class_info')
        defaults = info.get_editor_property('character_class_information')
        ability_classes = set(info.get_editor_property('common_abilities'))
        for kind in ('player', 'elite', 'boss'):
            actor = cdo(assets[kind])
            entry = {'class': actor.get_class().get_path_name(),
                     'character_class': str(actor.get_editor_property('character_class')),
                     'startup': [serial(c) for c in actor.get_editor_property('startup_ability')],
                     'passives': [serial(c) for c in actor.get_editor_property('startup_passive_ability')],
                     'anim_class': serial(actor.mesh.get_editor_property('anim_class'))}
            if kind != 'player':
                entry['behavior_tree'] = serial(actor.get_editor_property('behavior_tree'))
                entry['auto_possess_ai'] = str(actor.get_editor_property('auto_possess_ai'))
                row = defaults[actor.get_editor_property('character_class')]
                entry['class_abilities'] = [serial(c) for c in row.get_editor_property('startup_abilities')]
                ability_classes.update(row.get_editor_property('startup_abilities'))
            ability_classes.update(actor.get_editor_property('startup_ability'))
            ability_classes.update(actor.get_editor_property('startup_passive_ability'))
            report['actors'][kind] = entry
        shared_hashes = {}
        for cls in ability_classes:
            ability = u.get_default_object(cls)
            entry = {'class': cls.get_path_name()}
            for prop in ('ability_tags', 'net_execution_policy', 'damage_effect_class', 'damage_type', 'damage', 'cost_gameplay_effect_class', 'cooldown_gameplay_effect_class'):
                try:
                    entry[prop] = serial(ability.get_editor_property(prop))
                except Exception:
                    pass
            report['abilities'][cls.get_path_name()] = entry
            package = cls.get_path_name().split('.')[0]
            if package.startswith('/Game/'):
                file = root / ('Content/' + package[6:] + '.uasset')
                shared_hashes[str(file.relative_to(root))] = hashlib.sha256(file.read_bytes()).hexdigest()
        report['shared_ga_hashes'] = shared_hashes
        report['dirty_packages'] = [p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages()) + list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())]
        assert not report['dirty_packages'], 'DirtyPackagesAfterReadback'
        report['passed'] = True
    except Exception as error:
        report['errors'].append(str(error))
    (directory / 'run-asset-inspection.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


main()
