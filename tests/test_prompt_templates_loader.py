from pathlib import Path

import pytest


from backend.prompt_loader import load_prompt_template, render_prompt


TEMPLATE_DIR = Path('backend/prompt_templates')


def test_prompt_templates_exist_and_include_concise_guardrails():
    required = [
        TEMPLATE_DIR / 'followup_question.md',
        TEMPLATE_DIR / 'final_summary.md',
        TEMPLATE_DIR / 'debrief_instructions.md',
    ]

    for path in required:
        assert path.exists(), f'missing template: {path}'

    followup = load_prompt_template('followup_question')
    assert 'under 12 words' in followup.lower()
    assert 'one concise follow-up question' in followup.lower()

    final_summary = load_prompt_template('final_summary')
    for section in [
        'Executive summary:',
        'What changed:',
        'Decisions:',
        'Action items:',
        'Risks / blockers:',
        'Open questions:',
        'Follow-ups:',
    ]:
        assert section in final_summary


def test_render_prompt_injects_context_values():
    rendered = render_prompt('followup_question', transcript_text='Need owner for Friday follow-up')
    assert 'Need owner for Friday follow-up' in rendered


def test_load_prompt_template_unknown_raises():
    with pytest.raises(FileNotFoundError):
        load_prompt_template('not_a_real_template')
