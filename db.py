"""SQLite storage. Flights older than RETENTION_DAYS are deleted by cleanup()."""
from datetime import datetime, timedelta, timezone

import aiosqlite

import fields as F

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS users (
    tg_id      INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,          -- '' until the user sends a name
    created_at TEXT NOT NULL,
    lang       TEXT NOT NULL DEFAULT 'en'
);
CREATE TABLE IF NOT EXISTS flights (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id   INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    {", ".join(f"{k} TEXT" for k in F.HEADER)},
    remarks    TEXT
);
CREATE INDEX IF NOT EXISTS idx_flights_owner ON flights(owner_id, id);
CREATE TABLE IF NOT EXISTS checks (
    flight_id INTEGER NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
    item      TEXT NOT NULL,
    value     TEXT NOT NULL,
    PRIMARY KEY (flight_id, item)
);
CREATE TABLE IF NOT EXISTS times (
    flight_id INTEGER NOT NULL REFERENCES flights(id) ON DELETE CASCADE,
    event     TEXT NOT NULL,
    t1        TEXT,
    t2        TEXT,
    PRIMARY KEY (flight_id, event)
);
"""

EDITABLE = set(F.HEADER) | {"remarks"}


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("PRAGMA foreign_keys=ON")
        await self.conn.executescript(SCHEMA)
        # Upgrade databases created by older versions of the bot.
        async with self.conn.execute("PRAGMA table_info(users)") as cur:
            columns = {r["name"] for r in await cur.fetchall()}
        if "lang" not in columns:
            await self.conn.execute("ALTER TABLE users ADD COLUMN lang TEXT NOT NULL DEFAULT 'en'")
        # Header fields added to fields.HEADER later (e.g. bag_in/bag_out) become new columns.
        async with self.conn.execute("PRAGMA table_info(flights)") as cur:
            columns = {r["name"] for r in await cur.fetchall()}
        for key in F.HEADER:
            if key not in columns:
                await self.conn.execute(f"ALTER TABLE flights ADD COLUMN {key} TEXT")
        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()

    # --- users
    async def get_user(self, tg_id: int) -> tuple[str | None, str]:
        """(name or None if not set yet, language code)."""
        async with self.conn.execute("SELECT name, lang FROM users WHERE tg_id=?", (tg_id,)) as cur:
            row = await cur.fetchone()
        if not row:
            return None, "en"
        return (row["name"] or None), row["lang"]

    async def get_user_name(self, tg_id: int) -> str | None:
        return (await self.get_user(tg_id))[0]

    async def set_lang(self, tg_id: int, lang: str):
        await self.conn.execute(
            "INSERT INTO users(tg_id, name, created_at, lang) VALUES(?, '', ?, ?) "
            "ON CONFLICT(tg_id) DO UPDATE SET lang=excluded.lang",
            (tg_id, _utcnow(), lang),
        )
        await self.conn.commit()

    async def set_user_name(self, tg_id: int, name: str):
        await self.conn.execute(
            "INSERT INTO users(tg_id, name, created_at) VALUES(?,?,?) "
            "ON CONFLICT(tg_id) DO UPDATE SET name=excluded.name",
            (tg_id, name, _utcnow()),
        )
        await self.conn.commit()

    # --- flights (every query is scoped to the owner)
    async def create_flight(self, owner_id: int, values: dict) -> int:
        cols = [k for k in values if k in F.HEADER]
        sql = (f"INSERT INTO flights(owner_id, created_at{''.join(', ' + c for c in cols)}) "
               f"VALUES(?, ?{', ?' * len(cols)})")
        cur = await self.conn.execute(sql, (owner_id, _utcnow(), *(values[c] for c in cols)))
        await self.conn.commit()
        return cur.lastrowid

    async def get_flight(self, flight_id: int, owner_id: int) -> dict | None:
        async with self.conn.execute(
            "SELECT * FROM flights WHERE id=? AND owner_id=?", (flight_id, owner_id)
        ) as cur:
            row = await cur.fetchone()
        return dict(row) if row else None

    async def list_flights(self, owner_id: int, limit: int = 20) -> list[dict]:
        async with self.conn.execute(
            "SELECT id, date, flight FROM flights WHERE owner_id=? ORDER BY id DESC LIMIT ?",
            (owner_id, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def recent_values(self, owner_id: int, key: str, limit: int = 4) -> list[str]:
        """Last distinct values the user typed for a field, for reply-keyboard suggestions."""
        if key not in F.HEADER:
            return []
        async with self.conn.execute(
            f"SELECT {key} AS v, MAX(id) AS m FROM flights WHERE owner_id=? AND {key} IS NOT NULL "
            f"GROUP BY {key} ORDER BY m DESC LIMIT ?",
            (owner_id, limit),
        ) as cur:
            return [r["v"] for r in await cur.fetchall()]

    async def set_field(self, flight_id: int, owner_id: int, key: str, value: str | None):
        if key not in EDITABLE:  # column names are never taken from user input
            raise ValueError(key)
        await self.conn.execute(
            f"UPDATE flights SET {key}=? WHERE id=? AND owner_id=?", (value, flight_id, owner_id)
        )
        await self.conn.commit()

    async def delete_flight(self, flight_id: int, owner_id: int):
        await self.conn.execute("DELETE FROM flights WHERE id=? AND owner_id=?", (flight_id, owner_id))
        await self.conn.commit()

    # --- checklist
    async def get_checks(self, flight_id: int) -> dict:
        async with self.conn.execute(
            "SELECT item, value FROM checks WHERE flight_id=?", (flight_id,)
        ) as cur:
            return {r["item"]: r["value"] for r in await cur.fetchall()}

    async def set_check(self, flight_id: int, item: str, value: str | None):
        if value is None:
            await self.conn.execute("DELETE FROM checks WHERE flight_id=? AND item=?", (flight_id, item))
        else:
            await self.conn.execute(
                "INSERT INTO checks(flight_id, item, value) VALUES(?,?,?) "
                "ON CONFLICT(flight_id, item) DO UPDATE SET value=excluded.value",
                (flight_id, item, value),
            )
        await self.conn.commit()

    async def set_checks(self, flight_id: int, values: dict):
        await self.conn.executemany(
            "INSERT INTO checks(flight_id, item, value) VALUES(?,?,?) "
            "ON CONFLICT(flight_id, item) DO UPDATE SET value=excluded.value",
            [(flight_id, k, v) for k, v in values.items()],
        )
        await self.conn.commit()

    # --- timeline
    async def get_times(self, flight_id: int) -> dict:
        async with self.conn.execute(
            "SELECT event, t1, t2 FROM times WHERE flight_id=?", (flight_id,)
        ) as cur:
            return {r["event"]: (r["t1"], r["t2"]) for r in await cur.fetchall()}

    async def set_time(self, flight_id: int, event: str, which: int, value: str | None):
        col = "t1" if which == 1 else "t2"
        await self.conn.execute(
            f"INSERT INTO times(flight_id, event, {col}) VALUES(?,?,?) "
            f"ON CONFLICT(flight_id, event) DO UPDATE SET {col}=excluded.{col}",
            (flight_id, event, value),
        )
        await self.conn.commit()

    async def clear_time(self, flight_id: int, event: str):
        await self.conn.execute("DELETE FROM times WHERE flight_id=? AND event=?", (flight_id, event))
        await self.conn.commit()

    # --- retention
    async def cleanup(self, days: int) -> int:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
        async with self.conn.execute("DELETE FROM flights WHERE created_at < ?", (cutoff,)) as cur:
            removed = cur.rowcount
        await self.conn.commit()
        if removed:  # give the freed space back to the disk
            async with self.conn.execute("VACUUM"):
                pass
            async with self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)"):
                pass
        return removed
