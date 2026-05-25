# SCI Treatment Radar

AI-агент для ежедневной утренней подборки новостей, научных публикаций, клинических испытаний и технологических разработок по лечению травмы спинного мозга.

Приоритеты мониторинга:

- Россия
- Китай
- Израиль
- США
- новые технологии, аппараты, нейростимуляция, нейроинтерфейсы, регенеративная медицина, клеточная терапия, экзоскелеты, реабилитационные роботы, клинические испытания
- отдельный фокус: стволовые клетки и клеточная терапия при травме спинного мозга, включая MSC, NSC, iPSC, клеточную трансплантацию, экзосомы, шванновские клетки и olfactory ensheathing cells

## Что делает агент

Каждый день в 10:00 агент:

1. Забирает свежие материалы из PubMed, ClinicalTrials.gov и новостных RSS-поисков.
2. Отбирает публикации за последние дни.
3. Убирает дубли.
4. Проверяет историю отправленных материалов и не повторяет новости, которые уже были в рассылке.
5. Присваивает приоритет по странам и ключевым темам.
6. Формирует русскоязычный дайджест.
7. Отправляет его в Telegram, email, webhook или сохраняет Markdown-файл.

## Быстрый старт локально

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Заполните `.env`, затем выполните разовый запуск:

```powershell
python -m spinal_digest_agent run-once
```

Запуск постоянного расписания на сервере:

```powershell
python -m spinal_digest_agent serve
```

## GitHub Actions

В репозитории уже есть workflow `.github/workflows/daily-digest.yml`.

Он запускается каждый день в 10:00 по Улан-Батору, то есть в 02:00 UTC. Если нужен другой часовой пояс, поменяйте cron в workflow.

Для отправки через Telegram добавьте в GitHub Secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `OPENAI_API_KEY` опционально, если хотите AI-сводку

## Переменные окружения

Смотрите `.env.example`.

Минимально полезная конфигурация:

```env
DIGEST_TIMEZONE=Asia/Ulaanbaatar
DIGEST_HOUR=10
DIGEST_LOOKBACK_DAYS=3
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
STATE_PATH=state/sent_history.json
```

Файл `state/sent_history.json` хранит уже отправленные ссылки и заголовки. На сервере эту папку нужно сохранять между запусками. В GitHub Actions для нее настроен cache.

## Деплой на сервер

1. Создайте GitHub-репозиторий и загрузите туда этот проект.
2. На сервере установите Python 3.11+.
3. Склонируйте репозиторий.
4. Создайте `.env`.
5. Запустите `python -m spinal_digest_agent serve` через `systemd`, Docker или любой process manager.

Пример systemd unit:

```ini
[Unit]
Description=SCI Treatment Radar
After=network.target

[Service]
WorkingDirectory=/opt/sci-treatment-radar
EnvironmentFile=/opt/sci-treatment-radar/.env
ExecStart=/opt/sci-treatment-radar/.venv/bin/python -m spinal_digest_agent serve
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Как расширять источники

Основные запросы лежат в `config/queries.json`.

Добавляйте туда новые темы, страны, организации, клиники и названия технологий. Агент автоматически начнет включать их в мониторинг.
