from __future__ import annotations

import argparse
import csv
import getpass
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from app.core.config import BASE_DIR
from app.db import SessionLocal
from app.models import AthleteActivity, DeviceAccount, DeviceType
from app.tools.coros.automation import RealCorosAutomationClient
from app.tools.coros.credentials import decrypt_secret


OUT_DIR = BASE_DIR / "var" / "coros_real_sync" / "exports"
FILE_TYPES = {
    4: "fit",
    3: "tcx",
    2: "kml",
    1: "gpx",
    0: "csv",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Download COROS Training Hub export files for one activity.")
    parser.add_argument("label_id")
    parser.add_argument("--athlete-id", type=int, default=1)
    parser.add_argument("--username", default="")
    parser.add_argument("--sport-type", type=int, default=None)
    parser.add_argument(
        "--file-types",
        default="4,3,1,0",
        help="Comma-separated COROS file types: 4=fit, 3=tcx, 2=kml, 1=gpx, 0=csv.",
    )
    args = parser.parse_args()

    sport_type = args.sport_type or _sport_type_from_db(args.athlete_id, args.label_id) or 100
    username, password = _credentials(args.athlete_id, args.username)
    client = RealCorosAutomationClient()
    login = client.login(username, password)
    if not login.ok:
        print(f"Login failed: {login.message}")
        return 3

    requested_types = _parse_file_types(args.file_types)
    output_dir = OUT_DIR / args.label_id
    output_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for file_type in requested_types:
        ext = FILE_TYPES[file_type]
        result = _download_export(client, args.label_id, sport_type, file_type, ext, output_dir)
        results.append(result)
        status = "OK" if result["ok"] else "FAIL"
        detail = result.get("path") or result.get("message") or result.get("error") or ""
        print(f"{status} fileType={file_type} .{ext} {detail}")

    summary = {
        "timestamp": datetime.now(UTC).isoformat(),
        "athlete_id": args.athlete_id,
        "label_id": args.label_id,
        "sport_type": sport_type,
        "file_types": requested_types,
        "results": results,
    }
    summary_path = output_dir / f"export-summary-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Wrote: {summary_path}")
    return 0 if any(item["ok"] for item in results) else 1


def _credentials(athlete_id: int, username_arg: str) -> tuple[str, str]:
    if not username_arg:
        with SessionLocal() as db:
            account = db.execute(
                select(DeviceAccount)
                .where(
                    DeviceAccount.athlete_id == athlete_id,
                    DeviceAccount.device_type == DeviceType.COROS,
                    DeviceAccount.auth_status == "connected",
                )
                .order_by(DeviceAccount.id.desc())
                .limit(1)
            ).scalars().first()
            if account and account.username and account.encrypted_password:
                return account.username, decrypt_secret(account.encrypted_password)
    username = username_arg or input("COROS username: ").strip()
    password = getpass.getpass("COROS password: ")
    return username, password


def _sport_type_from_db(athlete_id: int, label_id: str) -> int | None:
    with SessionLocal() as db:
        activity = db.execute(
            select(AthleteActivity)
            .where(
                AthleteActivity.athlete_id == athlete_id,
                AthleteActivity.provider == "coros",
                AthleteActivity.provider_activity_id == label_id,
            )
            .limit(1)
        ).scalar_one_or_none()
    if activity is None:
        return None
    payload = _decode_json(activity.raw_payload_json)
    if isinstance(payload, dict) and payload.get("sportType") is not None:
        return int(payload["sportType"])
    if isinstance(payload, dict) and isinstance(payload.get("summary"), dict) and payload["summary"].get("sportType") is not None:
        return int(payload["summary"]["sportType"])
    return None


def _download_export(
    client: RealCorosAutomationClient,
    label_id: str,
    sport_type: int,
    file_type: int,
    ext: str,
    output_dir: Path,
) -> dict:
    try:
        response = _request_export_url(client, label_id, sport_type, file_type)
    except Exception as exc:
        return {"ok": False, "file_type": file_type, "extension": ext, "error": str(exc)}

    file_url = _extract_file_url(response)
    if not file_url:
        return {
            "ok": False,
            "file_type": file_type,
            "extension": ext,
            "message": response.get("message") or "Missing fileUrl",
            "response_shape": _shape(response),
        }

    output_path = output_dir / f"{label_id}.{ext}"
    try:
        data = _download_bytes(file_url)
        output_path.write_bytes(data)
    except Exception as exc:
        return {
            "ok": False,
            "file_type": file_type,
            "extension": ext,
            "file_url_host": urllib.parse.urlparse(file_url).netloc,
            "error": f"download failed: {exc}",
        }

    return {
        "ok": True,
        "file_type": file_type,
        "extension": ext,
        "path": str(output_path.relative_to(BASE_DIR)),
        "bytes": output_path.stat().st_size,
        "file_url_host": urllib.parse.urlparse(file_url).netloc,
        "summary": _summarize_export(output_path, ext),
    }


