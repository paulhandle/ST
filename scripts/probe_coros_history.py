#!/usr/bin/env python3
"""Probe COROS Training Hub for historical training plans.

Targets two specific date ranges the user identified as containing complete
training programs:

  - Summer 2025: 2025-06-23 → 2025-10-26
  - Winter 2025-26: 2025-12-02 → 2026-04-19

For each window we hit /training/schedule/query and save the sanitized
response under var/coros_probe/. We also print a structural summary so we can
see whether the response carries the "training course name" (训练课程名称)
field that distinguishes coach-prescribed workouts from self-runs.

Usage:
  uv run python scripts/probe_coros_history.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import load_local_env
from app.tools.coros.automation import RealCorosAutomationClient

load_local_env()

OUT_DIR = Path(__file__).resolve().parents[1] / "var" / "coros_probe"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WINDOWS = [
    ("summer_2025", date(2025, 6, 23), date(2025, 10, 26)),
    ("winter_2025_2026", date(2025, 12, 2), date(2026, 4, 19)),
]


def _ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


REDACT_KEYS = {"accessToken", "userId", "authorId", "operateUserId", "teamId"}


def _redact(text: str, secrets: list[str]) -> str:
    """Redact only quoted occurrences of secrets, leaving integer userId fields intact."""
    out = text
    for s in secrets:
        if not s:
            continue
        # Only replace string-quoted form, never raw substring
        out = out.replace(f'"{s}"', '"<redacted>"')
    return out


def _redact_struct(value):
    """Walk dict/list and redact known sensitive keys structurally."""
    if isinstance(value, dict):
        return {k: ("<redacted>" if k in REDACT_KEYS and v else _redact_struct(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_struct(v) for v in value]
    return value


def _shape(value, max_keys: int = 80, depth: int = 0) -> object:
    """Recursive structural summary — keys + types + sample, no full payload."""
    if depth > 6:
        return "<deep>"
    if isinstance(value, dict):
        out = {}
        for k, v in list(value.items())[:max_keys]:
            out[k] = _shape(v, max_keys, depth + 1)
        if len(value) > max_keys:
            out["__more__"] = f"{len(value) - max_keys} more keys"
        return out
    if isinstance(value, list):
        if not value:
            return "[empty]"
        return [f"[list:{len(value)}]", _shape(value[0], max_keys, depth + 1)]
    if isinstance(value, str):
        return f"<str:{len(value)}>"
    return type(value).__name__


def _scan_for_course_name(value, path: str = "") -> list[tuple[str, str]]:
    """Walk the structure looking for fields that smell like a 'course name'."""
    hits: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for k, v in value.items():
            kp = f"{path}.{k}" if path else k
            kl = k.lower()
            if any(hint in kl for hint in ("name", "title", "courseid", "courseno", "programname", "trainingname", "exercisename", "tag")):
                if isinstance(v, str) and v:
                    hits.append((kp, v))
                elif isinstance(v, (int, float)):
                    hits.append((kp, str(v)))
            hits.extend(_scan_for_course_name(v, kp))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            hits.extend(_scan_for_course_name(item, f"{path}[{i}]"))
    return hits


def _query_schedule(token: str, host: str, start: str, end: str) -> dict:
    qs = urllib.parse.urlencode({"startDate": start, "endDate": end, "supportRestExercise": "1"})
    url = f"https://{host}/training/schedule/query?{qs}"
    req = urllib.request.Request(
        url,
        headers={"accessToken": token, "User-Agent": "ST-Probe/1.0"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except Exception:
        return {"_raw_body_truncated": body[:1000]}


def main() -> int:
    username = os.environ.get("COROS_USERNAME")
    password = os.environ.get("COROS_PASSWORD")
    if not username or not password:
        print("ERROR: set COROS_USERNAME and COROS_PASSWORD in .env", file=sys.stderr)
        return 2

    client = RealCorosAutomationClient()
    login = client.login(username, password)
    if not login.ok:
        print(f"ERROR: login failed: {login.message}", file=sys.stderr)
        return 3
    print(f"[ok] logged in via {client._api_host}")

    secrets = [username, password, client._token, client._user_id]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    summary: dict = {"timestamp": timestamp, "windows": []}

    for label, start_d, end_d in WINDOWS:
        start, end = _ymd(start_d), _ymd(end_d)
        print(f"\n[probe] {label}: {start} → {end}")
        try:
            payload = _query_schedule(client._token, client._api_host, start, end)
        except Exception as exc:
            print(f"  ! request failed: {exc}")
            summary["windows"].append({"label": label, "start": start, "end": end, "error": repr(exc)})
            continue

        result = payload.get("result") if isinstance(payload, dict) else None
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        print(f"  result code: {result}")

        # Where the schedule body lives — varies by COROS version
        programs = data.get("programs") or data.get("programList") or []
        entities = data.get("entities") or data.get("planList") or data.get("scheduleList") or []
        sport_in = data.get("SportDatasInPlan") or data.get("sportDatasInPlan") or []
        sport_out = data.get("SportDatasNotInPlan") or data.get("sportDatasNotInPlan") or []
        max_id = data.get("maxIdInPlan")

        print(f"  programs: {len(programs)}  entities: {len(entities)}  in_plan: {len(sport_in)}  not_in_plan: {len(sport_out)}  maxIdInPlan: {max_id}")

        course_hits = _scan_for_course_name(payload)
        unique_names: dict[str, int] = {}
        for path, value in course_hits:
            unique_names[value] = unique_names.get(value, 0) + 1
        if unique_names:
            print("  candidate name/title fields (top 15 by occurrence):")
            for name, count in sorted(unique_names.items(), key=lambda x: -x[1])[:15]:
                print(f"    [{count:>3}x] {name[:80]}")

        # Save full payload with structural redaction (preserves valid JSON)
        out_file = OUT_DIR / f"history-{label}-{timestamp}.json"
        sanitized = _redact_struct(payload)
        out_file.write_text(json.dumps(sanitized, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"  saved: {out_file.relative_to(Path.cwd())}")

        # Save a smaller shape file
        shape_file = OUT_DIR / f"history-{label}-{timestamp}.shape.json"
        shape_file.write_text(json.dumps(_shape(payload), ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  shape: {shape_file.relative_to(Path.cwd())}")

        summary["windows"].append({
            "label": label,
            "start": start,
            "end": end,
            "result_code": result,
            "programs_count": len(programs),
            "entities_count": len(entities),
            "sport_in_plan_count": len(sport_in),
            "sport_not_in_plan_count": len(sport_out),
            "max_id_in_plan": max_id,
            "candidate_name_fields_top": [
                {"value": n, "count": c}
                for n, c in sorted(unique_names.items(), key=lambda x: -x[1])[:15]
            ],
            "files": {
                "raw": str(out_file.name),
                "shape": str(shape_file.name),
            },
        })

    summary_file = OUT_DIR / f"history-probe-{timestamp}.summary.json"
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[done] summary: {summary_file.relative_to(Path.cwd())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
