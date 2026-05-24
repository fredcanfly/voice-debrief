from backend.app.llm_debrief_openai import generate_debrief_document_openai


class FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_debrief_client_parses_responses_text_and_title(monkeypatch):
    payload = {
        'output': [
            {'content': [{'type': 'output_text', 'text': 'Title: Johnson Debrief\n\nExecutive summary:\n- x'}]}
        ]
    }

    def fake_post(*args, **kwargs):
        return FakeResponse(200, payload)

    monkeypatch.setattr('backend.app.llm_debrief_openai.httpx.post', fake_post)

    result = generate_debrief_document_openai(
        transcript_text='Transcript body',
        api_key='test-key',
        model='gpt-4.1-mini',
    )

    assert result['title'] == 'Johnson Debrief'
    assert result['slug'] == 'johnson-debrief'
    assert 'Executive summary:' in result['markdown']
