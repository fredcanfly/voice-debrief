from __future__ import annotations

import os

import httpx


class OpenAIFollowupError(RuntimeError):
    pass


def _extract_output_text(body: dict) -> str:
    direct = (body.get("output_text") or "").strip()
    if direct:
        return direct

    for item in body.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text":
                text = str(content.get("text") or "").strip()
                if text:
                    return text

    return ""


def generate_followup_question_openai(*, transcript_text: str, api_key: str | None = None, model: str | None = None) -> dict:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise OpenAIFollowupError("OPENAI_API_KEY is not set")

    llm_model = model or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"

    prompt = (
        "You are a concise reflective interviewer for a meeting debrief app. "
        "Given transcript text, produce exactly one short follow-up question. "
        "Rules: under 12 words, no filler, no preface, output only the question text.\n\n"
        f"Transcript:\n{transcript_text.strip()}"
    )

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {
        "model": llm_model,
        "input": prompt,
        "max_output_tokens": 48,
    }

    response = httpx.post("https://api.openai.com/v1/responses", headers=headers, json=payload, timeout=60)
    if response.status_code >= 400:
        raise OpenAIFollowupError(f"OpenAI follow-up error {response.status_code}: {response.text}")

    body = response.json()
    question = _extract_output_text(body)
    if not question:
        raise OpenAIFollowupError("OpenAI follow-up returned empty text")

    return {"question": question, "model": llm_model, "raw": body}
