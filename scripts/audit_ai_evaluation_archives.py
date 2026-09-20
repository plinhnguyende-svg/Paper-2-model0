"""Verify all real training archives without generating evaluation scenarios."""
import argparse
import json
from pathlib import Path
import subprocess
import os
import urllib.request
import urllib.error
import hashlib

from paper2_model0.ai.evaluation import frozen_registry, load_registered_policy, REGISTRY_SHA256
from paper2_model0.ai.training_protocol import runtime_fingerprint


def audit(root):
    entries = []
    schedules = {}
    for entry in frozen_registry()['entries']:
        policy, _, manifest = load_registered_policy(
            root / (entry['artifact_name'] + '.zip'), entry['regime'], entry['training_seed'])
        schedule = manifest['episodes']
        seed = entry['training_seed']
        if seed in schedules and schedules[seed] != schedule:
            raise ValueError('N/S/F training scenario schedules differ')
        schedules[seed] = schedule
        entries.append({k: entry[k] for k in (
            'regime', 'training_seed', 'artifact_id', 'artifact_digest',
            'final_checkpoint_sha256', 'final_manifest_sha256')})
        if any(a.updater is not None or a.network.training for a in policy.agents.values()):
            raise ValueError('inference state is not frozen')
    return {'status': 'PASS', 'archive_count': len(entries), 'heldout_scenarios_generated': 0,
            'source_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
            'registry_sha256': REGISTRY_SHA256, 'runtime': runtime_fingerprint(), 'entries': entries}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    if args.download:
        args.archive_dir.mkdir(parents=True, exist_ok=True)
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        for entry in frozen_registry()['entries']:
            url = ('https://api.github.com/repos/plinhnguyende-svg/Paper-2-model0'
                   f"/actions/artifacts/{entry['artifact_id']}/zip")
            request = urllib.request.Request(url, headers={
                'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
                'Accept': 'application/vnd.github+json', 'User-Agent': 'paper2-audit'})
            try:
                with urllib.request.build_opener(NoRedirect).open(request, timeout=120) as response:
                    data = response.read()
            except urllib.error.HTTPError as error:
                if error.code != 302:
                    raise
                location = error.headers['Location']
                if not location.startswith('https://'):
                    raise ValueError('non-HTTPS artifact redirect')
                # Signed storage URL receives no GitHub credential.
                with urllib.request.urlopen(location, timeout=120) as response:
                    data = response.read()
            if 'sha256:' + hashlib.sha256(data).hexdigest() != entry['artifact_digest']:
                raise ValueError('downloaded archive digest mismatch')
            (args.archive_dir / (entry['artifact_name'] + '.zip')).write_bytes(data)
    result = audit(args.archive_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'entries'}))
