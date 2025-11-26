"""Phase V: Schema & Migration Layer (opt-in, read-only by default)."""

from .schema_versions import get_schema_info, SCHEMAS, SchemaVersionInfo
from .migration_plans import build_migration_plan, MigrationPlan, MigrationStep
from .migration_runner import detect_current_versions, plan_migrations, apply_migrations
from .migration_reporter import write_plan_report, write_apply_report

__all__ = [
    "get_schema_info",
    "SCHEMAS",
    "SchemaVersionInfo",
    "build_migration_plan",
    "MigrationPlan",
    "MigrationStep",
    "detect_current_versions",
    "plan_migrations",
    "apply_migrations",
    "write_plan_report",
    "write_apply_report",
]
