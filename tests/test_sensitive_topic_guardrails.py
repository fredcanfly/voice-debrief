from backend.app.llm_openai import generate_followup_question_openai


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_sensitive_skill_hint_adds_gentle_tone_guidance(monkeypatch):
    captured = {}

    def fake_post(*args, **kwargs):
        captured['input'] = kwargs['json']['input']
        return FakeResponse(200, {'output_text': 'What feels most important to name first?'})

    monkeypatch.setattr('backend.app.llm_openai.httpx.post', fake_post)

    generate_followup_question_openai(
        transcript_text='Johnson family pastoral situation is sensitive.',
        memory_facts=['Client: Johnson family'],
        skill_hints=['Sensitive topic handling: start gently'],
        api_key='test-key',
        model='gpt-4.1-mini',
    )

    text = captured['input'].lower()
    assert 'start gently' in text
    assert 'avoid direct probing' in text


def test_non_sensitive_hints_do_not_add_sensitive_guardrail(monkeypatch):
    captured = {}

    def fake_post(*args, **kwargs):
        captured['input'] = kwargs['json']['input']
        return FakeResponse(200, {'output_text': 'Who owns the follow-up?'})

    monkeypatch.setattr('backend.app.llm_openai.httpx.post', fake_post)

    generate_followup_question_openai(
        transcript_text='Need owner by Friday.',
        memory_facts=['Deadline mentioned: Friday'],
        skill_hints=['Urgency: confirm owner and deadline explicitly'],
        api_key='test-key',
        model='gpt-4.1-mini',
    )

    text = captured['input'].lower()
    assert 'avoid direct probing' not in text
