from __future__ import annotations

import argparse
import getpass
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.core.config import BASE_DIR
from app.db import SessionLocal
from app.models import DeviceAccount, DeviceType
from app.tools.coros.automation import RealCorosAutomationClient
from app.tools.coros.credentials import decrypt_secret


OUT_DIR = BASE_DIR / "var" / "coros_real_sync"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a real COROS full-history fetch and write fetched JSON under var/coros_real_sync/."
    )
    parser.add_argument("--athlete-id", type=int, default=1)
    parser.add_argument("--username", default="")
    parser.add_argument("--prompt-password", action="store_true")
    parser.add_argument("--max-events", type=int, default=200)
    args = parser.parse_args()

    username = args.username.strip()
    password = ""
    credential_source = "prompt"

    if not username:
        loaded = _load_db_credentials(args.athlete_id)
        if loaded is not None:
            username, password = loaded
            credential_source = "encrypted_db"

    if not username:
        username = input("COROS username: ").strip()
    if not password:
        if not args.prompt_password:
            print("Password is not stored in .env. Prompting without echo.")
        password = getpass.getpass("COROS password: ")

    if not username or not password:
        print("Missing COROS username or password.")
        return 2

    events: list[dict] = []

    def progress(**event: object) -> None:
        safe_event = {key: value for key, value in event.items() if key != "password"}
        events.append(safe_event)
        if len(events) <= args.max_events:
            print(f"[{safe_event.get('level', 'info')}] {safe_event.get('phase')}: {safe_event.get('message')}")

    client = RealCorosAutomationClient()
    login = client.login(username, password)
    if not login.ok:
        print(f"Login failed: {login.message}")
        return 3

    history = client.fetch_full_history(username, progress=progress)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUT_DIR / f"full-fetch-{args.athlete_id}-{timestamp}.json"
    summary = _summarize(history)
    payload = {
        "timestamp": timestamp,
        "athlete_id": args.athlete_id,
        "credential_source": credential_source,
        "api_host": client._api_host,
        "summary": summary,
        "events": events[: args.max_events],
        "history": history,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("")
    print(f"Wrote: {output_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _load_db_credentials(athlete_id: int) -> tuple[str, str] | None:
    with SessionLocal() as db:
        account = db.execute(
            select(DeviceAccount)
            .where(
                DeviceAccount.athlete_id == athlete_id,
                DeviceAccount.device_type == DeviceType.COROS,
            )
            .order_by(DeviceAccount.id.desc())
            .limit(1)
        ).scalars().first()
        if account is None or not account.username or not account.encrypted_password:
            return None
        return account.username, decrypt_secret(account.encrypted_password)


def _summarize(history: dict) -> dict:
    activities = history.get("activities", [])
    raw_records = history.get("raw_records", [])
    metrics = history.get("metrics", [])
    sport_counts: dict[str, int] = {}
    raw_counts: dict[str, int] = {}
    for activity in activities:
        sport = str(activity.get("sport") or "unknown")
        sport_counts[sport] = sport_counts.get(sport, 0) + 1
    for record in raw_records:
        record_type = str(record.get("record_type") or "unknown")
        raw_counts[record_type] = raw_counts.get(record_type, 0) + 1
    first_started = min((str(a.get("started_at")) for a in activities if a.get("started_at")), default=None)
    last_started = max((str(a.get("started_at")) for a in activities if a.get("started_at")), default=None)
    return {
        "activity_count": len(activities),
        "metric_count": len(metrics),
        "raw_record_count": len(raw_records),
        "failed_count": int(history.get("stats", {}).get("failed_count", 0) or 0),
        "sport_counts": sport_counts,
        "raw_record_counts": raw_counts,
        "first_activity_started_at": first_started,
        "last_activity_started_at": last_started,
        "sample_activity_ids": [a.get("provider_activity_id") for a in activities[:10]],
        "sample_raw_record_ids": [r.get("provider_record_id") for r in raw_records[:10]],
    }


if __name__ == "__main__":
    raise SystemExit(main())
