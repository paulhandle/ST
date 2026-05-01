from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.request import urlopen

from app.core.config import BASE_DIR


ARTIFACT_DIR = BASE_DIR / "var" / "coros_probe"
KEYWORDS = [
    "activity",
    "workout",
    "calendar",
    "training",
    "dashboard",
    "plan",
    "schedule",
    "sport",
    "record",
    "statistic",
    "fitness",
    "fatigue",
    "running",
    "race",
]


def main() -> int:
    summaries = sorted(ARTIFACT_DIR.glob("summary-*.json"))
    if not summaries:
        print("No probe summaries found under var/coros_probe/. Run probe first.")
        return 2

    urls = _bundle_urls(summaries[-5:])
    if not urls:
        print("No bundle URLs found in probe summaries.")
        return 2

    results: dict[str, list[str]] = {}
    for url in urls:
        if "/public/" not in url or not url.endswith(".js"):
            continue
        try:
            text = urlopen(url, timeout=30).read().decode("utf-8", errors="ignore")
        except Exception as exc:
            results[url] = [f"fetch_error:{type(exc).__name__}:{exc}"]
            continue
        matches = sorted(set(_interesting_strings(text)))
        if matches:
            results[url] = matches[:300]

    output_path = ARTIFACT_DIR / "bundle-analysis.json"
    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote bundle analysis: {output_path}")
    print(f"Analyzed {len(urls)} bundle URLs, found {len(results)} bundles with matches/errors.")
    return 0


def _bundle_urls(paths: list[Path]) -> list[str]:
    urls: set[str] = set()
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ["request_urls", "response_urls"]:
            for item in data.get(key, []):
                url = item["url"] if isinstance(item, dict) else item
                if isinstance(url, str) and (url.startswith("https://static") or url.startswith("https://training")):
                    urls.add(url)
    return sorted(urls)


def _interesting_strings(text: str) -> list[str]:
    strings = re.findall(r"""['"`]([^'"`]{3,180})['"`]""", text)
    matches = []
    for value in strings:
        lowered = value.lower()
        if any(keyword in lowered for keyword in KEYWORDS):
            if any(secret in lowered for secret in ["token", "password", "secret"]):
                continue
            matches.append(value)
        elif value.startswith("/") and any(keyword in lowered for keyword in KEYWORDS):
            matches.append(value)
    return matches


if __name__ == "__main__":
    raise SystemExit(main())
