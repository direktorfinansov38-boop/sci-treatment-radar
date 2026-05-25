from datetime import datetime

from jinja2 import Template

from .models import Finding


DIGEST_TEMPLATE = Template(
    """# Дайджест SCI Treatment Radar за {{ date }}

{% if ai_brief -%}
{{ ai_brief }}

---
{% endif -%}

## Источники

{% if not findings -%}
Новых материалов, которые еще не участвовали в рассылке, за выбранный период не найдено.
{% endif -%}

{% for item in findings -%}
### {{ loop.index }}. {{ item.title }}

- Источник: {{ item.source }}
- Дата: {{ item.published_at.date().isoformat() if item.published_at else "не указана" }}
- Регион: {{ item.region or "глобально" }}
- Приоритет: {{ item.score }}
{% if item.tags -%}
- Теги: {{ ", ".join(item.tags[:8]) }}
{% endif -%}
{% if item.summary -%}
- Кратко: {{ item.summary }}
{% endif -%}
- Ссылка: {{ item.url }}

{% endfor -%}
"""
)


def render_digest(findings: list[Finding], ai_brief: str | None) -> str:
    return DIGEST_TEMPLATE.render(
        date=datetime.now().date().isoformat(),
        findings=findings,
        ai_brief=ai_brief,
    )
