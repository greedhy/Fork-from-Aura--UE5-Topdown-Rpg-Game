"""Host Python: retarget only the isolated run AnimBP's copied player references.

Run after author_run.py. Bound MCP calls keep durable receipts; interrupted mutations
must be inspected before rerunning. Original player/animation packages are hashed.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'skills/build-ga/scripts'))
from mcp_call import MCP, check_result


def main():
    report_dir = ROOT / 'Saved/RoguelikeGeneration'
    author = json.loads((report_dir / 'authoring-run.json').read_text(encoding='utf-8-sig'))
    src = author['dependencies']['animation']
    old_player = author['dependencies']['player']
    dst = author['assets']['animation']
    new_player = author['assets']['player']
    assert dst == '/Game/RoguelikeGeneration/Gameplay/ABP_DungeonPlayer'
    assert new_player == '/Game/RoguelikeGeneration/Gameplay/BP_DungeonPlayer'
    source_files = [ROOT / ('Content/' + p.removeprefix('/Game/') + '.uasset') for p in (src, old_player)]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    client = MCP(ROOT, 'DungeonAnimation')

    def call(name, arguments):
        request = {'name': name, 'arguments': arguments, '_project_path': client.project_path,
                   '_instance_uuid': client.instance_uuid,
                   'resource_locks': [{'id': 'world:current', 'mode': 'exclusive'}]}
        client.record('request', request)
        try:
            result = client.rpc('tools/call', request)
        except Exception as error:
            client.record('unknown', {'request': request, 'error': str(error)})
            raise
        client.record('submitted', result)
        check_result(result)
        job = (result.get('structuredContent') or {}).get('job_id') or result.get('job_id')
        if job:
            result = client.job(job, 25)
        client.record('result', result)
        return result

    def object_path(package):
        return package + '.' + package.rsplit('/', 1)[-1]

    # Existing source is immutable. The complete EventGraph is the recovery source.
    source_graph = call('blueprint_export_nodes_t3d', {'asset_path': src, 'graph_name': 'EventGraph', 'all_nodes': True})['t3d']
    assert object_path(old_player) in source_graph, 'Source player cast reference was not found'
    replacement = source_graph.replace(object_path(old_player), object_path(new_player)).replace(object_path(src), object_path(dst))
    assert object_path(old_player) not in replacement
    current = call('blueprint_export_nodes_t3d', {'asset_path': dst, 'graph_name': 'EventGraph', 'all_nodes': True})['t3d']
    if object_path(new_player) not in current or object_path(old_player) in current:
        graph = call('blueprint_analyze_graph', {'asset_path': dst, 'graph_name': 'EventGraph'})
        nodes = next(g for g in graph['graph_analysis'] if g['name'] == 'EventGraph')['nodes']
        for node in nodes:
            call('blueprint_delete_node', {'asset_path': dst, 'node_guid': node['guid']})
        call('blueprint_change_member_variable_type', {'asset_path': dst, 'variable_name': 'BP_Player_Character', 'type': 'object<' + object_path(new_player) + '_C>'})
        call('blueprint_import_nodes_t3d', {'asset_path': dst, 'graph_name': 'EventGraph', 't3d': replacement})
    compiled = call('blueprint_compile', {'asset_path': dst})
    final_graph = call('blueprint_export_nodes_t3d', {'asset_path': dst, 'graph_name': 'EventGraph', 'all_nodes': True})['t3d']
    assert object_path(new_player) in final_graph and object_path(old_player) not in final_graph
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest for p, digest in hashes.items())
    finalize = report_dir / 'finalize-run-animation.py'
    finalize.write_text('import unreal as u\n'
        + 'a=u.load_asset(' + repr(dst) + ')\n'
        + 'assert not u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()\n'
        + 'assert all(p.get_name()==' + repr(dst) + ' for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()))\n'
        + 'u.EditorAssetLibrary.set_metadata_tag(a,"DungeonPlayerReferencesRetargeted","true")\n'
        + 'assert u.EditorAssetLibrary.save_loaded_asset(a,False)\n', encoding='utf-8')
    call('console_exec', {'command': 'py "' + str(finalize).replace('\\', '/') + '"'})
    (report_dir / 'run-animation-retarget.json').write_text(json.dumps({
        'source_hashes': hashes, 'asset': dst, 'source': src, 'references_verified': True,
        'compile': compiled, 'receipts': str(client.receipts),
        'save_requires_author_run_readback': True}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Retarget verified; rerun author_run.py for saved-asset readback.')


if __name__ == '__main__':
    main()
