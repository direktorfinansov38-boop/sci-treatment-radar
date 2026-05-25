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
                    "Write only in Russian. Be concise, evidence-based, and avoid medical advice. "
                    "Use a clean Telegram digest style. Do not paste raw URLs. "
                    "Focus on spinal cord injury treatment trends, stem cells, cell therapy, devices, trials, and regional relevance."
                    "Exclude general disability news, household products, pillows, mattresses, basic wheelchairs, charity, motivation, wellness, and anything unrelated to functional recovery after spinal cord injury."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Сделай краткую русскоязычную аналитическую сводку по этим материалам. "
                    "Формат: сначала самое важное, затем короткие выводы по технологиям, рынку, бизнесу и клиническим перспективам. "
                    "Пиши без воды, без длинных ссылок, без повторов и без неподтвержденных выводов. "
                    "Каждый смысловой блок должен быть удобен для Telegram-поста. "
                    "Все иностранные заголовки и описания передавай только по-русски. "
                    "Объясняй сложные технические термины простым языком. "
                    "Оставляй только разработки, которые прямо связаны с восстановлением функций после травмы спинного мозга. "
                    "Не выдумывай факты, используй только список ниже.\n\n"
                    f"{_format_items(findings)}"
                ),
            },
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content
