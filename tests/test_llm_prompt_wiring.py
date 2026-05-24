from backend.app.llm_openai import generate_followup_question_openai


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_followup_openai_uses_prompt_template(monkeypatch):
    captured = {}

    def fake_post(*args, **kwargs):
        captured['input'] = kwargs['json']['input']
        return FakeResponse(200, {'output_text': 'Who owns Friday follow-up?'})

    monkeypatch.setattr('backend.app.llm_openai.httpx.post', fake_post)
    monkeypatch.setattr('backend.app.llm_openai.render_prompt', lambda name, **ctx: f'TEMPLATE::{name}::{ctx["transcript_text"]}')

    generate_followup_question_openai(
        transcript_text='Johnson family handoff is missing owner',
        api_key='test-key',
        model='gpt-4.1-mini',
    )

    assert captured['input'].startswith('TEMPLATE::followup_question::Johnson family handoff is missing owner')
