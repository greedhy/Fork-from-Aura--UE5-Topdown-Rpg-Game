"""Verify that the additive migration has not changed any pre-existing authored file."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
baseline = json.loads((root / 'Saved/PureMass/original-files.json').read_text(encoding='utf8'))
changed = []
for name, before in baseline.items():
    path = root / name
    if not path.is_file():
        changed.append({'file': name, 'reason': 'missing'})
        continue
    with path.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual != before['sha256']:
        changed.append({'file': name, 'reason': 'content changed'})
report = {'passed': not changed, 'checked': len(baseline), 'changed': changed}
(root / 'Saved/PureMass/preservation.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print(json.dumps(report, indent=2))
raise SystemExit(0 if report['passed'] else 1)
