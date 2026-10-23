"""Offline regression checks; never connect to or modify an Unreal project."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('mcp_call.py')
module = None
if SCRIPT.exists():
    spec = importlib.util.spec_from_file_location('ga_mcp', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(module, 'Missing project-bound GA MCP helper')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'project with spaces'
        self.root.mkdir()
        (self.root / 'game.uproject').write_text('{}', encoding='utf-8')
        (self.root / '.mcp.json').write_text(json.dumps({
            'mcpServers': {'somolmcp': {'url': 'http://127.0.0.1:12001/mcp'}}}), encoding='utf-8')
        self.calls = []
        self.queue = []
        self.reported = str(self.root)

    def transport(self, url, payload, headers, timeout):
        self.calls.append((payload, headers.copy()))
        if payload['method'] == 'initialize':
            result = {'serverInfo': {'projectPath': self.reported, 'instanceUuid': 'editor-one'}}
        else:
            result = self.queue.pop(0)
            if isinstance(result, Exception):
                raise result
        return {'jsonrpc': '2.0', 'id': payload['id'], 'result': result}, 'test-session'

    def client(self):
        return module.MCP(self.root, 'FrostNova', transport=self.transport)

    def test_wrong_project_rejected_before_tool_call(self):
        self.reported = str(self.root.parent / 'other-project')
        with self.assertRaisesRegex(RuntimeError, 'different project'):
            self.client()
        self.assertEqual([c[0]['method'] for c in self.calls], ['initialize'])

    def test_uproject_path_and_binding(self):
        self.reported = str(self.root / 'game.uproject')
        self.queue = [{'content': [], 'isError': False}]
        self.client().call('tool_catalog', {'mode': 'groups'}, wait=0)
        payload, headers = self.calls[-1]
        self.assertEqual(payload['params']['_project_path'], self.reported)
        self.assertEqual(payload['params']['_instance_uuid'], 'editor-one')
        self.assertEqual(headers['Mcp-Session-Id'], 'test-session')

    def test_async_success_requires_successful_steps(self):
        expected = {'content': [{'type': 'text', 'text': 'saved'}]}
        self.queue = [{'structuredContent': {'job_id': 'job-1'}},
                      {'terminal': True, 'status': 'succeeded',
                       'step_results': [{'result': expected}]}]
        self.assertEqual(self.client().call('asset_save', {}, wait=0), expected)
        self.assertEqual([c[0]['method'] for c in self.calls],
                         ['initialize', 'tools/call', 'jobs/get'])
        self.assertGreaterEqual(len(list((self.root / 'Saved/GAAuthoring').rglob('*.json'))), 3)

    def test_pending_never_resubmits(self):
        self.queue = [{'structuredContent': {'job_id': 'job-2'}},
                      {'terminal': False, 'status': 'running'}]
        with self.assertRaisesRegex(module.PendingJob, 'job-2'):
            self.client().call('asset_duplicate', {}, wait=0)
        self.assertEqual(sum(c[0]['method'] == 'tools/call' for c in self.calls), 1)

    def test_blocked_stops(self):
        self.queue = [{'client_status': 'blocked', 'terminal': False}]
        with self.assertRaisesRegex(RuntimeError, 'blocked'):
            self.client().job('job-3', wait=0)

    def test_failed_tool_and_failed_step_rejected(self):
        self.queue = [{'isError': True, 'content': []},
                      {'terminal': True, 'status': 'succeeded',
                       'step_results': [{'result': {'isError': True}},
                                        {'result': {'content': []}}]}]
        client = self.client()
        with self.assertRaises(RuntimeError):
            client.call('asset_save', {}, wait=0)
        with self.assertRaises(RuntimeError):
            client.job('job-4', wait=0)

    def test_transport_timeout_records_unknown_and_does_not_retry(self):
        self.queue = [TimeoutError('network timeout')]
        client = self.client()
        with self.assertRaisesRegex(RuntimeError, 'unknown'):
            client.call('asset_duplicate', {}, wait=0)
        records = [json.loads(p.read_text(encoding='utf-8')) for p in client.receipts.glob('*.json')]
        self.assertTrue(any(r.get('outcome') == 'unknown' for r in records))
        self.assertEqual(sum(c[0]['method'] == 'tools/call' for c in self.calls), 1)

    def test_failed_job_and_missing_steps_rejected(self):
        self.queue = [{'terminal': True, 'status': 'failed'},
                      {'terminal': True, 'status': 'succeeded', 'step_results': []}]
        client = self.client()
        for job_id in ['job-failed', 'job-empty']:
            with self.assertRaises(RuntimeError):
                client.job(job_id, wait=0)

    def test_unwrapped_business_failure_rejected(self):
        self.queue = [{'success': False, 'message': 'Asset change failed'}]
        with self.assertRaises(RuntimeError):
            self.client().call('asset_save', {}, wait=0)

    def test_receipts_do_not_overwrite_prior_run(self):
        first = self.client()
        second = self.client()
        self.assertNotEqual(first.receipts, second.receipts)

    def test_names_cannot_escape_saved_directory(self):
        with self.assertRaises(ValueError):
            module.MCP(self.root, '../outside', transport=self.transport)

    def test_json_and_sse_match_response_id(self):
        packet = {'jsonrpc': '2.0', 'id': 7, 'result': {'ok': True}}
        self.assertEqual(module.decode_response(json.dumps(packet), 7), packet)
        sse = ': ping\n\nevent: message\ndata: {"method":"notice"}\n\n'
        sse += 'event: message\ndata: ' + json.dumps(packet) + '\n\n'
        self.assertEqual(module.decode_response(sse, 7), packet)
        with self.assertRaises(RuntimeError):
            module.decode_response(json.dumps(packet), 8)


if __name__ == '__main__':
    unittest.main()
