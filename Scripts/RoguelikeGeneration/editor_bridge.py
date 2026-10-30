"""Call the project-bound editor MCP, recording receipts and current-world lock.

Usage: python editor_bridge.py TOOL --file request.json
Never retry an unknown mutation outcome without inspecting the editor and receipts.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'skills/build-ga/scripts'))
from mcp_call import MCP, check_result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tool')
    parser.add_argument('--file', type=Path)
    options = parser.parse_args()
    arguments = json.loads(options.file.read_text(encoding='utf-8-sig')) if options.file else {}
    client = MCP(ROOT, 'RoguelikeGeneration')
    request = {'name': options.tool, 'arguments': arguments,
               '_project_path': client.project_path, '_instance_uuid': client.instance_uuid,
               'resource_locks': [{'id': 'world:current', 'mode': 'exclusive'}]}
    client.record('request', request)
    try:
        result = client.rpc('tools/call', request)
    except Exception as error:
        client.record('unknown', {'request': request, 'error': str(error)})
        raise RuntimeError('Outcome unknown; inspect receipts and editor before retrying: '
                           + str(client.receipts)) from error
    client.record('submitted', result)
    check_result(result)
    job = (result.get('structuredContent') or {}).get('job_id') or result.get('job_id')
    if job:
        result = client.job(job, 25)
    client.record('result', result)
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
