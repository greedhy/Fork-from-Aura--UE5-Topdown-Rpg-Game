"""Project-bound SOMOLMCP client; no automatic resubmission of mutations.

Python 3.10+, standard library only. Use --help for call/job modes.
This transports tools; a successful console_exec still needs script/asset checks.
"""
import argparse
import json
from pathlib import Path
import re
import sys
import time
import urllib.request
import uuid


class PendingJob(RuntimeError):
    pass


def decode_response(body, request_id):
    """Accept JSON or finite SSE responses, ignoring unrelated notifications."""
    try:
        packets = [json.loads(body)]
    except json.JSONDecodeError:
        packets = []
        for event in body.replace('\r\n', '\n').split('\n\n'):
            data = '\n'.join(line[5:].lstrip() for line in event.splitlines()
                             if line.startswith('data:'))
            if data:
                try:
                    packets.append(json.loads(data))
                except json.JSONDecodeError:
                    continue
    for packet in packets:
        if isinstance(packet, dict) and packet.get('id') == request_id:
            return packet
    raise RuntimeError('No JSON-RPC response matched request id; outcome may be unknown')


def http_transport(url, payload, headers, timeout):
    request = urllib.request.Request(url, json.dumps(payload).encode('utf-8'), headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode('utf-8-sig')
        session = response.headers.get('Mcp-Session-Id')
    return decode_response(body, payload['id']), session


def check_result(result):
    if not isinstance(result, dict):
        raise RuntimeError('Expected a structured MCP result')
    structured = result.get('structuredContent') or {}
    if (result.get('isError') or result.get('ok') is False or result.get('success') is False
            or structured.get('ok') is False or structured.get('success') is False):
        raise RuntimeError('MCP tool failed: ' + json.dumps(result, ensure_ascii=False))
    return result


class MCP:
    def __init__(self, project, ability='Inspection', transport=None):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}', ability):
            raise ValueError('Ability report name must be a simple ASCII identifier')
        self.root = Path(project).resolve()
        if self.root.is_file() and self.root.suffix == '.uproject':
            self.root = self.root.parent
        projects = list(self.root.glob('*.uproject'))
        if len(projects) != 1:
            raise ValueError('Pass a project directory containing exactly one .uproject')
        config = json.loads((self.root / '.mcp.json').read_text(encoding='utf-8-sig'))
        self.url = config['mcpServers']['somolmcp']['url']
        self.transport = transport or http_transport
        self.session = None
        self.sequence = 0
        self.receipts = self.root / 'Saved/GAAuthoring' / ability / uuid.uuid4().hex / 'receipts'
        self.receipts.mkdir(parents=True)
        init = self.rpc('initialize', {
            'protocolVersion': '2024-11-05', 'capabilities': {},
            'clientInfo': {'name': 'build-ga', 'version': '1.0'}})
        self.session = self.session or init.get('sessionId')
        info = init['serverInfo']
        self.project_path = info['projectPath']
        reported = Path(self.project_path)
        if not reported.is_absolute() or reported.resolve() not in {self.root, projects[0].resolve()}:
            raise RuntimeError('MCP connected to a different project: ' + self.project_path)
        self.instance_uuid = info['instanceUuid']
        if not self.instance_uuid:
            raise RuntimeError('MCP did not identify an editor instance')
        self.record('binding', {'project': self.project_path, 'instance': self.instance_uuid,
                                'serverInfo': info})

    def record(self, label, value):
        path = self.receipts / (uuid.uuid4().hex + '-' + label + '.json')
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        return path

    def rpc(self, method, params):
        self.sequence += 1
        payload = {'jsonrpc': '2.0', 'id': self.sequence, 'method': method, 'params': params}
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
                   'MCP-Protocol-Version': '2024-11-05'}
        if self.session:
            headers['Mcp-Session-Id'] = self.session
        response, session = self.transport(self.url, payload, headers, 30)
        if session:
            self.session = session
        if response.get('id') != self.sequence:
            raise RuntimeError('Unexpected JSON-RPC response id')
        if 'error' in response:
            raise RuntimeError('JSON-RPC error: ' + json.dumps(response['error'], ensure_ascii=False))
        return response['result']

    def call(self, name, arguments, wait=30):
        if not isinstance(arguments, dict):
            raise ValueError('Tool arguments must be a JSON object')
        request = {'name': name, 'arguments': arguments,
                   '_project_path': self.project_path, '_instance_uuid': self.instance_uuid}
        self.record('request', request)
        try:
            result = self.rpc('tools/call', request)
        except Exception as error:
            self.record('unknown', {'outcome': 'unknown', 'request': request, 'error': str(error)})
            raise RuntimeError('Tool outcome unknown; inspect receipts, jobs and target assets before any retry. '
                               + str(self.receipts)) from error
        self.record('submitted', result)
        check_result(result)
        job_id = (result.get('structuredContent') or {}).get('job_id') or result.get('job_id')
        if job_id:
            return self.job(job_id, wait)
        return result

    def job(self, job_id, wait=30):
        deadline = time.monotonic() + max(0, min(wait, 45))
        while True:
            try:
                receipt = self.rpc('jobs/get', {'job_id': job_id})
            except Exception as error:
                self.record('poll-error', {'job_id': job_id, 'error': str(error)})
                raise PendingJob('Could not read job ' + job_id + '; resume jobs/get, do not resubmit') from error
            self.record('job', {'job_id': job_id, **receipt})
            if receipt.get('client_status') == 'blocked':
                raise RuntimeError('Job blocked: ' + json.dumps(receipt, ensure_ascii=False))
            if receipt.get('terminal'):
                if receipt.get('status') != 'succeeded':
                    raise RuntimeError('Job failed: ' + json.dumps(receipt, ensure_ascii=False))
                steps = receipt.get('step_results') or []
                if not steps:
                    raise RuntimeError('Job has no step results; verify target state')
                for step in steps:
                    if step.get('error') or step.get('status') in {'failed', 'cancelled'}:
                        raise RuntimeError('Job step failed: ' + json.dumps(step, ensure_ascii=False))
                    check_result(step.get('result'))
                return steps[-1]['result']
            if time.monotonic() >= deadline:
                raise PendingJob('Job pending: ' + job_id + '; use job mode, do not resubmit')
            time.sleep(min(1, max(0, deadline - time.monotonic())))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, help='Project folder or .uproject, never skill folder')
    parser.add_argument('--ability', default='Inspection', help='Name for Saved/GAAuthoring receipts')
    parser.add_argument('--wait', type=float, default=30, help='Job polling window, 0 to 45 seconds')
    sub = parser.add_subparsers(dest='mode', required=True)
    call = sub.add_parser('call', help='Submit exactly once; use a JSON file to avoid shell quoting')
    call.add_argument('tool')
    call.add_argument('--file', type=Path, help='UTF-8 JSON object; defaults to empty arguments')
    job = sub.add_parser('job', help='Resume jobs/get without resubmitting the tool')
    job.add_argument('job_id')
    args = parser.parse_args()
    try:
        client = MCP(args.project, args.ability)
        if args.mode == 'call':
            arguments = json.loads(args.file.read_text(encoding='utf-8-sig')) if args.file else {}
            result = client.call(args.tool, arguments, args.wait)
        else:
            result = client.job(args.job_id, args.wait)
        print(json.dumps({'result': result, 'receipts': str(client.receipts)}, ensure_ascii=False, indent=2))
        return 0
    except PendingJob as error:
        print(str(error), file=sys.stderr)
        return 2
    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())
