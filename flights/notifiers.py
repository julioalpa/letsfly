"""Canales de aviso. Hoy: Telegram (gratis) o consola si no hay credenciales."""
import requests
from django.conf import settings


class NotificationError(Exception):
    pass


class ConsoleNotifier:
    def send(self, text):
        print(text)


class TelegramNotifier:
    def __init__(self, token, chat_id, session=None, timeout=15):
        self.token = token
        self.chat_id = chat_id
        self.session = session or requests.Session()
        self.timeout = timeout

    def send(self, text):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            resp = self.session.post(
                url,
                json={"chat_id": self.chat_id, "text": text, "disable_web_page_preview": True},
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            raise NotificationError(f"Error de red con Telegram: {exc}") from exc
        if resp.status_code != 200:
            raise NotificationError(f"Telegram respondió {resp.status_code}: {resp.text[:200]}")


def get_notifier():
    if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
        return TelegramNotifier(settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID)
    return ConsoleNotifier()
