from backend.app.llm_openai import generate_followup_question_openai


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_followup_question_is_trimmed_to_12_words(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse(
            200,
            {
                'output_text': 'Can you clarify who exactly owns the Johnson family counseling follow-up action by Friday morning?',
            },
        )

    monkeypatch.setattr('backend.app.llm_openai.httpx.post', fake_post)

    result = generate_followup_question_openai(
        transcript_text='Johnson family follow-up owner unclear.',
        api_key='test-key',
        model='gpt-4.1-mini',
    )

    words = result['question'].strip().split()
    assert len(words) <= 12


def test_followup_question_ensures_question_mark(monkeypatch):
    def fake_post(*args, **kwargs):
        return FakeResponse(200, {'output_text': 'Who owns the Friday follow-up'})

    monkeypatch.setattr('backend.app.llm_openai.httpx.post', fake_post)

    result = generate_followup_question_openai(
        transcript_text='Need owner by Friday.',
        api_key='test-key',
        model='gpt-4.1-mini',
    )

    assert result['question'].endswith('?')
