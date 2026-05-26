const USER_ID_KEY = 'voiceDebrief.userId';
const userIdEl = document.getElementById('userId');
const passwordEl = document.getElementById('password');
const submitBtn = document.getElementById('submitBtn');
const msgEl = document.getElementById('msg');

const isSignup = window.location.pathname === '/signup';
const endpoint = isSignup ? '/api/auth/signup' : '/api/auth/login';

function setMsg(text, isErr = false) {
  msgEl.textContent = text;
  msgEl.className = isErr ? 'err' : '';
}

submitBtn?.addEventListener('click', async () => {
  const user_id = (userIdEl?.value || '').trim();
  const password = passwordEl?.value || '';

  if (!user_id || !password) {
    setMsg('Enter user ID and password.', true);
    return;
  }

  try {
    setMsg(isSignup ? 'Creating account…' : 'Logging in…');
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ user_id, password }),
    });
    if (!res.ok) throw new Error((await res.text()) || 'Request failed');

    window.localStorage?.setItem(USER_ID_KEY, user_id);
    window.location.href = '/';
  } catch (err) {
    setMsg(`Auth failed: ${err.message}`, true);
  }
});
