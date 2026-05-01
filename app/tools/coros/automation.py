from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import os
from typing import Protocol
from uuid import uuid5, NAMESPACE_URL


@dataclass(frozen=True)
class CorosLoginResult:
    ok: bool
    message: str


class CorosAutomationClient(Protocol):
    provider: str

    def login(self, username: str, password: str) -> CorosLoginResult:
        raise NotImplementedError

    def fetch_history(self, username: str) -> dict:
        raise NotImplementedError

    def sync_workouts(self, username: str, workouts: list[dict]) -> list[dict]:
        raise NotImplementedError


class RealCorosAutomationClient:
    """Direct COROS API client using MD5-hashed credentials (no browser required)."""

    provider = "coros"
    _RUNNING_SPORT_TYPES = {100, 101, 102}  # outdoor, trail, indoor/treadmill

    def __init__(self) -> None:
        self._token: str = ""
        self._api_host: str = ""
        self._user_id: str = ""
        self._lthr: float = 0.0  # cached from dashboard for intensity zone calculations

    def login(self, username: str, password: str) -> CorosLoginResult:
        import hashlib
        import json
        import urllib.request

        md5_pwd = hashlib.md5(password.encode()).hexdigest()
        payload = json.dumps({"account": username, "pwd": md5_pwd, "loginType": 2}).encode()
        req = urllib.request.Request(
            "https://teamapi.coros.com/account/login",
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "COROS-Training-Hub/1.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read())
        except Exception as exc:
            return CorosLoginResult(ok=False, message=f"Login request failed: {exc}")

        if not isinstance(result, dict) or result.get("result") != "0000":
            return CorosLoginResult(ok=False, message=result.get("message", "Login failed"))

        data = result.get("data", {})
        self._token = data.get("accessToken", "")
        self._user_id = data.get("userId", "")
        region_id = data.get("regionId", 1)
        self._api_host = "teamcnapi.coros.com" if region_id == 2 else "teamapi.coros.com"
        return CorosLoginResult(ok=True, message="COROS login succeeded")

    def fetch_history(self, username: str, days_back: int = 365) -> dict:
        if not self._token:
            raise RuntimeError("Not logged in. Call login() first.")

        activities = self._fetch_activities(days_back=days_back)
        metrics = self._fetch_metrics()
        return {"activities": activities, "metrics": metrics}

    def _fetch_activities(self, days_back: int = 365) -> list[dict]:
        from datetime import timezone, timedelta

        activities = []
        cutoff_ts = int((datetime.now(UTC) - timedelta(days=days_back)).timestamp())

        page = 1
        while page <= 100:  # Safety cap: 100 pages × 20 = 2000 activities max
            data = self._get(f"/activity/query?pageNumber={page}&size=20")
            items = data.get("dataList", [])
            done = False
            for item in items:
                if item.get("sportType") not in self._RUNNING_SPORT_TYPES:
                    continue
                if item.get("startTime", 0) < cutoff_ts:
                    done = True
                    break
                activities.append(self._map_activity(item))
            if done or page >= data.get("totalPage", 1):
                break
            page += 1

        return activities

    def _map_activity(self, item: dict) -> dict:
        from datetime import timezone, timedelta

        tz_offset_min = item.get("startTimezone", 0) * 15
        tz = timezone(timedelta(minutes=tz_offset_min))
        started_at = datetime.fromtimestamp(item["startTime"], tz=tz)

        distance_m = float(item.get("distance", 0) or 0)
        duration_sec = int(item.get("totalTime", 0) or 0)
        # adjustedPace is grade-adjusted pace in sec/km; fall back to computed pace
        raw_pace = item.get("adjustedPace") or item.get("avgSpeed")
        avg_pace = float(raw_pace) if raw_pace else (
            duration_sec / (distance_m / 1000) if distance_m > 0 else None
        )
        avg_hr = float(item["avgHr"]) if item.get("avgHr") else None
        avg_cadence = float(item["avgCadence"]) if item.get("avgCadence") else None
        avg_power = float(item["avgPower"]) if item.get("avgPower") else None
        training_load = float(item["trainingLoad"]) if item.get("trainingLoad") else None

        return {
            "provider_activity_id": item["labelId"],
            "sport": "running",
            "discipline": "run",
            "started_at": started_at,
            "timezone": _tz_name(tz_offset_min),
            "duration_sec": duration_sec,
            "moving_duration_sec": int(item.get("workoutTime", duration_sec) or duration_sec),
            "distance_m": distance_m,
            "elevation_gain_m": float(item.get("ascent", 0) or 0),
            "avg_pace_sec_per_km": avg_pace,
            "avg_hr": avg_hr,
            "max_hr": None,
            "avg_cadence": avg_cadence,
            "avg_power": avg_power,
            "training_load": training_load,
            "perceived_effort": None,
            "feedback_text": item.get("name", ""),
            "laps": [],
            "raw_payload": item,
        }

    def _fetch_metrics(self) -> list[dict]:
        from datetime import timezone

        metrics = []
        now = datetime.now(tz=timezone.utc)
        try:
            dash = self._get("/dashboard/query")
            summary = dash.get("summaryInfo", {})
            _maybe_metric(metrics, now, summary, "lthr", "lthr", "bpm")
            if summary.get("lthr"):
                self._lthr = float(summary["lthr"])
            _maybe_metric(metrics, now, summary, "ltsp", "ltsp", "sec_per_km")
            _maybe_metric(metrics, now, summary, "aerobicEnduranceScore", "aerobic_endurance_score", "score")
            if summary.get("staminaLevel") is not None:
                metrics.append({
                    "measured_at": now,
                    "metric_type": "marathon_level",
                    "value": float(summary["staminaLevel"]),
                    "unit": "score",
                    "raw_payload": {"source": "coros_dashboard"},
                })
            if summary.get("recoveryPct") is not None:
                metrics.append({
                    "measured_at": now,
                    "metric_type": "fatigue",
                    "value": round(100.0 - float(summary["recoveryPct"]), 1),
                    "unit": "score",
                    "raw_payload": {"source": "coros_dashboard"},
                })
            # Marathon race predictor: type=1 entry IS the COROS marathon time prediction
            for rs in summary.get("runScoreList", []):
                if rs.get("type") == 1 and rs.get("duration"):
                    metrics.append({
                        "measured_at": now,
                        "metric_type": "race_predictor_marathon",
                        "value": float(rs["duration"]),
                        "unit": "sec",
                        "raw_payload": {"source": "coros_run_score", "type": 1, **rs},
                    })
                    break
        except Exception:
            pass
        return metrics

    def _get(self, path: str) -> dict:
        import json
        import urllib.request

        url = f"https://{self._api_host}{path}"
        req = urllib.request.Request(
            url,
            headers={"accessToken": self._token, "User-Agent": "COROS-Training-Hub/1.0"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = json.loads(resp.read())
        if result.get("result") != "0000":
            raise RuntimeError(f"COROS API {path}: {result.get('message')}")
        return result.get("data", {})

    def sync_workouts(self, username: str, workouts: list[dict]) -> list[dict]:
        if not self._token:
            raise RuntimeError("Not logged in. Call login() first.")
        if not workouts:
            return []

        max_id = self._get_max_id_in_plan()
        entities: list[dict] = []
        programs: list[dict] = []
        version_objects: list[dict] = []
        results: list[dict] = []

        for i, workout in enumerate(workouts):
            id_in_plan = max_id + i + 1
            happen_day = workout["scheduled_date"].replace("-", "")
            duration_sec = int(workout.get("duration_sec") or 1800)
            name = workout.get("title") or "Training"
            workout_type = workout.get("workout_type", "easy")

            exercise = self._build_exercise(id_in_plan, duration_sec, workout_type)
            program = self._build_program(id_in_plan, name, duration_sec, exercise)
            entity = {
                "happenDay": happen_day,
                "idInPlan": id_in_plan,
                "sortNo": 0,
                "dayNo": 0,
                "sortNoInPlan": 0,
                "sortNoInSchedule": 0,
                "exerciseBarChart": program.get("exerciseBarChart", []),
            }
            entities.append(entity)
            programs.append(program)
            version_objects.append({"id": id_in_plan, "status": 1})
            results.append({
                "local_workout_id": workout.get("id"),
                "provider_workout_id": f"coros-plan-{id_in_plan}",
                "provider_calendar_item_id": f"coros-sched-{happen_day}-{id_in_plan}",
                "status": "pending",
                "raw_payload": {"source": "coros_real", "happen_day": happen_day, "id_in_plan": id_in_plan},
            })

        # Enrich each program with server-calculated metrics
        for program, entity in zip(programs, entities):
            try:
                calc = self._post("/training/program/calculate", program)
                if calc.get("result") == "0000":
                    cd = calc.get("data", {})
                    program["distance"] = cd.get("planDistance", program["distance"])
                    program["duration"] = cd.get("planDuration", program["duration"])
                    program["trainingLoad"] = cd.get("planTrainingLoad", program["trainingLoad"])
                    if cd.get("exerciseBarChart"):
                        program["exerciseBarChart"] = cd["exerciseBarChart"]
                        entity["exerciseBarChart"] = cd["exerciseBarChart"]
            except Exception:
                pass  # keep estimated values on calculate failure

        # COROS rejects multiple new idInPlan entries per call — send one at a time
        _BATCH = 1
        for start in range(0, len(entities), _BATCH):
            payload = {
                "entities": entities[start : start + _BATCH],
                "programs": programs[start : start + _BATCH],
                "pbVersion": 2,
                "versionObjects": version_objects[start : start + _BATCH],
            }
            r = self._post("/training/schedule/update", payload)
            if r.get("result") != "0000":
                raise RuntimeError(f"COROS schedule/update failed: {r.get('message')}")

        for result in results:
            result["status"] = "success"
        return results

    def _get_max_id_in_plan(self) -> int:
        from datetime import timezone
        today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
        try:
            data = self._get(f"/training/schedule/query?startDate={today}&endDate={today}&supportRestExercise=1")
            return int(data.get("maxIdInPlan", 0) or 0)
        except Exception:
            return 0

    def _build_exercise(self, id_in_plan: int, duration_sec: int, workout_type: str) -> dict:
        _ZONES: dict[str, tuple[int, int]] = {
            "recovery":  (55000, 65000),
            "easy":      (65000, 79000),
            "long":      (65000, 75000),
            "aerobic":   (75000, 85000),
            "tempo":     (85000, 92000),
            "threshold": (88000, 95000),
            "intervals": (95000, 100000),
            "race":      (95000, 105000),
        }
        lo, hi = _ZONES.get(workout_type, _ZONES["easy"])
        lthr = self._lthr or 170.0
        return {
            "access": 0,
            "createTimestamp": 1587381919,  # COROS system T3001 exercise creation timestamp
            "defaultOrder": 2,
            "equipment": [1],
            "exerciseType": 2,
            "groupId": "",
            "hrType": 3,
            "id": 1,
            "intensityCustom": 2,
            "intensityDisplayUnit": 0,
            "intensityMultiplier": 0,
            "intensityPercent": lo,
            "intensityPercentExtend": hi,
            "intensityType": 2,
            "intensityValue": int(lthr * lo / 100000),
            "intensityValueExtend": int(lthr * hi / 100000),
            "isDefaultAdd": 1,
            "isGroup": False,
            "isIntensityPercent": True,
            "name": "T3001",
            "originId": "426109589008859136",
            "overview": "sid_run_training",
            "part": [0],
            "restType": 3,
            "restValue": 0,
            "sets": 1,
            "sortNo": 2,
            "sourceId": "0",
            "sourceUrl": "",
            "sportType": 1,
            "subType": 0,
            "targetDisplayUnit": 0,
            "targetType": 2,
            "targetValue": duration_sec,
            "userId": 0,
            "videoUrl": "",
        }

    def _build_program(self, id_in_plan: int, name: str, duration_sec: int, exercise: dict) -> dict:
        est_distance_cm = int((duration_sec / 360.0) * 1000 * 100)
        est_load = max(5, int(duration_sec * 0.035))
        bar_chart = [{
            "exerciseId": str(exercise.get("id", 1)),
            "exerciseType": exercise["exerciseType"],
            "height": 93,
            "name": exercise["name"],
            "targetType": exercise["targetType"],
            "targetValue": exercise["targetValue"],
            "value": float(exercise["targetValue"]),
            "width": 100,
            "widthFill": 0,
        }]
        return {
            "idInPlan": id_in_plan,
            "name": name,
            "sportType": 1,
            "subType": 0,
            "totalSets": 1,
            "sets": 1,
            "exerciseNum": "",
            "targetType": "",
            "targetValue": "",
            "version": 0,
            "simple": True,
            "exercises": [exercise],
            "access": 1,
            "essence": 0,
            "estimatedTime": 0,
            "originEssence": 0,
            "overview": "",
            "type": 0,
            "unit": 0,
            "pbVersion": 2,
            "sourceId": "425868113867882496",
            "sourceUrl": "https://d31oxp44ddzkyk.cloudfront.net/source/source_default/0/5a9db1c3363348298351aaabfd70d0f5.jpg",
            "referExercise": {"intensityType": 0, "hrType": 0, "valueType": 0},
            "poolLengthId": 1,
            "poolLength": 2500,
            "poolLengthUnit": 2,
            "distance": f"{est_distance_cm:.2f}",
            "duration": duration_sec,
            "trainingLoad": est_load,
            "pitch": 0,
            "exerciseBarChart": bar_chart,
            "distanceDisplayUnit": 1,
        }

    def _post(self, path: str, body: dict) -> dict:
        import json
        import urllib.request

        url = f"https://{self._api_host}{path}"
        payload_bytes = json.dumps(body).encode()
        req = urllib.request.Request(
            url,
            data=payload_bytes,
            headers={"accessToken": self._token, "Content-Type": "application/json", "User-Agent": "COROS-Training-Hub/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())


def _tz_name(offset_min: int) -> str:
    h, m = divmod(abs(offset_min), 60)
    sign = "+" if offset_min >= 0 else "-"
    return f"UTC{sign}{h:02d}:{m:02d}" if m else f"UTC{sign}{h}"


def _maybe_metric(metrics: list, now, src: dict, src_key: str, metric_type: str, unit: str) -> None:
    val = src.get(src_key)
    if val is not None:
        metrics.append({
            "measured_at": now,
            "metric_type": metric_type,
            "value": float(val),
            "unit": unit,
            "raw_payload": {"source": "coros_dashboard"},
        })



class FakeCorosAutomationClient:
    """Deterministic local stand-in for the future COROS Training Hub browser automation."""

    provider = "coros"

    def login(self, username: str, password: str) -> CorosLoginResult:
        if not username or not password:
            return CorosLoginResult(ok=False, message="Missing COROS credentials")
        return CorosLoginResult(ok=True, message="Fake COROS login succeeded")

    def fetch_history(self, username: str) -> dict:
        now = datetime.now(UTC).replace(hour=7, minute=0, second=0, microsecond=0, tzinfo=None)
        activities = []
        for week_offset in range(12, 0, -1):
            week_start = now - timedelta(days=week_offset * 7)
            week_scale = 1 + (12 - week_offset) * 0.025
            templates = [
                (0, 8000, 330, 135, 55, "Easy aerobic run"),
                (2, 10000, 315, 148, 75, "Steady run with strides"),
                (4, 12000, 305, 154, 88, "Tempo progression"),
                (6, 16000 + (12 - week_offset) * 650, 340, 142, 120, "Long run"),
            ]
            for day_offset, distance_m, pace_sec_per_km, avg_hr, load, note in templates:
                started_at = week_start + timedelta(days=day_offset)
                scaled_distance = float(distance_m * week_scale)
                duration_sec = int((scaled_distance / 1000) * pace_sec_per_km)
                activity_id = str(uuid5(NAMESPACE_URL, f"{username}:{started_at.isoformat()}:{scaled_distance:.0f}"))
                activities.append(
                    {
                        "provider_activity_id": activity_id,
                        "sport": "running",
                        "discipline": "run",
                        "started_at": started_at,
                        "timezone": "Asia/Shanghai",
                        "duration_sec": duration_sec,
                        "moving_duration_sec": duration_sec,
                        "distance_m": scaled_distance,
                        "elevation_gain_m": 45.0 if day_offset == 6 else 18.0,
                        "avg_pace_sec_per_km": float(pace_sec_per_km),
                        "avg_hr": float(avg_hr),
                        "max_hr": float(avg_hr + 18),
                        "avg_cadence": 174.0,
                        "avg_power": None,
                        "training_load": float(load * week_scale),
                        "perceived_effort": 4 if day_offset in (0, 6) else 6,
                        "feedback_text": note,
                        "laps": [
                            {
                                "lap_index": 1,
                                "duration_sec": duration_sec,
                                "distance_m": scaled_distance,
                                "avg_pace_sec_per_km": float(pace_sec_per_km),
                                "avg_hr": float(avg_hr),
                                "elevation_gain_m": 45.0 if day_offset == 6 else 18.0,
                            }
                        ],
                        "raw_payload": {"source": "fake_coros", "note": note},
                    }
                )

        metrics = [
            {
                "measured_at": now,
                "metric_type": "marathon_level",
                "value": 68.0,
                "unit": "score",
                "raw_payload": {"source": "fake_coros"},
            },
            {
                "measured_at": now,
                "metric_type": "fatigue",
                "value": 38.0,
                "unit": "score",
                "raw_payload": {"source": "fake_coros"},
            },
            {
                "measured_at": now,
                "metric_type": "race_predictor_marathon",
                "value": 14400.0,
                "unit": "sec",
                "raw_payload": {"source": "fake_coros"},
            },
        ]
        return {"activities": activities, "metrics": metrics}

    def sync_workouts(self, username: str, workouts: list[dict]) -> list[dict]:
        results = []
        for workout in workouts:
            stable_key = f"{username}:{workout['id']}:{workout['scheduled_date']}"
            remote_id = str(uuid5(NAMESPACE_URL, stable_key))
            results.append(
                {
                    "local_workout_id": workout["id"],
                    "provider_workout_id": f"coros-workout-{remote_id}",
                    "provider_calendar_item_id": f"coros-calendar-{remote_id}",
                    "status": "success",
                    "raw_payload": {"source": "fake_coros", "title": workout["title"]},
                }
            )
        return results


def coros_automation_client() -> CorosAutomationClient:
    mode = os.environ.get("COROS_AUTOMATION_MODE", "fake").strip().lower()
    if mode == "real":
        return RealCorosAutomationClient()
    return FakeCorosAutomationClient()
