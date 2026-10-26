def _batch5_validate():
    import unreal as u,json,hashlib
    from pathlib import Path
    root=Path(u.Paths.project_dir()).resolve();out=root/'Saved/GAAuthoring/Batch5'
    a=json.loads((out/'assets.json').read_text(encoding='utf-8'));r={'passed':False,'checks':{}}
    def check(n,v):r['checks'][n]=bool(v);assert v,n
    try:
     for name,path in a['classes'].items():
      cls=u.load_class(None,path);cdo=u.get_default_object(cls);n=cdo.get_editor_property('prototype')
      check(name+'_extension_class',isinstance(cdo,u.ExtensionAbility))
      check(name+'_valid_graph',isinstance(n,u.ExtensionNode) and n.validate_graph())
      check(name+'_unique_identity','Abilities.Extension.'+name+'"' in cdo.get_editor_property('ability_tags').export_text())
      check(name+'_no_startup_slot',cdo.get_editor_property('startup_input_tag').export_text()=='(TagName="")')
      check(name+'_short_summary',len(str(n.get_editor_property('summary')))<=35 and '\n' not in str(n.get_editor_property('summary')))
     for name,path in a['nodes'].items():check(name+'_readback',u.load_asset(path).validate_graph())
     cat=u.load_asset('/Game/PrototypeExtensions/Batch5/DA_AbilityInfo');rows=cat.get_editor_property('ability_information')
     check('catalog_35',len(rows)==35)
     for path,digest in a['original_hashes'].items():check('unchanged_'+Path(path).stem,hashlib.sha256((root/path).read_bytes()).hexdigest()==digest)
     old=json.loads((out/'original-source-hashes.json').read_text(encoding='utf-8'))
     check('all_preexisting_source_unchanged',all(hashlib.sha256((root/p).read_bytes()).hexdigest()==v for p,v in old.items()))
     pawn=u.get_default_object(u.load_class(None,'/Game/PrototypeExtensions/Batch5/BP_ExtensionPlayer.BP_ExtensionPlayer_C'))
     check('dedicated_animation',pawn.get_component_by_class(u.SkeletalMeshComponent).get_editor_property('anim_class').get_path_name()=='/Game/PrototypeExtensions/Batch5/ABP_ExtensionPlayer.ABP_ExtensionPlayer_C')
     r['passed']=True
    except Exception as e:r['error']=repr(e)
    finally:(out/'validation.json').write_text(json.dumps(r,indent=2),encoding='utf-8')

_batch5_validate()
