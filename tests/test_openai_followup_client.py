from backend.app.llm_openai import generate_followup_question_openai


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_followup_client_parses_responses_output_shape(monkeypatch):
    payload = {
        'output': [
            {
                'content': [
                    {'type': 'output_text', 'text': 'Who owns the Friday follow-up?'}
                ]
            }
        ]
    }

    def fake_post(*args, **kwargs):
        return FakeResponse(200, payload)

    monkeypatch.setattr('backend.app.llm_openai.httpx.post', fake_post)
    result = generate_followup_question_openai(
        transcript_text='Brief transcript',
        api_key='test-key',
        model='gpt-4.1-mini',
    )

    assert result['question'] == 'Who owns the Friday follow-up?'
    assert result['model'] == 'gpt-4.1-mini'
