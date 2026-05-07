from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

from app.core.config import BASE_DIR, load_local_env


ARTIFACT_DIR = BASE_DIR / "var" / "coros_probe"


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
    summary_path = ARTIFACT_DIR / f"summary-{timestamp}.json"
    screenshot_path = ARTIFACT_DIR / f"post-login-{timestamp}.png"
    pre_login_screenshot_path = ARTIFACT_DIR / f"pre-login-{timestamp}.png"
    html_path = ARTIFACT_DIR / f"page-{timestamp}.html"

    summary: dict[str, object] = {
        "timestamp": timestamp,
        "training_hub_url": training_hub_url,
        "username_present": bool(username),
        "headless": headless,
        "steps": [],
        "errors": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        request_urls: list[str] = []
        response_urls: list[dict[str, object]] = []
        console_messages: list[str] = []
        page_errors: list[str] = []
        page.on("request", lambda request: _append_request(request_urls, request.url))
        page.on("response", lambda response: _append_response(response_urls, response.url, response.status))
        page.on("console", lambda message: _append_console(console_messages, message.type, message.text))
        page.on("pageerror", lambda exc: _append_page_error(page_errors, str(exc)))
        try:
            page.goto(training_hub_url, wait_until="domcontentloaded", timeout=45000)
            summary["steps"].append({"name": "goto", "url": page.url, "title": page.title()})
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except PlaywrightTimeoutError:
                summary["errors"].append("networkidle timeout before login form probe")
            page.screenshot(path=str(pre_login_screenshot_path), full_page=True)
            html_path.write_text(_redact(page.content(), username), encoding="utf-8")
            summary["pre_login_screenshot"] = str(pre_login_screenshot_path.relative_to(BASE_DIR))
            summary["page_html"] = str(html_path.relative_to(BASE_DIR))
            summary["pre_login_inputs"] = _collect_inputs(page)
            summary["pre_login_buttons"] = _collect_texts(page, "button", username)
            summary["pre_login_text_sample"] = _redact(page.locator("body").inner_text(timeout=5000), username)

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
            try:
                with page.expect_response(lambda response: "account/login" in response.url, timeout=15000) as response_info:
                    _click_login(page)
                summary["steps"].append({"name": "submitted_login"})
                login_response_holder = _safe_login_response(response_info.value, username)
            except PlaywrightTimeoutError:
                _click_login(page)
                summary["steps"].append({"name": "submitted_login"})
                login_response_holder = {"error": "Timed out waiting for account/login response"}
            summary["login_response"] = login_response_holder
            if _login_succeeded(login_response_holder):
                dashboard_url = f"{training_hub_url.rstrip('/')}/admin/views/dash-board"
                try:
                    page.goto(dashboard_url, wait_until="commit", timeout=45000)
                except Exception as exc:
                    summary["warnings"] = [*summary.get("warnings", []), f"dashboard navigation warning: {type(exc).__name__}: {exc}"]
                _wait_for_dashboard_shell(page, summary)
                summary["steps"].append({"name": "goto_dashboard", "url": page.url, "title": page.title()})

            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                summary["errors"].append("networkidle timeout after login submit")
            page.wait_for_timeout(3000)

            page.screenshot(path=str(screenshot_path), full_page=True)
            summary["post_login_url"] = page.url
            summary["post_login_title"] = page.title()
            summary["screenshot"] = str(screenshot_path.relative_to(BASE_DIR))
            summary["visible_text_sample"] = _redact(page.locator("body").inner_text(timeout=5000), username)
            summary["links"] = _collect_links(page, username)
            summary["buttons"] = _collect_texts(page, "button", username)
            summary["inputs"] = _collect_inputs(page)
            summary["local_storage_keys"] = page.evaluate("Object.keys(window.localStorage)")
            summary["session_storage_keys"] = page.evaluate("Object.keys(window.sessionStorage)")
            summary["cookie_names"] = sorted({cookie["name"] for cookie in context.cookies()})
            summary["console_messages"] = console_messages[-80:]
            summary["page_errors"] = page_errors[-40:]
            summary["request_urls"] = _redact_urls(request_urls, username)
            summary["response_urls"] = _redact_response_urls(response_urls, username)
        except Exception as exc:
            summary["errors"].append(f"{type(exc).__name__}: {exc}")
            try:
                page.screenshot(path=str(screenshot_path), full_page=True)
                summary["post_login_url"] = page.url
                summary["post_login_title"] = page.title()
                summary["screenshot"] = str(screenshot_path.relative_to(BASE_DIR))
                summary["visible_text_sample"] = _redact(page.locator("body").inner_text(timeout=5000), username)
                summary["links"] = _collect_links(page, username)
                summary["buttons"] = _collect_texts(page, "button", username)
                summary["inputs"] = _collect_inputs(page)
                summary["local_storage_keys"] = page.evaluate("Object.keys(window.localStorage)")
                summary["session_storage_keys"] = page.evaluate("Object.keys(window.sessionStorage)")
                summary["cookie_names"] = sorted({cookie["name"] for cookie in context.cookies()})
                summary["console_messages"] = console_messages[-80:]
                summary["page_errors"] = page_errors[-40:]
                summary["request_urls"] = _redact_urls(request_urls, username)
                summary["response_urls"] = _redact_response_urls(response_urls, username)
            except Exception as artifact_exc:
                summary["errors"].append(f"artifact capture failed: {type(artifact_exc).__name__}: {artifact_exc}")
        finally:
            context.close()
            browser.close()

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote probe summary: {summary_path}")
    if summary.get("errors"):
        print("Probe completed with errors. Inspect the summary and screenshot under var/coros_probe/.")
        return 1
    print("Probe completed. Inspect summary and screenshot under var/coros_probe/.")
    return 0


def _fill_first_available(page, selectors: list[str], value: str) -> None:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.count() and locator.is_visible(timeout=1500):
                locator.fill(value)
                return
        except Exception:
            continue
    raise RuntimeError(f"Could not find input for selectors: {selectors}")


def _click_first_available(page, selectors: list[str]) -> None:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if locator.count() and locator.is_visible(timeout=1500):
                locator.click()
                return
        except Exception:
            continue
    raise RuntimeError(f"Could not find clickable login control for selectors: {selectors}")


def _click_login(page) -> None:
    _click_first_available(
        page,
        [
            "button[type=submit]",
            "button:has-text('Log in')",
            "button:has-text('Login')",
            "button:has-text('登录')",
            "text=Log in",
            "text=Login",
            "text=登录",
        ],
    )


def _wait_for_dashboard_shell(page, summary: dict[str, object]) -> None:
    wait_results: list[str] = []
    for timeout_ms in [5000, 10000, 15000]:
        page.wait_for_timeout(timeout_ms)
        try:
            body_text = page.locator("body").inner_text(timeout=1500).strip()
        except Exception as exc:
            wait_results.append(f"body_text_error:{type(exc).__name__}")
            body_text = ""
        if body_text:
            wait_results.append(f"body_text_len:{len(body_text)}")
            break
        wait_results.append(f"empty_after_ms:{timeout_ms}")
    summary["dashboard_wait"] = wait_results


def _check_privacy_policy(page) -> None:
    text_locator = page.locator("text=我已阅读并同意").first
    try:
        if text_locator.count():
            text_locator.click(timeout=1500, force=True)
            return
    except Exception:
        pass

    checkbox = page.locator("input[type=checkbox]")
    count = checkbox.count()
    if count:
        checkbox.nth(count - 1).check(force=True)
        return

    wrapper = page.locator(".el-checkbox")
    count = wrapper.count()
    if count:
        wrapper.nth(count - 1).click(force=True)
        return


def _collect_links(page, username: str) -> list[dict[str, str]]:
    links = []
    for item in page.locator("a").all()[:80]:
        try:
            links.append(
                {
                    "text": _redact(item.inner_text(timeout=500), username)[:120],
                    "href": item.get_attribute("href") or "",
                }
            )
        except Exception:
            continue
    return links


def _collect_texts(page, selector: str, username: str) -> list[str]:
    values = []
    for item in page.locator(selector).all()[:80]:
        try:
            text = _redact(item.inner_text(timeout=500), username).strip()
            if text:
                values.append(text[:120])
        except Exception:
            continue
    return values


def _collect_inputs(page) -> list[dict[str, str | None]]:
    values = []
    for item in page.locator("input").all()[:80]:
        try:
            values.append(
                {
                    "type": item.get_attribute("type"),
                    "name": item.get_attribute("name"),
                    "placeholder": item.get_attribute("placeholder"),
                    "autocomplete": item.get_attribute("autocomplete"),
                }
            )
        except Exception:
            continue
    return values


def _redact(value: str, username: str) -> str:
    redacted = value.replace(username, "[COROS_USERNAME]")
    local_part = username.split("@", 1)[0]
    if local_part:
        redacted = redacted.replace(local_part, "[COROS_USER]")
    redacted = re.sub(r"\b[\w.+-]+@[\w.-]+\.\w+\b", "[email]", redacted)
    redacted = re.sub(r"\+?\d[\d -]{7,}\d", "[number]", redacted)
    return redacted[:5000]


def _append_request(request_urls: list[str], url: str) -> None:
    if len(request_urls) < 400:
        request_urls.append(url)


def _append_response(response_urls: list[dict[str, object]], url: str, status: int) -> None:
    if len(response_urls) < 400:
        response_urls.append({"url": url, "status": status})


def _append_console(console_messages: list[str], message_type: str, text: str) -> None:
    if len(console_messages) < 400:
        console_messages.append(f"{message_type}: {text[:500]}")


def _append_page_error(page_errors: list[str], text: str) -> None:
    if len(page_errors) < 200:
        page_errors.append(text[:1000])


def _redact_urls(urls: list[str], username: str) -> list[str]:
    return [_redact(url, username) for url in urls]


def _redact_response_urls(items: list[dict[str, object]], username: str) -> list[dict[str, object]]:
    return [{"url": _redact(str(item["url"]), username), "status": item["status"]} for item in items]


def _safe_login_response(response, username: str) -> dict[str, object]:
    info: dict[str, object] = {
        "url": _redact(response.url, username),
        "status": response.status,
        "ok": response.ok,
        "headers": {
            key: value
            for key, value in response.headers.items()
            if key.lower() in {"content-type", "cache-control"}
        },
    }
    try:
        payload = response.json()
    except Exception:
        try:
            text = response.text()
        except Exception:
            text = ""
        info["body_sample"] = _redact(text, username)[:500]
        return info

    if isinstance(payload, dict):
        info["json"] = _safe_value(payload, username)
    else:
        info["json_type"] = type(payload).__name__
    return info


def _summarize_value(value: object, username: str) -> object:
    if isinstance(value, str):
        return _redact(value, username)[:200]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return f"[{type(value).__name__}]"


def _safe_value(value: object, username: str, key: str = "") -> object:
    lowered = key.lower()
    sensitive_fragments = {
        "token",
        "secret",
        "password",
        "session",
        "cookie",
        "mobile",
        "phone",
        "email",
        "birthday",
        "birth",
        "weight",
        "stature",
        "nickname",
        "userid",
        "user_id",
        "profile",
    }
    if any(fragment in lowered for fragment in sensitive_fragments):
        return "[redacted]"
    if isinstance(value, dict):
        return {str(item_key): _safe_value(item_value, username, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return f"[list:{len(value)}]"
    if isinstance(value, str):
        return _redact(value, username)[:200]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return f"[{type(value).__name__}]"


def _login_succeeded(login_response: dict[str, object]) -> bool:
    payload = login_response.get("json")
    return isinstance(payload, dict) and payload.get("result") == "0000"


if __name__ == "__main__":
    raise SystemExit(main())
