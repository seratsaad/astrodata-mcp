"""Schema introspection so the agent can write correct ADQL."""
from __future__ import annotations

from astropy.table import Table

from .tap import run_adql


def list_columns(endpoint: str, table_name: str) -> Table:
    """List columns of a table via TAP_SCHEMA (table_name stored unquoted)."""
    name = table_name.strip('"')
    query = (
        "SELECT column_name, datatype, unit, description "
        "FROM TAP_SCHEMA.columns "
        f"WHERE table_name = '{name}' ORDER BY column_name"
    )
    return run_adql(endpoint, query)


def list_tables(endpoint: str, like: str | None = None) -> Table:
    """List tables (optionally filtered by a name/description LIKE pattern)."""
    query = "SELECT table_name, description FROM TAP_SCHEMA.tables"
    if like:
        query += f" WHERE table_name LIKE '%{like}%' OR description LIKE '%{like}%'"
    return run_adql(endpoint, query)