def _request_export_url(client: RealCorosAutomationClient, label_id: str, sport_type: int, file_type: int) -> dict:
    params = urllib.parse.urlencode({"labelId": label_id, "sportType": sport_type, "fileType": file_type})
    path = f"/activity/detail/download?{params}"
    url = f"https://{client._api_host}{path}"
    req = urllib.request.Request(
        url,
        data=b"",
        headers={
            "accessToken": client._token,
            "Content-Type": "application/json",
            "User-Agent": "COROS-Training-Hub/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    payload = json.loads(raw)
    if isinstance(payload, dict) and payload.get("result") not in {None, "0000"}:
        return payload
    return payload


def _download_bytes(file_url: str) -> bytes:
    req = urllib.request.Request(file_url, headers={"User-Agent": "COROS-Training-Hub/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _extract_file_url(response: dict) -> str:
    if not isinstance(response, dict):
        return ""
    if isinstance(response.get("data"), dict) and response["data"].get("fileUrl"):
        return str(response["data"]["fileUrl"])
    if isinstance(response.get("value"), dict) and response["value"].get("fileUrl"):
        return str(response["value"]["fileUrl"])
    if response.get("fileUrl"):
        return str(response["fileUrl"])
    return ""


def _summarize_export(path: Path, ext: str) -> dict:
    if ext == "csv":
        return _summarize_csv(path)
    if ext in {"tcx", "gpx", "kml"}:
        return _summarize_xml(path, ext)
    return {"kind": "binary", "header_hex": path.read_bytes()[:16].hex()}


def _summarize_csv(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    fields = reader.fieldnames or []
    return {
        "kind": "csv",
        "row_count": len(rows),
        "fields": fields[:80],
        "first_row": _truncate_mapping(rows[0]) if rows else {},
        "last_row": _truncate_mapping(rows[-1]) if rows else {},
    }


def _summarize_xml(path: Path, ext: str) -> dict:
    root = ET.parse(path).getroot()
    tags = [_local_name(element.tag) for element in root.iter()]
    counts = {name: tags.count(name) for name in sorted(set(tags))}
    summary = {"kind": ext, "root": _local_name(root.tag), "counts": counts}
    if ext == "gpx":
        points = root.findall(".//{*}trkpt")
        summary["trackpoint_count"] = len(points)
        summary["first_point"] = _point_summary(points[0]) if points else {}
        summary["last_point"] = _point_summary(points[-1]) if points else {}
    if ext == "tcx":
        points = root.findall(".//{*}Trackpoint")
        summary["trackpoint_count"] = len(points)
        summary["first_point"] = _tcx_point_summary(points[0]) if points else {}
        summary["last_point"] = _tcx_point_summary(points[-1]) if points else {}
    if ext == "kml":
        coordinates = root.findall(".//{*}coordinates")
        coord_text = " ".join((item.text or "").strip() for item in coordinates).strip()
        summary["coordinate_tuple_count"] = len([item for item in coord_text.split() if item])
    return summary


def _point_summary(element: ET.Element) -> dict:
    return {
        "lat": element.attrib.get("lat"),
        "lon": element.attrib.get("lon"),
        "time": _find_text(element, "time"),
        "ele": _find_text(element, "ele"),
    }


def _tcx_point_summary(element: ET.Element) -> dict:
    position = element.find(".//{*}Position")
    return {
        "time": _find_text(element, "Time"),
        "distance_m": _find_text(element, "DistanceMeters"),
        "heart_rate": _find_text(element, "Value"),
        "lat": _find_text(position, "LatitudeDegrees") if position is not None else None,
        "lon": _find_text(position, "LongitudeDegrees") if position is not None else None,
        "altitude_m": _find_text(element, "AltitudeMeters"),
    }


def _find_text(element: ET.Element | None, local_name: str) -> str | None:
    if element is None:
        return None
    found = element.find(f".//{{*}}{local_name}")
    return found.text if found is not None else None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _truncate_mapping(row: dict) -> dict:
    return {key: str(value)[:120] for key, value in list(row.items())[:40]}


def _shape(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _shape(item) for key, item in value.items()}
    if isinstance(value, list):
        return f"list:{len(value)}"
    return type(value).__name__


def _decode_json(raw: str | None) -> object:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _parse_file_types(raw: str) -> list[int]:
    values = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        file_type = int(item)
        if file_type not in FILE_TYPES:
            raise ValueError(f"Unsupported COROS file type: {file_type}")
        values.append(file_type)
    return values or [4]


if __name__ == "__main__":
    raise SystemExit(main())
