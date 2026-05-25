from pathlib import Path


def test_caddy_and_hardening_assets_exist():
    caddy = Path('deploy/ovh/Caddyfile')
    hardening = Path('deploy/ovh/HARDENING.md')

    assert caddy.exists()
    assert hardening.exists()

    c = caddy.read_text(encoding='utf-8')
    assert 'encode zstd gzip' in c
    assert 'header {' in c
    assert 'reverse_proxy 127.0.0.1:8000' in c

    h = hardening.read_text(encoding='utf-8')
    assert 'ufw allow OpenSSH' in h
    assert 'ufw allow 80' in h
    assert 'ufw allow 443' in h
    assert 'fail2ban' in h
