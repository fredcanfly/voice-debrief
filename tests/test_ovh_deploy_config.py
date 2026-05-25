from pathlib import Path


def test_ovh_deploy_assets_exist_with_reproducible_steps():
    readme = Path('deploy/ovh/README.md')
    service = Path('deploy/ovh/voice-debrief.service')
    script = Path('deploy/ovh/deploy.sh')

    assert readme.exists()
    assert service.exists()
    assert script.exists()

    content = readme.read_text(encoding='utf-8')
    assert 'OVH VPS-1' in content
    assert 'git clone' in content
    assert 'systemctl enable --now voice-debrief' in content

    svc = service.read_text(encoding='utf-8')
    assert 'ExecStart=' in svc
    assert 'uvicorn backend.app.main:app' in svc
