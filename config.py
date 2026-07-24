import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError as exc:
            raise RuntimeError(f"Invalid ADMIN_IDS value: {part!r}") from exc
    return ids


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    database_path: str

    @classmethod
    def from_env(cls) -> "Config":
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError("BOT_TOKEN is missing. Add it in Railway Variables.")

        admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
        if not admin_ids:
            raise RuntimeError("ADMIN_IDS is missing. Add your Telegram numeric user ID.")

        db_path = os.getenv("DATABASE_PATH", "data/india_business_wallet.db").strip()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        return cls(bot_token=token, admin_ids=admin_ids, database_path=db_path)
