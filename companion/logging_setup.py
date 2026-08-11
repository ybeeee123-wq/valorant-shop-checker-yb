import logging
from logging.handlers import RotatingFileHandler

from paths import LOG_DIR, ensure_directories


class SecretFilter(logging.Filter):
    blocked = ("access_token", "entitlements_token", "Authorization", "device_token", "/api/webhooks/")

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if any(value.lower() in message.lower() for value in self.blocked):
            record.msg = "Sensitive diagnostic message redacted"
            record.args = ()
        return True


def configure_logging() -> None:
    ensure_directories()
    handler = RotatingFileHandler(LOG_DIR / "valshop.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.addFilter(SecretFilter())
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)
