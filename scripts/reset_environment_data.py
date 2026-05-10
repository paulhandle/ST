from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import DATABASE_URL
from app.db import Base
from app.seed import seed_training_methods

# Global seed/config tables that should survive an environment reset.
PRESERVED_TABLES = {"training_methods"}


@dataclass(frozen=True)
class ResetResult:
    database_url: str
    dry_run: bool
    preserved_tables: dict[str, int]
    target_tables: dict[str, int]
    deleted_tables: dict[str, int]

    @property
    def target_total(self) -> int:
        return sum(self.target_tables.values())

    @property
    def deleted_total(self) -> int:
        return sum(self.deleted_tables.values())

    def as_dict(self) -> dict[str, Any]:
        return {
            "database_url": redact_database_url(self.database_url),
            "dry_run": self.dry_run,
            "target_total": self.target_total,
            "deleted_total": self.deleted_total,
            "preserved_tables": self.preserved_tables,
            "target_tables": self.target_tables,
            "deleted_tables": self.deleted_tables,
        }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset PerformanceProtocol environment data while preserving global seed tables."
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL") or os.environ.get("ST_DATABASE_URL") or DATABASE_URL,
        help="Database URL to reset. Defaults to DATABASE_URL/ST_DATABASE_URL/app default.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete rows. Without this flag the command only prints a dry-run report.",
    )
    parser.add_argument(
        "--confirm-reset",
        action="store_true",
        help="Required together with --execute to guard destructive environment resets.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    if args.execute and not args.confirm_reset:
        print("Refusing to reset data: pass both --execute and --confirm-reset.")
        return 2

    result = reset_environment_data(
        args.database_url,
        execute=args.execute,
        confirm_reset=args.confirm_reset,
    )
    if args.json:
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True))
    else:
        print(format_result(result))
    return 0


def reset_environment_data(database_url: str, *, execute: bool, confirm_reset: bool = False) -> ResetResult:
    if execute and not confirm_reset:
        raise ValueError("execute requires confirm_reset=True")

    engine = _create_engine(database_url)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    existing_tables = set(inspect(engine).get_table_names())

    # Importing app.models registers every ORM table on Base.metadata. The import
    # is intentionally local so tests can construct temporary databases first.
    import app.models  # noqa: F401

    ordered_tables = [table for table in Base.metadata.sorted_tables if table.name in existing_tables]
    preserved_tables = {
        table.name: _count_rows(engine, table)
        for table in ordered_tables
        if table.name in PRESERVED_TABLES
    }
    target_tables = {
        table.name: _count_rows(engine, table)
        for table in reversed(ordered_tables)
        if table.name not in PRESERVED_TABLES
    }

    deleted_tables: dict[str, int] = {}
    if execute:
        with session_factory() as db:
            deleted_tables = _delete_target_tables(db, ordered_tables, target_tables)
            db.commit()
            seed_training_methods(db)

    return ResetResult(
        database_url=database_url,
        dry_run=not execute,
        preserved_tables=preserved_tables,
        target_tables=target_tables,
        deleted_tables=deleted_tables,
    )


def _delete_target_tables(db: Session, ordered_tables: list[Any], target_counts: dict[str, int]) -> dict[str, int]:
    if db.bind and db.bind.dialect.name == "postgresql":
        target_names = [table.name for table in ordered_tables if table.name not in PRESERVED_TABLES]
        if target_names:
            preparer = db.bind.dialect.identifier_preparer
            table_list = ", ".join(preparer.quote(name) for name in target_names)
            db.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE"))
        return dict(target_counts)

    deleted: dict[str, int] = {}
    for table in reversed(ordered_tables):
        if table.name in PRESERVED_TABLES:
            continue
        result = db.execute(table.delete())
        deleted[table.name] = int(result.rowcount or 0)
    if db.bind and db.bind.dialect.name == "sqlite":
        _reset_sqlite_sequences(db, deleted)
    return deleted


def _reset_sqlite_sequences(db: Session, deleted: dict[str, int]) -> None:
    has_sequence = db.execute(text(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
    )).first()
    if not has_sequence:
        return
    for table_name in deleted:
        db.execute(text("DELETE FROM sqlite_sequence WHERE name = :name"), {"name": table_name})


def _count_rows(engine: Engine, table: Any) -> int:
    with engine.connect() as conn:
        return int(conn.execute(select(func.count()).select_from(table)).scalar_one())


def _create_engine(database_url: str) -> Engine:
    engine_kwargs: dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    else:
        engine_kwargs["pool_pre_ping"] = True
    return create_engine(database_url, **engine_kwargs)


def redact_database_url(database_url: str) -> str:
    if "@" not in database_url or "://" not in database_url:
        return database_url
    scheme, rest = database_url.split("://", 1)
    if "@" not in rest:
        return database_url
    _credentials, host_part = rest.rsplit("@", 1)
    return f"{scheme}://***:***@{host_part}"


def format_result(result: ResetResult) -> str:
    mode = "DRY RUN" if result.dry_run else "EXECUTED"
    lines = [
        f"Environment reset {mode}",
        f"Database: {redact_database_url(result.database_url)}",
        f"Rows targeted: {result.target_total}",
    ]

    if result.preserved_tables:
        lines.append("")
        lines.append("Preserved tables:")
        for name, count in sorted(result.preserved_tables.items()):
            lines.append(f"  {name}: {count}")

    lines.append("")
    lines.append("Target tables:")
    for name, count in result.target_tables.items():
        lines.append(f"  {name}: {count}")

    if result.deleted_tables:
        lines.append("")
        lines.append(f"Deleted rows: {result.deleted_total}")
        for name, count in result.deleted_tables.items():
            lines.append(f"  {name}: {count}")

    if result.dry_run:
        lines.append("")
        lines.append("No rows were deleted. Re-run with --execute --confirm-reset to reset this environment.")

    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
