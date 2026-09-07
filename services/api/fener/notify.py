"""Telegram delivery for watchlist notifications.

Fixed provider endpoint, no redirects, no automatic retries: a failed send
raises and the worker keeps its watermark, so the next pass redelivers.
"""

import httpx

TELEGRAM_SEND = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MESSAGE_CHARS = 3800


class TelegramError(RuntimeError):
    """Raised when Telegram could not accept the message."""


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    if not token or not chat_id:
        raise TelegramError("telegram_not_configured")
    # The bot token is part of the fixed endpoint path by Telegram API design.
    # It must never be logged or included in error messages.
    try:
        response = httpx.post(
            TELEGRAM_SEND.format(token=token),
            json={"chat_id": chat_id, "text": text[:MAX_MESSAGE_CHARS]},
            timeout=httpx.Timeout(15, connect=5),
            follow_redirects=False,
        )
    except httpx.HTTPError as error:
        raise TelegramError("telegram_unreachable") from error
    if response.status_code != 200:
        raise TelegramError(f"telegram_http_{response.status_code}")
