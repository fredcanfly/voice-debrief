from __future__ import annotations

import os

import httpx

from backend.prompt_loader import render_prompt


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


def _enforce_concise_question(text: str, max_words: int = 12) -> str:
    normalized = " ".join((text or "").strip().split())
    if not normalized:
        return ""

    words = normalized.split(" ")
    if len(words) > max_words:
        normalized = " ".join(words[:max_words]).rstrip(".,;:!?")

    if not normalized.endswith("?"):
        normalized = normalized.rstrip(".,;:!") + "?"

    return normalized



def generate_followup_question_openai(
    *,
    transcript_text: str,
    memory_facts: list[str] | None = None,
    skill_hints: list[str] | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> dict:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise OpenAIFollowupError("OPENAI_API_KEY is not set")

    llm_model = model or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
    facts = [f"- {item.strip()}" for item in (memory_facts or []) if str(item).strip()]
    memory_context = "\n".join(facts) if facts else "- none"
    hints = [f"- {item.strip()}" for item in (skill_hints or []) if str(item).strip()]
    skill_context = "\n".join(hints) if hints else "- none"

    tone_guidance = ""
    combined_hints = " ".join((skill_hints or [])).lower()
    if "sensitive topic handling" in combined_hints or "sensitive" in combined_hints:
        tone_guidance = "Sensitive-mode: start gently, avoid direct probing, and use emotionally-safe wording."

    prompt = render_prompt(
        'followup_question',
        transcript_text=transcript_text.strip(),
        memory_context=memory_context,
        skill_context=skill_context,
        tone_guidance=tone_guidance,
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
    question = _enforce_concise_question(_extract_output_text(body))
    if not question:
        raise OpenAIFollowupError("OpenAI follow-up returned empty text")

    return {"question": question, "model": llm_model, "raw": body}
