from __future__ import annotations

from pathlib import Path


class _DefaultDict(dict):
    def __missing__(self, key):
        return ''


TEMPLATE_DIR = Path(__file__).resolve().parent / 'prompt_templates'


def load_prompt_template(name: str) -> str:
    path = TEMPLATE_DIR / f'{name}.md'
    if not path.exists():
        raise FileNotFoundError(f'Prompt template not found: {path}')
    return path.read_text(encoding='utf-8')


def render_prompt(name: str, **context: str) -> str:
    template = load_prompt_template(name)
    return template.format_map(_DefaultDict(context))
