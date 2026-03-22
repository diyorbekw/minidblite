"""
database.py — Core Database class for minidblite.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from .formatter import QueryResult
from .utils import (
    build_error,
    build_success,
    python_type_to_sql,
    validate_identifier,
)

logger = logging.getLogger("minidblite")


class Database:
    """
    A lightweight, beginner-friendly SQLite wrapper.

    Provides a simple Pythonic API for common database operations
    without requiring any knowledge of SQL.

    Args:
        db_name: Path/filename of the SQLite database file.
                 Use ``":memory:"`` for an in-memory database.

    Example::

        db = Database("my_app.db")
        db.new_table("users")
        db.new_column("name", str)
        db.new_column("age", int)
        db.add("users", name="Ali", age=20)
        result = db.get("users")
        result.decorate()
    """

    def __init__(self, db_name: str = "database_session.db") -> None:
        self.db_name = db_name
        self._connection: sqlite3.Connection | None = None
        self._cursor: sqlite3.Cursor | None = None
        self._last_table: str | None = None
        self._connect()

    def _connect(self) -> None:
        """Open (or create) the SQLite database file and store connection."""
        try:
            self._connection = sqlite3.connect(self.db_name)
            self._connection.row_factory = sqlite3.Row
            self._cursor = self._connection.cursor()
            self._cursor.execute("PRAGMA foreign_keys = ON")
            self._cursor.execute("PRAGMA journal_mode = WAL")
            self._connection.commit()
            logger.info("Connected to database: %s", self.db_name)
        except sqlite3.Error as exc:
            logger.error("Failed to connect to database: %s", exc)
            raise

    def close(self) -> dict:
        """
        Close the database connection.

        Returns:
            Structured success/error dict.
        """
        try:
            if self._connection:
                self._connection.close()
                self._connection = None
                self._cursor = None
                logger.info("Database connection closed.")
            return build_success("Database connection closed.")
        except sqlite3.Error as exc:
            logger.error("Error closing connection: %s", exc)
            return build_error("Failed to close connection.", exc)

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @property
    def _conn(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("Database connection is closed.")
        return self._connection

    @property
    def _cur(self) -> sqlite3.Cursor:
        if self._cursor is None:
            raise RuntimeError("Database connection is closed.")
        return self._cursor

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute SQL with auto-commit and error propagation."""
        cursor = self._cur.execute(sql, params)
        self._conn.commit()
        return cursor

    def _validate_name(self, name: str, kind: str = "identifier") -> None:
        """Raise ValueError for unsafe identifiers."""
        if not validate_identifier(name):
            raise ValueError(
                f"Invalid {kind} name '{name}'. "
                "Use only letters, digits, and underscores, "
                "and start with a letter or underscore."
            )

    def _table_exists(self, table_name: str) -> bool:
        """Return True if the table exists in the database."""
        row = self._cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        return row is not None

    def _column_exists(self, table_name: str, column_name: str) -> bool:
        """Return True if column_name exists in table_name."""
        columns = self._get_columns(table_name)
        return column_name in columns

    def _get_columns(self, table_name: str) -> list[str]:
        """Return a list of column names for a table."""
        rows = self._cur.execute(
            f"PRAGMA table_info({table_name})" 
        ).fetchall()
        return [row[1] for row in rows]

    def new_table(self, table_name: str) -> dict:
        """
        Create a new table with an auto-increment primary key.

        If the table already exists the operation is a no-op (no error).

        Args:
            table_name: Name of the table to create.

        Returns:
            Structured success/error dict.

        Example::

            db.new_table("products")
        """
        try:
            self._validate_name(table_name, "table")
            sql = (
                f"CREATE TABLE IF NOT EXISTS {table_name} "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT)"
            )
            self._execute(sql)
            self._last_table = table_name
            msg = f"Table '{table_name}' created (or already exists)."
            logger.info(msg)
            return build_success(msg, {"table": table_name})
        except (ValueError, sqlite3.Error) as exc:
            msg = f"Failed to create table '{table_name}': {exc}"
            logger.error(msg)
            return build_error(msg, exc)

    def drop_table(self, table_name: str) -> dict:
        """
        Drop a table entirely.

        Args:
            table_name: Name of the table to drop.

        Returns:
            Structured success/error dict.
        """
        try:
            self._validate_name(table_name, "table")
            if not self._table_exists(table_name):
                msg = f"Table '{table_name}' does not exist."
                logger.warning(msg)
                return build_error(msg)
            self._execute(f"DROP TABLE {table_name}")
            if self._last_table == table_name:
                self._last_table = None
            msg = f"Table '{table_name}' dropped."
            logger.info(msg)
            return build_success(msg)
        except (ValueError, sqlite3.Error) as exc:
            msg = f"Failed to drop table '{table_name}': {exc}"
            logger.error(msg)
            return build_error(msg, exc)

    def list_tables(self) -> list[str]:
        """
        Return a list of all user-created table names.

        Returns:
            List of table name strings.
        """
        rows = self._cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        return [row[0] for row in rows]

    def new_column(
        self,
        column_name: str,
        data_type: type,
        table_name: str | None = None,
    ) -> dict:
        """
        Add a column to an existing table.

        Uses the most-recently created table when ``table_name`` is omitted.

        Args:
            column_name: Name for the new column.
            data_type: Python type — ``int``, ``str``, or ``float``.
            table_name: Target table. Defaults to the last table created
                        via :meth:`new_table`.

        Returns:
            Structured success/error dict.

        Example::

            db.new_table("users")
            db.new_column("email", str)
            db.new_column("score", float, table_name="users")
        """
        target = table_name or self._last_table
        try:
            if target is None:
                raise ValueError(
                    "No table context set. "
                    "Call new_table() first or pass table_name explicitly."
                )
            self._validate_name(column_name, "column")
            self._validate_name(target, "table")

            if not self._table_exists(target):
                raise ValueError(f"Table '{target}' does not exist.")

            if self._column_exists(target, column_name):
                msg = (
                    f"Column '{column_name}' already exists in '{target}'. "
                    "Skipping."
                )
                logger.warning(msg)
                return build_success(msg, {"column": column_name, "table": target})

            sql_type = python_type_to_sql(data_type)
            self._execute(
                f"ALTER TABLE {target} ADD COLUMN {column_name} {sql_type}"
            )
            msg = f"Column '{column_name}' ({sql_type}) added to '{target}'."
            logger.info(msg)
            return build_success(msg, {"column": column_name, "type": sql_type, "table": target})
        except (ValueError, TypeError, sqlite3.Error) as exc:
            msg = f"Failed to add column '{column_name}': {exc}"
            logger.error(msg)
            return build_error(msg, exc)

    def add(self, table_name: str, **columns: Any) -> dict:
        """
        Insert a new row into a table.

        Args:
            table_name: Target table.
            **columns: Column-name / value pairs.

        Returns:
            Structured success/error dict with the new row ``id``.

        Example::

            db.add("users", name="Ali", age=20)
        """
        try:
            self._validate_name(table_name, "table")
            if not self._table_exists(table_name):
                raise ValueError(f"Table '{table_name}' does not exist.")
            if not columns:
                raise ValueError("Provide at least one column=value pair.")

            for col in columns:
                self._validate_name(col, "column")

            col_names = ", ".join(columns.keys())
            placeholders = ", ".join("?" * len(columns))
            sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
            cursor = self._execute(sql, tuple(columns.values()))

            msg = f"Row inserted into '{table_name}' (id={cursor.lastrowid})."
            logger.info(msg)
            return build_success(msg, {"id": cursor.lastrowid})
        except (ValueError, sqlite3.Error) as exc:
            msg = f"Failed to insert into '{table_name}': {exc}"
            logger.error(msg)
            return build_error(msg, exc)

    def get(self, table_name: str, **filters: Any) -> QueryResult:
        """
        Retrieve rows from a table, optionally filtered.

        Args:
            table_name: Target table.
            **filters: Optional column=value filters (AND-joined).

        Returns:
            :class:`~minidblite.formatter.QueryResult` — iterable result object.

        Example::

            all_users  = db.get("users")
            found_user = db.get("users", name="Ali")
            found_user.decorate()
        """
        try:
            self._validate_name(table_name, "table")
            if not self._table_exists(table_name):
                logger.error("Table '%s' does not exist.", table_name)
                return QueryResult([], [])

            if filters:
                for col in filters:
                    self._validate_name(col, "column")
                where = " AND ".join(f"{col} = ?" for col in filters)
                sql = f"SELECT * FROM {table_name} WHERE {where}"
                rows = self._cur.execute(sql, tuple(filters.values())).fetchall()
            else:
                sql = f"SELECT * FROM {table_name}"
                rows = self._cur.execute(sql).fetchall()

            columns = self._get_columns(table_name)
            raw = [tuple(row) for row in rows]
            logger.info("Fetched %d row(s) from '%s'.", len(raw), table_name)
            return QueryResult(raw, columns)
        except (ValueError, sqlite3.Error) as exc:
            logger.error("Failed to get from '%s': %s", table_name, exc)
            return QueryResult([], [])

    def update(self, table_name: str, row_id: int, **new_values: Any) -> dict:
        """
        Update columns of an existing row identified by its ``id``.

        Args:
            table_name: Target table.
            row_id: The ``id`` of the row to update.
            **new_values: Column=value pairs to apply.

        Returns:
            Structured success/error dict.

        Example::

            db.update("users", row_id=1, name="Vali", age=25)
        """
        try:
            self._validate_name(table_name, "table")
            if not self._table_exists(table_name):
                raise ValueError(f"Table '{table_name}' does not exist.")
            if not new_values:
                raise ValueError("Provide at least one column=value pair to update.")
            if not isinstance(row_id, int) or row_id < 1:
                raise ValueError("row_id must be a positive integer.")

            for col in new_values:
                self._validate_name(col, "column")

            set_clause = ", ".join(f"{col} = ?" for col in new_values)
            sql = f"UPDATE {table_name} SET {set_clause} WHERE id = ?"
            cursor = self._execute(sql, (*new_values.values(), row_id))

            if cursor.rowcount == 0:
                msg = f"No row with id={row_id} found in '{table_name}'."
                logger.warning(msg)
                return build_error(msg)

            msg = f"Row id={row_id} in '{table_name}' updated."
            logger.info(msg)
            return build_success(msg, {"id": row_id, "updated": new_values})
        except (ValueError, sqlite3.Error) as exc:
            msg = f"Failed to update '{table_name}': {exc}"
            logger.error(msg)
            return build_error(msg, exc)

    def delete(
        self,
        table_name: str,
        is_all: bool = False,
        **filters: Any,
    ) -> dict:
        """
        Delete rows from a table.

        * With **filters** and ``is_all=False`` → delete only the first match.
        * With **filters** and ``is_all=True`` → delete every match.
        * With **no filters** and ``is_all=True`` → truncate the whole table.
        * With **no filters** and ``is_all=False`` → warning, nothing deleted.

        Args:
            table_name: Target table.
            is_all: When ``True`` delete all matching rows; when ``False``
                    delete only the first match (by lowest ``id``).
            **filters: Optional column=value conditions.

        Returns:
            Structured success/error dict with ``deleted_count``.

        Example::

            db.delete("users", name="Ali")          # first match only
            db.delete("users", is_all=True, age=20) # all matches
            db.delete("users", is_all=True)         # delete EVERYTHING
        """
        try:
            self._validate_name(table_name, "table")
            if not self._table_exists(table_name):
                raise ValueError(f"Table '{table_name}' does not exist.")

            if not filters and not is_all:
                msg = (
                    "No filters provided and is_all=False. "
                    "Pass is_all=True to delete all rows, "
                    "or provide filter conditions."
                )
                logger.warning(msg)
                return build_error(msg)

            for col in filters:
                self._validate_name(col, "column")

            if filters:
                where = " AND ".join(f"{col} = ?" for col in filters)
                params = tuple(filters.values())
                if is_all:
                    sql = f"DELETE FROM {table_name} WHERE {where}"
                    cursor = self._execute(sql, params)
                else:
                    subquery = (
                        f"DELETE FROM {table_name} WHERE id = "
                        f"(SELECT id FROM {table_name} WHERE {where} "
                        f"ORDER BY id LIMIT 1)"
                    )
                    cursor = self._execute(subquery, (*params, *params))
            else:
                cursor = self._execute(f"DELETE FROM {table_name}")

            count = cursor.rowcount
            msg = f"Deleted {count} row(s) from '{table_name}'."
            logger.info(msg)
            return build_success(msg, {"deleted_count": count})
        except (ValueError, sqlite3.Error) as exc:
            msg = f"Failed to delete from '{table_name}': {exc}"
            logger.error(msg)
            return build_error(msg, exc)


    def schema(self, table_name: str) -> dict:
        """
        Return column metadata for a table.

        Args:
            table_name: Name of the table to inspect.

        Returns:
            Dict with ``columns`` list (name, type, nullable, default, pk).
        """
        try:
            self._validate_name(table_name, "table")
            if not self._table_exists(table_name):
                raise ValueError(f"Table '{table_name}' does not exist.")
            rows = self._cur.execute(
                f"PRAGMA table_info({table_name})"
            ).fetchall()
            cols = [
                {
                    "name": r[1],
                    "type": r[2],
                    "nullable": not r[3],
                    "default": r[4],
                    "primary_key": bool(r[5]),
                }
                for r in rows
            ]
            return build_success(f"Schema for '{table_name}'.", {"columns": cols})
        except (ValueError, sqlite3.Error) as exc:
            return build_error(str(exc), exc)

    def export_json(self, table_name: str, path: str | None = None) -> dict:
        """
        Export a table to a JSON file (or return the JSON string).

        Args:
            table_name: Table to export.
            path: Optional file path to write JSON to. If ``None`` the JSON
                  string is returned in the result dict.

        Returns:
            Structured success/error dict.
        """
        try:
            result = self.get(table_name)
            json_str = result.to_json()
            if path:
                Path(path).write_text(json_str, encoding="utf-8")
                msg = f"Table '{table_name}' exported to '{path}'."
            else:
                msg = f"Table '{table_name}' serialised to JSON."
            logger.info(msg)
            return build_success(msg, json_str)
        except (ValueError, OSError) as exc:
            return build_error(str(exc), exc)

    def __repr__(self) -> str:
        tables = self.list_tables()
        return f"Database(name={self.db_name!r}, tables={tables})"