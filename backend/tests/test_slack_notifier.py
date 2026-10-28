from unittest.mock import MagicMock

from app import config
from app.services import slack_notifier

ALERT = {"title": "Fact F-001 changed", "priority": "High", "content_id": "LIV-01"}


def _set_settings(monkeypatch, token: str, channel: str) -> None:
    fake = config.Settings(
        DATABASE_URL="postgresql://x", JWT_SECRET="x",
        SLACK_BOT_TOKEN=token, SLACK_CHANNEL_ID=channel,
    )
    monkeypatch.setattr(slack_notifier, "get_settings", lambda: fake)


def test_no_token_returns_false_and_sends_nothing(monkeypatch):
    _set_settings(monkeypatch, token="", channel="")
    client = MagicMock()
    assert slack_notifier.notify_alert(ALERT, client=client) is False
    client.chat_postMessage.assert_not_called()


def test_token_posts_once_with_alert_title(monkeypatch):
    _set_settings(monkeypatch, token="xoxb-test", channel="C123")
    client = MagicMock()
    assert slack_notifier.notify_alert(ALERT, client=client) is True
    client.chat_postMessage.assert_called_once()
    kwargs = client.chat_postMessage.call_args.kwargs
    assert kwargs["channel"] == "C123"
    assert "Fact F-001 changed" in kwargs["text"]