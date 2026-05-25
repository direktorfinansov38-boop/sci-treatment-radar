"""
Автоматическая настройка sci-treatment-radar.

Запуск:
    python setup.py

Что делает:
  1. Спрашивает Anthropic API key и Telegram bot token
  2. Автоматически получает chat_id (достаточно написать боту /start)
  3. Прописывает все три секрета в GitHub Actions через API
  4. Запускает workflow вручную, чтобы сразу пришёл первый дайджест
"""

import base64
import getpass
import json
import subprocess
import sys
import time
import urllib.request
from urllib.error import HTTPError


REPO = "direktorfinansov38-boop/sci-treatment-radar"


# ── helpers ──────────────────────────────────────────────────────────────────

def _ask(prompt: str, secret: bool = False) -> str:
    while True:
        value = (getpass.getpass if secret else input)(prompt).strip()
        if value:
            return value
        print("  Нельзя оставлять пустым, попробуй ещё раз.")


def _api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    url = f"https://api.github.com{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def _tg(token: str, method: str, **params) -> dict:
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = json.dumps(params).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def _encrypt_secret(pub_key_b64: str, secret_value: str) -> str:
    """Encrypt secret with repo public key using PyNaCl (libsodium)."""
    try:
        from nacl.encoding import Base64Encoder
        from nacl.public import PublicKey, SealedBox
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyNaCl", "-q"])
        from nacl.encoding import Base64Encoder
        from nacl.public import PublicKey, SealedBox

    pub_key = PublicKey(pub_key_b64.encode(), Base64Encoder)
    box = SealedBox(pub_key)
    encrypted = box.encrypt(secret_value.encode())
    return base64.b64encode(encrypted).decode()


def _set_secret(repo: str, name: str, value: str, gh_token: str) -> None:
    key_info = _api("GET", f"/repos/{repo}/actions/secrets/public-key", gh_token)
    encrypted = _encrypt_secret(key_info["key"], value)
    _api(
        "PUT",
        f"/repos/{repo}/actions/secrets/{name}",
        gh_token,
        {"encrypted_value": encrypted, "key_id": key_info["key_id"]},
    )
    print(f"  ✓ GitHub secret {name!r} установлен")


def _get_chat_id(bot_token: str) -> str:
    print("\nПолучаю chat_id автоматически...")
    print("  → Открой Telegram и напиши своему боту команду /start")
    print("  → Жду 60 секунд...", end="", flush=True)
    deadline = time.time() + 60
    while time.time() < deadline:
        time.sleep(3)
        print(".", end="", flush=True)
        try:
            upd = _tg(bot_token, "getUpdates", limit=5, timeout=2)
            for update in upd.get("result", []):
                msg = update.get("message") or update.get("channel_post")
                if msg:
                    chat_id = str(msg["chat"]["id"])
                    chat_name = msg["chat"].get("title") or msg["chat"].get("username") or chat_id
                    print(f"\n  ✓ chat_id = {chat_id!r}  (чат: {chat_name})")
                    return chat_id
        except Exception:
            pass
    print()
    return _ask("  Не удалось получить автоматически. Введи chat_id вручную: ")


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  Настройка SCI Treatment Radar")
    print("=" * 60)

    # 1. Anthropic API key
    print("\n[1/3] Anthropic API key")
    print("  Получить на: https://console.anthropic.com/settings/keys")
    anthropic_key = _ask("  Вставь ключ (sk-ant-...): ", secret=True)

    # 2. Telegram bot token
    print("\n[2/3] Telegram bot token")
    print("  Создать бота: напиши @BotFather → /newbot")
    bot_token = _ask("  Вставь токен (1234:AAAA...): ", secret=True)

    # 3. Auto-detect chat_id
    chat_id = _get_chat_id(bot_token)

    # 4. GitHub token
    print("\n[4/4] GitHub Personal Access Token")
    print("  Нужен токен с правом 'repo' для записи секретов.")
    print("  Создать: https://github.com/settings/tokens/new?scopes=repo")
    gh_token = _ask("  Вставь токен (ghp_...): ", secret=True)

    # 5. Set secrets
    print("\nПрописываю секреты в GitHub Actions...")
    try:
        _set_secret(REPO, "ANTHROPIC_API_KEY", anthropic_key, gh_token)
        _set_secret(REPO, "TELEGRAM_BOT_TOKEN", bot_token, gh_token)
        _set_secret(REPO, "TELEGRAM_CHAT_ID", chat_id, gh_token)
    except HTTPError as exc:
        print(f"\nОшибка GitHub API: {exc.code} {exc.reason}")
        print("Проверь что токен имеет scope 'repo' и ты владелец репозитория.")
        sys.exit(1)

    # 6. Trigger workflow
    print("\nЗапускаю workflow вручную — первый дайджест придёт через ~2 минуты...")
    try:
        _api(
            "POST",
            f"/repos/{REPO}/actions/workflows/daily-digest.yml/dispatches",
            gh_token,
            {"ref": "main"},
        )
        print("  ✓ Workflow запущен")
    except HTTPError as exc:
        print(f"  Не удалось запустить workflow: {exc.code} — запусти вручную на GitHub.")

    print("\n✅ Готово! Бот будет присылать дайджест каждый день в 10:00.")


if __name__ == "__main__":
    main()
