from __future__ import annotations

import os
import re

import httpx

from backend.prompts import FINAL_SUMMARY_REQUEST


class OpenAIDebriefError(RuntimeError):
    pass


def _extract_output_text(body: dict) -> str:
    direct = (body.get('output_text') or '').strip()
    if direct:
        return direct

    for item in body.get('output', []) or []:
        for content in item.get('content', []) or []:
            if content.get('type') == 'output_text':
                text = str(content.get('text') or '').strip()
                if text:
                    return text

    return ''


def _extract_title(markdown: str) -> str:
    for line in markdown.splitlines():
        if line.lower().startswith('title:'):
            return line.split(':', 1)[1].strip() or 'Debrief Notes'
    return 'Debrief Notes'


def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r'[^a-z0-9\s-]', '', value)
    value = re.sub(r'[\s_-]+', '-', value)
    value = re.sub(r'^-+|-+$', '', value)
    return value or 'debrief-notes'


def generate_debrief_document_openai(*, transcript_text: str, api_key: str | None = None, model: str | None = None) -> dict:
    key = api_key or os.getenv('OPENAI_API_KEY')
    if not key:
        raise OpenAIDebriefError('OPENAI_API_KEY is not set')

    llm_model = model or os.getenv('OPENAI_MODEL') or 'gpt-4.1-mini'

    prompt = (
        f"{FINAL_SUMMARY_REQUEST}\n\n"
        "Use this transcript bundle as source of truth.\n"
        f"Transcript:\n{transcript_text.strip()}"
    )

    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    payload = {'model': llm_model, 'input': prompt, 'max_output_tokens': 1400}

    response = httpx.post('https://api.openai.com/v1/responses', headers=headers, json=payload, timeout=90)
    if response.status_code >= 400:
        raise OpenAIDebriefError(f'OpenAI debrief error {response.status_code}: {response.text}')

    body = response.json()
    markdown = _extract_output_text(body)
    if not markdown:
        raise OpenAIDebriefError('OpenAI debrief returned empty text')

    title = _extract_title(markdown)
    return {'markdown': markdown, 'model': llm_model, 'title': title, 'slug': _slugify(title), 'raw': body}
