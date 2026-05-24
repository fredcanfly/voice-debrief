from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import httpx

from .config import Settings
from .prompts import DEBRIEF_INSTRUCTIONS, FINAL_SUMMARY_REQUEST


@dataclass
class HermesReply:
    response_id: str | None
    text: str
    raw: dict[str, Any]


class HermesClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def health(self) -> dict[str, Any]:
        url = f"{self.settings.hermes_api_base.rstrip('/')}/health"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def send_debrief_turn(self, conversation: str, text: str) -> HermesReply:
        return await self._responses(conversation=conversation, input_text=text, instructions=DEBRIEF_INSTRUCTIONS)

    async def end_debrief(self, conversation: str) -> HermesReply:
        return await self._responses(conversation=conversation, input_text=FINAL_SUMMARY_REQUEST, instructions=DEBRIEF_INSTRUCTIONS)

    async def _responses(self, conversation: str, input_text: str, instructions: str) -> HermesReply:
        url = f"{self.settings.hermes_api_base.rstrip('/')}/responses"
        payload = {
            'model': self.settings.hermes_model,
            'input': input_text,
            'instructions': instructions,
            'conversation': conversation,
            'store': True,
        }
        async with httpx.AsyncClient(timeout=180) as client:
            resp = await client.post(url, json=payload, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
        return HermesReply(response_id=data.get('id'), text=_extract_response_text(data), raw=data)

    def _headers(self) -> dict[str, str]:
        headers = {'Content-Type': 'application/json'}
        if self.settings.hermes_api_key:
            headers['Authorization'] = f"Bearer {self.settings.hermes_api_key}"
        return headers


def _extract_response_text(data: dict[str, Any]) -> str:
    chunks: list[str] = []
    for item in data.get('output') or []:
        if item.get('type') != 'message':
            continue
        for part in item.get('content') or []:
            if isinstance(part, dict) and part.get('type') in {'output_text', 'text'}:
                chunks.append(str(part.get('text') or ''))
    if chunks:
        return ''.join(chunks).strip()
    # Chat-completions-shaped fallback, useful if the API changes or tests mock it.
    choices = data.get('choices') or []
    if choices:
        return str(choices[0].get('message', {}).get('content') or '').strip()
    return ''
