"""Unit tests for RealCorosAutomationClient with mocked urllib calls.

These tests verify field mapping, pagination logic, MD5 credential hashing,
and sync payload construction without requiring real COROS credentials.
"""
import hashlib
import json
import os
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, call, patch

os.environ.setdefault("ST_DATABASE_URL", "sqlite:///st_test.db")
os.environ["COROS_AUTOMATION_MODE"] = "fake"

from app.tools.coros.automation import RealCorosAutomationClient


def _resp(data: dict) -> MagicMock:
    """Build a mock context-manager response that returns data as JSON.

    urllib.request.urlopen is used as a context manager:
        with urlopen(req) as resp: resp.read()
    MagicMock.__enter__ returns a new MagicMock by default, so we must
    explicitly set __enter__.return_value = self so that resp.read() works.
    """
    m = MagicMock()
    m.read.return_value = json.dumps(data).encode()
    m.__enter__.return_value = m
    return m


_LOGIN_OK = {
    "result": "0000",
    "message": "success",
    "data": {
        "accessToken": "test-token-abc",
        "userId": "user123",
        "regionId": 2,
    },
}

_LOGIN_FAIL = {
    "result": "1030",
    "message": "The login credentials you entered do not match our records.",
}

_ACTIVITY_PAGE = {
    "result": "0000",
    "data": {
        "dataList": [
            {
                "labelId": "act-001",
                "sportType": 100,
                "startTime": int(datetime(2026, 4, 20, 8, 0, tzinfo=UTC).timestamp()),
                "startTimezone": 32,  # 32 × 15 = 480 min = UTC+8
                "totalTime": 3600,
                "distance": 10000,
                "adjustedPace": 360.0,
                "avgHr": 145,
                "avgCadence": 172,
                "avgPower": None,
                "trainingLoad": 80,
                "workoutTime": 3550,
                "ascent": 50,
                "name": "Easy morning run",
            }
        ],
        "totalPage": 1,
    },
}

_DASHBOARD = {
    "result": "0000",
    "data": {
        "summaryInfo": {
            "lthr": 170.0,
            "ltsp": 310.0,
            "aerobicEnduranceScore": 62.5,
            "staminaLevel": 3,
            "recoveryPct": 85.0,
            "runScoreList": [
                {"type": 1, "duration": 14400},  # marathon prediction 4:00:00
                {"type": 2, "duration": 6600},
            ],
        }
    },
}

_SCHEDULE_QUERY = {
    "result": "0000",
    "data": {"maxIdInPlan": 10},
}

_PROGRAM_CALC = {
    "result": "0000",
    "data": {
        "planDistance": "10000.00",
        "planDuration": 3600,
        "planTrainingLoad": 126,
    },
}

_SCHEDULE_UPDATE_OK = {"result": "0000", "data": {}}


class TestRealCorosLogin(unittest.TestCase):
    def test_login_success_sets_token_and_cn_host(self):
        client = RealCorosAutomationClient()
        with patch("urllib.request.urlopen", return_value=_resp(_LOGIN_OK)):
            result = client.login("user@example.com", "password123")

        self.assertTrue(result.ok)
        self.assertEqual("COROS login succeeded", result.message)
        self.assertEqual("test-token-abc", client._token)
        self.assertEqual("teamcnapi.coros.com", client._api_host)  # regionId=2 → CN host

    def test_login_uses_md5_hashed_password(self):
        client = RealCorosAutomationClient()
        captured_requests = []

        def fake_urlopen(req, timeout=None):
            captured_requests.append(req)
            return _resp(_LOGIN_OK)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.login("user@example.com", "mypassword")

        req = captured_requests[0]
        body = json.loads(req.data.decode())
        expected_md5 = hashlib.md5("mypassword".encode()).hexdigest()
        self.assertEqual(expected_md5, body["pwd"])
        self.assertEqual("user@example.com", body["account"])

    def test_login_failure_returns_ok_false(self):
        client = RealCorosAutomationClient()
        with patch("urllib.request.urlopen", return_value=_resp(_LOGIN_FAIL)):
            result = client.login("user@example.com", "wrongpassword")

        self.assertFalse(result.ok)
        self.assertIn("match", result.message.lower())

    def test_login_network_error_returns_ok_false(self):
        client = RealCorosAutomationClient()
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            result = client.login("user@example.com", "pass")

        self.assertFalse(result.ok)
        self.assertIn("timeout", result.message)

    def test_login_region_1_uses_global_host(self):
        client = RealCorosAutomationClient()
        global_login = {**_LOGIN_OK, "data": {**_LOGIN_OK["data"], "regionId": 1}}
        with patch("urllib.request.urlopen", return_value=_resp(global_login)):
            client.login("user@example.com", "pass")

        self.assertEqual("teamapi.coros.com", client._api_host)


