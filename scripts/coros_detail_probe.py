from __future__ import annotations

import argparse
import getpass
import json
import urllib.parse
import urllib.request
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import BASE_DIR
from app.db import SessionLocal
from app.models import DeviceAccount, DeviceType
from app.tools.coros.automation import RealCorosAutomationClient
from app.tools.coros.credentials import decrypt_secret


OUT_DIR = BASE_DIR / "var" / "coros_real_sync"


def main() -> int:
    parser = argparse.ArgumentParser(description="Try COROS activity detail request variants for one activity.")
    parser.add_argument("label_id")
    parser.add_argument("--athlete-id", type=int, default=1)
    parser.add_argument("--username", default="")
    parser.add_argument("--sport-type", type=int, default=None)
    parser.add_argument("--start-time", type=int, default=None)
    args = parser.parse_args()

    username, password = _credentials(args.athlete_id, args.username)
    client = RealCorosAutomationClient()
    login = client.login(username, password)
    if not login.ok:
        print(f"Login failed: {login.message}")
        return 3

    variants = _variants(args.label_id, sport_type=args.sport_type, start_time=args.start_time)
    results = []
    for variant in variants:
        try:
            response = _request(client, variant)
            results.append({**variant, "ok": response.get("result") == "0000", "response": response})
        except Exception as exc:
            results.append({**variant, "ok": False, "error": str(exc)})
        status = "OK" if results[-1]["ok"] else "FAIL"
        message = results[-1].get("response", {}).get("message") or results[-1].get("error") or ""
        print(f"{status} {variant['method']} {variant['path']} {variant.get('body') or ''} {message}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUT_DIR / f"detail-probe-{args.label_id}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.json"
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote: {output_path}")
    return 0


def _credentials(athlete_id: int, username_arg: str) -> tuple[str, str]:
    if not username_arg:
        with SessionLocal() as db:
            account = db.execute(
                select(DeviceAccount)
                .where(DeviceAccount.athlete_id == athlete_id, DeviceAccount.device_type == DeviceType.COROS)
                .order_by(DeviceAccount.id.desc())
                .limit(1)
            ).scalars().first()
            if account and account.username and account.encrypted_password:
                return account.username, decrypt_secret(account.encrypted_password)
    username = username_arg or input("COROS username: ").strip()
    password = getpass.getpass("COROS password: ")
    return username, password


def _variants(label_id: str, sport_type: int | None = None, start_time: int | None = None) -> list[dict]:
    bodies = [
        {"labelId": label_id},
        {"labelId": int(label_id)} if label_id.isdigit() else None,
        {"activityId": label_id},
        {"activityId": int(label_id)} if label_id.isdigit() else None,
        {"id": label_id},
        {"id": int(label_id)} if label_id.isdigit() else None,
    ]
    variants = []
    for body in bodies:
        if body is not None:
            variants.append({"method": "POST", "path": "/activity/detail/filter", "body": body})
    for key in ["labelId", "activityId", "id"]:
        qs = urllib.parse.urlencode({key: label_id})
        variants.append({"method": "GET", "path": f"/activity/detail/filter?{qs}"})
    if sport_type is not None:
        qs = urllib.parse.urlencode({"labelId": label_id, "sportType": sport_type})
        variants.append({"method": "GET", "path": f"/activity/detail/filter?{qs}"})
        qs = urllib.parse.urlencode({"labelId": label_id, "sportType": sport_type, "source": 1})
        variants.append({"method": "GET", "path": f"/activity/detail/filter?{qs}"})
        qs = urllib.parse.urlencode({"labelId": label_id, "sportType": sport_type, "teamId": "", "userId": ""})
        variants.append({"method": "GET", "path": f"/activity/detail/filter?{qs}"})
    if sport_type is not None and start_time is not None:
        qs = urllib.parse.urlencode({"labelId": label_id, "sportType": sport_type, "startTime": start_time})
        variants.append({"method": "GET", "path": f"/activity/detail/filter?{qs}"})
    qs = urllib.parse.urlencode({"labelId": label_id})
    variants.append({"method": "GET", "path": f"/activity/detail/download?{qs}"})
    if sport_type is not None:
        qs = urllib.parse.urlencode({"labelId": label_id, "sportType": sport_type})
        variants.append({"method": "GET", "path": f"/activity/detail/download?{qs}"})
    return variants


def _request(client: RealCorosAutomationClient, variant: dict) -> dict:
    url = f"https://{client._api_host}{variant['path']}"
    headers = {"accessToken": client._token, "User-Agent": "COROS-Training-Hub/1.0"}
    data = None
    if variant["method"] == "POST":
        data = json.dumps(variant["body"]).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=variant["method"])
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except Exception:
        return {"_raw_body": body[:2000]}


if __name__ == "__main__":
    raise SystemExit(main())
