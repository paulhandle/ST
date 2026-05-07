from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import BASE_DIR, load_local_env
from scripts.probe_coros_training_hub import (
    _check_privacy_policy,
    _click_login,
    _fill_first_available,
    _redact,
    _safe_value,
)


ARTIFACT_DIR = BASE_DIR / "var" / "coros_probe"
READ_ONLY_HINTS = {
    "/account/query",
    "/dashboard/query",
    "/dashboard/detail/query",
    "/dashboard/queryCycleRecord",
    "/profile/private/query",
    "/team/user/teamlist",
    "/activity/query",
    "/activity/detail/filter",
    "/activity/fit/getImportSportList",
    "/training/schedule/query",
    "/training/schedule/querysum",
    "/training/plan/query",
}
WRITE_HINTS = {
    "/update",
    "/add",
    "/delete",
    "/copy",
    "/import",
    "/execute",
    "/quit",
    "/teamexecute",
}


def main() -> int:
    load_local_env()
    username = os.environ.get("COROS_USERNAME")
    password = os.environ.get("COROS_PASSWORD")
    training_hub_url = os.environ.get("COROS_TRAINING_HUB_URL", "https://training.coros.com")
    headless = os.environ.get("COROS_HEADLESS", "false").lower() in {"1", "true", "yes"}

    if not username or not password:
        print("Missing COROS_USERNAME or COROS_PASSWORD. Export them in the current shell for this probe only.")
        return 2

    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Missing playwright. Install with: uv pip install playwright && uv run playwright install chromium")
        return 2

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    output_path = ARTIFACT_DIR / f"api-probe-{timestamp}.json"
    screenshot_path = ARTIFACT_DIR / f"api-probe-{timestamp}.png"

    captured: dict[str, dict] = {}
    summary: dict[str, object] = {
        "timestamp": timestamp,
        "headless": headless,
        "training_hub_url": training_hub_url,
        "steps": [],
        "errors": [],
        "endpoints": captured,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        auth_token: list[str] = []  # mutable container so closure can write to it

        def on_response(response) -> None:
            url = response.url
            parsed = urlparse(url)
            if "teamcnapi.coros.com" not in parsed.netloc and "teamapi.coros.com" not in parsed.netloc:
                return
            if not _is_read_only(parsed.path):
                return
            key = parsed.path
            if key in captured:
                return
            try:
                content_type = response.headers.get("content-type", "")
                if "json" not in content_type:
                    captured[key] = {
                        "url": _redact(url, username),
                        "status": response.status,
                        "content_type": content_type,
                        "note": "non-json response skipped",
                    }
                    return
                payload = response.json()
            except Exception as exc:
                captured[key] = {
                    "url": _redact(url, username),
                    "status": response.status,
                    "error": f"{type(exc).__name__}: {exc}",
                }
                return
            captured[key] = {
                "url": _redact(url, username),
                "status": response.status,
                "shape": _shape(payload),
                "sample": _safe_sample(payload, username),
            }
            # Extract accessToken from account/query response for later direct API calls
            if not auth_token and key == "/account/query" and isinstance(payload, dict):
                token = payload.get("data", {}).get("accessToken", "")
                if token:
                    auth_token.append(token)

        page.on("response", on_response)

        try:
            cn_api_host = _login(page, training_hub_url, username, password, PlaywrightTimeoutError)
            summary["steps"].append({"name": "login", "url": page.url, "cn_api_host": cn_api_host})

            # After login, page lands on CN regional domain - navigate within it
            cn_base = f"https://{cn_api_host.replace('teamcnapi', 'trainingcn').replace('teamapi', 'training')}"
            _visit(page, "dashboard", f"{cn_base}/admin/views/dash-board", summary)
            _visit(page, "activity", f"{cn_base}/admin/views/activity", summary)
            _visit(page, "schedule", f"{cn_base}/admin/views/schedule", summary)
            _visit(page, "plan_query_page", f"{cn_base}/schedule-plan", summary)

            # Make direct API calls for endpoints not triggered by navigation
            _direct_api_calls(context, captured, cn_api_host, auth_token[0] if auth_token else "", username, summary)

            page.screenshot(path=str(screenshot_path), full_page=True)
            summary["screenshot"] = str(screenshot_path.relative_to(BASE_DIR))
            summary["final_url"] = page.url
            summary["visible_text_sample"] = _redact(page.locator("body").inner_text(timeout=5000), username)
            summary["cookie_names"] = sorted({cookie["name"] for cookie in context.cookies()})
            summary["local_storage_keys"] = page.evaluate("Object.keys(window.localStorage)")
            summary["session_storage_keys"] = page.evaluate("Object.keys(window.sessionStorage)")
        except Exception as exc:
            summary["errors"].append(f"{type(exc).__name__}: {exc}")
        finally:
            context.close()
            browser.close()

    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote API probe summary: {output_path}")
    print(f"Captured {len(captured)} read-only endpoint responses.")
    return 1 if summary["errors"] else 0


def _login(page, training_hub_url: str, username: str, password: str, timeout_error_type) -> str:
    """Login to COROS Training Hub. Returns the CN API host detected from login response."""
    page.goto(training_hub_url, wait_until="domcontentloaded", timeout=45000)
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except timeout_error_type:
        pass
    _fill_first_available(
        page,
        [
            "input[type=email]",
            "input[name=email]",
            "input[type=text]",
            "input[placeholder*=email i]",
            "input[placeholder*=account i]",
            "input[placeholder*=邮箱]",
            "input[placeholder*=账号]",
            ".el-input__inner",
        ],
        username,
    )
    _fill_first_available(
        page,
        [
            "input[type=password]",
            "input[name=password]",
            "input[placeholder*=password i]",
            "input[placeholder*=密码]",
            ".el-input__inner[type=password]",
        ],
        password,
    )
    _check_privacy_policy(page)
    with page.expect_response(lambda response: "account/login" in response.url, timeout=15000) as response_info:
        _click_login(page)
    payload = response_info.value.json()
    if not isinstance(payload, dict) or payload.get("result") != "0000":
        raise RuntimeError(f"COROS login failed: {_safe_value(payload, username)}")

    # Detect CN vs global API host from the login endpoint URL
    login_url = response_info.value.url
    if "teamcnapi" in login_url or "cn" in login_url.lower():
        return "teamcnapi.coros.com"
    # Wait a moment for redirect, then check page URL for region
    page.wait_for_timeout(2000)
    if "cn" in page.url.lower() or "trainingcn" in page.url.lower():
        return "teamcnapi.coros.com"
    return "teamapi.coros.com"


def _direct_api_calls(context, captured: dict, cn_api_host: str, access_token: str, username: str, summary: dict) -> None:
    """Make direct read-only API calls that page navigation may not trigger automatically."""
    from datetime import datetime, timedelta

    today = datetime.utcnow()
    start_date = (today - timedelta(days=90)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")

    direct_endpoints = [
        f"/activity/query?pageNumber=1&size=20",
        f"/training/schedule/query?startDate={start_date}&endDate={end_date}&supportRestExercise=1",
        f"/training/program/query",
    ]

    headers = {"accessToken": access_token} if access_token else {}
    direct_results = []
    for path in direct_endpoints:
        key = path.split("?")[0]
        if key in captured and captured[key].get("source") != "direct_api_call":
            # Already captured via navigation interception - keep it
            direct_results.append({"path": key, "note": "already_captured_via_nav"})
            continue
        url = f"https://{cn_api_host}{path}"
        try:
            response = context.request.get(url, headers=headers, timeout=15000)
            content_type = response.headers.get("content-type", "")
            if "json" in content_type:
                payload = response.json()
                api_result = payload.get("result") if isinstance(payload, dict) else "?"
                captured[key] = {
                    "url": _redact(url, username),
                    "status": response.status,
                    "shape": _shape(payload),
                    "sample": _safe_sample(payload, username),
                    "source": "direct_api_call",
                }
                direct_results.append({"path": key, "status": response.status, "result": api_result})
            else:
                captured[key] = {
                    "url": _redact(url, username),
                    "status": response.status,
                    "content_type": content_type,
                    "note": "non-json response",
                    "source": "direct_api_call",
                }
                direct_results.append({"path": key, "status": response.status, "note": "non-json"})
        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {exc}"
            captured[key] = {"url": _redact(url, username), "error": err_msg, "source": "direct_api_call"}
            direct_results.append({"path": key, "error": err_msg})

    summary["direct_api_calls"] = direct_results
    summary["had_access_token"] = bool(access_token)


def _visit(page, name: str, url: str, summary: dict[str, object]) -> None:
    try:
        page.goto(url, wait_until="commit", timeout=45000)
    except Exception as exc:
        summary["steps"].append({"name": name, "url": page.url, "warning": f"{type(exc).__name__}: {exc}"})
    page.wait_for_timeout(6000)
    summary["steps"].append({"name": name, "url": page.url, "title": page.title()})


def _is_read_only(path: str) -> bool:
    if any(hint in path for hint in WRITE_HINTS):
        return False
    if any(hint == path or hint in path for hint in READ_ONLY_HINTS):
        return True
    return path.endswith("/query") or path.endswith("/filter") or path.endswith("/querysum")


def _shape(value: object, depth: int = 0, max_keys: int = 60) -> object:
    if depth >= 4:
        return type(value).__name__
    if isinstance(value, dict):
        return {str(key): _shape(item, depth + 1, max_keys) for key, item in list(value.items())[:max_keys]}
    if isinstance(value, list):
        if not value:
            return []
        return [{"length": len(value), "item": _shape(value[0], depth + 1, max_keys)}]
    return type(value).__name__


def _safe_sample(value: object, username: str) -> object:
    return _truncate(_safe_value(value, username))


def _truncate(value: object, depth: int = 0) -> object:
    if depth >= 5:
        return f"[{type(value).__name__}]"
    if isinstance(value, dict):
        return {str(key): _truncate(item, depth + 1) for key, item in list(value.items())[:20]}
    if isinstance(value, list):
        return [_truncate(item, depth + 1) for item in value[:2]]
    if isinstance(value, str):
        return value[:240]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
