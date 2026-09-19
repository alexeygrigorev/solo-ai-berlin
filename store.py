"""Application and payment storage. SQLite locally; DynamoDB in AWS."""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT / "private-data" / "applications.sqlite3")))
TABLE = os.getenv("DYNAMODB_TABLE", "")


def using_dynamo() -> bool:
    return bool(TABLE)


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def initialise_database() -> None:
    if using_dynamo():
        return
    with closing(connect()) as con, con:
        con.executescript(
            """
        CREATE TABLE IF NOT EXISTS applications (
          id TEXT PRIMARY KEY, submission_key TEXT UNIQUE NOT NULL,
          payload_hash TEXT NOT NULL, created_at INTEGER NOT NULL,
          answers TEXT NOT NULL, terms_version TEXT NOT NULL,
          decision TEXT NOT NULL DEFAULT 'pending'
        );
        CREATE TABLE IF NOT EXISTS payments (
          session_id TEXT PRIMARY KEY, application_id TEXT,
          payment_intent TEXT, payment_status TEXT NOT NULL,
          amount INTEGER, currency TEXT, received_at INTEGER NOT NULL,
          flag TEXT NOT NULL DEFAULT '',
          FOREIGN KEY(application_id) REFERENCES applications(id)
        );
        CREATE TABLE IF NOT EXISTS stripe_events (
          event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL,
          received_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS rate_limits (
          key TEXT NOT NULL, received_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_rate_key ON rate_limits(key, received_at);
        """
        )
    try:
        DB_PATH.chmod(0o600)
    except OSError:
        pass


def _ddb():
    import boto3

    return boto3.resource("dynamodb").Table(TABLE)


def rate_limit(key: str, now: int, maximum: int = 12, window: int = 900) -> bool:
    """Return True if the request should be rejected."""
    if using_dynamo():
        table = _ddb()
        cutoff = now - window
        resp = table.query(
            KeyConditionExpression="pk = :pk AND sk > :sk",
            ExpressionAttributeValues={":pk": f"RL#{key}", ":sk": f"TS#{cutoff:010d}"},
        )
        if len(resp.get("Items", [])) >= maximum:
            return True
        table.put_item(
            Item={"pk": f"RL#{key}", "sk": f"TS#{now:010d}", "ttl": now + window}
        )
        return False
    with closing(connect()) as con, con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM rate_limits WHERE received_at < ?", (now - window,))
        count = con.execute("SELECT COUNT(*) FROM rate_limits WHERE key=?", (key,)).fetchone()[0]
        if count >= maximum:
            return True
        con.execute("INSERT INTO rate_limits VALUES (?, ?)", (key, now))
        return False


def get_application_by_submission(submission_key: str) -> dict | None:
    if using_dynamo():
        item = _ddb().get_item(Key={"pk": f"SUB#{submission_key}", "sk": "META"}).get("Item")
        if not item:
            return None
        app = _ddb().get_item(Key={"pk": f"APP#{item['application_id']}", "sk": "META"}).get("Item")
        if not app:
            return None
        return {"id": app["id"], "payload_hash": app["payload_hash"]}
    with closing(connect()) as con:
        row = con.execute(
            "SELECT id,payload_hash FROM applications WHERE submission_key=?", (submission_key,)
        ).fetchone()
        return dict(row) if row else None


def insert_application(application_id: str, submission_key: str, digest: str, created_at: int, payload: str, terms_version: str) -> None:
    if using_dynamo():
        table = _ddb()
        table.put_item(
            Item={
                "pk": f"APP#{application_id}",
                "sk": "META",
                "id": application_id,
                "submission_key": submission_key,
                "payload_hash": digest,
                "created_at": created_at,
                "answers": payload,
                "terms_version": terms_version,
                "decision": "pending",
            }
        )
        table.put_item(
            Item={
                "pk": f"SUB#{submission_key}",
                "sk": "META",
                "application_id": application_id,
            }
        )
        return
    with closing(connect()) as con, con:
        con.execute(
            "INSERT INTO applications (id,submission_key,payload_hash,created_at,answers,terms_version) VALUES (?,?,?,?,?,?)",
            (application_id, submission_key, digest, created_at, payload, terms_version),
        )


def get_application(application_id: str) -> dict | None:
    if using_dynamo():
        item = _ddb().get_item(Key={"pk": f"APP#{application_id}", "sk": "META"}).get("Item")
        return {"id": item["id"]} if item else None
    with closing(connect()) as con:
        row = con.execute("SELECT id FROM applications WHERE id=?", (application_id,)).fetchone()
        return dict(row) if row else None


def event_seen(event_id: str) -> bool:
    if using_dynamo():
        return bool(_ddb().get_item(Key={"pk": f"EVT#{event_id}", "sk": "META"}).get("Item"))
    with closing(connect()) as con:
        return bool(con.execute("SELECT 1 FROM stripe_events WHERE event_id=?", (event_id,)).fetchone())


