import json
import sqlite3
import threading
from datetime import datetime, timezone

from paths import CACHE_DB, ensure_directories


class LocalStore:
    def __init__(self, path=str(CACHE_DB)) -> None:
        ensure_directories()
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self.connection.executescript("""
        create table if not exists cache (key text primary key, value text not null, updated_at text not null);
        create table if not exists wishlist (skin_uuid text primary key, payload text not null);
        create table if not exists history (rotation_key text primary key, payload text not null, fetched_at text not null);
        create table if not exists pending_sync (rotation_key text primary key, payload text not null, attempts integer not null default 0);
        create table if not exists notified (rotation_key text not null, skin_uuid text not null, channel text not null, primary key(rotation_key,skin_uuid,channel));
        """)
        self.connection.commit()

    def set_cache(self, key: str, value) -> None:
        with self.lock:
            self.connection.execute("insert or replace into cache values(?,?,?)", (key, json.dumps(value), datetime.now(timezone.utc).isoformat()))
            self.connection.commit()

    def get_cache(self, key: str, default=None):
        row = self.connection.execute("select value from cache where key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def set_wishlist(self, items: list[dict]) -> None:
        with self.lock:
            self.connection.execute("delete from wishlist")
            self.connection.executemany("insert into wishlist values(?,?)", [(item["skin_uuid"], json.dumps(item)) for item in items])
            self.connection.commit()

    def wishlist(self) -> list[dict]:
        return [json.loads(row["payload"]) for row in self.connection.execute("select payload from wishlist")]

    def add_wishlist(self, item: dict) -> None:
        with self.lock:
            self.connection.execute("insert or replace into wishlist values(?,?)", (item["skin_uuid"], json.dumps(item))); self.connection.commit()

    def remove_wishlist(self, skin_uuid: str) -> None:
        with self.lock:
            self.connection.execute("delete from wishlist where skin_uuid=?", (skin_uuid,)); self.connection.commit()

    def save_shop(self, payload: dict) -> None:
        key = payload["rotation_key"]
        self.set_cache("shop", payload)
        with self.lock:
            self.connection.execute("insert or replace into history values(?,?,?)", (key, json.dumps(payload), payload.get("fetched_at", datetime.now(timezone.utc).isoformat())))
            self.connection.execute("insert or replace into pending_sync(rotation_key,payload,attempts) values(?,?,coalesce((select attempts from pending_sync where rotation_key=?),0))", (key, json.dumps(payload), key))
            self.connection.commit()

    def history(self, limit: int = 30) -> list[dict]:
        rows = self.connection.execute("select payload from history order by fetched_at desc limit ?", (limit,)).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def pending(self) -> list[dict]:
        return [json.loads(row["payload"]) for row in self.connection.execute("select payload from pending_sync order by rowid")]

    def mark_uploaded(self, rotation_key: str) -> None:
        with self.lock:
            self.connection.execute("delete from pending_sync where rotation_key=?", (rotation_key,)); self.connection.commit()

    def should_notify(self, rotation_key: str, skin_uuid: str, channel: str = "desktop") -> bool:
        with self.lock:
            try:
                self.connection.execute("insert into notified values(?,?,?)", (rotation_key, skin_uuid, channel)); self.connection.commit(); return True
            except sqlite3.IntegrityError:
                return False
