from pathlib import Path
import subprocess


def test_pilot_onboarding_assets_exist():
    checklist = Path('docs/validation/pilot_onboarding_checklist.md')
    users = Path('docs/validation/pilot_users.csv')

    assert checklist.exists()
    assert users.exists()

    c = checklist.read_text(encoding='utf-8')
    assert '3-5 trusted users' in c
    assert 'consent' in c.lower()
    assert 'Tuesday' in c

    rows = users.read_text(encoding='utf-8').strip().splitlines()
    assert rows[0] == 'user_id,display_name,channel,status'
    assert len(rows) >= 4  # header + at least 3 pilot rows


def test_feedback_assets_exist():
    form = Path('docs/validation/feedback_form.md')
    log = Path('docs/validation/feedback_log.csv')

    assert form.exists()
    assert log.exists()

    f = form.read_text(encoding='utf-8')
    assert 'trust' in f.lower()
    assert 'cognitive load' in f.lower()
    assert '1-5' in f

    assert log.read_text(encoding='utf-8').splitlines()[0] == (
        'timestamp_utc,user_id,trust_score,cognitive_load_score,notes,next_changes'
    )


def test_weekly_usage_script_generates_report(tmp_path):
    report = tmp_path / 'weekly_usage.md'
    cmd = [
        'python',
        'scripts/generate_weekly_usage_summary.py',
        '--db',
        'data/voice_debrief.sqlite3',
        '--out',
        str(report),
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert report.exists()
    body = report.read_text(encoding='utf-8')
    assert '# Weekly Usage Summary' in body
    assert 'session_created' in body


def test_backlog_prioritization_template_exists():
    backlog = Path('docs/validation/trust_impact_backlog.md')
    assert backlog.exists()
    text = backlog.read_text(encoding='utf-8')
    assert 'Trust Impact' in text
    assert 'Frequency' in text
    assert 'Effort' in text
    assert 'Priority Score' in text
