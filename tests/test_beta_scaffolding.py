from pathlib import Path


def test_beta_env_template_exists_with_top_variables():
    env_path = Path('.env.example.beta')
    assert env_path.exists()
    content = env_path.read_text(encoding='utf-8')
    assert '# BETA VARIABLES YOU WILL CHANGE' in content
    assert 'SUPABASE_URL=https://YOUR_PROJECT.supabase.co' in content
    assert 'SUPABASE_ANON_KEY=YOUR_ANON_KEY' in content
    assert 'SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY' in content


def test_backend_has_beta_scaffold_routes():
    app_path = Path('backend/app.py')
    content = app_path.read_text(encoding='utf-8')
    assert "@app.get('/api/me/settings')" in content
    assert "@app.post('/api/me/settings')" in content
    assert "@app.get('/api/beta/can-signup')" in content
