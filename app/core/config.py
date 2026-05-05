from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _resolve_database_url() -> str:
    raw = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("ST_DATABASE_URL")
        or f"sqlite:///{BASE_DIR / 'st.db'}"
    )
    if raw.startswith("postgres://"):
        return "postgresql+psycopg://" + raw[len("postgres://"):]
    if raw.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw[len("postgresql://"):]
    return raw


DATABASE_URL = _resolve_database_url()


SMS_PROVIDER = os.environ.get("SMS_PROVIDER", "mock").strip().lower() or "mock"
SMS_MOCK_RETURN_CODE = os.environ.get("SMS_MOCK_RETURN_CODE", "true").strip().lower() not in {
    "0",
    "false",
    "no",
    "off",
}
SMS_API_KEY = os.environ.get("SMS_API_KEY", "")
SMS_API_SECRET = os.environ.get("SMS_API_SECRET", "")
SMS_SENDER_ID = os.environ.get("SMS_SENDER_ID", "PerformanceProtocol")


def sms_provider_name() -> str:
    return os.environ.get("SMS_PROVIDER", SMS_PROVIDER).strip().lower() or "mock"


def sms_mock_return_code() -> bool:
    raw = os.environ.get("SMS_MOCK_RETURN_CODE")
    if raw is None:
        return SMS_MOCK_RETURN_CODE
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def load_local_env(path: Path | None = None) -> None:
    env_path = path or BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_local_env()