class TestRealCorosActivityMapping(unittest.TestCase):
    def _logged_in_client(self) -> RealCorosAutomationClient:
        client = RealCorosAutomationClient()
        client._token = "test-token"
        client._api_host = "teamcnapi.coros.com"
        return client

    def test_fetch_history_maps_activity_fields_correctly(self):
        client = self._logged_in_client()
        with patch("urllib.request.urlopen", side_effect=[
            _resp(_ACTIVITY_PAGE),  # /activity/query page 1
            _resp(_DASHBOARD),      # /dashboard/query
        ]):
            result = client.fetch_history("user@example.com")

        activities = result["activities"]
        self.assertEqual(1, len(activities))
        a = activities[0]

        # Distance must be in meters (COROS field = meters)
        self.assertAlmostEqual(10000.0, a["distance_m"])
        # Duration must be in seconds
        self.assertEqual(3600, a["duration_sec"])
        # Pace must be sec/km (COROS adjustedPace = sec/km)
        self.assertAlmostEqual(360.0, a["avg_pace_sec_per_km"])
        self.assertAlmostEqual(145.0, a["avg_hr"])
        self.assertEqual("act-001", a["provider_activity_id"])
        self.assertEqual("running", a["sport"])
        # Timezone: 32 × 15 = 480 min = UTC+8 (no zero-pad when no minutes)
        self.assertEqual("UTC+8", a["timezone"])

    def test_fetch_history_maps_dashboard_metrics(self):
        client = self._logged_in_client()
        with patch("urllib.request.urlopen", side_effect=[
            _resp(_ACTIVITY_PAGE),
            _resp(_DASHBOARD),
        ]):
            result = client.fetch_history("user@example.com")

        metrics = result["metrics"]
        metric_types = {m["metric_type"] for m in metrics}
        self.assertIn("lthr", metric_types)
        self.assertIn("ltsp", metric_types)
        self.assertIn("race_predictor_marathon", metric_types)

        marathon_pred = next(m for m in metrics if m["metric_type"] == "race_predictor_marathon")
        self.assertAlmostEqual(14400.0, marathon_pred["value"])

    def test_fetch_history_stops_at_cutoff(self):
        """Activities older than days_back should not be included."""
        client = self._logged_in_client()
        # Page with one very old activity
        old_ts = int((datetime.now(UTC) - timedelta(days=400)).timestamp())
        old_page = {
            "result": "0000",
            "data": {
                "dataList": [
                    {**_ACTIVITY_PAGE["data"]["dataList"][0], "startTime": old_ts}
                ],
                "totalPage": 1,
            },
        }
        with patch("urllib.request.urlopen", side_effect=[
            _resp(old_page),
            _resp(_DASHBOARD),
        ]):
            result = client.fetch_history("user@example.com", days_back=365)

        # Activity is older than 365 days → should not be included
        self.assertEqual(0, len(result["activities"]))

    def test_fetch_history_raises_when_not_logged_in(self):
        client = RealCorosAutomationClient()
        with self.assertRaises(RuntimeError):
            client.fetch_history("user@example.com")


