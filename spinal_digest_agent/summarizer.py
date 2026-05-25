from openai import AsyncOpenAI

from .config import Settings
from .models import Finding


def _format_items(findings: list[Finding]) -> str:
    lines: list[str] = []
    for index, item in enumerate(findings, start=1):
        published = item.published_at.date().isoformat() if item.published_at else "date unknown"
        lines.append(
            f"{index}. {item.title}\n"
            f"   Source: {item.source}; Date: {published}; Region: {item.region or 'global'}\n"
            f"   Summary: {item.summary}\n"
            f"   URL: {item.url}"
        )
    return "\n".join(lines)


async def build_ai_brief(settings: Settings, findings: list[Finding]) -> str | None:
    if not settings.openai_api_key or not findings:
        return None

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a medical technology intelligence analyst. "
                    "Write in Russian. Be concise, evidence-based, and avoid medical advice. "
                    "Focus on spinal cord injury treatment trends, devices, trials, and regional relevance."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Сделай утренний дайджест по этим материалам. "
                    "Структура: 1) главное за утро, 2) Россия/Китай/Израиль/США, "
                    "3) технологии и аппараты, 4) что стоит отслеживать дальше. "
                    "Не выдумывай факты, используй только список ниже.\n\n"
                    f"{_format_items(findings)}"
                ),
            },
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content

