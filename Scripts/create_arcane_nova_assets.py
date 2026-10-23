"""Host-side authoring entry point. Run after compiling C++ and opening the project."""
from pathlib import Path
import json
import shutil
from mcp_client import MCP, ROOT

BASE = '/Game/BluePrints/AbilitySystem/Player/Ability/Arcane/ArcaneNova/'
REFERENCE = '/Game/BluePrints/AbilitySystem/Player/Ability/Arcane/ArcaneChard/'


def asset_file(path):
    return ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')


def main():
    mcp = MCP()
    # Preserve complete pre-edit binary assets once, including the user's existing work.
    for path in ['/Game/BluePrints/Characters/Player/BP_Player',
                 '/Game/BluePrints/AbilitySystem/Data/DA_AbilityInfo',
                 '/Game/BluePrints/UI/SpellMenu/WBP_OffensiveSpellTree']:
        source = asset_file(path)
        backup = ROOT / 'Saved/ArcaneNova/Backups' / source.relative_to(ROOT)
        if source.exists() and not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)
    # SOMOLMCP 3.13.5 blueprint_create pre-creates the package before the UE 5.8
    # library's existence check. Use Unreal's BlueprintFactory via its console tool.
    create_script = (ROOT / 'Scripts/create_arcane_nova_blueprints.py').as_posix()
    print(json.dumps(mcp.call('console_exec', {'command': 'py "' + create_script + '"'}), ensure_ascii=False))
    for source, target in [('GE_Cost_ArcaneShards', 'GE_Cost_ArcaneNova'),
                           ('GE_Cooldown_ArcaneShards', 'GE_Cooldown_ArcaneNova')]:
        if not asset_file(BASE + target).exists():
            print(mcp.call('asset_duplicate', {'source_asset_path': REFERENCE + source,
                                             'destination_asset_path': BASE + target}))
    script = (ROOT / 'Scripts/configure_arcane_nova_assets.py').as_posix()
    result_file = ROOT / 'Saved/ArcaneNova/authoring-result.json'
    result_file.unlink(missing_ok=True)
    print(json.dumps(mcp.call('console_exec', {'command': 'py "' + script + '"'}), ensure_ascii=False))
    assert result_file.exists() and json.loads(result_file.read_text())['configured'], 'Configuration did not finish'
    tree = '/Game/BluePrints/UI/SpellMenu/WBP_OffensiveSpellTree'
    print(mcp.call('umg_widget_tree_set_widget_properties', {
        'asset_path': tree, 'widget_name': 'WBP_My_SpellGLobeButton_7',
        'properties': {'AbilityTag': {'TagName': 'Abilities.Arcane.ArcaneNova'}}}))
    print(mcp.call('blueprint_compile', {'asset_path': tree}))
    print(mcp.call('asset_save', {'asset_path': tree}))


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    main()