class TestRealCorosSyncWorkouts(unittest.TestCase):
    def _logged_in_client(self) -> RealCorosAutomationClient:
        client = RealCorosAutomationClient()
        client._token = "test-token"
        client._api_host = "teamcnapi.coros.com"
        client._lthr = 168.0
        return client

    def test_sync_workouts_returns_empty_for_empty_input(self):
        client = self._logged_in_client()
        result = client.sync_workouts("user@example.com", [])
        self.assertEqual([], result)

    def test_sync_workouts_calls_schedule_update_once_per_workout(self):
        client = self._logged_in_client()
        workouts = [
            {"id": 1, "scheduled_date": "2026-05-10", "title": "Easy Run",
             "workout_type": "easy", "duration_sec": 2700},
            {"id": 2, "scheduled_date": "2026-05-12", "title": "Long Run",
             "workout_type": "long", "duration_sec": 5400},
        ]
        urlopen_responses = [
            _resp(_SCHEDULE_QUERY),       # _get_max_id_in_plan
            _resp(_PROGRAM_CALC),         # program/calculate workout 1
            _resp(_PROGRAM_CALC),         # program/calculate workout 2
            _resp(_SCHEDULE_UPDATE_OK),   # schedule/update workout 1
            _resp(_SCHEDULE_UPDATE_OK),   # schedule/update workout 2
        ]
        with patch("urllib.request.urlopen", side_effect=urlopen_responses) as mock_open:
            results = client.sync_workouts("user@example.com", workouts)

        self.assertEqual(2, len(results))
        self.assertTrue(all(r["status"] == "success" for r in results))
        # 1 schedule/query + 2 program/calculate + 2 schedule/update = 5 calls
        self.assertEqual(5, mock_open.call_count)

    def test_sync_workouts_id_in_plan_increments_from_max(self):
        client = self._logged_in_client()
        captured_update_payloads = []

        def fake_urlopen(req, timeout=None):
            url = req.full_url if hasattr(req, "full_url") else str(req)
            if "schedule/query" in url:
                return _resp(_SCHEDULE_QUERY)  # maxIdInPlan=10
            if "program/calculate" in url:
                return _resp(_PROGRAM_CALC)
            if "schedule/update" in url:
                body = json.loads(req.data.decode())
                captured_update_payloads.append(body)
                return _resp(_SCHEDULE_UPDATE_OK)
            return _resp({"result": "0000", "data": {}})

        workouts = [
            {"id": 1, "scheduled_date": "2026-05-10", "title": "Easy",
             "workout_type": "easy", "duration_sec": 2700},
        ]
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            client.sync_workouts("user@example.com", workouts)

        self.assertEqual(1, len(captured_update_payloads))
        entity = captured_update_payloads[0]["entities"][0]
        # maxIdInPlan=10 → new workout gets id_in_plan=11
        self.assertEqual(11, entity["idInPlan"])

    def test_sync_workouts_raises_when_schedule_update_fails(self):
        client = self._logged_in_client()
        workouts = [
            {"id": 1, "scheduled_date": "2026-05-10", "title": "Easy",
             "workout_type": "easy", "duration_sec": 2700},
        ]
        fail_resp = {"result": "9999", "message": "Plan data is illegal"}
        urlopen_responses = [
            _resp(_SCHEDULE_QUERY),
            _resp(_PROGRAM_CALC),
            _resp(fail_resp),
        ]
        with patch("urllib.request.urlopen", side_effect=urlopen_responses):
            with self.assertRaises(RuntimeError) as ctx:
                client.sync_workouts("user@example.com", workouts)

        self.assertIn("schedule/update", str(ctx.exception))

    def test_sync_workouts_raises_when_not_logged_in(self):
        client = RealCorosAutomationClient()
        with self.assertRaises(RuntimeError):
            client.sync_workouts("user@example.com", [{"id": 1}])


if __name__ == "__main__":
    unittest.main()
