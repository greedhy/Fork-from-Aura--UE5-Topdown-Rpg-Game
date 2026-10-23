"""QA-only host Aftershock / guest HunterSentry loadout; no persistent user save changes."""
def main():
    import unreal as u
    def tag(s):
        t=u.GameplayTag();t.import_text('(TagName="'+s+'")');return t
    host=next(p for p in u.ObjectIterator(u.MyPlayerController) if 'UEDPIE_' in p.get_path_name() and p.is_local_controller() and p.get_local_role()==u.NetRole.ROLE_AUTHORITY and p.get_controlled_pawn())
    host.get_controlled_pawn().call_method('AddToSpellPoints',(1,))
    asc=host.get_editor_property('player_state').get_component_by_class(u.MyAbilitySystemComponent)
    asc.call_method('ServerSpendSpellPoint',(tag('Abilities.Composition.Aftershock'),))
    asc.call_method('ServerEquipAbility',(tag('Abilities.Composition.Aftershock'),tag('InputTag.4')))
main()
