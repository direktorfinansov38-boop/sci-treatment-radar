from datetime import datetime
from html import escape

from .models import Finding

_SOURCE_EMOJI = {
    "PubMed": "🔬",
    "ClinicalTrials.gov": "🏥",
    "Google News": "📰",
    "Яндекс Новости": "🇷🇺",
}

MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def format_article_caption(finding: Finding) -> str:
    """Single-article caption for Telegram photo message."""
    emoji = _SOURCE_EMOJI.get(finding.source, "📄")
    title = escape(finding.russian_title or finding.title)
    link = escape(finding.short_url or finding.url, quote=True)

    if finding.published_at:
        d = finding.published_at
        date_str = f"{d.day} {MONTHS_RU[d.month]} {d.year}"
    else:
        date_str = "дата не указана"

    region_tag = ""
    if finding.region:
        flags = {"Russia": "🇷🇺", "China": "🇨🇳", "Israel": "🇮🇱", "United States": "🇺🇸"}
        flag = flags.get(finding.region, "🌍")
        region_tag = f" {flag}"

    return (
        f"{emoji}{region_tag} <b>{title}</b>\n\n"
        f"📅 {date_str} · {escape(finding.source)}\n"
        f'🔗 <a href="{link}">{link}</a>'
    )


REGION_NAMES = {
    "Russia": "Россия",
    "China": "Китай",
    "Israel": "Израиль",
    "United States": "США",
}


def _region_name(region: str | None) -> str:
    return REGION_NAMES.get(region or "", region or "мир")


def _topic_title(item: Finding) -> str:
    text = f"{item.title} {item.summary} {' '.join(item.tags)}".lower()
    region = _region_name(item.region)

    if any(word in text for word in ["stem cell", "cell therapy", "msc", "nsc", "ipsc", "клеточ", "стволов", "трансплантац", "экзосом", "мезенхим", "матриселф", "нейромат"]):
        return f"Клеточная терапия и стволовые клетки: {region}"
    if any(word in text for word in ["clinical trial", "phase", "клиничес", "испытани"]):
        return f"Клинические испытания по травме спинного мозга: {region}"
    if any(word in text for word in ["neurostimulation", "epidural stimulation", "нейростим", "электростимул", "эпидуральн"]):
        return f"Нейростимуляция при травме спинного мозга: {region}"
    if any(word in text for word in ["exoskeleton", "robot", "экзоскелет", "реабилитац"]):
        return f"Реабилитационные технологии и аппараты: {region}"
    if any(word in text for word in ["implant", "device", "fda", "аппарат", "имплант"]):
        return f"Новые устройства и импланты: {region}"
    return f"Новая разработка по лечению травмы спинного мозга: {region}"


def _brief(item: Finding) -> str:
    text = f"{item.title} {item.summary} {' '.join(item.tags)}".lower()
    region = _region_name(item.region)
    source = escape(item.source)
    date = item.published_at.date().isoformat() if item.published_at else "дата не указана"

    parts = [
        f"Появился новый материал по теме лечения травмы спинного мозга. Региональный фокус: {escape(region)}; источник: {source}; дата: {date}.",
    ]

    if any(word in text for word in ["stem cell", "cell therapy", "msc", "nsc", "ipsc", "exosome", "клеточ", "стволов", "трансплантац", "экзосом", "мезенхим", "матриселф", "нейромат"]):
        parts.append(
            "Главный интерес — клеточная терапия, стволовые клетки, экзосомы или смежные регенеративные подходы. Это важно для отслеживания направлений, где могут появляться новые клинические протоколы, патенты, инвестиции и медицинские технологии."
        )
    elif any(word in text for word in ["clinical trial", "phase", "клиничес"]):
        parts.append(
            "Материал связан с клиническими испытаниями или обновлением исследовательской повестки. Такие новости важны, потому что они показывают, какие методы переходят от лабораторных данных к проверке на пациентах."
        )
    elif any(word in text for word in ["neurostimulation", "epidural stimulation", "bci", "нейростим"]):
        parts.append(
            "Фокус — нейротехнологии, стимуляция или нейроинтерфейсы. Для рынка это может означать рост интереса к имплантам, аппаратной реабилитации и высокотехнологичным медицинским устройствам."
        )
    else:
        parts.append(
            "Новость стоит включить в мониторинг как часть общей картины по технологиям восстановления, реабилитации и лечению последствий травмы спинного мозга."
        )

    if item.tags:
        readable_tags = ", ".join(escape(tag) for tag in item.tags[:5])
        parts.append(f"Ключевые темы: {readable_tags}.")

    return " ".join(parts)


def _perspective(item: Finding) -> str:
    text = f"{item.title} {item.summary} {' '.join(item.tags)}".lower()

    if any(word in text for word in ["clinical trial", "phase 2", "phase 3", "fda", "breakthrough device"]):
        return (
            "Перспективность: высокая. Материал связан с клинической проверкой, регуляторным статусом или приближением технологии к практическому применению; такие разработки стоит отслеживать в первую очередь."
        )
    if any(word in text for word in ["first-in-human", "phase 1", "implant", "neurostimulation", "epidural stimulation", "bci"]):
        return (
            "Перспективность: выше средней. Технология выглядит значимой, но, скорее всего, еще требует клинического подтверждения, настройки протоколов и оценки безопасности для широкого применения."
        )
    if any(word in text for word in ["stem cell", "cell therapy", "cell transplantation", "exosome", "ipsc", "mesenchymal", "neural stem", "стволов", "клеточн", "трансплантац", "экзосом", "мезенхим", "нейральн", "матриселф", "нейромат"]):
        return (
            "Перспективность: осторожно высокая. Клеточные и регенеративные подходы потенциально важны для восстановления тканей и функций, но практическая польза зависит от стадии испытаний, безопасности и воспроизводимости результата."
        )
    if any(word in text for word in ["robot", "exoskeleton", "rehabilitation", "gait"]):
        return (
            "Перспективность: практическая. Такие технологии чаще всего ближе к реабилитационному применению, но их влияние зависит от доступности, стоимости и доказанного улучшения самостоятельности пациента."
        )
    return (
        "Перспективность: требует наблюдения. Материал релевантен теме восстановления после травмы спинного мозга, но для оценки реальной пользы нужны дополнительные данные о стадии разработки и результатах."
    )


def _item_block(index: int, item: Finding) -> str:
    title = escape(_topic_title(item))
    brief = _brief(item)
    perspective = escape(_perspective(item))
    url = escape(item.url, quote=True)

    return (
        f"<b>{index}. {title}</b>\n\n"
        f"{brief}\n\n"
        f"{perspective}\n\n"
        f"Источник: <a href=\"{url}\">открыть материал</a>"
    )


def render_digest(findings: list[Finding], ai_brief: str | None) -> str:
    date = datetime.now().date().isoformat()
    header = (
        f"<b>SCI Treatment Radar — сводка за {date}</b>\n\n"
        "Главное: свежие материалы по лечению травмы спинного мозга, стволовым клеткам, клеточной терапии, нейротехнологиям, аппаратам и клиническим испытаниям."
    )

    if not findings:
        return (
            f"{header}\n\n"
            "Новых материалов, которые еще не участвовали в рассылке, за выбранный период не найдено."
        )

    blocks = [header]
    if ai_brief:
        blocks.append(escape(ai_brief))
    blocks.extend(_item_block(index, item) for index, item in enumerate(findings, start=1))
    return "\n\n━━━━━━━━━━━━\n\n".join(blocks)
