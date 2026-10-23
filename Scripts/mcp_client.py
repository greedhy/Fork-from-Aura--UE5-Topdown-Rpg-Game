"""Small JSON-RPC client for the project's .mcp.json SOMOLMCP endpoint.

Usage: python Scripts/mcp_client.py TOOL '{"argument": "value"}'
       python Scripts/mcp_client.py TOOL --file request.json
Responses (including asynchronous job receipts) are retained under Saved/ArcaneNova.
"""
import json
from pathlib import Path
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class MCP:
    def __init__(self):
        self.url = json.loads((ROOT / '.mcp.json').read_text(encoding='utf-8-sig'))['mcpServers']['somolmcp']['url']
        self.session = None
        self.sequence = 0
        init = self.rpc('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                                     'clientInfo': {'name': 'codex-ga-authoring', 'version': '1.0'}})
        self.session = init.get('sessionId')
        self.project_path = init['serverInfo']['projectPath']
        reported_target = Path(self.project_path)
        allowed_targets = {ROOT.resolve(), *(path.resolve() for path in ROOT.glob('*.uproject'))}
        if not reported_target.is_absolute() or reported_target.resolve() not in allowed_targets:
            raise RuntimeError('MCP is connected to a different project: ' + self.project_path
                               + '; expected ' + str(ROOT))
        self.instance_uuid = init['serverInfo']['instanceUuid']

    def rpc(self, method, params):
        self.sequence += 1
        payload = {'jsonrpc': '2.0', 'id': self.sequence, 'method': method, 'params': params}
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
        if self.session:
            headers['Mcp-Session-Id'] = self.session
        request = urllib.request.Request(self.url, json.dumps(payload).encode(), headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            body = response.read().decode('utf-8')
        if body.startswith('event:') or body.startswith('data:'):
            body = next(line[5:].strip() for line in body.splitlines() if line.startswith('data:'))
        result = json.loads(body)
        if 'error' in result:
            raise RuntimeError(json.dumps(result['error'], ensure_ascii=False))
        return result.get('result', result)

    def call(self, name, arguments):
        result = self.rpc('tools/call', {'name': name, 'arguments': arguments,
                                      '_project_path': self.project_path, '_instance_uuid': self.instance_uuid})
        job_id = result.get('structuredContent', {}).get('job_id')
        if not job_id:
            return result
        folder = ROOT / 'Saved' / 'ArcaneNova' / 'receipts'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / (job_id + '-submitted.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
        deadline = time.monotonic() + 50
        while time.monotonic() < deadline:
            time.sleep(1)
            receipt = self.rpc('jobs/get', {'job_id': job_id})
            if receipt.get('client_status') == 'blocked':
                (folder / (job_id + '.json')).write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
                raise RuntimeError(json.dumps(receipt, ensure_ascii=False))
            if receipt.get('terminal'):
                folder = ROOT / 'Saved' / 'ArcaneNova' / 'receipts'
                folder.mkdir(parents=True, exist_ok=True)
                (folder / (job_id + '.json')).write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
                if receipt.get('status') != 'succeeded':
                    raise RuntimeError(json.dumps(receipt, ensure_ascii=False))
                return receipt['step_results'][-1]['result']
        raise TimeoutError('MCP job still pending: ' + job_id + '; poll jobs/get, do not resubmit.')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    arguments = json.loads(Path(sys.argv[3]).read_text(encoding='utf-8-sig') if len(sys.argv) > 3 and sys.argv[2] == '--file' else sys.argv[2] if len(sys.argv) > 2 else '{}')
    result = MCP().call(sys.argv[1], arguments)
    folder = ROOT / 'Saved' / 'ArcaneNova'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (sys.argv[1] + '-latest.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