def mark_event(event_id: str, kind: str, now: int) -> None:
    if using_dynamo():
        _ddb().put_item(Item={"pk": f"EVT#{event_id}", "sk": "META", "event_type": kind, "received_at": now})
        return
    with closing(connect()) as con, con:
        con.execute("INSERT INTO stripe_events VALUES (?,?,?)", (event_id, kind, now))


def previous_payment_status(session_id: str) -> str | None:
    if using_dynamo():
        item = _ddb().get_item(Key={"pk": f"PAY#{session_id}", "sk": "META"}).get("Item")
        return item.get("payment_status") if item else None
    with closing(connect()) as con:
        row = con.execute("SELECT payment_status FROM payments WHERE session_id=?", (session_id,)).fetchone()
        return row["payment_status"] if row else None


def has_other_paid(application_id: str, session_id: str) -> bool:
    if using_dynamo():
        resp = _ddb().query(
            IndexName="ApplicationIndex",
            KeyConditionExpression="application_id = :id",
            ExpressionAttributeValues={":id": application_id},
        )
        return any(
            item.get("payment_status") == "paid" and item.get("session_id") != session_id
            for item in resp.get("Items", [])
        )
    with closing(connect()) as con:
        return bool(
            con.execute(
                "SELECT 1 FROM payments WHERE application_id=? AND session_id<>? AND payment_status='paid'",
                (application_id, session_id),
            ).fetchone()
        )


def upsert_payment(session_id, application_id, intent, status, amount, currency, now, flag) -> None:
    if using_dynamo():
        item = {
            "pk": f"PAY#{session_id}",
            "sk": "META",
            "session_id": session_id,
            "application_id": application_id or "",
            "payment_intent": intent or "",
            "payment_status": status,
            "amount": amount if amount is not None else 0,
            "currency": currency or "",
            "received_at": now,
            "flag": flag,
        }
        _ddb().put_item(Item=item)
        return
    with closing(connect()) as con, con:
        con.execute(
            """INSERT INTO payments VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(session_id) DO UPDATE SET
               payment_status=excluded.payment_status,flag=excluded.flag""",
            (session_id, application_id, intent, status, amount, currency, now, flag),
        )


def record_ignored_event(event_id: str, kind: str, now: int) -> None:
    mark_event(event_id, kind, now)


def list_applications() -> list[dict]:
    if using_dynamo():
        # Small-pilot scan; not a public endpoint.
        items = []
        scan_kwargs = {"FilterExpression": "begins_with(pk, :p) AND sk = :sk", "ExpressionAttributeValues": {":p": "APP#", ":sk": "META"}}
        table = _ddb()
        resp = table.scan(**scan_kwargs)
        items.extend(resp.get("Items", []))
        while "LastEvaluatedKey" in resp:
            resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"], **scan_kwargs)
            items.extend(resp.get("Items", []))
        rows = []
        for item in sorted(items, key=lambda i: int(i.get("created_at", 0))):
            row = {
                "id": item["id"],
                "created_at": int(item["created_at"]),
                "answers": item["answers"],
                "terms_version": item["terms_version"],
                "decision": item.get("decision", "pending"),
            }
            pay = table.query(
                IndexName="ApplicationIndex",
                KeyConditionExpression="application_id = :id",
                ExpressionAttributeValues={":id": item["id"]},
            )
            row["payments"] = [
                {k: p.get(k) for k in ("session_id", "payment_status", "amount", "currency", "flag", "payment_intent")}
                for p in pay.get("Items", [])
            ]
            rows.append(row)
        return rows
    with closing(connect()) as con:
        applications = con.execute("SELECT * FROM applications ORDER BY created_at").fetchall()
        rows = []
        for raw in applications:
            item = dict(raw)
            item.pop("submission_key", None)
            item.pop("payload_hash", None)
            item["answers"] = json.loads(item["answers"])
            item["payments"] = [dict(p) for p in con.execute("SELECT * FROM payments WHERE application_id=?", (item["id"],))]
            rows.append(item)
        return rows


def payment_counts() -> tuple[int, int]:
    if using_dynamo():
        paid = flagged = 0
        table = _ddb()
        scan_kwargs = {"FilterExpression": "begins_with(pk, :p) AND sk = :sk", "ExpressionAttributeValues": {":p": "PAY#", ":sk": "META"}}
        resp = table.scan(**scan_kwargs)
        items = resp.get("Items", [])
        while "LastEvaluatedKey" in resp:
            resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"], **scan_kwargs)
            items.extend(resp.get("Items", []))
        for item in items:
            if item.get("payment_status") == "paid":
                paid += 1
            if item.get("flag") or item.get("payment_status") == "needs_review":
                flagged += 1
        return paid, flagged
    with closing(connect()) as con:
        paid = con.execute("SELECT COUNT(*) FROM payments WHERE payment_status='paid'").fetchone()[0]
        flagged = con.execute("SELECT COUNT(*) FROM payments WHERE flag<>'' OR payment_status='needs_review'").fetchone()[0]
        return paid, flagged
