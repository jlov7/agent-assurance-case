import copy
import importlib.util
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('verify', BASE / 'verifier' / 'verify.py')
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


def load(name):
    return json.loads((BASE / 'examples' / name).read_text())


def resign(case):
    priv, _ = verify._demo_keypair()
    case['evidence']['signed_by'] = verify._DEMO_SIGNED_BY
    case['evidence']['key_id'] = verify._DEMO_KEY_ID
    verify.sign_case(case, priv)
    return case


def write(tmp_path, name, case):
    path = tmp_path / name
    path.write_text(json.dumps(case, indent=2))
    return path


def test_bad_signature_fails_without_silent_skip(tmp_path):
    case = load('pass-with-coverage.json')
    case['evidence']['signature'] = 'ed25519:' + 'A' * 88
    path = write(tmp_path, 'case.json', case)
    assert verify.verify(path, None, allow_demo_key=False, resign_demo=False, verbose=False) == 1


def test_evidence_metadata_tamper_changes_hash(tmp_path):
    case = load('pass-with-coverage.json')
    case['evidence']['signed_by'] = 'did:web:evil.example'
    path = write(tmp_path, 'case.json', case)
    assert verify.verify(path, None, allow_demo_key=True, resign_demo=False, verbose=False) == 1


def test_partial_inventory_prevents_pass(tmp_path):
    case = load('pass-with-coverage.json')
    case['coverage']['inventory_status'] = 'partial'
    resign(case)
    path = write(tmp_path, 'case.json', case)
    assert verify.verify(path, None, allow_demo_key=True, resign_demo=False, verbose=False) == 1


def test_finding_references_undeclared_asset_fails(tmp_path):
    case = load('skill-poisoning-hold.json')
    case['findings'][0]['subject_asset_id'] = 'skill:missing@1.0.0'
    resign(case)
    path = write(tmp_path, 'case.json', case)
    assert verify.verify(path, None, allow_demo_key=True, resign_demo=False, verbose=False) == 1


def test_fail_example_verifies_as_fail():
    case = load('critical-exfiltration-fail.json')
    expected, reasons = verify.recompute_verdict(case)
    assert expected == 'fail'


def test_profile_missing_required_skill_detector_fails(tmp_path):
    case = load('pass-with-coverage.json')
    for run in case['coverage']['detector_runs']:
        if run['detector']['name'] == 'runwright-skill-static':
            run['categories'] = [c for c in run['categories'] if c != 'skill-secret-exposure']
    resign(case)
    path = write(tmp_path, 'case.json', case)
    assert verify.verify(path, None, allow_demo_key=True, resign_demo=False, verbose=False) == 1


def test_evidence_ref_missing_from_artifact_manifest_fails(tmp_path):
    case = load('pass-with-coverage.json')
    case['findings'].append({
        'finding_id': 'finding_missing_ref',
        'category': 'RUNWRIGHT-SKILL-INFO',
        'severity': 'info',
        'status': 'open',
        'subject_asset_id': case['assets'][0]['asset_id'],
        'title': 'Informational finding with unbound evidence',
        'created_at': '2026-05-11T13:00:01Z',
        'evidence_refs': ['evidence://missing/not-in-manifest.json']
    })
    resign(case)
    path = write(tmp_path, 'case.json', case)
    assert verify.verify(path, None, allow_demo_key=True, resign_demo=False, verbose=False) == 1


def test_duplicate_json_member_rejected():
    raw = '{"schema_version":"0.2","schema_version":"0.2"}'
    try:
        verify.load_json_no_duplicates(raw)
        assert False, 'duplicate key should have raised'
    except ValueError as e:
        assert 'Duplicate JSON object member' in str(e)


def test_non_utc_timestamp_rejected(tmp_path):
    case = load('pass-with-coverage.json')
    case['evidence']['signed_at'] = '2026-05-11T13:00:00+00:00'
    resign(case)
    path = write(tmp_path, 'case.json', case)
    assert verify.verify(path, None, allow_demo_key=True, resign_demo=False, verbose=False) == 1


def test_accepted_critical_risk_is_hold_not_pass():
    case = load('critical-exfiltration-fail.json')
    case['policy_decisions'] = []
    finding = case['findings'][0]
    finding['status'] = 'accepted_risk'
    finding['resolution'] = {'approval_id': 'approval_1', 'expires_at': '2026-06-11T13:00:00Z'}
    case['approvals'] = [{
        'approval_id': 'approval_1',
        'decision': 'accept_risk',
        'decided_by': 'ciso@example.com',
        'decided_at': '2026-05-11T13:10:00Z',
        'expires_at': '2026-06-11T13:00:00Z',
        'signature': 'ed25519:' + 'A' * 88
    }]
    expected, reasons = verify.recompute_verdict(case)
    assert expected == 'hold'
